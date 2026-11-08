"""
Minimal FastAPI-compatible layer on top of Starlette.

Only used when the `fastapi` package is not importable (see `app/compat.py`).
It implements the subset of FastAPI conventions this project relies on:

* `FastAPI()` / `APIRouter()` with `.get/.post/.put/.patch/.delete`
* path parameters, typed query parameters, Pydantic request bodies
* `Depends()` (including generator dependencies with `yield`, per-request cache)
* `UploadFile = File(...)`, `Form(...)`
* `HTTPException`, 422 validation errors in FastAPI's `{"detail": [...]}` shape
* automatic JSON serialisation of dicts / lists / Pydantic models

It is intentionally small and readable; it is not a full re-implementation.
"""
from __future__ import annotations

import inspect
import typing as t
from datetime import date, datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ValidationError
from starlette import status  # noqa: F401  (re-exported)
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile  # noqa: F401  (re-exported)
from starlette.middleware.cors import CORSMiddleware  # noqa: F401  (re-exported)
from starlette.requests import Request  # noqa: F401  (re-exported)
from starlette.responses import JSONResponse, PlainTextResponse, Response  # noqa: F401
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles  # noqa: F401  (re-exported)


class HTTPException(Exception):
    def __init__(self, status_code: int, detail: t.Any = None, headers: dict | None = None):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail if detail is not None else "HTTP error"
        self.headers = headers


class Depends:
    def __init__(self, dependency: t.Callable | None = None, use_cache: bool = True):
        self.dependency = dependency
        self.use_cache = use_cache


class _Param:
    kind = "query"

    def __init__(self, default: t.Any = ..., **_: t.Any):
        self.default = default


class _Query(_Param):
    kind = "query"


class _Form(_Param):
    kind = "form"


class _File(_Param):
    kind = "file"


def Query(default: t.Any = ..., **kw: t.Any) -> t.Any:  # noqa: N802 (FastAPI naming)
    return _Query(default, **kw)


def Form(default: t.Any = ..., **kw: t.Any) -> t.Any:  # noqa: N802
    return _Form(default, **kw)


def File(default: t.Any = ..., **kw: t.Any) -> t.Any:  # noqa: N802
    return _File(default, **kw)


# --------------------------------------------------------------------------- helpers


def jsonable(obj: t.Any) -> t.Any:
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, bytes):
        return obj.decode("utf-8", "replace")
    return obj


def _unwrap_optional(annotation: t.Any) -> tuple[t.Any, bool]:
    origin = t.get_origin(annotation)
    if origin is t.Union or str(origin) == "<class 'types.UnionType'>":
        args = [a for a in t.get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return args[0], True
    return annotation, False


def _convert(value: str, annotation: t.Any, name: str) -> t.Any:
    annotation, _ = _unwrap_optional(annotation)
    try:
        if annotation in (inspect.Parameter.empty, str, t.Any):
            return value
        if annotation is bool:
            return value.lower() in ("1", "true", "yes", "on")
        if annotation is int:
            return int(value)
        if annotation is float:
            return float(value)
        if annotation is UUID:
            return UUID(value)
        if inspect.isclass(annotation) and issubclass(annotation, Enum):
            return annotation(value)
    except (ValueError, TypeError):
        raise HTTPException(
            422,
            [{"loc": ["query", name], "msg": f"Invalid value for {name}", "type": "type_error"}],
        )
    return value


def _is_model(annotation: t.Any) -> bool:
    annotation, _ = _unwrap_optional(annotation)
    return inspect.isclass(annotation) and issubclass(annotation, BaseModel)


class _RequestState:
    def __init__(self, request: Request):
        self.request = request
        self.cache: dict[t.Callable, t.Any] = {}
        self.cleanups: list[t.Callable[[], t.Awaitable[None]]] = []
        self._body_json: t.Any = ...
        self._form: t.Any = None

    async def body_json(self) -> t.Any:
        if self._body_json is ...:
            raw = await self.request.body()
            if not raw:
                self._body_json = None
            else:
                try:
                    import json

                    self._body_json = json.loads(raw)
                except ValueError:
                    raise HTTPException(
                        422, [{"loc": ["body"], "msg": "Invalid JSON body", "type": "value_error.jsondecode"}]
                    )
        return self._body_json

    async def form(self) -> t.Any:
        if self._form is None:
            self._form = await self.request.form()
        return self._form


async def _call(fn: t.Callable, kwargs: dict) -> t.Any:
    if inspect.iscoroutinefunction(fn):
        return await fn(**kwargs)
    return await run_in_threadpool(fn, **kwargs)


async def _resolve_dependency(dep: Depends, state: _RequestState) -> t.Any:
    fn = dep.dependency
    assert fn is not None
    if dep.use_cache and fn in state.cache:
        return state.cache[fn]
    kwargs = await _resolve_params(fn, state)
    if inspect.isasyncgenfunction(fn):
        agen = fn(**kwargs)
        value = await agen.__anext__()

        async def _cleanup_async() -> None:
            try:
                await agen.__anext__()
            except StopAsyncIteration:
                pass

        state.cleanups.append(_cleanup_async)
    elif inspect.isgeneratorfunction(fn):
        gen = fn(**kwargs)
        value = next(gen)

        async def _cleanup_sync() -> None:
            try:
                next(gen)
            except StopIteration:
                pass

        state.cleanups.append(_cleanup_sync)
    else:
        value = await _call(fn, kwargs)
    if dep.use_cache:
        state.cache[fn] = value
    return value


async def _resolve_params(fn: t.Callable, state: _RequestState) -> dict:
    sig = inspect.signature(fn)
    try:
        hints = t.get_type_hints(fn)
    except Exception:  # pragma: no cover - defensive
        hints = {}
    request = state.request
    kwargs: dict[str, t.Any] = {}
    errors: list[dict] = []
    for name, param in sig.parameters.items():
        annotation = hints.get(name, param.annotation)
        default = param.default
        if isinstance(default, Depends):
            kwargs[name] = await _resolve_dependency(default, state)
            continue
        if annotation is Request:
            kwargs[name] = request
            continue
        if name in request.path_params:
            kwargs[name] = _convert(request.path_params[name], annotation, name)
            continue
        base_annotation, optional = _unwrap_optional(annotation)
        if isinstance(default, _File) or base_annotation is UploadFile:
            form = await state.form()
            value = form.get(name)
            if value is None or isinstance(value, str):
                if isinstance(default, _Param) and default.default is not ...:
                    kwargs[name] = default.default
                elif optional or (not isinstance(default, _Param) and default is not inspect.Parameter.empty):
                    kwargs[name] = None if default is inspect.Parameter.empty else default
                else:
                    errors.append({"loc": ["body", name], "msg": "Field required", "type": "missing"})
            else:
                kwargs[name] = value
            continue
        if isinstance(default, _Form):
            form = await state.form()
            value = form.get(name)
            if value is None:
                if default.default is ...:
                    errors.append({"loc": ["body", name], "msg": "Field required", "type": "missing"})
                else:
                    kwargs[name] = default.default
            else:
                kwargs[name] = _convert(str(value), annotation, name)
            continue
        if _is_model(annotation):
            body = await state.body_json()
            if body is None:
                if optional or default is not inspect.Parameter.empty:
                    kwargs[name] = None if default is inspect.Parameter.empty else default
                else:
                    errors.append({"loc": ["body"], "msg": "Field required", "type": "missing"})
                continue
            try:
                kwargs[name] = base_annotation.model_validate(body)
            except ValidationError as exc:
                for err in exc.errors(include_url=False):
                    err = dict(err)
                    err["loc"] = ["body", *list(err.get("loc", []))]
                    err.pop("ctx", None)
                    err.pop("input", None)
                    errors.append(err)
            continue
        # plain query parameter
        raw = request.query_params.get(name)
        if raw is None:
            if isinstance(default, _Param):
                if default.default is ...:
                    errors.append({"loc": ["query", name], "msg": "Field required", "type": "missing"})
                else:
                    kwargs[name] = default.default
            elif default is not inspect.Parameter.empty:
                kwargs[name] = default
            elif optional:
                kwargs[name] = None
            else:
                errors.append({"loc": ["query", name], "msg": "Field required", "type": "missing"})
        else:
            kwargs[name] = _convert(raw, annotation, name)
    if errors:
        raise HTTPException(422, errors)
    return kwargs


def _to_response(result: t.Any, status_code: int) -> Response:
    if isinstance(result, Response):
        return result
    if status_code == 204 or result is None and status_code in (200, 201):
        if result is None:
            return Response(status_code=204 if status_code == 204 else status_code)
    return JSONResponse(jsonable(result), status_code=status_code)


class APIRouter:
    def __init__(self, prefix: str = "", tags: list[str] | None = None, **_: t.Any):
        self.prefix = prefix.rstrip("/")
        self.tags = tags or []
        self.routes: list[tuple[str, list[str], t.Callable, int]] = []

    def api_route(self, path: str, methods: list[str], status_code: int = 200, **_: t.Any):
        def decorator(fn: t.Callable) -> t.Callable:
            self.routes.append((self.prefix + path, methods, fn, status_code))
            return fn

        return decorator

    def get(self, path: str, **kw: t.Any):
        return self.api_route(path, ["GET"], **kw)

    def post(self, path: str, **kw: t.Any):
        return self.api_route(path, ["POST"], **kw)

    def put(self, path: str, **kw: t.Any):
        return self.api_route(path, ["PUT"], **kw)

    def patch(self, path: str, **kw: t.Any):
        return self.api_route(path, ["PATCH"], **kw)

    def delete(self, path: str, **kw: t.Any):
        return self.api_route(path, ["DELETE"], **kw)

    def include_router(self, router: "APIRouter", prefix: str = "", **_: t.Any) -> None:
        for path, methods, fn, code in router.routes:
            self.routes.append((prefix.rstrip("/") + path, methods, fn, code))


class FastAPI(APIRouter):
    def __init__(self, title: str = "API", version: str = "0.0.0", lifespan: t.Any = None, **kw: t.Any):
        super().__init__()
        self.title = title
        self.version = version
        self._lifespan = lifespan
        self._middleware: list[tuple[t.Any, dict]] = []
        self._mounts: list[Mount] = []
        self._exception_handlers: dict[t.Any, t.Callable] = {}
        self._app: Starlette | None = None

    # FastAPI-like configuration API --------------------------------------
    def add_middleware(self, middleware_class: t.Any, **options: t.Any) -> None:
        self._middleware.append((middleware_class, options))

    def mount(self, path: str, app: t.Any, name: str | None = None) -> None:
        self._mounts.append(Mount(path, app=app, name=name))

    def add_exception_handler(self, exc_class: t.Any, handler: t.Callable) -> None:
        self._exception_handlers[exc_class] = handler

    # Build the Starlette application lazily -------------------------------
    def _make_endpoint(self, fn: t.Callable, status_code: int) -> t.Callable:
        async def endpoint(request: Request) -> Response:
            state = _RequestState(request)
            try:
                kwargs = await _resolve_params(fn, state)
                result = await _call(fn, kwargs)
                return _to_response(result, status_code)
            finally:
                for cleanup in reversed(state.cleanups):
                    try:
                        await cleanup()
                    except Exception:  # pragma: no cover - cleanup must never mask errors
                        pass

        endpoint.__name__ = getattr(fn, "__name__", "endpoint")
        return endpoint

    def _build(self) -> Starlette:
        routes: list[t.Any] = []
        for path, methods, fn, code in self.routes:
            routes.append(Route(path or "/", self._make_endpoint(fn, code), methods=methods, name=fn.__name__))
        routes.extend(self._mounts)

        async def http_exception_handler(request: Request, exc: HTTPException) -> Response:
            return JSONResponse({"detail": jsonable(exc.detail)}, status_code=exc.status_code, headers=exc.headers)

        async def starlette_exception_handler(request: Request, exc: Exception) -> Response:
            status_code = getattr(exc, "status_code", 500)
            detail = getattr(exc, "detail", "Internal server error")
            return JSONResponse({"detail": detail}, status_code=status_code)

        from starlette.exceptions import HTTPException as StarletteHTTPException

        handlers: dict[t.Any, t.Callable] = {
            HTTPException: http_exception_handler,
            StarletteHTTPException: starlette_exception_handler,
        }
        handlers.update(self._exception_handlers)
        from starlette.middleware import Middleware

        middleware = [Middleware(cls, **opts) for cls, opts in self._middleware]
        return Starlette(routes=routes, middleware=middleware, exception_handlers=handlers, lifespan=self._lifespan)

    async def __call__(self, scope: dict, receive: t.Callable, send: t.Callable) -> None:
        if self._app is None:
            self._app = self._build()
        await self._app(scope, receive, send)


__all__ = [
    "APIRouter",
    "CORSMiddleware",
    "Depends",
    "FastAPI",
    "File",
    "Form",
    "HTTPException",
    "JSONResponse",
    "PlainTextResponse",
    "Query",
    "Request",
    "Response",
    "StaticFiles",
    "UploadFile",
    "jsonable",
    "status",
]

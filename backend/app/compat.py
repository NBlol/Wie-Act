"""
FastAPI import indirection.

The application is written against the FastAPI API surface. When FastAPI is
installed (the normal case: `pip install -r requirements.txt` / Docker image),
the real framework is used. In environments where FastAPI cannot be installed
(the offline sandbox this project was first built in, where PyPI was blocked),
a small, documented Starlette-based compatibility layer with the same calling
conventions is used instead (see `app/minifastapi.py`).

`USING_FASTAPI` is exposed on `/api/health` so nobody is misled about which
layer is running.
"""
from __future__ import annotations

try:  # pragma: no cover - exercised only where FastAPI is installed
    from fastapi import (  # type: ignore
        APIRouter,
        Depends,
        FastAPI,
        File,
        Form,
        HTTPException,
        Query,
        Request,
        Response,
        UploadFile,
        status,
    )
    from fastapi.middleware.cors import CORSMiddleware  # type: ignore
    from fastapi.responses import JSONResponse, PlainTextResponse  # type: ignore
    from fastapi.staticfiles import StaticFiles  # type: ignore

    USING_FASTAPI = True
except ImportError:  # pragma: no cover - depends on the environment
    from app.minifastapi import (  # noqa: F401
        APIRouter,
        CORSMiddleware,
        Depends,
        FastAPI,
        File,
        Form,
        HTTPException,
        JSONResponse,
        PlainTextResponse,
        Query,
        Request,
        Response,
        StaticFiles,
        UploadFile,
        status,
    )

    USING_FASTAPI = False

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
    "status",
    "USING_FASTAPI",
]

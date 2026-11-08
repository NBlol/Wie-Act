"""Pydantic request models (validation layer)."""
from __future__ import annotations

import typing as t

from pydantic import BaseModel, Field, field_validator

from app.utils import LEARNING_STYLES, LEVELS, SUPPORTED_LANGUAGES

Language = t.Literal["en", "fr", "ar", "tn"]


def _check_language(value: str | None) -> str | None:
    if value is None:
        return value
    if value not in SUPPORTED_LANGUAGES:
        raise ValueError(f"language must be one of {SUPPORTED_LANGUAGES}")
    return value


class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=200)
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=2, max_length=40)
    preferred_language: str = "en"
    role: t.Literal["learner", "teacher"] = "learner"

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("invalid email address")
        return v

    @field_validator("preferred_language")
    @classmethod
    def _lang(cls, v: str) -> str:
        return _check_language(v) or "en"


class LoginRequest(BaseModel):
    email: str
    password: str


class UpdateMeRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=40)
    preferred_language: str | None = None
    darija_script: t.Literal["arabic", "latin"] | None = None
    learning_style: str | None = None
    level: str | None = None
    goal: str | None = Field(default=None, max_length=300)

    @field_validator("preferred_language")
    @classmethod
    def _lang(cls, v: str | None) -> str | None:
        return _check_language(v)

    @field_validator("learning_style")
    @classmethod
    def _style(cls, v: str | None) -> str | None:
        if v is not None and v not in LEARNING_STYLES:
            raise ValueError(f"learning_style must be one of {LEARNING_STYLES}")
        return v

    @field_validator("level")
    @classmethod
    def _level(cls, v: str | None) -> str | None:
        if v is not None and v not in LEVELS:
            raise ValueError(f"level must be one of {LEVELS}")
        return v


class DiagnosticAnswer(BaseModel):
    question_id: str
    option_id: str


class DiagnosticSubmit(BaseModel):
    answers: list[DiagnosticAnswer]
    self_reported_level: str | None = None
    goal: str | None = Field(default=None, max_length=300)
    language: str | None = None


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    language: str | None = None
    document_id: str | None = None


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=6000)
    mode: t.Literal["guided", "direct"] = "guided"
    use_documents: bool = True
    style_override: str | None = None


class QuizGenerate(BaseModel):
    topic: str | None = Field(default=None, max_length=200)
    document_id: str | None = None
    num_questions: int = Field(default=5, ge=3, le=10)
    difficulty: t.Literal["beginner", "intermediate", "advanced", "auto"] = "auto"
    language: str | None = None
    question_types: list[t.Literal["mcq", "short"]] = Field(default_factory=lambda: ["mcq"])
    room_id: str | None = None


class QuizAnswer(BaseModel):
    question_id: str
    option_id: str | None = None
    text: str | None = Field(default=None, max_length=1000)


class QuizSubmit(BaseModel):
    answers: list[QuizAnswer]
    time_spent_s: int = Field(default=0, ge=0, le=36000)


class RoomCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    topic: str = Field(min_length=2, max_length=160)
    language: str | None = None


class RoomJoin(BaseModel):
    code: str = Field(min_length=4, max_length=12)


class RoomMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=3000)


class RoomModerate(BaseModel):
    action: t.Literal["nudge", "check_explanation", "summarize", "guiding_question"]
    message_id: str | None = None


class RoomQuizCreate(BaseModel):
    num_questions: int = Field(default=5, ge=3, le=10)


class DocumentSearch(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    k: int = Field(default=5, ge=1, le=12)


class DocumentAsk(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    language: str | None = None


class RoadmapCreate(BaseModel):
    goal: str = Field(min_length=3, max_length=300)
    weeks: int = Field(default=4, ge=1, le=12)
    hours_per_week: int = Field(default=5, ge=1, le=40)
    language: str | None = None
    document_id: str | None = None


class ActivityUpdate(BaseModel):
    done: bool


class NoteGenerate(BaseModel):
    source: t.Literal["conversation", "document", "room", "topic"]
    source_id: str | None = None
    topic: str | None = Field(default=None, max_length=200)
    language: str | None = None
    format: t.Literal["summary", "flashcards", "both"] = "both"


class ClassCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)


class ClassJoin(BaseModel):
    code: str = Field(min_length=4, max_length=12)


__all__ = [n for n in dir() if n[0].isupper()]

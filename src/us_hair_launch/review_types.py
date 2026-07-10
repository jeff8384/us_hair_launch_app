from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Axis = Literal[
    "science",
    "clinical",
    "ingredient",
    "sensorial",
    "clean",
    "authority",
    "social",
    "problem",
]

AXES: tuple[Axis, ...] = (
    "science",
    "clinical",
    "ingredient",
    "sensorial",
    "clean",
    "authority",
    "social",
    "problem",
)


class DraftReviewRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    product_name: str = ""
    category: str = "serum"
    copy_text: str = Field(alias="copy")
    ai_backend: str = "llama-server"
    top_n: int = Field(default=30, ge=1, le=200)


class ComplianceFlag(BaseModel):
    term: str
    fix: str


class RewriteOption(BaseModel):
    label: Literal["marketing", "compliance_safe"]
    text: str


class DraftReviewResponse(BaseModel):
    scores: dict[Axis, int]
    compliance: dict[str, Any]
    differentiation: list[str]
    crowded: list[str]
    gaps: list[str]
    rewrites: list[RewriteOption]
    summary: str
    backend: str
    diagnostics: list[str] = Field(default_factory=list)


class AiReviewPayload(BaseModel):
    summary: str = ""
    differentiation: list[str] = Field(default_factory=list)
    crowded: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    rewrites: list[RewriteOption] = Field(default_factory=list)
    compliance: dict[str, Any] = Field(default_factory=dict)

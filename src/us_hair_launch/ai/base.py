from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel


class GenerationRequest(BaseModel):
    backend: str
    prompt: str
    mode: str = "marketing"


class GenerationResponse(BaseModel):
    backend: str
    text: str
    used_remote: bool = False
    diagnostics: list[str] = []


class AiProvider(Protocol):
    name: str

    def generate(self, request: GenerationRequest) -> GenerationResponse: ...


class DeterministicFallbackProvider:
    name = "deterministic"

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        return GenerationResponse(
            backend=self.name,
            text=f"{request.mode}: {request.prompt[:500]}",
            diagnostics=["No AI backend was required for deterministic pipeline outputs."],
        )

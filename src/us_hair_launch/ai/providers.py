from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from json import JSONDecodeError

import httpx
from google.genai.errors import APIError

from .base import DeterministicFallbackProvider, GenerationRequest, GenerationResponse

GEMMA_MODEL_NAME = "gemma-4-12B-it-Q4_K_M.gguf"
EXAONE_MODEL_NAME = "EXAONE-Deep-7.8B-Q8_0.gguf"
GEMINI_DEFAULT_MODEL = "gemini-2.0-flash"


@dataclass
class OllamaProvider:
    name: str = "ollama"
    base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    model: str = os.getenv("OLLAMA_MODEL", GEMMA_MODEL_NAME)

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        try:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": request.prompt, "stream": False},
                timeout=20,
            )
            response.raise_for_status()
            return GenerationResponse(
                backend=self.name,
                text=str(response.json().get("response", "")),
            )
        except (httpx.HTTPError, JSONDecodeError, KeyError, TypeError) as exc:
            return GenerationResponse(
                backend=self.name,
                text="",
                diagnostics=[f"Ollama unavailable: {type(exc).__name__}: {exc}"],
            )


@dataclass
class LlamaServerProvider:
    name: str = "llama-server"
    base_url: str = os.getenv("LLAMA_SERVER_BASE_URL", "http://127.0.0.1:8080")
    model: str = os.getenv("LLAMA_SERVER_MODEL", GEMMA_MODEL_NAME)

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        try:
            response = httpx.post(
                f"{self.base_url.rstrip('/')}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": request.prompt}],
                    "temperature": 0.2,
                    "max_tokens": 512,
                },
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            choice = payload.get("choices", [{}])[0]
            message = choice.get("message", {})
            text = _clean_llama_text(str(message.get("content", "")).strip())
            diagnostics: list[str] = []
            reasoning = str(message.get("reasoning_content", "")).strip()
            if reasoning:
                diagnostics.append("llama-server returned reasoning_content.")
            if not text and reasoning:
                cleaned = reasoning.strip()
                if cleaned.startswith('"') and cleaned.endswith('"'):
                    cleaned = cleaned[1:-1]
                text = cleaned
                diagnostics.append("Using reasoning_content as fallback output.")
            return GenerationResponse(
                backend=self.name,
                text=text,
                used_remote=False,
                diagnostics=diagnostics,
            )
        except (httpx.HTTPError, JSONDecodeError, KeyError, TypeError) as exc:
            return GenerationResponse(
                backend=self.name,
                text="",
                diagnostics=[f"llama-server unavailable: {type(exc).__name__}: {exc}"],
            )


@dataclass
class CodexProvider:
    name: str = "codex"

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        try:
            result = subprocess.run(
                ["codex", "exec", request.prompt],
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
            )
            return GenerationResponse(
                backend=self.name,
                text=result.stdout.strip(),
                used_remote=True,
                diagnostics=[] if result.returncode == 0 else [result.stderr.strip()],
            )
        except (subprocess.SubprocessError, OSError) as exc:
            return GenerationResponse(
                backend=self.name,
                text="",
                used_remote=True,
                diagnostics=[f"Codex CLI unavailable: {type(exc).__name__}: {exc}"],
            )


@dataclass
class OpenAICompatibleProvider:
    name: str = "openai-compatible"
    base_url: str = os.getenv("OPENAI_COMPATIBLE_BASE_URL", "")
    api_key: str = os.getenv("OPENAI_COMPATIBLE_API_KEY", "")
    model: str = os.getenv("OPENAI_COMPATIBLE_MODEL", "local-model")

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        if not self.base_url:
            return GenerationResponse(
                backend=self.name,
                text="",
                used_remote=True,
                diagnostics=["OPENAI_COMPATIBLE_BASE_URL is not set."],
            )
        try:
            response = httpx.post(
                f"{self.base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": request.prompt}],
                },
                timeout=30,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return GenerationResponse(backend=self.name, text=str(content), used_remote=True)
        except (httpx.HTTPError, JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            return GenerationResponse(
                backend=self.name,
                text="",
                used_remote=True,
                diagnostics=[f"OpenAI-compatible backend unavailable: {type(exc).__name__}: {exc}"],
            )


@dataclass
class GeminiProvider:
    name: str = "gemini"
    api_key: str = ""
    model: str = os.getenv("GEMINI_MODEL", GEMINI_DEFAULT_MODEL)

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        key = self.api_key or os.getenv("GEMINI_API_KEY", "")
        if not key:
            return GenerationResponse(
                backend=self.name,
                text="",
                used_remote=True,
                diagnostics=["GEMINI_API_KEY is not set."],
            )
        try:
            from google import genai

            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model=self.model,
                contents=request.prompt,
            )
            return GenerationResponse(
                backend=self.name,
                text=response.text or "",
                used_remote=True,
            )
        except ImportError as exc:
            return _gemini_unavailable(exc)
        except (APIError, AttributeError, TypeError, ValueError) as exc:
            return _gemini_unavailable(exc)
        except Exception as exc:  # noqa: BLE001
            return _gemini_unavailable(exc)


def _gemini_unavailable(exc: Exception) -> GenerationResponse:
    return GenerationResponse(
        backend="gemini",
        text="",
        used_remote=True,
        diagnostics=[f"Gemini unavailable: {type(exc).__name__}: {exc}"],
    )


def provider_for(
    name: str,
    api_key: str = "",
) -> (
    DeterministicFallbackProvider
    | OllamaProvider
    | LlamaServerProvider
    | CodexProvider
    | OpenAICompatibleProvider
    | GeminiProvider
):
    normalized = name.strip().lower()
    if normalized == "ollama":
        return OllamaProvider()
    if normalized in {"llama-server-exaone", "llama-exaone", "exaone"}:
        return LlamaServerProvider(name="llama-server-exaone", model=EXAONE_MODEL_NAME)
    if normalized in {"llama-server-gemma", "llama-gemma", "gemma"}:
        return LlamaServerProvider(name="llama-server-gemma", model=GEMMA_MODEL_NAME)
    if normalized in {"llama-server", "llama", "llamacpp", "llama.cpp"}:
        return LlamaServerProvider()
    if normalized == "codex":
        return CodexProvider()
    if normalized in {"openai", "openai-compatible"}:
        return OpenAICompatibleProvider()
    if normalized in {"gemini", "google", "google-ai", "google-gemini"}:
        return GeminiProvider(api_key=api_key)
    return DeterministicFallbackProvider()


def _clean_llama_text(text: str) -> str:
    without_block = re.sub(r"(?is)<thought>.*?</thought>", "", text).strip()
    return re.sub(r"(?is)^</thought>\s*", "", without_block).strip()

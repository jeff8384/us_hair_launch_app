from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import orjson
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .ingestion import scan_input_dir
from .pipeline import run_pipeline
from .review import DraftReviewRequest, review_draft

ROOT = Path(__file__).resolve().parents[2]
templates = Jinja2Templates(directory=str(ROOT / "templates"))


def create_app(
    default_input_dir: Path = Path("/Users/sy/us_hair"),
    default_output_dir: Path = ROOT / "data" / "processed",
    default_exports_dir: Path = ROOT / "data" / "exports",
) -> FastAPI:
    app = FastAPI()
    app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "input_dir": str(default_input_dir),
                "output_dir": str(default_output_dir),
                "exports_dir": str(default_exports_dir),
            },
        )

    @app.get("/api/preview")
    async def preview(input_dir: Annotated[str | None, Query()] = None) -> dict[str, Any]:
        target = _resolve_input_dir(input_dir, default_input_dir)
        return scan_input_dir(target).model_dump()

    @app.post("/api/run")
    async def run(
        input_dir: Annotated[str | None, Query()] = None,
        ai_backend: str = "deterministic",
    ) -> dict[str, Any]:
        target = _resolve_input_dir(input_dir, default_input_dir)
        result = run_pipeline(
            target,
            default_output_dir,
            default_exports_dir,
            ROOT / "schemas",
            ai_backend=ai_backend,
        )
        payload = result.model_dump()
        payload["ai_backend"] = ai_backend
        return payload

    @app.get("/api/artifacts")
    async def artifacts() -> dict[str, Any]:
        return {
            "normalized": _read_jsonl(default_output_dir / "competitor_normalized.jsonl", None),
            "claims": _read_jsonl(default_output_dir / "competitor_claims.jsonl", None),
            "gaps": _read_json(default_output_dir / "competitor_gaps.json"),
            "message_map": _read_json(default_output_dir / "message_map_candidates.json"),
            "pdp_blocks": _read_json(default_output_dir / "pdp_blocks.json"),
            "exports": {
                "markdown": "/exports/pdp_copy_drafts.md",
                "json": {
                    "normalized": "/api/artifacts/competitor_normalized",
                    "claims": "/api/artifacts/competitor_claims",
                    "gaps": "/api/artifacts/competitor_gaps",
                    "message_map": "/api/artifacts/message_map_candidates",
                    "pdp_blocks": "/api/artifacts/pdp_blocks",
                },
            },
        }

    @app.post("/api/review")
    async def review(payload: DraftReviewRequest) -> dict[str, Any]:
        result = review_draft(
            payload,
            default_output_dir / "competitor_claims.jsonl",
            payload.ai_backend,
        )
        return result.model_dump()

    @app.get("/api/artifacts/{name}")
    async def artifact(name: str) -> Any:
        files = {
            "competitor_normalized": default_output_dir / "competitor_normalized.jsonl",
            "competitor_claims": default_output_dir / "competitor_claims.jsonl",
            "competitor_gaps": default_output_dir / "competitor_gaps.json",
            "message_map_candidates": default_output_dir / "message_map_candidates.json",
            "pdp_blocks": default_output_dir / "pdp_blocks.json",
        }
        path = files.get(name)
        if path is None or not path.exists():
            raise HTTPException(status_code=404, detail="artifact not found")
        if path.suffix == ".jsonl":
            return _read_jsonl(path, None)
        return _read_json(path)

    @app.get("/exports/pdp_copy_drafts.md")
    async def markdown_export() -> FileResponse:
        path = default_exports_dir / "pdp_copy_drafts.md"
        if not path.exists():
            raise HTTPException(status_code=404, detail="export not found")
        return FileResponse(path, media_type="text/markdown", filename=path.name)

    return app


def _resolve_input_dir(value: str | None, allowed_root: Path) -> Path:
    root = allowed_root.resolve()
    target = root if value is None else Path(value).resolve()
    if target != root and root not in target.parents:
        raise HTTPException(status_code=400, detail="input_dir outside allowed root")
    return target


def _read_json(path: Path) -> Any:
    if not path.exists():
        return {}
    return orjson.loads(path.read_bytes())


def _read_jsonl(path: Path, limit: int | None) -> list[Any]:
    if not path.exists():
        return []
    rows: list[Any] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        if limit is not None and index >= limit:
            break
        rows.append(orjson.loads(line))
    return rows


app = create_app()

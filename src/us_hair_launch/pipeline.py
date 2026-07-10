from __future__ import annotations

from pathlib import Path

from .analysis import analyze_gaps
from .extraction import extract_claims
from .ingestion import read_raw_rows
from .io import dump_json, dump_jsonl
from .messaging import generate_message_map
from .models import PipelineResult, write_schema_files
from .normalization import normalize_rows
from .pdp import generate_pdp_blocks, render_markdown

PROCESSED_FILES = [
    "competitor_normalized.jsonl",
    "competitor_claims.jsonl",
    "competitor_gaps.json",
    "message_map_candidates.json",
    "pdp_blocks.json",
]


def run_pipeline(
    input_dir: Path | str = Path("/Users/sy/us_hair"),
    output_dir: Path | str = Path("data/processed"),
    exports_dir: Path | str = Path("data/exports"),
    schema_dir: Path | str = Path("schemas"),
    ai_backend: str = "deterministic",
    ai_api_key: str = "",
) -> PipelineResult:
    input_path = _resolve_input_path(Path(input_dir))
    output_path = Path(output_dir)
    exports_path = Path(exports_dir)
    schema_path = Path(schema_dir)
    raw_rows, diagnostics = read_raw_rows(input_path)
    normalized = normalize_rows(raw_rows)
    claims = extract_claims(normalized)
    gaps = analyze_gaps(claims)
    messages = generate_message_map(gaps)
    pdp = generate_pdp_blocks(messages, gaps, ai_backend=ai_backend, ai_api_key=ai_api_key)

    write_schema_files(schema_path)
    dump_jsonl(output_path / "competitor_normalized.jsonl", normalized)
    dump_jsonl(output_path / "competitor_claims.jsonl", claims)
    dump_json(output_path / "competitor_gaps.json", gaps)
    dump_json(output_path / "message_map_candidates.json", messages)
    dump_json(output_path / "pdp_blocks.json", pdp)
    exports_path.mkdir(parents=True, exist_ok=True)
    (exports_path / "pdp_copy_drafts.md").write_text(
        render_markdown(messages, pdp),
        encoding="utf-8",
    )

    return PipelineResult(
        input_dir=str(input_path),
        output_dir=str(output_path),
        exports_dir=str(exports_path),
        normalized_count=len(normalized),
        claims_count=len(claims),
        retailers=sorted({record.retailer for record in normalized}),
        processed=PROCESSED_FILES,
        exports=["pdp_copy_drafts.md"],
        diagnostics=diagnostics,
    )


def _resolve_input_path(input_path: Path) -> Path:
    if _has_supported_files(input_path):
        return input_path
    raw_path = Path("data/raw")
    if _has_supported_files(raw_path):
        return raw_path
    return input_path


def _has_supported_files(path: Path) -> bool:
    if not path.exists() or not path.is_dir():
        return False
    return any(item.suffix.lower() in {".csv", ".xlsx"} for item in path.iterdir())

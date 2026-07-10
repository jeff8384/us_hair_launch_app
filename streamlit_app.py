"""Streamlit Cloud entry point for the US hair-care launch workflow."""

from __future__ import annotations

import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import orjson
import streamlit as st

from us_hair_launch.ingestion import scan_input_dir
from us_hair_launch.pipeline import run_pipeline

ROOT = Path(__file__).resolve().parent
SAMPLE_PROCESSED = ROOT / "data" / "processed"
SAMPLE_EXPORT = ROOT / "data" / "exports" / "pdp_copy_drafts.md"


class UploadedFileLike(Protocol):
    name: str

    def getvalue(self) -> bytes: ...


@dataclass(frozen=True, slots=True)
class RunArtifacts:
    markdown: str
    gaps: dict[str, object]
    pdp_blocks: dict[str, object]
    normalized_count: int
    claims_count: int
    retailers: tuple[str, ...]
    backend: str


def _secret(name: str) -> str:
    try:
        value = st.secrets.get(name, "")
    except (AttributeError, FileNotFoundError, KeyError, TypeError):
        return ""
    return str(value).strip()


def _google_api_key() -> str:
    manual = str(st.session_state.get("google_api_key", "")).strip()
    return manual or _secret("GEMINI_API_KEY") or _secret("GOOGLE_API_KEY")


def _write_uploads(files: Sequence[UploadedFileLike], target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for file in files:
        (target / Path(file.name).name).write_bytes(file.getvalue())


def _load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return orjson.loads(path.read_bytes())


def _run(files: Sequence[UploadedFileLike], api_key: str) -> RunArtifacts:
    backend = "gemini" if api_key else "deterministic"
    with (
        tempfile.TemporaryDirectory() as input_dir,
        tempfile.TemporaryDirectory() as output_dir,
        tempfile.TemporaryDirectory() as export_dir,
        tempfile.TemporaryDirectory() as schema_dir,
    ):
        _write_uploads(files, Path(input_dir))
        result = run_pipeline(
            input_dir=input_dir,
            output_dir=output_dir,
            exports_dir=export_dir,
            schema_dir=schema_dir,
            ai_backend=backend,
            ai_api_key=api_key,
        )
        export_path = Path(export_dir) / "pdp_copy_drafts.md"
        return RunArtifacts(
            markdown=export_path.read_text(encoding="utf-8") if export_path.exists() else "",
            gaps=_load_json(Path(output_dir) / "competitor_gaps.json"),
            pdp_blocks=_load_json(Path(output_dir) / "pdp_blocks.json"),
            normalized_count=result.normalized_count,
            claims_count=result.claims_count,
            retailers=tuple(result.retailers),
            backend=backend,
        )


def _sample_artifacts() -> RunArtifacts:
    return RunArtifacts(
        markdown=SAMPLE_EXPORT.read_text(encoding="utf-8") if SAMPLE_EXPORT.exists() else "",
        gaps=_load_json(SAMPLE_PROCESSED / "competitor_gaps.json"),
        pdp_blocks=_load_json(SAMPLE_PROCESSED / "pdp_blocks.json"),
        normalized_count=sum(1 for _ in (SAMPLE_PROCESSED / "competitor_normalized.jsonl").open()),
        claims_count=sum(1 for _ in (SAMPLE_PROCESSED / "competitor_claims.jsonl").open()),
        retailers=("sephora", "ulta"),
        backend="sample",
    )


def _inject_style() -> None:
    st.markdown(
        """
        <style>
        .stApp { background: #f7f3ef; color: #241b22; }
        [data-testid="stSidebar"] { background: #fffdfa; border-right: 1px solid #e2d9d3; }
        h1, h2, h3 { color: #241b22; letter-spacing: 0; }
        .metric-card {
          border: 1px solid #e2d9d3;
          border-radius: 8px;
          background: #fffdfa;
          padding: 16px;
        }
        .strategy-note {
          border-left: 4px solid #a62e5c;
          background: #fffdfa;
          padding: 14px 16px;
          margin: 12px 0 18px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _sidebar(api_key: str) -> None:
    with st.sidebar:
        st.subheader("Google API")
        st.caption("Streamlit secrets use `GEMINI_API_KEY` or `GOOGLE_API_KEY`.")
        if api_key:
            st.success("Gemini is the primary AI backend.")
        else:
            st.warning("No Google key found. Deterministic fallback will run.")
        st.text_input(
            "Optional API key",
            key="google_api_key",
            type="password",
            placeholder="AI...",
            help="Stored only in this Streamlit session.",
        )
        st.divider()
        st.caption("Upload Sephora and Ulta CSV/XLSX files, then generate launch outputs.")


def _preview(files: Sequence[UploadedFileLike]) -> None:
    with tempfile.TemporaryDirectory() as input_dir:
        _write_uploads(files, Path(input_dir))
        preview = scan_input_dir(Path(input_dir))
    st.write(f"Detected files: {len(preview.files)}")
    for file in preview.files:
        with st.expander(f"{file.filename} · {file.retailer_hint} · {file.file_type}"):
            st.write("Sheets:", ", ".join(file.sheets))
            st.dataframe(file.sample_rows, use_container_width=True, hide_index=True)
    for message in preview.diagnostics:
        st.warning(message)


def _render_artifacts(artifacts: RunArtifacts) -> None:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Normalized", artifacts.normalized_count)
    col2.metric("Claims", artifacts.claims_count)
    col3.metric("Retailers", ", ".join(artifacts.retailers) or "none")
    col4.metric("AI backend", artifacts.backend)

    st.markdown(
        (
            '<div class="strategy-note">'
            "Whitespace and PDP drafts are generated from the current competitor set."
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    tabs = st.tabs(["Whitespace", "PDP Blocks", "Markdown Export"])
    with tabs[0]:
        st.json(artifacts.gaps, expanded=False)
    with tabs[1]:
        st.json(artifacts.pdp_blocks, expanded=False)
    with tabs[2]:
        st.markdown(artifacts.markdown or "No markdown output generated.")
        st.download_button(
            "Download Markdown",
            data=artifacts.markdown.encode("utf-8"),
            file_name="pdp_copy_drafts.md",
            mime="text/markdown",
            use_container_width=True,
        )


def main() -> None:
    st.set_page_config(page_title="US Hair Launch", layout="wide")
    _inject_style()
    api_key = _google_api_key()
    _sidebar(api_key)

    st.title("US Hair Launch Copy Lab")
    st.caption("Competitor ingestion, whitespace analysis, and PDP copy drafting.")

    files = st.file_uploader(
        "Upload Sephora and Ulta competitor files",
        type=("csv", "xlsx"),
        accept_multiple_files=True,
    )
    if files:
        _preview(files)
        if st.button("Run workflow", type="primary", use_container_width=True):
            with st.spinner("Processing competitor files and generating copy blocks..."):
                st.session_state["artifacts"] = _run(files, api_key)
    else:
        st.info("Upload CSV/XLSX files, or inspect the bundled sample output below.")
        if st.button("Load bundled sample output", use_container_width=True):
            st.session_state["artifacts"] = _sample_artifacts()

    artifacts = st.session_state.get("artifacts")
    if isinstance(artifacts, RunArtifacts):
        st.divider()
        _render_artifacts(artifacts)


main()

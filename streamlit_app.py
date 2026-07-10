"""Streamlit version of CopyDiffLab for public deployment."""

from __future__ import annotations

import tempfile
from collections import Counter, defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

import orjson
import streamlit as st

from us_hair_launch.io import dump_jsonl
from us_hair_launch.models import CompetitorClaims
from us_hair_launch.pipeline import run_pipeline
from us_hair_launch.review import _scores, review_draft
from us_hair_launch.review_types import AXES, Axis, DraftReviewRequest

ROOT = Path(__file__).resolve().parent
CLAIMS_PATH = ROOT / "data" / "processed" / "competitor_claims.jsonl"
AXIS_LABELS: dict[Axis, str] = {
    "science": "과학·기술",
    "clinical": "임상 검증·CRO",
    "ingredient": "성분 히어로",
    "sensorial": "감각·프리미엄",
    "clean": "클린·안전",
    "authority": "전문가·살롱",
    "social": "사회적 증거",
    "problem": "문제·해결",
}
RETAILER_LABELS = {"sephora": "Sephora", "ulta": "Ulta", "unknown": "기타", "other": "기타"}


class UploadedFileLike(Protocol):
    name: str

    def getvalue(self) -> bytes: ...


def _secret(name: str) -> str:
    try:
        return str(st.secrets.get(name, "")).strip()
    except (AttributeError, FileNotFoundError, KeyError, TypeError):
        return ""


def _api_key() -> str:
    manual = str(st.session_state.get("google_api_key", "")).strip()
    return manual or _secret("GEMINI_API_KEY") or _secret("GOOGLE_API_KEY")


def _load_claims(path: Path) -> list[CompetitorClaims]:
    return [
        CompetitorClaims.model_validate(orjson.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _claims_from_uploads(files: Sequence[UploadedFileLike]) -> list[CompetitorClaims]:
    with (
        tempfile.TemporaryDirectory() as input_dir,
        tempfile.TemporaryDirectory() as output_dir,
        tempfile.TemporaryDirectory() as export_dir,
        tempfile.TemporaryDirectory() as schema_dir,
    ):
        input_path = Path(input_dir)
        for file in files:
            (input_path / Path(file.name).name).write_bytes(file.getvalue())
        run_pipeline(input_path, output_dir, export_dir, schema_dir, ai_backend="deterministic")
        return _load_claims(Path(output_dir) / "competitor_claims.jsonl")


def _session_upload_claims() -> list[CompetitorClaims]:
    stored = st.session_state.get("uploaded_claims", [])
    if not isinstance(stored, list):
        return []
    return [CompetitorClaims.model_validate(item) for item in stored]


def _top_n_by_retailer(claims: list[CompetitorClaims], top_n: int) -> list[CompetitorClaims]:
    counts: dict[str, int] = defaultdict(int)
    scoped: list[CompetitorClaims] = []
    for claim in claims:
        counts[claim.retailer] += 1
        if counts[claim.retailer] <= top_n:
            scoped.append(claim)
    return scoped


def _coverage(claims: list[CompetitorClaims]) -> dict[Axis, int]:
    if not claims:
        return dict.fromkeys(AXES, 0)
    totals = Counter[Axis]()
    for claim in claims:
        for axis, value in _scores(claim).items():
            if value >= 30:
                totals[axis] += 1
    return {axis: round((totals[axis] / len(claims)) * 100) for axis in AXES}


def _source_counts(claims: list[CompetitorClaims]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for claim in claims:
        counts[RETAILER_LABELS.get(claim.retailer, claim.retailer)] += 1
    return dict(counts)


def _write_temp_claims(claims: list[CompetitorClaims]) -> Path:
    path = Path(tempfile.mkdtemp()) / "competitor_claims.jsonl"
    dump_jsonl(path, claims)
    return path


def _radar_svg(scores: dict[Axis, int], coverage: dict[Axis, int]) -> str:
    size = 330
    center = size / 2
    radius = 108

    def point(index: int, value: int) -> tuple[float, float]:
        import math

        angle = -math.pi / 2 + index * 2 * math.pi / len(AXES)
        scale = value / 100
        return center + radius * scale * math.cos(angle), center + radius * scale * math.sin(angle)

    mine_points = [point(i, scores[a]) for i, a in enumerate(AXES)]
    comp_points = [point(i, coverage[a]) for i, a in enumerate(AXES)]
    mine = " ".join(f"{x:.1f},{y:.1f}" for x, y in mine_points)
    comp = " ".join(f"{x:.1f},{y:.1f}" for x, y in comp_points)
    labels = "".join(
        '<text '
        f'x="{point(i, 122)[0]:.1f}" y="{point(i, 122)[1]:.1f}" '
        f'text-anchor="middle" font-size="10" fill="#796d75">{AXIS_LABELS[a]}</text>'
        for i, a in enumerate(AXES)
    )
    grids = "".join(
        '<polygon points="'
        + " ".join(f"{x:.1f},{y:.1f}" for x, y in [point(i, level) for i in range(len(AXES))])
        + '" fill="none" stroke="#e2d9d3" stroke-width="1"/>'
        for level in (25, 50, 75, 100)
    )
    return f"""
    <svg viewBox="0 0 {size} {size}" width="100%" role="img">
      {grids}
      {labels}
      <polygon points="{comp}" fill="#2e7d5b" fill-opacity="0.10"
        stroke="#2e7d5b" stroke-width="1.5" stroke-dasharray="4 4"/>
      <polygon points="{mine}" fill="#a62e5c" fill-opacity="0.22"
        stroke="#a62e5c" stroke-width="2.5"/>
    </svg>
    """


def _style() -> None:
    st.markdown(
        """
        <style>
        .stApp { background:#f7f3ef; color:#241b22; }
        [data-testid="stSidebar"] {
          background:#fffdfa; border-right:1px solid #e2d9d3;
        }
        h1 { font-family: Georgia, serif; font-weight: 700; }
        h2, h3, label, .stMarkdown { letter-spacing:0; }
        .lab-head {
          border-bottom:1px solid #e2d9d3; padding:10px 0 18px; margin-bottom:16px;
        }
        .mark-a { font-family:Georgia,serif; font-size:34px; color:#241b22; }
        .mark-b {
          font-family:Georgia,serif; font-size:34px; color:#a62e5c; margin-left:4px;
        }
        .section {
          border:1px solid #e2d9d3; border-radius:8px; background:#fffdfa;
          padding:18px; margin:14px 0;
        }
        .section-h { font-weight:700; color:#241b22; margin-bottom:10px; }
        .ax { color:#a62e5c; font-family:monospace; margin-right:8px; }
        .pill {
          display:inline-block; border:1px solid #e2d9d3; border-radius:999px;
          padding:3px 9px; margin:3px; font-size:12px;
        }
        .note {
          border-left:4px solid #a62e5c; background:#fffdfa;
          padding:12px 14px; margin:10px 0;
        }
        .risk-low { color:#2e7d5b; font-weight:700; }
        .risk-medium { color:#c58a22; font-weight:700; }
        .risk-high { color:#b23a44; font-weight:700; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_header() -> None:
    st.markdown(
        """
        <div class="lab-head">
          <span class="mark-a">문안</span><span class="mark-b">차별화 검토</span>
          <div>US Hair Care · Copy Differentiation Lab</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _section(title: str, number: str) -> None:
    html = (
        '<div class="section"><div class="section-h">'
        f'<span class="ax">{number}</span>{title}</div>'
    )
    st.markdown(
        html,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(page_title="Copy Differentiation Lab", layout="wide")
    _style()
    _render_header()

    key = _api_key()
    bundled = _load_claims(CLAIMS_PATH)
    uploaded = _session_upload_claims()
    all_claims = bundled + uploaded

    with st.sidebar:
        st.subheader("AI backend")
        st.text_input("Google API key", key="google_api_key", type="password", placeholder="AI...")
        st.caption("Secrets: `GEMINI_API_KEY` or `GOOGLE_API_KEY`")
        if key:
            st.success("Google Gemini 우선")
        else:
            st.warning("키 없음: deterministic fallback")
        st.divider()
        top_n = st.slider("베스트셀러 상위", 5, 200, 30, step=5)
        use_sephora = st.checkbox("Sephora 사용", value=True)
        use_ulta = st.checkbox("Ulta 사용", value=True)
        use_uploaded = st.checkbox("업로드 데이터 사용", value=True)

    _section("경쟁 데이터", "01")
    files = st.file_uploader(
        "CSV 또는 XLSX를 추가하면 기본 DB에 누적됩니다.",
        type=("csv", "xlsx"),
        accept_multiple_files=True,
    )
    if files and st.button("데이터 추가하기", use_container_width=True):
        with st.spinner("업로드 파일을 경쟁 DB로 변환 중..."):
            new_claims = _claims_from_uploads(files)
        st.session_state["uploaded_claims"] = [
            claim.model_dump() for claim in uploaded + new_claims
        ]
        st.success(f"{len(new_claims)}행 추가됨")
        st.rerun()

    source_counts = _source_counts(all_claims)
    st.write(" ".join(f"{name} {count}개" for name, count in source_counts.items()))
    st.markdown("</div>", unsafe_allow_html=True)

    active = [
        claim
        for claim in all_claims
        if (claim.retailer == "sephora" and use_sephora)
        or (claim.retailer == "ulta" and use_ulta)
        or (claim.retailer not in {"sephora", "ulta"} and use_uploaded)
    ]
    scoped = _top_n_by_retailer(active, top_n)
    coverage = _coverage(scoped)

    _section("내 문안", "02")
    c1, c2 = st.columns([2, 1])
    product_name = c1.text_input("제품명", value="PeachBiome Repair Serum")
    category = c2.selectbox(
        "카테고리",
        [
            "serum",
            "shampoo",
            "conditioner",
            "mask",
            "oil",
            "scalp_treatment",
            "leave_in",
            "styling",
        ],
    )
    copy = st.text_area(
        "검토받을 영문 PDP 문안",
        value=(
            "Postbiotic peach-derived repair serum. Our PeachBiome028 microbiome complex "
            "rebalances the scalp barrier and reinforces weakened strands. Lightweight and "
            "non-greasy, for damaged and color-treated hair."
        ),
        height=140,
    )
    run = st.button("문안 검토 요청", type="primary", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if run:
        request = DraftReviewRequest(
            product_name=product_name,
            category=category,
            copy=copy,
            ai_backend="gemini" if key else "deterministic",
            top_n=top_n,
        )
        with st.spinner("경쟁 포지셔닝과 컴플라이언스 리스크를 검토 중..."):
            st.session_state["review"] = review_draft(
                request,
                _write_temp_claims(scoped),
                "gemini" if key else "deterministic",
                ai_api_key=key,
            ).model_dump()

    review_raw = st.session_state.get("review")
    if not isinstance(review_raw, dict):
        return

    review = review_raw
    scores = {axis: int(review["scores"][axis]) for axis in AXES}
    _section("차별화 맵", "03")
    st.markdown(f'<div class="note">{review["summary"]}</div>', unsafe_allow_html=True)
    diagnostics = review.get("diagnostics", [])
    if isinstance(diagnostics, list) and diagnostics:
        st.warning(" / ".join(str(item) for item in diagnostics))
    risk = str(review.get("compliance", {}).get("risk", "low"))
    st.markdown(
        f'컴플라이언스 리스크: <span class="risk-{risk}">{risk.upper()}</span>',
        unsafe_allow_html=True,
    )

    left, right = st.columns([1, 1])
    with left:
        st.markdown("#### 포지셔닝 레이더")
        st.markdown(_radar_svg(scores, coverage), unsafe_allow_html=True)
        st.caption("실선: 내 문안 · 점선: 경쟁 커버리지")
    with right:
        st.markdown("#### 근거 커버리지 · 여백")
        for axis in AXES:
            st.write(f"{AXIS_LABELS[axis]} · 경쟁 {coverage[axis]}% · 내 문안 {scores[axis]}")
            st.progress(min(coverage[axis], 100))

    a, b, c = st.columns(3)
    a.markdown("#### 여기서 차별화됩니다")
    a.write("\n".join(f"- {item}" for item in review.get("differentiation", [])) or "- 없음")
    b.markdown("#### 여기선 묻힙니다")
    b.write("\n".join(f"- {item}" for item in review.get("crowded", [])) or "- 없음")
    c.markdown("#### 비어 있는 여백")
    c.write("\n".join(f"- {item}" for item in review.get("gaps", [])) or "- 없음")

    flags = review.get("compliance", {}).get("flags", [])
    if flags:
        st.markdown("#### 컴플라이언스 플래그")
        for flag in flags:
            st.code(f"{flag.get('term', '')} -> {flag.get('fix', '')}")

    st.markdown("#### 리라이트")
    for rewrite in review.get("rewrites", []):
        st.markdown(f'<span class="pill">{rewrite["label"]}</span>', unsafe_allow_html=True)
        st.write(rewrite["text"])
    st.markdown("</div>", unsafe_allow_html=True)


main()

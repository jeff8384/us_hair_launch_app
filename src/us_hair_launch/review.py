from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import orjson

from .ai.base import GenerationRequest
from .ai.providers import provider_for
from .extraction import extract_record_claims
from .models import CompetitorClaims, CompetitorNormalized
from .review_types import (
    AXES,
    AiReviewPayload,
    Axis,
    ComplianceFlag,
    DraftReviewRequest,
    DraftReviewResponse,
    RewriteOption,
)


def review_draft(
    request: DraftReviewRequest,
    claims_path: Path,
    ai_backend: str,
    ai_api_key: str = "",
) -> DraftReviewResponse:
    claims = _read_claims(claims_path)
    scoped = _top_n_by_retailer(claims, request.top_n)
    draft_claim = _draft_claim(request)
    baseline = _deterministic_review(request, draft_claim, scoped, ai_backend)
    if ai_backend == "deterministic":
        return baseline

    generation = provider_for(ai_backend, api_key=ai_api_key).generate(
        GenerationRequest(
            backend=ai_backend,
            mode="copy_diff_review",
            prompt=_prompt(request, draft_claim, scoped, baseline),
        )
    )
    if generation.text:
        parsed = _parse_ai_review(generation.text, baseline)
        if parsed is not None:
            parsed.backend = generation.backend
            parsed.diagnostics.extend(generation.diagnostics)
            return parsed

    baseline.backend = generation.backend
    baseline.diagnostics.extend(generation.diagnostics)
    baseline.diagnostics.append("AI review unavailable; deterministic review displayed.")
    return baseline


def _read_claims(path: Path) -> list[CompetitorClaims]:
    if not path.exists():
        return []
    return [
        CompetitorClaims.model_validate(orjson.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _top_n_by_retailer(claims: list[CompetitorClaims], top_n: int) -> list[CompetitorClaims]:
    counts: dict[str, int] = defaultdict(int)
    scoped: list[CompetitorClaims] = []
    for claim in claims:
        counts[claim.retailer] += 1
        if counts[claim.retailer] <= top_n:
            scoped.append(claim)
    return scoped


def _draft_claim(request: DraftReviewRequest) -> CompetitorClaims:
    record = CompetitorNormalized(
        record_id="draft",
        source_file="draft",
        source_sheet="copy_lab",
        row_index=1,
        retailer="unknown",
        product_name=request.product_name,
        category=request.category,
        description_raw=request.copy_text,
        claims_raw=request.copy_text,
        ingredients_raw=request.copy_text,
    )
    return extract_record_claims(record)


def _deterministic_review(
    request: DraftReviewRequest,
    draft: CompetitorClaims,
    competitors: list[CompetitorClaims],
    backend: str,
) -> DraftReviewResponse:
    scores = _scores(draft)
    coverage = _coverage(competitors)
    used: list[Axis] = []
    for axis in AXES:
        if scores[axis] >= 30:
            used.append(axis)
    crowded = [_axis_label(axis) for axis in used if coverage[axis] >= 60]
    whitespace = [_axis_label(axis) for axis in used if coverage[axis] < 40]
    missing = [_axis_label(axis) for axis in AXES if scores[axis] < 15]
    differentiation = whitespace or [_axis_label(axis) for axis in used[:2]]
    flags = _flags(request.copy_text)
    risk = "high" if any(flag.term in _HIGH_RISK for flag in flags) else draft.compliance_risk
    return DraftReviewResponse(
        scores=scores,
        compliance={"risk": risk, "flags": [flag.model_dump() for flag in flags]},
        differentiation=[f"{item} 축이 상대적으로 선명합니다." for item in differentiation[:2]],
        crowded=[f"{item} 축은 경쟁사도 많이 사용합니다." for item in crowded[:2]],
        gaps=[f"{item} 축 보강 여지가 있습니다." for item in missing[:2]],
        rewrites=_rewrites(request, risk),
        summary=_summary(scores, coverage),
        backend=backend,
    )


def _scores(claim: CompetitorClaims) -> dict[Axis, int]:
    proof = set(claim.proof_type)
    benefits = set(claim.benefit_keywords)
    sensory = set(claim.sensory_keywords)
    concerns = set(claim.target_concerns)
    return {
        "science": _clamp(len(proof & {"formulation", "ingredient"}) * 34),
        "clinical": _clamp(len(proof & {"clinical", "consumer_test", "before_after"}) * 34),
        "ingredient": _clamp(len(claim.ingredients_called_out) * 18),
        "sensorial": _clamp((len(sensory) * 22) + (25 if "shine" in benefits else 0)),
        "clean": _clamp(65 if claim.visual_style == "clean-minimal" else 0),
        "authority": _clamp(65 if proof & {"award_press", "expert"} else 0),
        "social": _clamp(70 if proof & {"review_social_proof", "award_press"} else 0),
        "problem": _clamp((len(benefits | concerns)) * 12),
    }


def _coverage(claims: list[CompetitorClaims]) -> dict[Axis, int]:
    if not claims:
        return dict.fromkeys(AXES, 0)
    totals = Counter[Axis]()
    for claim in claims:
        for axis, value in _scores(claim).items():
            if value >= 30:
                totals[axis] += 1
    return {axis: round((totals[axis] / len(claims)) * 100) for axis in AXES}


def _flags(copy: str) -> list[ComplianceFlag]:
    text = copy.lower()
    flags = [
        ComplianceFlag(term=term, fix="Use appearance-support language instead.")
        for term in _HIGH_RISK + _MEDIUM_RISK
        if term in text
    ]
    return flags[:4]


def _rewrites(request: DraftReviewRequest, risk: str) -> list[RewriteOption]:
    product = request.product_name or "This hair-care routine"
    return [
        RewriteOption(
            label="marketing",
            text=(
                f"{product} turns visible repair, shine, and lightweight softness "
                "into a daily ritual."
            ),
        ),
        RewriteOption(
            label="compliance_safe",
            text=(
                f"{product} helps hair look smoother, shinier, and more resilient "
                "with routine use."
            ),
        ),
    ] if risk != "high" else [
        RewriteOption(
            label="marketing",
            text=f"{product} supports a smoother, healthier-looking finish.",
        ),
        RewriteOption(
            label="compliance_safe",
            text=f"{product} helps improve the look and feel of stronger, softer hair.",
        ),
    ]


def _summary(scores: dict[Axis, int], coverage: dict[Axis, int]) -> str:
    lead = max(AXES, key=lambda axis: scores[axis])
    crowd = coverage[lead]
    if crowd >= 60:
        return f"{_axis_label(lead)} 중심이지만 경쟁 밀도가 높아 보조 축 차별화가 필요합니다."
    return f"{_axis_label(lead)} 중심 문안이 경쟁 공백을 일부 선점합니다."


def _prompt(
    request: DraftReviewRequest,
    draft: CompetitorClaims,
    competitors: list[CompetitorClaims],
    baseline: DraftReviewResponse,
) -> str:
    proof_counts = Counter(item for claim in competitors for item in claim.proof_type)
    benefit_counts = Counter(item for claim in competitors for item in claim.benefit_keywords)
    compact = {
        "scope": f"top {request.top_n} by retailer; {len(competitors)} competitor products",
        "top_proof": proof_counts.most_common(8),
        "top_benefits": benefit_counts.most_common(10),
        "draft_claims": draft.model_dump(),
        "deterministic_review": baseline.model_dump(),
    }
    return (
        "You are a US hair-care copy differentiation reviewer. "
        "Return only compact JSON matching this shape: "
        '{"summary":"","differentiation":[""],"crowded":[""],"gaps":[""],'
        '"rewrites":[{"label":"marketing","text":""},{"label":"compliance_safe","text":""}],'
        '"compliance":{"risk":"low|medium|high","flags":[{"term":"","fix":""}]}}. '
        "Keep Korean analysis concise. Scores have 8 axes; clinical is quantified third-party "
        "or consumer evidence, while authority is human expert, salon, stylist, or awards. "
        "Rewrites must be English and cosmetic-compliance safe.\n"
        f"{json.dumps(compact, ensure_ascii=False)}"
    )


def _parse_ai_review(text: str, baseline: DraftReviewResponse) -> DraftReviewResponse | None:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        payload = AiReviewPayload.model_validate_json(text[start : end + 1])
    except ValueError:
        return None
    return DraftReviewResponse(
        scores=baseline.scores,
        compliance=payload.compliance or baseline.compliance,
        differentiation=payload.differentiation or baseline.differentiation,
        crowded=payload.crowded or baseline.crowded,
        gaps=payload.gaps or baseline.gaps,
        rewrites=payload.rewrites or baseline.rewrites,
        summary=payload.summary or baseline.summary,
        backend=baseline.backend,
    )


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def _axis_label(axis: Axis) -> str:
    labels: dict[Axis, str] = {
        "science": "과학·기술",
        "clinical": "임상 검증·CRO",
        "ingredient": "성분 히어로",
        "sensorial": "감각·프리미엄",
        "clean": "클린·안전",
        "authority": "전문가·살롱",
        "social": "사회적 증거",
        "problem": "문제·해결",
    }
    return labels[axis]


_HIGH_RISK = ["cure", "prevent hair loss", "regrow", "treats", "heals"]
_MEDIUM_RISK = ["guaranteed", "overnight", "10x", "stimulates growth", "repairs damage"]

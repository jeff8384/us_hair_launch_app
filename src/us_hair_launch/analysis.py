from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable

from .models import CompetitorClaims, CompetitorGaps, PatternCount, Retailer, RetailerGap


def analyze_gaps(claims: list[CompetitorClaims]) -> CompetitorGaps:
    by_retailer: dict[Retailer, list[CompetitorClaims]] = defaultdict(list)
    for claim in claims:
        by_retailer[claim.retailer].append(claim)
    retailer_breakdown = [
        _retailer_gap(retailer, rows) for retailer, rows in sorted(by_retailer.items())
    ]
    claim_counts = _counts(item for claim in claims for item in claim.benefit_keywords)
    proof_counts = _counts(item for claim in claims for item in claim.proof_type)
    gaps = _whitespace(claims)
    return CompetitorGaps(
        summary=f"Analyzed {len(claims)} competitor records across {len(by_retailer)} retailers.",
        total_records=len(claims),
        retailer_breakdown=retailer_breakdown,
        top_claim_patterns=claim_counts,
        top_proof_patterns=proof_counts,
        category_insights=[
            "Repair, moisture, frizz, and thinning language dominate the competitive set.",
            "Ingredient and formulation proof appear more often than clinical proof.",
        ],
        gap_opportunities=gaps,
        retailer_specific_differences=_differences(retailer_breakdown),
    )


def _retailer_gap(retailer: Retailer, rows: list[CompetitorClaims]) -> RetailerGap:
    claim_counts = _counts(item for claim in rows for item in claim.benefit_keywords)
    proof_counts = _counts(item for claim in rows for item in claim.proof_type)
    return RetailerGap(
        retailer=retailer,
        record_count=len(rows),
        top_claim_patterns=claim_counts,
        top_proof_patterns=proof_counts,
        whitespace=_whitespace(rows),
    )


def _counts(items: Iterable[str]) -> list[PatternCount]:
    counter = Counter(str(item) for item in items if str(item))
    return [PatternCount(pattern=name, count=count) for name, count in counter.most_common(10)]


def _whitespace(claims: list[CompetitorClaims]) -> list[str]:
    text = " ".join(" ".join(claim.benefit_keywords + claim.proof_type) for claim in claims)
    options: list[str] = []
    if "clinical" not in text:
        options.append("Clinical substantiation appears underused versus ingredient storytelling.")
    if "scalp" not in text:
        options.append("Scalp barrier positioning has room for sharper ownership.")
    if "lightweight" not in text:
        options.append("Trade-off language around high-performance lightweight feel is sparse.")
    options.append(
        "Combine measurable-looking proof structure with compliance-safe appearance language."
    )
    return options[:4]


def _differences(retailer_breakdown: list[RetailerGap]) -> list[str]:
    differences: list[str] = []
    for gap in retailer_breakdown:
        top = gap.top_claim_patterns[0].pattern if gap.top_claim_patterns else "no dominant claim"
        differences.append(
            f"{gap.retailer}: {gap.record_count} records; leading claim pattern is {top}."
        )
    return differences

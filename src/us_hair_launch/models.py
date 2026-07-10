from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

Retailer = Literal["sephora", "ulta", "other", "unknown"]
ComplianceRisk = Literal["low", "medium", "high"]
CopyMode = Literal["marketing", "compliance_safe"]
ProofType = Literal[
    "ingredient",
    "formulation",
    "clinical",
    "consumer_test",
    "review_social_proof",
    "expert",
    "before_after",
    "award_press",
    "none_detected",
]


class RawRow(BaseModel):
    source_file: str
    source_sheet: str
    row_index: int
    values: dict[str, Any]


class FilePreview(BaseModel):
    path: str
    filename: str
    file_type: Literal["csv", "xlsx"]
    retailer_hint: Retailer
    sheets: list[str]
    columns: list[str]
    sample_rows: list[dict[str, Any]]
    diagnostics: list[str] = Field(default_factory=list)


class PreviewResult(BaseModel):
    input_dir: str
    files: list[FilePreview]
    diagnostics: list[str] = Field(default_factory=list)


class CompetitorNormalized(BaseModel):
    record_id: str
    source_file: str
    source_sheet: str
    row_index: int
    retailer: Retailer
    retailer_inference_source: str = ""
    retailer_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    brand: str = ""
    product_name: str = ""
    category: str = "other"
    subcategory: str = ""
    price_usd: float | None = Field(default=None, ge=0.0)
    currency: str = "USD"
    size: str = ""
    description_raw: str = ""
    claims_raw: str = ""
    ingredients_raw: str = ""
    how_to_use_raw: str = ""
    rating: float | None = None
    review_count: int | None = Field(default=None, ge=0)
    target_hair_type_raw: str = ""
    target_concern_raw: str = ""
    product_url: str = ""
    image_url: str = ""
    extra_raw_fields: dict[str, Any] = Field(default_factory=dict)


class CompetitorClaims(BaseModel):
    record_id: str
    retailer: Retailer
    brand: str = ""
    product_name: str = ""
    hero_claim: str = ""
    supporting_claims: list[str] = Field(default_factory=list)
    proof_type: list[ProofType] = Field(default_factory=list)
    ingredients_called_out: list[str] = Field(default_factory=list)
    target_concerns: list[str] = Field(default_factory=list)
    target_hair_types: list[str] = Field(default_factory=list)
    benefit_keywords: list[str] = Field(default_factory=list)
    sensory_keywords: list[str] = Field(default_factory=list)
    tone: str = "functional"
    visual_style: str = "unknown"
    cta_style: str = "learn_more"
    compliance_risk: ComplianceRisk = "low"
    tradeoff_resolution: list[str] = Field(default_factory=list)
    positioning_pattern: str = "unknown"
    evidence_notes: list[str] = Field(default_factory=list)


class PatternCount(BaseModel):
    pattern: str
    count: int


class RetailerGap(BaseModel):
    retailer: Retailer
    record_count: int
    top_claim_patterns: list[PatternCount]
    top_proof_patterns: list[PatternCount]
    whitespace: list[str]


class CompetitorGaps(BaseModel):
    summary: str
    total_records: int
    retailer_breakdown: list[RetailerGap]
    top_claim_patterns: list[PatternCount]
    top_proof_patterns: list[PatternCount]
    category_insights: list[str]
    gap_opportunities: list[str]
    retailer_specific_differences: list[str]


class MessageTerritory(BaseModel):
    territory: Literal["science-led", "sensorial-premium", "clean-performance"]
    core_promise: str
    differentiator: str
    proof_direction: str
    emotional_payoff: str
    headline_options: list[str] = Field(min_length=2)
    subheadline_options: list[str] = Field(min_length=2)
    benefit_bullets: list[str] = Field(min_length=3)
    compliance_safe_rewrites: list[str] = Field(min_length=2)
    recommended_use_case: str


class MessageMapCandidates(BaseModel):
    territories: list[MessageTerritory] = Field(min_length=3)
    source_summary: str


class CopyVariant(BaseModel):
    mode: CopyMode
    headline: str
    body: str
    bullets: list[str] = Field(default_factory=list)
    cta: str = ""


class FaqItem(BaseModel):
    question: str
    answer: str


class HeroBlock(BaseModel):
    headline: str
    subheadline: str
    cta: str


class PdpBlockSet(BaseModel):
    hero: HeroBlock
    problem_solution: dict[str, Any]
    proof_block: dict[str, Any]
    ingredients_technology: dict[str, Any]
    sensory_experience: dict[str, Any]
    results_social_proof: dict[str, Any]
    routine_integration: dict[str, Any]
    faq: dict[str, Any]
    closing_cta: dict[str, Any]


class PdpBlocks(BaseModel):
    blocks: PdpBlockSet
    copy_modes: dict[CopyMode, dict[str, CopyVariant]]
    faq: list[FaqItem] = Field(min_length=2)
    ai_assist: dict[str, Any] = Field(default_factory=dict)


class PipelineResult(BaseModel):
    input_dir: str
    output_dir: str
    exports_dir: str
    normalized_count: int
    claims_count: int
    retailers: list[Retailer]
    processed: list[str]
    exports: list[str]
    diagnostics: list[str] = Field(default_factory=list)


SCHEMA_MODELS: dict[str, type[BaseModel]] = {
    "competitor_normalized.schema.json": CompetitorNormalized,
    "competitor_claims.schema.json": CompetitorClaims,
    "competitor_gaps.schema.json": CompetitorGaps,
    "message_map_candidates.schema.json": MessageMapCandidates,
    "pdp_blocks.schema.json": PdpBlocks,
    "copy_variants.schema.json": CopyVariant,
}


def write_schema_files(schema_dir: Path) -> None:
    import json

    schema_dir.mkdir(parents=True, exist_ok=True)
    for filename, model in SCHEMA_MODELS.items():
        payload = model.model_json_schema()
        (schema_dir / filename).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

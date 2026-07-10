from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

from .models import CompetitorClaims, CompetitorNormalized, ComplianceRisk, ProofType

BENEFITS = [
    "repair",
    "strengthen",
    "hydrate",
    "moisturize",
    "shine",
    "smooth",
    "frizz",
    "volume",
    "thinning",
    "breakage",
    "color safe",
    "scalp",
    "density",
]
SENSORY = ["soft", "silky", "lightweight", "rich", "creamy", "glossy", "smooth", "clean"]
CONCERNS = ["dryness", "frizz", "damage", "breakage", "thinning", "color", "scalp", "shine"]
HAIR_TYPES = ["straight", "wavy", "curly", "coily", "fine", "medium", "thick"]
INGREDIENTS = [
    "rosemary",
    "ceramide",
    "protein",
    "hyaluronic",
    "argan",
    "shea",
    "coconut",
    "peptide",
    "biotin",
    "caffeine",
    "keratin",
    "bond",
]


def extract_claims(records: list[CompetitorNormalized]) -> list[CompetitorClaims]:
    return [extract_record_claims(record) for record in records]


def extract_record_claims(record: CompetitorNormalized) -> CompetitorClaims:
    text = _joined(record)
    support = _supporting_claims(record.claims_raw or record.description_raw)
    hero = support[0] if support else ""
    benefits = _keywords(text, BENEFITS)
    sensory = _keywords(text, SENSORY)
    ingredients = _keywords(text, INGREDIENTS)
    proof = _proof_types(text, ingredients)
    risks = _risk(text)
    return CompetitorClaims(
        record_id=record.record_id,
        retailer=record.retailer,
        brand=record.brand,
        product_name=record.product_name,
        hero_claim=hero,
        supporting_claims=support[1:6] if hero else support[:5],
        proof_type=proof,
        ingredients_called_out=ingredients,
        target_concerns=_keywords(record.target_concern_raw + " " + text, CONCERNS),
        target_hair_types=_keywords(record.target_hair_type_raw + " " + text, HAIR_TYPES),
        benefit_keywords=benefits,
        sensory_keywords=sensory,
        tone=_tone(text),
        visual_style=_visual_style(text),
        cta_style="shop_now" if record.product_url else "learn_more",
        compliance_risk=risks,
        tradeoff_resolution=_tradeoffs(text),
        positioning_pattern=_positioning(text, proof, sensory),
        evidence_notes=_evidence(record, proof, risks),
    )


def _joined(record: CompetitorNormalized) -> str:
    return " ".join(
        [
            record.product_name,
            record.description_raw,
            record.claims_raw,
            record.ingredients_raw,
            record.target_concern_raw,
            record.target_hair_type_raw,
        ]
    ).lower()


def _supporting_claims(raw: str) -> list[str]:
    parts = re.split(r"\s*/\s*|\n+|Benefits|Key Ingredients|Item\s+\d+", raw)
    cleaned = [part.strip(" :-•\t") for part in parts if part and len(part.strip()) > 3]
    return list(dict.fromkeys(cleaned))


def _keywords(text: str, candidates: Iterable[str]) -> list[str]:
    text_lower = text.lower()
    return [item for item in candidates if item in text_lower]


def _proof_types(text: str, ingredients: list[str]) -> list[ProofType]:
    proof: list[ProofType] = []
    if ingredients:
        proof.append("ingredient")
    if any(word in text for word in ["formula", "formulation", "complex", "technology"]):
        proof.append("formulation")
    if any(word in text for word in ["clinical", "clinically", "study"]):
        proof.append("clinical")
    if any(word in text for word in ["consumer", "panel", "%"]):
        proof.append("consumer_test")
    if any(word in text for word in ["review", "award", "allure"]):
        proof.append("award_press")
    return proof or ["none_detected"]


def _risk(text: str) -> ComplianceRisk:
    if any(word in text for word in ["cure", "heal", "regrow", "prevent hair loss"]):
        return "high"
    if any(word in text for word in ["thinning", "density", "anti-aging", "repair damaged"]):
        return "medium"
    return "low"


def _tone(text: str) -> str:
    if any(word in text for word in ["clinical", "peptide", "ceramide", "technology"]):
        return "scientific"
    if any(word in text for word in ["luxury", "silky", "glossy", "premium"]):
        return "premium"
    if any(word in text for word in ["clean", "vegan", "cruelty-free", "without"]):
        return "clean"
    return "functional"


def _visual_style(text: str) -> str:
    if "clean" in text or "vegan" in text:
        return "clean-minimal"
    if "award" in text or "salon" in text:
        return "authority-led"
    if any(word in text for word in ["silky", "shine", "gloss"]):
        return "sensory-gloss"
    return "clinical-functional"


def _tradeoffs(text: str) -> list[str]:
    patterns = {
        "repair_without_heaviness": ["repair", "lightweight"],
        "moisture_without_greasiness": ["moisture", "lightweight"],
        "shine_without_buildup": ["shine", "buildup"],
        "scalp_care_without_stripping": ["scalp", "stripping"],
        "frizz_control_without_stiffness": ["frizz", "soft"],
    }
    return [name for name, words in patterns.items() if all(word in text for word in words)]


def _positioning(text: str, proof: Sequence[str], sensory: list[str]) -> str:
    if "clinical" in proof or "peptide" in text or "technology" in text:
        return "science-led"
    if sensory or any(word in text for word in ["luxury", "gloss", "silky"]):
        return "sensorial-premium"
    if any(word in text for word in ["clean", "vegan", "without", "cruelty-free"]):
        return "clean-performance"
    if "salon" in text:
        return "salon-authority"
    if proof and proof != ["none_detected"]:
        return "ingredient-hero"
    return "problem-solution"


def _evidence(record: CompetitorNormalized, proof: Sequence[str], risk: str) -> list[str]:
    notes = [f"Raw provenance {record.source_file}/{record.source_sheet}/{record.row_index}"]
    notes.append(f"Proof detected: {', '.join(proof)}")
    if risk != "low":
        notes.append(f"Compliance risk elevated by claim language: {risk}")
    return notes

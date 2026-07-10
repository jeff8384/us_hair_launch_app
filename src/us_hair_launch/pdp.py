from __future__ import annotations

from .ai.base import GenerationRequest
from .ai.providers import provider_for
from .models import (
    CompetitorGaps,
    CopyMode,
    CopyVariant,
    FaqItem,
    MessageMapCandidates,
    PdpBlocks,
    PdpBlockSet,
)

BLOCK_NAMES = [
    "hero",
    "problem_solution",
    "proof_block",
    "ingredients_technology",
    "sensory_experience",
    "results_social_proof",
    "routine_integration",
    "faq",
    "closing_cta",
]


def generate_pdp_blocks(
    messages: MessageMapCandidates,
    gaps: CompetitorGaps,
    ai_backend: str = "deterministic",
    ai_api_key: str = "",
) -> PdpBlocks:
    lead = messages.territories[0]
    blocks = {
        "hero": {
            "headline": lead.headline_options[0],
            "subheadline": lead.subheadline_options[0],
            "cta": "Build the routine",
        },
        "problem_solution": {
            "body": (
                "Competitors cluster around repair, moisture, frizz, and thinning. "
                "The opportunity is a sharper routine story that connects concern, "
                "ingredient logic, and finish."
            )
        },
        "proof_block": {
            "body": lead.proof_direction,
            "proof_patterns": [item.pattern for item in gaps.top_proof_patterns],
        },
        "ingredients_technology": {
            "body": (
                "Use named ingredients as evidence, then connect them to visible "
                "hair appearance and feel."
            )
        },
        "sensory_experience": {"body": "Describe slip, softness, polish, and lightweight finish."},
        "results_social_proof": {
            "body": (
                "Anchor social proof in reviews, awards, or consumer language only "
                "when source data supports it."
            )
        },
        "routine_integration": {
            "body": "Place the product in a simple cleanse, treat, condition, style flow."
        },
        "faq": {"items": [{"question": item.question, "answer": item.answer} for item in _faq()]},
        "closing_cta": {
            "body": "Choose the territory, then generate channel-specific copy variants."
        },
    }
    provider = provider_for(ai_backend, api_key=ai_api_key)
    assist_prompts = {
        "territory_generation": "Suggest one sharper territory angle from the gap analysis.",
        "compliance_rewrite": "Rewrite the hero claim in compliance-safe appearance language.",
        "pdp_copy": "Suggest one concise PDP proof block refinement.",
        "faq_phrasing": "Suggest one FAQ answer that avoids guaranteed results.",
    }
    assists = {
        name: provider.generate(
            GenerationRequest(backend=ai_backend, mode="compliance_safe", prompt=prompt)
        ).model_dump()
        for name, prompt in assist_prompts.items()
    }
    return PdpBlocks(
        blocks=PdpBlockSet.model_validate(blocks),
        faq=_faq(),
        copy_modes={
            "marketing": _variants("marketing", messages),
            "compliance_safe": _variants("compliance_safe", messages),
        },
        ai_assist={"backend": ai_backend, "tasks": assists},
    )


def render_markdown(messages: MessageMapCandidates, pdp: PdpBlocks) -> str:
    lines = ["# US Hair Care PDP Copy Drafts", ""]
    for territory in messages.territories:
        lines.extend([f"## {territory.territory}", territory.core_promise, ""])
        lines.extend(f"- {headline}" for headline in territory.headline_options)
        lines.append("")
    for mode, variants in pdp.copy_modes.items():
        lines.extend([f"## {mode}", ""])
        for block, variant in variants.items():
            lines.extend([f"### {block}", variant.headline, variant.body, ""])
            lines.extend(f"- {bullet}" for bullet in variant.bullets)
            if variant.cta:
                lines.append(f"CTA: {variant.cta}")
            lines.append("")
    return "\n".join(lines).strip() + "\n"


def _variants(mode: CopyMode, messages: MessageMapCandidates) -> dict[str, CopyVariant]:
    lead = messages.territories[0]
    safe = mode == "compliance_safe"
    hero_headline = lead.compliance_safe_rewrites[0] if safe else lead.headline_options[0]
    proof_body = (
        "Supports the appearance of stronger, smoother hair with ingredient-led care."
        if safe
        else "A proof-minded routine built around ingredient clarity and visible performance."
    )
    return {
        "hero": CopyVariant(
            mode=mode,
            headline=hero_headline,
            body=lead.subheadline_options[0],
            bullets=lead.benefit_bullets[:3],
            cta="Shop the routine",
        ),
        "problem_solution": CopyVariant(
            mode=mode,
            headline="From scattered claims to a clear routine",
            body="Address dryness, frizz, damage, and scalp comfort in one story.",
            bullets=lead.benefit_bullets[:3],
        ),
        "proof_block": CopyVariant(
            mode=mode,
            headline="Proof direction",
            body=proof_body,
            bullets=[lead.proof_direction],
        ),
        "ingredients_technology": CopyVariant(
            mode=mode,
            headline="Ingredient logic",
            body="Name ingredients, explain their role, and keep results appearance-based.",
            bullets=lead.compliance_safe_rewrites,
        ),
        "sensory_experience": CopyVariant(
            mode=mode,
            headline="Feel the finish",
            body="Softness, slip, shine, and a lightweight finish make it memorable.",
            bullets=["Soft feel", "Polished shine", "Lightweight finish"],
        ),
        "results_social_proof": CopyVariant(
            mode=mode,
            headline="Results framing",
            body="Use reviews, awards, and consumer language only when source data supports it.",
            bullets=["No fabricated statistics", "Source-aware proof"],
        ),
        "routine_integration": CopyVariant(
            mode=mode,
            headline="Routine fit",
            body="Position as an easy step in a cleanse, treat, condition, and style routine.",
            bullets=["Simple order", "Clear usage moment"],
        ),
        "faq": CopyVariant(
            mode=mode,
            headline="FAQ",
            body="Answer fit, frequency, and hair type questions in restrained language.",
            bullets=["Who it is for", "How often to use", "What to expect"],
        ),
        "closing_cta": CopyVariant(
            mode=mode,
            headline="Complete the routine",
            body="Move shoppers from concern to next step with a concise CTA.",
            cta="Build your routine",
        ),
    }


def _faq() -> list[FaqItem]:
    return [
        FaqItem(
            question="What hair concerns should this positioning address?",
            answer=(
                "Lead with visible dryness, frizz, breakage, shine, and scalp comfort "
                "patterns found in the competitor set."
            ),
        ),
        FaqItem(
            question="How should compliance-safe copy handle results?",
            answer=(
                "Use helps, supports, appearance, look, feel, and source-backed proof "
                "instead of medical or guaranteed result language."
            ),
        ),
    ]

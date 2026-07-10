from __future__ import annotations

from .models import CompetitorGaps, MessageMapCandidates, MessageTerritory, PatternCount


def generate_message_map(gaps: CompetitorGaps) -> MessageMapCandidates:
    claim_focus = _patterns(gaps.top_claim_patterns, ["repair", "shine", "frizz"])
    proof_focus = _patterns(gaps.top_proof_patterns, ["ingredient", "formulation"])
    whitespace = gaps.gap_opportunities[0] if gaps.gap_opportunities else "Sharpen whitespace."
    return MessageMapCandidates(
        source_summary=gaps.summary,
        territories=[
            MessageTerritory(
                territory="science-led",
                core_promise=f"Visible {claim_focus[0]} confidence through proof-aware care.",
                differentiator=(
                    f"Pairs {proof_focus[0]} substantiation with {claim_focus[1]} benefit framing."
                ),
                proof_direction=(
                    f"Lead with {proof_focus[0]} and {proof_focus[1]} support, then "
                    "translate benefits into measured appearance language."
                ),
                emotional_payoff=(
                    "Confidence that the routine is serious without sounding clinical."
                ),
                headline_options=[
                    "Stronger-looking hair starts at the routine.",
                    "Proof-minded care for modern hair stress.",
                ],
                subheadline_options=[
                    "A targeted system built around ingredients consumers already scan for.",
                    "Designed to support smoother, healthier-looking hair without heavy promises.",
                ],
                benefit_bullets=[
                    f"Frames {claim_focus[0]}, {claim_focus[1]}, and scalp comfort as one routine.",
                    "Uses compliance-safe appearance language for visible results.",
                    f"Responds to whitespace: {whitespace}",
                ],
                compliance_safe_rewrites=[
                    "Supports the appearance of fuller-looking, more resilient hair.",
                    "Supports the look and feel of a healthier scalp environment.",
                ],
                recommended_use_case=(
                    "Lead territory when proof hierarchy matters more than fragrance "
                    "or luxury cues."
                ),
            ),
            MessageTerritory(
                territory="sensorial-premium",
                core_promise=f"High-performance {claim_focus[1]} care with a polished finish.",
                differentiator=(
                    "Owns texture, shine, and finish without losing functional credibility."
                ),
                proof_direction=(
                    "Use sensory descriptors, routine ritual cues, and lightweight "
                    "trade-off claims."
                ),
                emotional_payoff="A daily upgrade that makes hair feel finished before styling.",
                headline_options=[
                    "The soft-finish routine hair keeps asking for.",
                    "Performance you can feel before you style.",
                ],
                subheadline_options=[
                    "A sensorial system for shine, slip, and touchable control.",
                    "Built to make treatment-level care feel easy in a daily routine.",
                ],
                benefit_bullets=[
                    f"Elevates softness, glide, and {claim_focus[1]} as hero outcomes.",
                    "Resolves moisture without heaviness and polish without buildup.",
                    "Creates premium cues while staying specific about hair concerns.",
                ],
                compliance_safe_rewrites=[
                    "Leaves hair feeling softer, smoother, and more polished.",
                    "Helps improve the appearance of shine and manageability.",
                ],
                recommended_use_case=(
                    "Use for PDP modules and campaigns where luxury feel can differentiate."
                ),
            ),
            MessageTerritory(
                territory="clean-performance",
                core_promise=f"Clean-positioned care that still speaks in {claim_focus[0]}.",
                differentiator=(
                    "Balances free-from cues with functional claims and ingredient clarity."
                ),
                proof_direction=(
                    "Use ingredient exclusions only as support, not as the main performance story."
                ),
                emotional_payoff="Trust that cleaner choices do not mean weaker results.",
                headline_options=[
                    "Clean cues. Performance discipline.",
                    "A cleaner routine with results language built in.",
                ],
                subheadline_options=[
                    (
                        "A focused system for consumers who want ingredient clarity "
                        "and visible polish."
                    ),
                    "Free-from messaging supports the story while benefits stay in the lead.",
                ],
                benefit_bullets=[
                    "Separates clean values from measurable-looking performance claims.",
                    f"Keeps benefit language concrete across {', '.join(claim_focus)}.",
                    "Avoids overclaiming by using support, help, and appearance framing.",
                ],
                compliance_safe_rewrites=[
                    "Helps improve the look of healthier, smoother hair.",
                    "Formulated without selected ingredients consumers often avoid.",
                ],
                recommended_use_case="Use when clean positioning must avoid sounding generic.",
            ),
        ],
    )


def _patterns(patterns: list[PatternCount], fallback: list[str]) -> list[str]:
    names = [item.pattern for item in patterns if item.pattern]
    merged = list(dict.fromkeys(names + fallback))
    return merged[:3]

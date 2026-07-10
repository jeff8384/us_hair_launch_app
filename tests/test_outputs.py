import json
from pathlib import Path

from jsonschema import validate

from us_hair_launch.pipeline import run_pipeline

REQUIRED_PROCESSED = [
    "competitor_normalized.jsonl",
    "competitor_claims.jsonl",
    "competitor_gaps.json",
    "message_map_candidates.json",
    "pdp_blocks.json",
]


def test_required_outputs_validate_against_schemas(
    real_input_dir: Path,
    app_output_dir: Path,
    app_exports_dir: Path,
) -> None:
    run_pipeline(real_input_dir, app_output_dir, app_exports_dir)
    schema_root = Path("schemas")

    for filename in REQUIRED_PROCESSED:
        assert (app_output_dir / filename).exists(), filename

    assert (app_exports_dir / "pdp_copy_drafts.md").exists()

    gaps = json.loads((app_output_dir / "competitor_gaps.json").read_text())
    message_map = json.loads((app_output_dir / "message_map_candidates.json").read_text())
    pdp_blocks = json.loads((app_output_dir / "pdp_blocks.json").read_text())

    validate(gaps, json.loads((schema_root / "competitor_gaps.schema.json").read_text()))
    validate(
        message_map,
        json.loads((schema_root / "message_map_candidates.schema.json").read_text()),
    )
    validate(pdp_blocks, json.loads((schema_root / "pdp_blocks.schema.json").read_text()))
    assert {item["territory"] for item in message_map["territories"]} == {
        "science-led",
        "sensorial-premium",
        "clean-performance",
    }
    assert set(pdp_blocks["blocks"]) == {
        "hero",
        "problem_solution",
        "proof_block",
        "ingredients_technology",
        "sensory_experience",
        "results_social_proof",
        "routine_integration",
        "faq",
        "closing_cta",
    }


def test_copy_modes_are_separate_and_raw_text_is_preserved(
    real_input_dir: Path,
    app_output_dir: Path,
    app_exports_dir: Path,
) -> None:
    run_pipeline(real_input_dir, app_output_dir, app_exports_dir)
    pdp_blocks = json.loads((app_output_dir / "pdp_blocks.json").read_text())
    normalized = (app_output_dir / "competitor_normalized.jsonl").read_text()

    assert pdp_blocks["copy_modes"]["marketing"] != pdp_blocks["copy_modes"]["compliance_safe"]
    assert pdp_blocks["ai_assist"]["backend"] == "deterministic"
    assert {"territory_generation", "compliance_rewrite", "pdp_copy", "faq_phrasing"} <= set(
        pdp_blocks["ai_assist"]["tasks"]
    )
    assert "description_raw" in normalized
    assert "claims_raw" in normalized
    assert "ingredients_raw" in normalized
    assert "retailer_inference_source" in normalized
    assert "retailer_confidence" in normalized

from pathlib import Path

from fastapi.testclient import TestClient

from us_hair_launch.web import create_app


def test_preview_and_run_pipeline_api_with_real_inputs(
    real_input_dir: Path,
    tmp_path: Path,
) -> None:
    client = TestClient(
        create_app(
            default_input_dir=real_input_dir,
            default_output_dir=tmp_path / "processed",
            default_exports_dir=tmp_path / "exports",
        )
    )

    preview = client.get("/api/preview")
    assert preview.status_code == 200
    preview_json = preview.json()
    assert {item["retailer_hint"] for item in preview_json["files"]} >= {"sephora", "ulta"}
    assert any(item["sheets"] for item in preview_json["files"])

    run = client.post("/api/run")
    assert run.status_code == 200
    run_json = run.json()
    assert run_json["normalized_count"] >= 250
    assert "pdp_copy_drafts.md" in run_json["exports"]

    artifacts = client.get("/api/artifacts")
    assert artifacts.status_code == 200
    artifact_json = artifacts.json()
    assert artifact_json["normalized"]
    assert artifact_json["claims"]
    assert len(artifact_json["message_map"]["territories"]) == 3
    assert set(artifact_json["pdp_blocks"]["blocks"]) >= {"hero", "faq", "closing_cta"}

    export = client.get("/exports/pdp_copy_drafts.md")
    assert export.status_code == 200
    assert "US Hair Care PDP Copy Drafts" in export.text


def test_review_api_scores_draft_against_processed_competitors(
    real_input_dir: Path,
    tmp_path: Path,
) -> None:
    client = TestClient(
        create_app(
            default_input_dir=real_input_dir,
            default_output_dir=tmp_path / "processed",
            default_exports_dir=tmp_path / "exports",
        )
    )
    run = client.post("/api/run?ai_backend=deterministic")
    assert run.status_code == 200

    response = client.post(
        "/api/review",
        json={
            "product_name": "PeachBiome Repair Serum",
            "category": "serum",
            "copy": (
                "A lightweight glossing serum with peptide technology, peach extract, "
                "visible shine, smoother-looking frizz control, and routine-use softness."
            ),
            "ai_backend": "deterministic",
            "top_n": 30,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["backend"] == "deterministic"
    assert set(payload["scores"]) >= {"science", "clinical", "ingredient", "sensorial", "problem"}
    assert payload["summary"]
    assert {rewrite["label"] for rewrite in payload["rewrites"]} == {
        "marketing",
        "compliance_safe",
    }
    assert "risk" in payload["compliance"]


def test_preview_rejects_input_dir_outside_allowed_root(
    real_input_dir: Path,
    tmp_path: Path,
) -> None:
    secret_dir = tmp_path / "outside"
    secret_dir.mkdir()
    (secret_dir / "secret.csv").write_text("token,password\nabc,def\n")
    client = TestClient(create_app(default_input_dir=real_input_dir))

    response = client.get(f"/api/preview?input_dir={secret_dir}")

    assert response.status_code == 400
    assert "outside allowed root" in response.text

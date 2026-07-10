from pathlib import Path

import pytest

from us_hair_launch.pipeline import run_pipeline


def test_real_us_hair_inputs_normalize_with_provenance(
    real_input_dir: Path,
    app_output_dir: Path,
    app_exports_dir: Path,
) -> None:
    result = run_pipeline(real_input_dir, app_output_dir, app_exports_dir)

    assert result.normalized_count >= 250
    assert {"sephora", "ulta"}.issubset(result.retailers)
    assert (app_output_dir / "competitor_normalized.jsonl").exists()

    first_lines = (app_output_dir / "competitor_normalized.jsonl").read_text().splitlines()
    assert first_lines
    assert "source_file" in first_lines[0]
    assert "source_sheet" in first_lines[0]
    assert "row_index" in first_lines[0]


def test_empty_input_dir_returns_diagnostics(tmp_path: Path) -> None:
    empty_input = tmp_path / "empty"
    empty_input.mkdir()
    result = run_pipeline(empty_input, tmp_path / "processed", tmp_path / "exports")

    assert result.normalized_count == 0
    assert result.diagnostics
    assert "No supported input files" in " ".join(result.diagnostics)


def test_default_input_falls_back_to_data_raw_when_primary_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "data/raw").mkdir(parents=True)
    (tmp_path / "data/raw/sample_ulta.csv").write_text(
        "brand_name,product_name,details_original\nTest,Soft Shampoo,Benefits\\nshine\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    result = run_pipeline(
        tmp_path / "missing-primary",
        tmp_path / "processed",
        tmp_path / "exports",
        tmp_path / "schemas",
    )

    assert result.normalized_count == 1
    assert result.input_dir == "data/raw"

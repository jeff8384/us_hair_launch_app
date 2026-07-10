from pathlib import Path

from openpyxl import Workbook

from us_hair_launch.ai.base import GenerationRequest
from us_hair_launch.ai.providers import (
    EXAONE_MODEL_NAME,
    GEMMA_MODEL_NAME,
    GeminiProvider,
    LlamaServerProvider,
    _clean_llama_text,
    provider_for,
)
from us_hair_launch.extraction import extract_record_claims
from us_hair_launch.ingestion import read_raw_rows
from us_hair_launch.models import CompetitorNormalized
from us_hair_launch.normalization import normalize_rows
from us_hair_launch.review import review_draft
from us_hair_launch.review_types import DraftReviewRequest


def test_multisheet_xlsx_and_alternate_columns_normalize(tmp_path: Path) -> None:
    workbook = Workbook()
    first = workbook.active
    assert first is not None
    first.title = "Sephora A"
    first.append(["브랜드", "제품명", "Highlights", "Ingredients"])
    first.append(["Brand A", "Repair Mask", "Good for: Damage / Shine", "Argan Oil"])
    second = workbook.create_sheet("Ulta B")
    second.append(["brand_name", "product_name", "details_original", "ingredients_original"])
    second.append(["Brand B", "Soft Conditioner", "Benefits\nFights frizz", "Shea Butter"])
    path = tmp_path / "mixed_hair.xlsx"
    workbook.save(path)

    rows, diagnostics = read_raw_rows(tmp_path)
    normalized = normalize_rows(rows)

    assert diagnostics == []
    assert len(normalized) == 2
    assert {item.source_sheet for item in normalized} == {"Sephora A", "Ulta B"}
    assert {item.retailer for item in normalized} == {"sephora", "ulta"}
    assert all(item.extra_raw_fields for item in normalized)


def test_extraction_detects_proof_risk_and_tradeoff() -> None:
    record = CompetitorNormalized(
        record_id="r1",
        source_file="ulta.csv",
        source_sheet="CSV",
        row_index=2,
        retailer="ulta",
        retailer_inference_source="source_file",
        retailer_confidence=0.99,
        brand="Test",
        product_name="Density Scalp Serum",
        claims_raw=(
            "Clinical consumer study / peptide technology / repairs damaged hair / "
            "moisture lightweight / visibly improved density"
        ),
        ingredients_raw="Peptide, caffeine, rosemary",
        target_concern_raw="Thinning / Breakage",
        target_hair_type_raw="Fine, Thick",
    )

    claims = extract_record_claims(record)

    assert {"clinical", "consumer_test", "ingredient", "formulation"}.issubset(
        set(claims.proof_type)
    )
    assert claims.compliance_risk == "medium"
    assert "moisture_without_greasiness" in claims.tradeoff_resolution
    assert claims.positioning_pattern == "science-led"


def test_llama_server_provider_aliases_select_local_models() -> None:
    exaone = provider_for("llama-server-exaone")
    gemma = provider_for("llama-server-gemma")
    current = provider_for("llama-server")

    assert isinstance(exaone, LlamaServerProvider)
    assert exaone.name == "llama-server-exaone"
    assert exaone.model == EXAONE_MODEL_NAME

    assert isinstance(gemma, LlamaServerProvider)
    assert gemma.name == "llama-server-gemma"
    assert gemma.model == GEMMA_MODEL_NAME

    assert isinstance(current, LlamaServerProvider)
    assert current.base_url == "http://127.0.0.1:8080"


def test_llama_server_text_cleaning_removes_thought_tags() -> None:
    assert _clean_llama_text("</thought>\n\nOK") == "OK"
    assert _clean_llama_text("<thought>hidden</thought>\n{\"ok\": true}") == '{"ok": true}'


def test_gemini_provider_returns_diagnostics_when_google_api_rejects_request(
    monkeypatch,
) -> None:
    from google import genai
    from google.genai.errors import ClientError

    class RejectingModels:
        def generate_content(self, *, model: str, contents: str):
            raise ClientError(400, {"error": {"message": "invalid api key"}})

    class RejectingClient:
        models = RejectingModels()

        def __init__(self, *, api_key: str) -> None:
            assert api_key == "bad-key"

    monkeypatch.setattr(genai, "Client", RejectingClient)

    response = GeminiProvider(api_key="bad-key").generate(
        GenerationRequest(backend="gemini", mode="copy_diff_review", prompt="review this")
    )

    assert response.backend == "gemini"
    assert response.text == ""
    assert response.used_remote is True
    assert response.diagnostics
    assert "Gemini unavailable: ClientError" in response.diagnostics[0]


def test_review_draft_falls_back_when_ai_provider_raises(
    monkeypatch,
    tmp_path: Path,
) -> None:
    import us_hair_launch.review as review_module

    class ExplodingProvider:
        name = "gemini"

        def generate(self, request: GenerationRequest):
            raise RuntimeError("upstream rejected request")

    def exploding_provider_for(name: str, api_key: str = ""):
        return ExplodingProvider()

    claims_path = tmp_path / "competitor_claims.jsonl"
    claims_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(review_module, "provider_for", exploding_provider_for)

    response = review_draft(
        DraftReviewRequest(
            product_name="PeachBiome Repair Serum",
            category="serum",
            copy="Lightweight shine serum for smoother-looking frizz control.",
            top_n=30,
        ),
        claims_path,
        "gemini",
        ai_api_key="bad-key",
    )

    assert response.backend == "gemini"
    assert response.summary
    assert response.diagnostics == [
        "AI review unavailable: RuntimeError; deterministic review displayed."
    ]

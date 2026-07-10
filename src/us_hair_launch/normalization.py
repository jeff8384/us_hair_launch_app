from __future__ import annotations

import hashlib
import re
from typing import Any

from .ingestion import infer_retailer
from .models import CompetitorNormalized, RawRow, Retailer

FIELD_ALIASES = {
    "brand": ["brand", "brand_name", "브랜드"],
    "product_name": ["product_name", "제품명", "name"],
    "description_raw": ["about the product", "description", "description_raw", "details_original"],
    "claims_raw": ["highlights", "key benefits", "claims", "claims_raw", "details_original"],
    "ingredients_raw": ["ingredients", "ingredients_original", "highlighted ingredients"],
    "how_to_use_raw": ["usage_original", "how to use", "사용법"],
    "target_hair_type_raw": ["hair type", "hair texture", "scent type"],
    "target_concern_raw": ["hair concerns", "key notes"],
    "product_url": ["product_url", "url"],
    "image_url": ["image_url", "image"],
    "price_usd": ["price", "price_usd"],
    "rating": ["rating"],
    "review_count": ["review_count", "reviews"],
    "size": ["size"],
}

CATEGORY_RULES = {
    "shampoo": ["shampoo"],
    "conditioner": ["conditioner"],
    "mask": ["mask", "masque"],
    "serum": ["serum", "drops"],
    "oil": ["oil"],
    "scalp_treatment": ["scalp", "rosemary", "density"],
    "leave_in": ["leave-in", "leave in", "detangling"],
    "styling": ["spray", "mousse", "gel", "cream", "styling"],
    "bundle": ["set", "kit", "bundle"],
}


def normalize_rows(rows: list[RawRow]) -> list[CompetitorNormalized]:
    return [normalize_row(row) for row in rows]


def normalize_row(row: RawRow) -> CompetitorNormalized:
    lookup = {_clean_key(key): value for key, value in row.values.items()}
    retailer, retailer_source, retailer_confidence = _retailer(row, lookup)
    brand = _text(_pick(lookup, FIELD_ALIASES["brand"]))
    product_name = _text(_pick(lookup, FIELD_ALIASES["product_name"]))
    description = _combine(lookup, FIELD_ALIASES["description_raw"])
    claims = _combine(lookup, FIELD_ALIASES["claims_raw"])
    ingredients = _combine(lookup, FIELD_ALIASES["ingredients_raw"])
    hair_types = _combine(lookup, FIELD_ALIASES["target_hair_type_raw"])
    concerns = _combine(lookup, FIELD_ALIASES["target_concern_raw"])
    record_id = _record_id(row, retailer, brand, product_name)
    return CompetitorNormalized(
        record_id=record_id,
        source_file=row.source_file,
        source_sheet=row.source_sheet,
        row_index=row.row_index,
        retailer=retailer,
        retailer_inference_source=retailer_source,
        retailer_confidence=retailer_confidence,
        brand=brand,
        product_name=product_name,
        category=_category(product_name, claims, description),
        price_usd=_float(_pick(lookup, FIELD_ALIASES["price_usd"])),
        size=_text(_pick(lookup, FIELD_ALIASES["size"])),
        description_raw=description,
        claims_raw=claims,
        ingredients_raw=ingredients,
        how_to_use_raw=_combine(lookup, FIELD_ALIASES["how_to_use_raw"]),
        rating=_float(_pick(lookup, FIELD_ALIASES["rating"])),
        review_count=_int(_pick(lookup, FIELD_ALIASES["review_count"])),
        target_hair_type_raw=hair_types,
        target_concern_raw=concerns,
        product_url=_text(_pick(lookup, FIELD_ALIASES["product_url"])),
        image_url=_text(_pick(lookup, FIELD_ALIASES["image_url"])),
        extra_raw_fields=row.values,
    )


def _retailer(row: RawRow, lookup: dict[str, Any]) -> tuple[Retailer, str, float]:
    file_retailer = infer_retailer(row.source_file)
    if file_retailer != "unknown":
        return file_retailer, "source_file", 0.99
    sheet_retailer = infer_retailer(row.source_sheet)
    if sheet_retailer != "unknown":
        return sheet_retailer, "source_sheet", 0.9
    values = " ".join(_text(value) for value in lookup.values())
    row_retailer = infer_retailer(values)
    if row_retailer != "unknown":
        return row_retailer, "row_context", 0.6
    return "unknown", "none", 0.0


def _clean_key(key: str) -> str:
    return re.sub(r"\s+", " ", key.strip().lower())


def _pick(lookup: dict[str, Any], aliases: list[str]) -> Any:
    for alias in aliases:
        for key, value in lookup.items():
            if alias in key:
                return value
    return None


def _combine(lookup: dict[str, Any], aliases: list[str]) -> str:
    parts: list[str] = []
    for alias in aliases:
        for key, value in lookup.items():
            if alias in key:
                text = _text(value)
                if text and text not in parts and text.upper() != "N/A":
                    parts.append(text)
    return " / ".join(parts)


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _float(value: Any) -> float | None:
    match = re.search(r"\d+(?:\.\d+)?", _text(value).replace(",", ""))
    return float(match.group(0)) if match else None


def _int(value: Any) -> int | None:
    match = re.search(r"\d+", _text(value).replace(",", ""))
    return int(match.group(0)) if match else None


def _category(*texts: str) -> str:
    joined = " ".join(texts).lower()
    for category, needles in CATEGORY_RULES.items():
        if any(needle in joined for needle in needles):
            return category
    return "other"


def _record_id(row: RawRow, retailer: str, brand: str, product_name: str) -> str:
    raw = f"{row.source_file}|{row.source_sheet}|{row.row_index}|{retailer}|{brand}|{product_name}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]

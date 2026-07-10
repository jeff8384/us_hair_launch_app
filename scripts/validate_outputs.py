from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import validate

JSON_FILES = {
    "competitor_gaps.json": "competitor_gaps.schema.json",
    "message_map_candidates.json": "message_map_candidates.schema.json",
    "pdp_blocks.json": "pdp_blocks.schema.json",
}
JSONL_FILES = {
    "competitor_normalized.jsonl": "competitor_normalized.schema.json",
    "competitor_claims.jsonl": "competitor_claims.schema.json",
}


def main() -> int:
    processed = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/processed")
    exports = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data/exports")
    schemas = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("schemas")
    for filename, schema_name in JSON_FILES.items():
        instance = json.loads((processed / filename).read_text())
        schema = json.loads((schemas / schema_name).read_text())
        validate(instance, schema)
    for filename, schema_name in JSONL_FILES.items():
        schema = json.loads((schemas / schema_name).read_text())
        lines = (processed / filename).read_text().splitlines()
        if not lines:
            raise RuntimeError(f"{filename} is empty")
        for line in lines:
            validate(json.loads(line), schema)
    markdown = exports / "pdp_copy_drafts.md"
    if not markdown.exists() or not markdown.read_text().strip():
        raise RuntimeError("pdp_copy_drafts.md missing or empty")
    sys.stdout.write("validated outputs\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

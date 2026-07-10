from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import orjson
from pydantic import BaseModel


def dump_json(path: Path, payload: BaseModel | dict[str, Any] | list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, BaseModel):
        path.write_text(payload.model_dump_json(indent=2) + "\n", encoding="utf-8")
        return
    path.write_bytes(orjson.dumps(payload, option=orjson.OPT_INDENT_2) + b"\n")


def dump_jsonl(path: Path, rows: Sequence[BaseModel]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(row.model_dump_json() + "\n")

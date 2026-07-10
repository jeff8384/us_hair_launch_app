from __future__ import annotations

import argparse
from pathlib import Path

from rich import print_json

from .pipeline import run_pipeline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="us-hair-launch")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run-pipeline")
    run_parser.add_argument("--input", type=Path, default=Path("/Users/sy/us_hair"))
    run_parser.add_argument("--output", type=Path, default=Path("data/processed"))
    run_parser.add_argument("--exports", type=Path, default=Path("data/exports"))
    run_parser.add_argument("--schemas", type=Path, default=Path("schemas"))
    run_parser.add_argument("--ai-backend", default="deterministic")
    args = parser.parse_args(argv)
    if args.command == "run-pipeline":
        result = run_pipeline(args.input, args.output, args.exports, args.schemas, args.ai_backend)
        print_json(data=result.model_dump())
        return 0
    return 2


def app() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    app()

# US Hair Launch App

Local-first Python web app for US hair-care competitor analysis and PDP copy workflow.

## Setup

```bash
cd /Users/sy/us_hair_launch_app
uv sync
```

The app is optimized for local competitor source files under:

```text
/Users/sy/us_hair
```

## Run

```bash
./run_us_hair_app.sh
```

Open:

```text
http://127.0.0.1:8015
```

## Local AI

Run with a local `llama-server` backend:

```bash
./run_us_hair_app.sh --with-llama --llama-model gemma
```

Run with EXAONE Deep:

```bash
US_HAIR_LLAMA_MODEL=exaone ./run_us_hair_app.sh --with-llama
```

By default, the app uses:

- app port: `8015`
- llama-server port: `8080`
- Ollama-compatible port remains available at `11434`

## Validate

```bash
uv run ruff check .
uv run basedpyright
uv run pytest -q
```

## Outputs

Generated workflow outputs are written under:

- `data/processed/`
- `data/exports/`

Schema files live under:

- `schemas/`

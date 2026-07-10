#!/bin/zsh
set -euo pipefail

APP_DIR="/Users/sy/us_hair_launch_app"
PYTHON_BIN="$APP_DIR/.venv/bin/python"
export PYTHONPATH="$APP_DIR/src"
APP_HOST="${US_HAIR_HOST:-127.0.0.1}"
APP_PORT="${US_HAIR_PORT:-8015}"
WITH_LLAMA=false
LLAMA_MODEL_CHOICE="${US_HAIR_LLAMA_MODEL:-gemma}"

usage() {
  cat <<'EOF'
Usage: run_us_hair_app.sh [--with-llama] [--llama-model gemma|exaone|/path/model.gguf]

Starts the US Hair Launch local web app at http://127.0.0.1:8015.

Environment:
  US_HAIR_HOST   Bind host. Defaults to 127.0.0.1.
  US_HAIR_PORT   Bind port. Defaults to 8015.
  US_HAIR_LLAMA_MODEL  llama-server model choice or path. Defaults to gemma.
  US_HAIR_LLAMA_PORT   llama-server port. Defaults to 8080 to avoid Ollama's 11434.

Options:
  --with-llama   Also start/check the local llama-server backend.
  --llama-model  Select llama-server model. Choices: gemma, exaone, or a GGUF path.
  -h, --help     Show this help.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-llama)
      WITH_LLAMA=true
      shift
      ;;
    --llama-model)
      if [[ $# -lt 2 ]]; then
        echo "[ERROR] --llama-model requires gemma, exaone, or a GGUF path" >&2
        exit 2
      fi
      LLAMA_MODEL_CHOICE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[ERROR] Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

LLAMA_SERVER_BIN="$(command -v llama-server || true)"
GEMMA_MODEL="/Users/sy/gemma-4-12B-it-Q4_K_M.gguf"
EXAONE_MODEL="/Users/sy/EXAONE-Deep-7.8B-Q8_0.gguf"
LLAMA_MODEL=""
LLAMA_HOST="127.0.0.1"
LLAMA_PORT="${US_HAIR_LLAMA_PORT:-8080}"
LLAMA_PID_FILE="$APP_DIR/.llama-server.pid"

resolve_llama_model() {
  case "$LLAMA_MODEL_CHOICE" in
    gemma|Gemma)
      LLAMA_MODEL="$GEMMA_MODEL"
      ;;
    exaone|EXAONE|exaone-deep|EXAONE-Deep)
      LLAMA_MODEL="$EXAONE_MODEL"
      ;;
    /*.gguf|*.gguf)
      LLAMA_MODEL="$LLAMA_MODEL_CHOICE"
      ;;
    *)
      echo "[ERROR] Unknown --llama-model value: $LLAMA_MODEL_CHOICE" >&2
      echo "[ERROR] Use gemma, exaone, or a GGUF path" >&2
      exit 2
      ;;
  esac
}

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "[ERROR] Python virtualenv not found: $PYTHON_BIN" >&2
  echo "[ERROR] Run: cd $APP_DIR && uv sync" >&2
  exit 1
fi

ensure_llama_server() {
  resolve_llama_model

  if [[ -z "$LLAMA_SERVER_BIN" ]]; then
    echo "[ERROR] llama-server not found in PATH" >&2
    exit 1
  fi

  if [[ ! -f "$LLAMA_MODEL" ]]; then
    echo "[ERROR] GGUF model not found: $LLAMA_MODEL" >&2
    exit 1
  fi

  if curl -fsS "http://$LLAMA_HOST:$LLAMA_PORT/health" >/dev/null 2>&1; then
    echo "[INFO] llama-server already responding on http://$LLAMA_HOST:$LLAMA_PORT"
    echo "[INFO] Requested model for app calls: $(basename "$LLAMA_MODEL")"
    local loaded_models
    loaded_models="$(curl -fsS "http://$LLAMA_HOST:$LLAMA_PORT/v1/models" 2>/dev/null || true)"
    if [[ -n "$loaded_models" && "$loaded_models" != *"$(basename "$LLAMA_MODEL")"* ]]; then
      echo "[WARN] Existing llama-server does not report requested model: $(basename "$LLAMA_MODEL")" >&2
      echo "[WARN] Stop the existing llama-server, or change LLAMA_PORT before switching models." >&2
    fi
    return 0
  fi

  if command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:"$LLAMA_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "[ERROR] Port $LLAMA_PORT is already in use, but it is not a healthy llama-server endpoint." >&2
    lsof -nP -iTCP:"$LLAMA_PORT" -sTCP:LISTEN >&2 || true
    echo "[ERROR] Set US_HAIR_LLAMA_PORT to a free port or stop the process using $LLAMA_PORT." >&2
    exit 1
  fi

  echo "[INFO] Starting llama-server with model: $LLAMA_MODEL"
  "$LLAMA_SERVER_BIN" -m "$LLAMA_MODEL" --host "$LLAMA_HOST" --port "$LLAMA_PORT" >/tmp/us_hair_llama_server.log 2>&1 &
  local llama_pid=$!
  echo "$llama_pid" > "$LLAMA_PID_FILE"

  for _ in {1..180}; do
    if ! kill -0 "$llama_pid" >/dev/null 2>&1; then
      echo "[ERROR] llama-server exited before becoming ready. Check /tmp/us_hair_llama_server.log" >&2
      tail -n 40 /tmp/us_hair_llama_server.log >&2 || true
      exit 1
    fi
    if curl -fsS "http://$LLAMA_HOST:$LLAMA_PORT/health" >/dev/null 2>&1; then
      echo "[INFO] llama-server ready on http://$LLAMA_HOST:$LLAMA_PORT"
      return 0
    fi
    sleep 1
  done

  echo "[ERROR] llama-server failed to become ready. Check /tmp/us_hair_llama_server.log" >&2
  tail -n 40 /tmp/us_hair_llama_server.log >&2 || true
  exit 1
}

if [[ "$WITH_LLAMA" == true ]]; then
  ensure_llama_server
  export OLLAMA_BASE_URL="http://$LLAMA_HOST:$LLAMA_PORT"
  export OLLAMA_MODEL="$(basename "$LLAMA_MODEL")"
  export LLAMA_SERVER_BASE_URL="http://$LLAMA_HOST:$LLAMA_PORT"
  export LLAMA_SERVER_MODEL="$(basename "$LLAMA_MODEL")"
fi

cd "$APP_DIR"

echo "[INFO] Starting US Hair Launch app..."
echo "[INFO] App dir: $APP_DIR"
echo "[INFO] Python: $PYTHON_BIN"
echo "[INFO] URL: http://$APP_HOST:$APP_PORT"
if [[ "$WITH_LLAMA" == true ]]; then
  echo "[INFO] Local AI backend: $(basename "$LLAMA_MODEL") via llama-server ($LLAMA_SERVER_MODEL)"
else
  echo "[INFO] Local AI backend: disabled by default; use --with-llama to enable it"
fi
exec "$PYTHON_BIN" -m uvicorn --app-dir "$APP_DIR/src" us_hair_launch.web:app --host "$APP_HOST" --port "$APP_PORT"

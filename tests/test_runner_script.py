import json
import os
import subprocess
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


def test_runner_script_starts_web_app_from_outside_project() -> None:
    script = Path(__file__).parents[1] / "run_us_hair_app.sh"
    port = "8767"
    env = os.environ.copy()
    env["US_HAIR_PORT"] = port
    process = subprocess.Popen(
        [str(script)],
        cwd="/Users/sy",
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        deadline = time.monotonic() + 20
        payload: dict[str, object] | None = None
        while time.monotonic() < deadline:
            if process.poll() is not None:
                output = process.stdout.read() if process.stdout is not None else ""
                raise AssertionError(f"runner exited before serving preview:\n{output}")
            try:
                with urlopen(f"http://127.0.0.1:{port}/api/preview", timeout=1) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    break
            except URLError:
                time.sleep(0.25)

        assert payload is not None
        assert payload["files"]
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def test_runner_script_documents_exaone_model_option() -> None:
    script = Path(__file__).parents[1] / "run_us_hair_app.sh"

    result = subprocess.run(
        [str(script), "--help"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "--llama-model gemma|exaone|/path/model.gguf" in result.stdout
    assert "US_HAIR_LLAMA_MODEL" in result.stdout
    assert "US_HAIR_LLAMA_PORT" in result.stdout
    assert "8080" in result.stdout
    assert "exaone" in result.stdout

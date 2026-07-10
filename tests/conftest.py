from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def real_input_dir() -> Path:
    return Path("/Users/sy/us_hair")


@pytest.fixture()
def app_output_dir(tmp_path: Path) -> Path:
    return tmp_path / "processed"


@pytest.fixture()
def app_exports_dir(tmp_path: Path) -> Path:
    return tmp_path / "exports"

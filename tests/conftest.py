import pytest
from pathlib import Path

@pytest.fixture(scope="session")
def tests_dir() -> Path:
    return Path(__file__).parent

@pytest.fixture
def load_fga_schema(tests_dir: Path):
    def _load(filename: str) -> str:
        with open(tests_dir / filename, 'r') as f:
            return f.read()
    return _load

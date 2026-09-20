"""Fixtures shared by the tests."""

from pathlib import Path

import pytest

DATA_DIR = Path(__file__).parent / "data"


@pytest.fixture
def sample() -> "SampleLoader":
    """Return a loader for the sample records of `tests/data`."""
    return SampleLoader(DATA_DIR)


class SampleLoader:
    """Reads the sample records used by the parser tests."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def __call__(self, name: str) -> bytes:
        """Return the bytes of `tests/data/{name}`."""
        return (self.directory / name).read_bytes()

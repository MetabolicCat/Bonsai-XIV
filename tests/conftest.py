import sys
from pathlib import Path

import pytest

# The test helpers are modules that sit beside the tests.
sys.path.insert(0, str(Path(__file__).parent))

from upstream import Upstream

from bonsai.cache import Cache


@pytest.fixture
def upstream() -> Upstream:
    return Upstream()


@pytest.fixture
def cache(tmp_path: Path) -> Cache:
    return Cache(tmp_path / "cache")

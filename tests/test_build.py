import sqlite3
from pathlib import Path

import pytest
from upstream import Upstream

from bonsai.build import build
from bonsai.cache import Cache
from bonsai.refresh import refresh_game


@pytest.fixture
def upstream() -> Upstream:
    return Upstream()


@pytest.fixture
def cache(tmp_path: Path) -> Cache:
    return Cache(tmp_path / "cache")


def built(upstream: Upstream, cache: Cache) -> sqlite3.Connection:
    with upstream.client() as client:
        refresh_game(client, cache)
    build(cache)
    return sqlite3.connect(cache.database)


def test_items_are_built_from_the_item_sheet(upstream: Upstream, cache: Cache) -> None:
    upstream.sheets["Item"] = [
        {"#": 5057, "Name": "Iron Ingot", "StackSize": 999},
    ]

    db = built(upstream, cache)

    assert db.execute("SELECT id, name, stack_size FROM item").fetchall() == [
        (5057, "Iron Ingot", 999)
    ]

import re
import sqlite3
from pathlib import Path

import pytest
from upstream import Upstream

from bonsai.build import build
from bonsai.cache import Cache
from bonsai.refresh import refresh_game, refresh_market

IRON_INGOT, IRON_ORE, FIRE_SHARD, UNSOLD = 5057, 5111, 2, 9999


@pytest.fixture
def upstream() -> Upstream:
    upstream = Upstream()
    upstream.sheets["CraftType"] = [{"#": 1, "Name": "Smithing"}]
    upstream.sheets["RecipeLevelTable"] = [{"#": 1, "ClassJobLevel": 1, "Stars": 0}]
    upstream.sheets["Item"] = [
        {"#": IRON_INGOT, "Name": "Iron Ingot", "ItemSearchCategory": 48},
        {"#": IRON_ORE, "Name": "Iron Ore", "ItemSearchCategory": 48},
        {"#": FIRE_SHARD, "Name": "Fire Shard"},
        {"#": UNSOLD, "Name": "Not In Any Recipe", "ItemSearchCategory": 48},
    ]
    upstream.sheets["Recipe"] = [
        {
            "#": 43,
            "CraftType": 1,
            "ItemResult": IRON_INGOT,
            "RecipeLevelTable": 1,
            "Ingredient[0]": IRON_ORE,
            "AmountIngredient[0]": 3,
            "Ingredient[6]": FIRE_SHARD,
            "AmountIngredient[6]": 1,
        }
    ]
    return upstream


@pytest.fixture
def cache(tmp_path: Path, upstream: Upstream) -> Cache:
    cache = Cache(tmp_path / "cache")
    with upstream.client() as client:
        refresh_game(client, cache)
    build(cache)
    return cache


def market(upstream: Upstream, cache: Cache, scope: str = "Japan") -> None:
    with upstream.client() as client:
        refresh_market(client, cache, scope)
    build(cache)


def aggregated(price: int, average: float, velocity: float) -> dict[str, object]:
    return {
        "minListing": {"region": {"price": price, "worldId": 72}},
        "averageSalePrice": {"region": {"price": average}},
        "dailySaleVelocity": {"region": {"quantity": velocity}},
    }


def test_market_data_is_fetched_for_marketable_items_of_the_tree(
    upstream: Upstream, cache: Cache
) -> None:
    upstream.market[IRON_INGOT] = {
        "nq": aggregated(100, 150.5, 30.0),
        "hq": aggregated(400, 420.0, 2.5),
    }
    upstream.market[IRON_ORE] = {"nq": aggregated(10, 12.0, 900.0), "hq": {}}

    market(upstream, cache)

    db = sqlite3.connect(cache.database)
    assert db.execute("SELECT * FROM market ORDER BY item_id, hq").fetchall() == [
        (IRON_INGOT, False, 100, 150.5, 30.0),
        (IRON_INGOT, True, 400, 420.0, 2.5),
        (IRON_ORE, False, 10, 12.0, 900.0),
    ]
    assert [path for path in upstream.requests if "universalis" in path] == [
        f"universalis.app/api/v2/aggregated/Japan/{IRON_INGOT},{IRON_ORE}"
    ]


def test_the_tree_records_the_versions_it_was_built_from(
    upstream: Upstream, cache: Cache
) -> None:
    market(upstream, cache, scope="Elemental")

    db = sqlite3.connect(cache.database)
    meta = dict(db.execute("SELECT key, value FROM meta").fetchall())
    assert meta.pop("market_fetched_at") == AnyIsoTime()
    assert meta == {
        "datamining_version": upstream.datamining_commit,
        "teamcraft_version": upstream.teamcraft_commit,
        "market_scope": "Elemental",
    }


def test_items_are_asked_for_in_batches_of_100(
    upstream: Upstream, cache: Cache
) -> None:
    items = range(10000, 10250)
    upstream.sheets["Item"] += [
        {"#": item, "Name": f"Item {item}", "ItemSearchCategory": 48} for item in items
    ]
    upstream.sheets["Recipe"] += [
        {"#": item, "CraftType": 1, "ItemResult": item, "RecipeLevelTable": 1}
        for item in items
    ]
    upstream.datamining_commit = "f" * 40
    with upstream.client() as client:
        refresh_game(client, cache)
    build(cache)

    market(upstream, cache)

    batches = [path for path in upstream.requests if "universalis" in path]
    assert [len(path.rsplit("/", 1)[1].split(",")) for path in batches] == [
        100,
        100,
        52,
    ]


class AnyIsoTime:
    def __eq__(self, other: object) -> bool:
        return isinstance(other, str) and bool(
            re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", other)
        )


def test_progress_is_reported_after_each_batch(
    upstream: Upstream, cache: Cache
) -> None:
    items = range(10000, 10150)
    upstream.sheets["Item"] += [
        {"#": item, "Name": f"Item {item}", "ItemSearchCategory": 48} for item in items
    ]
    upstream.sheets["Recipe"] += [
        {"#": item, "CraftType": 1, "ItemResult": item, "RecipeLevelTable": 1}
        for item in items
    ]
    upstream.datamining_commit = "f" * 40
    with upstream.client() as client:
        refresh_game(client, cache)
    build(cache)
    reports: list[tuple[int, int]] = []

    with upstream.client() as client:
        refresh_market(
            client, cache, "Japan", progress=lambda *done: reports.append(done)
        )

    assert reports == [(100, 152), (152, 152)]

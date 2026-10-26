import sqlite3
from pathlib import Path

import pytest
from tree import built, named, sources
from upstream import Upstream

from bonsai.cache import Cache

IRON_ORE, SKIN, GLUE, POETICS = 5111, 44000, 44001, 28


@pytest.fixture
def upstream() -> Upstream:
    upstream = Upstream()
    upstream.sheets["Item"] = [
        {"#": IRON_ORE, "Name": "Iron Ore", "PriceMid": 18},
        *named(SKIN, GLUE, POETICS),
    ]
    upstream.sheets["GilShopItem"] = [{"#": "262173.0", "Item": IRON_ORE}]
    upstream.sheets["SpecialShop"] = [
        {
            "#": 1770417,
            "Item[0].Item[0]": SKIN,
            "Item[0].ReceiveCount[0]": 1,
            "Item[0].ItemCost[0]": POETICS,
            "Item[0].CurrencyCost[0]": 15,
        },
    ]
    return upstream


def overrides(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content)
    return path


def test_without_overrides_the_sources_are_the_built_ones(
    upstream: Upstream, cache: Cache
) -> None:
    assert sources(built(upstream, cache)) == [
        (IRON_ORE, "gil_shop", 262173, 1, ((1, 18),)),
        (SKIN, "special_shop", 1770417, 1, ((POETICS, 15),)),
    ]


def test_an_override_replaces_the_sources_of_its_item_kind_and_ref(
    tmp_path: Path, upstream: Upstream, cache: Cache
) -> None:
    fix = overrides(
        tmp_path,
        "overrides.toml",
        """
        [[source]]
        item = 44000
        kind = "special_shop"
        ref = 1770417
        amount = 1
        costs = [{ item = 28, amount = 20 }]

        [[source]]
        item = 44000
        kind = "special_shop"
        ref = 1770417
        amount = 3
        costs = [{ item = 28, amount = 50 }]
        """,
    )

    assert sources(built(upstream, cache, [fix])) == [
        (IRON_ORE, "gil_shop", 262173, 1, ((1, 18),)),
        (SKIN, "special_shop", 1770417, 1, ((POETICS, 20),)),
        (SKIN, "special_shop", 1770417, 3, ((POETICS, 50),)),
    ]


def test_an_override_adds_a_source_the_build_did_not_find(
    tmp_path: Path, upstream: Upstream, cache: Cache
) -> None:
    fix = overrides(
        tmp_path,
        "overrides.toml",
        """
        [[source]]
        item = 44001
        kind = "drop"
        ref = 38
        """,
    )

    assert (GLUE, "drop", 38, None, ()) in sources(built(upstream, cache, [fix]))


def test_an_override_removes_a_source(
    tmp_path: Path, upstream: Upstream, cache: Cache
) -> None:
    fix = overrides(
        tmp_path,
        "overrides.toml",
        """
        [[source]]
        item = 5111
        kind = "gil_shop"
        ref = 262173
        remove = true
        """,
    )

    assert sources(built(upstream, cache, [fix])) == [
        (SKIN, "special_shop", 1770417, 1, ((POETICS, 15),)),
    ]


def test_a_later_file_wins_for_the_same_item_kind_and_ref(
    tmp_path: Path, upstream: Upstream, cache: Cache
) -> None:
    shared = overrides(
        tmp_path,
        "shared.toml",
        """
        [[source]]
        item = 44000
        kind = "special_shop"
        ref = 1770417
        amount = 1
        costs = [{ item = 28, amount = 20 }]

        [[source]]
        item = 44001
        kind = "drop"
        ref = 38
        """,
    )
    personal = overrides(
        tmp_path,
        "personal.toml",
        """
        [[source]]
        item = 44000
        kind = "special_shop"
        ref = 1770417
        amount = 1
        costs = [{ item = 28, amount = 25 }]
        """,
    )

    assert sources(built(upstream, cache, [shared, personal])) == [
        (IRON_ORE, "gil_shop", 262173, 1, ((1, 18),)),
        (SKIN, "special_shop", 1770417, 1, ((POETICS, 25),)),
        (GLUE, "drop", 38, None, ()),
    ]


@pytest.mark.parametrize(
    ("entry", "error"),
    [
        ('item = 99999\nkind = "drop"\nref = 1', "unknown item 99999"),
        ('item = 44001\nkind = "dorp"\nref = 1', "unknown kind 'dorp'"),
        (
            'item = 44001\nkind = "trade"\ncosts = [{ item = 99999, amount = 1 }]',
            "unknown item 99999",
        ),
        ("kind = 'drop'", "'item'"),
    ],
)
def test_a_mistake_in_an_override_stops_the_build(
    tmp_path: Path, upstream: Upstream, cache: Cache, entry: str, error: str
) -> None:
    fix = overrides(tmp_path, "overrides.toml", f"[[source]]\n{entry}\n")

    with pytest.raises(ValueError, match=error) as raised:
        built(upstream, cache, [fix])

    assert str(fix) in str(raised.value)


def test_a_removal_stands_alone(
    tmp_path: Path, upstream: Upstream, cache: Cache
) -> None:
    fix = overrides(
        tmp_path,
        "overrides.toml",
        """
        [[source]]
        item = 5111
        kind = "gil_shop"
        ref = 262173
        remove = true

        [[source]]
        item = 5111
        kind = "gil_shop"
        ref = 262173
        amount = 1
        costs = [{ item = 1, amount = 20 }]
        """,
    )

    with pytest.raises(ValueError, match="remove"):
        built(upstream, cache, [fix])


def test_a_failed_build_keeps_the_previous_tree(
    tmp_path: Path, upstream: Upstream, cache: Cache
) -> None:
    built(upstream, cache)
    fix = overrides(
        tmp_path, "overrides.toml", "[[source]]\nitem = 99999\nkind = 'drop'\n"
    )

    with pytest.raises(ValueError):
        built(upstream, cache, [fix])

    assert len(sources(sqlite3.connect(cache.database))) == 2

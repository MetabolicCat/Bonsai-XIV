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


def test_items_carry_what_pruning_needs_to_know(
    upstream: Upstream, cache: Cache
) -> None:
    upstream.sheets["ItemUICategory"] = [{"#": 46, "Name": "Meal"}]
    upstream.sheets["Item"] = [
        {
            "#": 4650,
            "Name": "Boiled Egg",
            "StackSize": 999,
            "CanBeHq": "True",
            "IsUntradable": "False",
            "ItemSearchCategory": 45,
            "ItemUICategory": 46,
            "LevelItem": 5,
            "LevelEquip": 1,
        },
        {
            "#": 2,
            "Name": "Fire Shard",
            "StackSize": 9999,
            "CanBeHq": "False",
            "IsUntradable": "True",
            "ItemSearchCategory": 0,
            "ItemUICategory": 0,
            "LevelItem": 1,
            "LevelEquip": 1,
        },
    ]

    db = built(upstream, cache)

    assert db.execute(
        "SELECT id, can_be_hq, untradable, marketable, ui_category,"
        " item_level, equip_level FROM item ORDER BY id"
    ).fetchall() == [
        (2, False, True, False, None, 1, 1),
        (4650, True, False, True, "Meal", 5, 1),
    ]


def test_recipes_link_an_item_to_its_ingredients(
    upstream: Upstream, cache: Cache
) -> None:
    upstream.sheets["CraftType"] = [{"#": 1, "Name": "Smithing"}]
    upstream.sheets["RecipeLevelTable"] = [{"#": 16, "ClassJobLevel": 16, "Stars": 0}]
    upstream.sheets["Recipe"] = [
        {"#": 0, "ItemResult": 0},
        {
            "#": 43,
            "CraftType": 1,
            "ItemResult": 5057,
            "AmountResult": 1,
            "RecipeLevelTable": 16,
            "Ingredient[0]": 5111,
            "AmountIngredient[0]": 3,
            "Ingredient[6]": 2,
            "AmountIngredient[6]": 1,
            "SecretRecipeBook": 0,
            "IsExpert": "False",
        },
    ]

    db = built(upstream, cache)

    assert db.execute("SELECT * FROM recipe").fetchall() == [
        (43, 5057, 1, "Smithing", 16, 0, False, False)
    ]
    assert db.execute("SELECT * FROM ingredient ORDER BY item_id").fetchall() == [
        (43, 2, 1),
        (43, 5111, 3),
    ]


def test_recipe_level_and_master_book(upstream: Upstream, cache: Cache) -> None:
    upstream.sheets["CraftType"] = [{"#": 7, "Name": "Cooking"}]
    upstream.sheets["RecipeLevelTable"] = [{"#": 690, "ClassJobLevel": 100, "Stars": 2}]
    upstream.sheets["Recipe"] = [
        {
            "#": 35000,
            "CraftType": 7,
            "ItemResult": 44000,
            "AmountResult": 3,
            "RecipeLevelTable": 690,
            "SecretRecipeBook": 12,
            "IsExpert": "True",
        },
    ]

    db = built(upstream, cache)

    assert db.execute("SELECT * FROM recipe").fetchall() == [
        (35000, 44000, 3, "Cooking", 100, 2, True, True)
    ]

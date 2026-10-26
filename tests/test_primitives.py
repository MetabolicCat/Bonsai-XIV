from typing import Any

import pytest
from upstream import Upstream
from world import World

from bonsai.cache import Cache
from bonsai.primitives import Primitives


@pytest.fixture
def world(upstream: Upstream, cache: Cache) -> World:
    return World(upstream, cache)


def primitives(world: World, recipe: int, **parameters: Any) -> dict[str, Any]:
    tree = world.tree()
    return Primitives(tree, parameters).of(tree.recipes[recipe])


def test_a_recipe_describes_itself_and_its_item(world: World) -> None:
    ore, shard = world.item(1), world.crystal(2)
    stew = world.item(10, "Stew", stack=99, hq=True, category="Meal", equip=63)
    world.recipe(100, stew, {ore: 3, shard: 2}, job="Cooking", level=63, stars=1)

    values = primitives(world, 100)

    assert {
        key: values[key]
        for key in [
            "recipe_id",
            "item_id",
            "name",
            "job",
            "level",
            "stars",
            "level_band",
            "amount",
            "burden",
            "ingredients",
            "crystals",
            "stack_size",
            "stackable",
            "can_be_hq",
            "ui_category",
            "equip_level",
            "level_cap",
            "expert",
            "master_book",
        ]
    } == {
        "recipe_id": 100,
        "item_id": 10,
        "name": "Stew",
        "job": "Cooking",
        "level": 63,
        "stars": 1,
        "level_band": 61,
        "amount": 1,
        "burden": 3,
        "ingredients": 1,
        "crystals": 2,
        "stack_size": 99,
        "stackable": True,
        "can_be_hq": True,
        "ui_category": "Meal",
        "equip_level": 63,
        "level_cap": 70,
        "expert": False,
        "master_book": False,
    }


def test_parameters_set_level_bands_and_caps(world: World) -> None:
    item = world.item(10)
    world.recipe(100, item, {}, level=63)
    above = world.item(11)
    world.recipe(101, above, {}, level=95)

    values = primitives(world, 100, band_size=5, level_caps=[90])

    assert (values["level_band"], values["level_cap"]) == (61, 90)
    assert primitives(world, 101, level_caps=[90])["level_cap"] is None


def test_leves_are_a_sink(world: World) -> None:
    item = world.item(10)
    world.recipe(100, item, {})
    world.leve(36, item, level=15)
    world.leve(37, item, level=5)
    other = world.item(11)
    world.recipe(101, other, {})

    tree = world.tree()
    found = Primitives(tree, {})

    assert [
        (found.of(tree.recipes[r])["leve"], found.of(tree.recipes[r])["leve_level"])
        for r in (100, 101)
    ] == [(True, 5), (False, None)]


def test_the_market_of_an_hq_item_is_its_hq_one(world: World) -> None:
    item = world.item(10, hq=True)
    world.recipe(100, item, {})
    world.market(item, 1000, 900.0, 2.0)
    world.market(item, 3000, 2800.0, 5.0, hq=True)

    values = primitives(world, 100)

    assert (
        values["min_listing"],
        values["average_price"],
        values["price"],
        values["velocity"],
        values["turnover"],
    ) == (3000, 2800.0, 2800.0, 5.0, 14000.0)


def test_the_price_is_capped_by_the_lowest_listing(world: World) -> None:
    """Sales that move gil between players make an average meaningless."""
    item = world.item(10)
    world.recipe(100, item, {})
    world.market(item, 150, 41_620_706.9, 2.0)

    assert primitives(world, 100)["price"] == 450
    assert primitives(world, 100, price_cap=10)["price"] == 1500


def test_with_no_listing_the_price_is_the_average(world: World) -> None:
    item = world.item(10)
    world.recipe(100, item, {})
    world.market(item, None, 500.0, 1.0)

    assert primitives(world, 100)["price"] == 500.0


def test_without_market_data_the_market_is_unknown(world: World) -> None:
    item = world.item(10)
    world.recipe(100, item, {})

    values = primitives(world, 100)

    assert [values[key] for key in ["price", "velocity", "turnover"]] == [None] * 3


def test_craft_cost_buys_each_ingredient_where_it_is_cheapest(world: World) -> None:
    ore = world.item(1)
    world.sold(ore, 18)
    world.market(ore, 10, 12.0, 100.0)
    sand = world.item(2)
    world.sold(sand, 5)
    ingot = world.item(3)
    world.recipe(100, ingot, {ore: 3, sand: 1}, amount=2)  # 35 gil for 2
    world.market(ingot, 100, 100.0, 1.0)
    blade = world.item(4)
    world.recipe(101, blade, {ingot: 4})
    world.market(blade, 200, 200.0, 1.0)

    values = primitives(world, 101)

    # Ingots cost 17.5 to make, less than the 100 they are listed at.
    assert (values["craft_cost"], values["profit"]) == (70.0, 130.0)


def test_craft_cost_is_unknown_when_an_ingredient_cannot_be_priced(
    world: World,
) -> None:
    hide = world.item(1)
    world.dropped(hide)
    item = world.item(10)
    world.recipe(100, item, {hide: 1})

    assert primitives(world, 100)["craft_cost"] is None


def test_leaves_are_counted_by_how_they_are_obtained(world: World) -> None:
    ore, log, hide, oddity, shard = (
        world.item(1),
        world.item(2),
        world.item(3),
        world.item(4),
        world.crystal(5),
    )
    world.sold(ore, 18)
    world.gathered(ore)
    world.gathered(log)
    world.dropped(hide)
    world.gathered(shard)
    board = world.item(10)
    world.recipe(100, board, {log: 2, shard: 1})
    item = world.item(11)
    world.recipe(101, item, {board: 1, ore: 1, hide: 1, oddity: 1, shard: 1})

    values = primitives(world, 101)

    assert {
        key: values[key]
        for key in [
            "leaves",
            "vendor_leaves",
            "gathered_leaves",
            "farmed_leaves",
            "unsourced_leaves",
        ]
    } == {
        "leaves": 4,
        "vendor_leaves": 1,
        "gathered_leaves": 2,
        "farmed_leaves": 1,
        "unsourced_leaves": 1,
    }


def test_every_primitive_is_documented_and_known(world: World) -> None:
    item = world.item(10)
    world.recipe(100, item, {})
    tree = world.tree()

    assert set(Primitives(tree, {}).of(tree.recipes[100])) == set(Primitives.NAMES)


def test_the_level_cap_of_a_consumable_is_the_one_of_its_recipe(world: World) -> None:
    """Meals and potions can be used from level 1: their recipe tells their tier."""
    draught = world.item(10, category="Medicine", equip=1)
    world.recipe(100, draught, {}, job="Alchemy", level=90)

    assert primitives(world, 100)["level_cap"] == 90

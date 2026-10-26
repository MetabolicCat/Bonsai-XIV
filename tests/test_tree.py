import pytest
from upstream import Upstream
from world import World

from bonsai.cache import Cache


@pytest.fixture
def world(upstream: Upstream, cache: Cache) -> World:
    return World(upstream, cache)


def test_the_preferred_recipe_of_an_item_is_its_lowest_level_one(
    world: World,
) -> None:
    ore = world.item(5111, "Iron Ore")
    shard = world.crystal(2)
    ingot = world.item(5057, "Iron Ingot")
    world.recipe(43, ingot, {ore: 3, shard: 1}, job="Smithing", level=16)
    world.recipe(189, ingot, {ore: 3, shard: 1}, job="Armorcraft", level=13)

    tree = world.tree()

    assert [recipe.id for recipe in tree.recipes_of(ingot)] == [43, 189]
    assert tree.preferred_recipe(ingot).id == 189
    assert tree.preferred_recipe(ore) is None
    assert tree.recipes[43].ingredients == {ore: 3, shard: 1}
    assert tree.items[ingot].name == "Iron Ingot"


def test_a_recipe_needs_base_ingredients_through_preferred_recipes(
    world: World,
) -> None:
    ore, sand, shard = world.item(1), world.item(2), world.crystal(3)
    ingot, rivet = world.item(10), world.item(11)
    world.recipe(100, ingot, {ore: 3, shard: 1})
    world.recipe(101, rivet, {ingot: 2, sand: 1}, amount=2)
    world.recipe(102, rivet, {ore: 50}, level=50)
    sword = world.item(12)
    world.recipe(103, sword, {rivet: 3, ingot: 1, shard: 2})

    tree = world.tree()

    # Averaged over many crafts: 3 rivets are 1.5 crafts making 2 each,
    # for 3 ingots and 1.5 sand; with the other ingot, 4 ingots need 12
    # ore and 4 shards.
    assert tree.base_ingredients(103) == {ore: 12, sand: 1.5, shard: 6}

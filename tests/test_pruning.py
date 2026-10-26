import pytest
from upstream import Upstream
from world import World

from bonsai.cache import Cache
from bonsai.pruning import prune
from bonsai.rules import Rules
from bonsai.tree import Tree

RULES = """
[[rule]]
name = "Gil-maker"
where = "turnover >= 1000"
score = "turnover"
keep = 1
"""


@pytest.fixture
def world(upstream: Upstream, cache: Cache) -> World:
    return World(upstream, cache)


@pytest.fixture
def tree(world: World) -> Tree:
    ore, sand, hide, shard = (
        world.item(1),
        world.item(2),
        world.item(3),
        world.crystal(4),
    )
    world.gathered(ore)
    world.sold(sand, 5)
    world.dropped(hide)
    ingot, rivet = world.item(10), world.item(11)
    world.recipe(100, ingot, {ore: 3, shard: 1})
    world.recipe(101, rivet, {ingot: 1, sand: 1})
    world.recipe(110, ingot, {ore: 9}, level=50)  # not preferred
    sword, shield = world.item(20), world.item(21)
    world.recipe(200, sword, {rivet: 2, ingot: 1, shard: 1})
    world.recipe(201, shield, {hide: 2, rivet: 1})
    world.market(sword, 1000, 1000.0, 5.0)
    world.market(shield, 500, 500.0, 1.0)
    return world.tree()


def test_kept_recipes_keep_their_precursors(tree: Tree) -> None:
    pruning = prune(tree, Rules.parse(RULES))

    assert sorted(pruning.kept) == [100, 101, 200]
    assert [rule for rule, _ in pruning.kept[200].rules] == ["Gil-maker"]
    assert pruning.kept[101].needed_by == {200}
    assert pruning.kept[100].needed_by == {101, 200}
    assert pruning.kept[100].rules == []


def test_the_hoard_is_the_base_ingredients_of_the_kept_recipes(tree: Tree) -> None:
    pruning = prune(tree, Rules.parse(RULES))

    assert {item: sorted(h.needed_by) for item, h in pruning.hoard.items()} == {
        1: [100],
        2: [101],
        4: [100, 200],
    }
    assert pruning.hoard[1].kinds == {"gathering"}


def test_what_is_not_kept_is_pruned(tree: Tree) -> None:
    pruning = prune(tree, Rules.parse(RULES))

    assert sorted(pruning.pruned) == [110, 201]


def test_each_rule_reports_what_it_selected(tree: Tree) -> None:
    pruning = prune(
        tree,
        Rules.parse(
            RULES
            + """
            [[rule]]
            name = "Everything with a market"
            where = "velocity > 0"
            """
        ),
    )

    assert {
        name: [s.recipe_id for s in found] for name, found in pruning.selections.items()
    } == {
        "Gil-maker": [200],
        "Everything with a market": [200, 201],
    }
    assert [rule for rule, _ in pruning.kept[200].rules] == [
        "Gil-maker",
        "Everything with a market",
    ]


def test_parameters_reach_the_primitives(tree: Tree) -> None:
    pruning = prune(tree, Rules.parse("[parameters]\nprice_cap = 0.1\n" + RULES))

    assert pruning.selections["Gil-maker"] == []

import pytest
from upstream import Upstream
from world import World

from bonsai import report
from bonsai.cache import Cache
from bonsai.pruning import Pruning, prune
from bonsai.rules import Rules
from bonsai.tree import Tree

RULES = """
[[rule]]
name = "Gil-maker"
where = "turnover > 0"
score = "turnover"
"""


@pytest.fixture
def tree(upstream: Upstream, cache: Cache) -> Tree:
    world = World(upstream, cache)
    ore, shard = world.item(1, "Iron Ore"), world.crystal(2)
    world.gathered(ore)
    world.sold(ore, 18)
    ingot = world.item(10, "Iron Ingot")
    world.recipe(100, ingot, {ore: 3, shard: 1})
    sword = world.item(20, "Iron Sword")
    world.recipe(200, sword, {ingot: 2}, level=20)
    world.market(sword, 1000, 1000.0, 5.0)
    lance = world.item(30, "Iron Lance")
    world.recipe(300, lance, {ingot: 3}, job="Armorcraft", level=25)
    world.market(lance, 100, 100.0, 1.0)
    return world.tree()


@pytest.fixture
def pruning(tree: Tree) -> Pruning:
    return prune(tree, Rules.parse(RULES))


def test_the_summary_counts_what_each_rule_selected(
    tree: Tree, pruning: Pruning
) -> None:
    assert report.summary(tree, pruning) == {
        "rules": {"Gil-maker": 2},
        "recipes": 3,
        "kept": 3,
        "pruned": 0,
        "hoard": 2,
    }


def test_selections_rank_each_rule_s_picks(tree: Tree, pruning: Pruning) -> None:
    assert report.selections(tree, pruning, "Gil-maker") == [
        {
            "rank": 1,
            "group": "",
            "name": "Iron Sword",
            "job": "Smithing",
            "level": 20,
            "score": 5000.0,
            "recipe": 200,
        },
        {
            "rank": 2,
            "group": "",
            "name": "Iron Lance",
            "job": "Armorcraft",
            "level": 25,
            "score": 100.0,
            "recipe": 300,
        },
    ]


def test_kept_recipes_say_why_they_are_kept(tree: Tree, pruning: Pruning) -> None:
    assert report.kept(tree, pruning) == [
        {
            "name": "Iron Lance",
            "job": "Armorcraft",
            "level": 25,
            "why": "Gil-maker #2",
            "recipe": 300,
        },
        {
            "name": "Iron Sword",
            "job": "Smithing",
            "level": 20,
            "why": "Gil-maker #1",
            "recipe": 200,
        },
        {
            "name": "Iron Ingot",
            "job": "Smithing",
            "level": 1,
            "why": "for Iron Sword, Iron Lance",
            "recipe": 100,
        },
    ]


def test_the_hoard_says_how_much_and_how_to_obtain(
    tree: Tree, pruning: Pruning
) -> None:
    assert report.hoard(tree, pruning) == [
        {
            "name": "Iron Ore",
            "needed by": 1,
            "sources": "gathering, gil_shop",
            "item": 1,
        },
        {"name": "Item 2", "needed by": 1, "sources": "no known source", "item": 2},
    ]


def test_explore_ranks_every_recipe_by_an_ad_hoc_score(
    tree: Tree, pruning: Pruning
) -> None:
    rows = report.explore(
        pruning, where="level >= 20", score="price", columns=["name", "velocity"]
    )

    assert rows == [
        {"score": 1000.0, "name": "Iron Sword", "velocity": 5.0, "recipe": 200},
        {"score": 100.0, "name": "Iron Lance", "velocity": 1.0, "recipe": 300},
    ]


def test_explore_reports_a_mistake_in_its_expressions(pruning: Pruning) -> None:
    with pytest.raises(ValueError, match="pirce"):
        report.explore(pruning, where="true", score="pirce", columns=[])

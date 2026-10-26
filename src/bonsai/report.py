"""The results of a pruning as rows, for the command line and the UI."""

from collections.abc import Sequence
from typing import Any

from bonsai.pruning import Pruning
from bonsai.rules import rule, select
from bonsai.tree import Tree

Row = dict[str, Any]


def summary(tree: Tree, pruning: Pruning) -> Row:
    return {
        "rules": {name: len(found) for name, found in pruning.selections.items()},
        "recipes": len(tree.recipes),
        "kept": len(pruning.kept),
        "pruned": len(pruning.pruned),
        "hoard": len(pruning.hoard),
    }


def selections(tree: Tree, pruning: Pruning, name: str) -> list[Row]:
    """What the rule `name` selected, group by group, best first."""
    return [
        {
            "rank": selection.rank,
            "group": ", ".join(str(value) for value in selection.group),
            "name": _made(tree, selection.recipe_id),
            "job": tree.recipes[selection.recipe_id].job,
            "level": tree.recipes[selection.recipe_id].level,
            "score": selection.score,
            "recipe": selection.recipe_id,
        }
        for selection in pruning.selections[name]
    ]


def kept(tree: Tree, pruning: Pruning) -> list[Row]:
    """The kept recipes, those rules selected first, highest level first."""
    rows = []
    for recipe_kept in sorted(
        pruning.kept.values(),
        key=lambda k: (not k.rules, -tree.recipes[k.recipe_id].level, k.recipe_id),
    ):
        recipe = tree.recipes[recipe_kept.recipe_id]
        why = [f"{name} #{selection.rank}" for name, selection in recipe_kept.rules]
        if recipe_kept.needed_by:
            needed_by = sorted(recipe_kept.needed_by)
            why.append("for " + ", ".join(_made(tree, r) for r in needed_by))
        rows.append(
            {
                "name": _made(tree, recipe.id),
                "job": recipe.job,
                "level": recipe.level,
                "why": "; ".join(why),
                "recipe": recipe.id,
            }
        )
    return rows


def hoard(tree: Tree, pruning: Pruning) -> list[Row]:
    """The base ingredients to hoard, the most needed first."""
    return [
        {
            "name": tree.items[hoarded.item_id].name,
            "needed by": len(hoarded.needed_by),
            "sources": ", ".join(sorted(hoarded.kinds)) or "no known source",
            "item": hoarded.item_id,
        }
        for hoarded in sorted(
            pruning.hoard.values(),
            key=lambda h: (-len(h.needed_by), tree.items[h.item_id].name),
        )
    ]


def explore(
    pruning: Pruning, where: str, score: str, columns: Sequence[str]
) -> list[Row]:
    """Every recipe `where` is true of, by `score`: a rule to try out."""
    adhoc = rule(
        {"name": "explore", "where": where, "score": score}, pruning.parameters
    )
    found = select(adhoc, pruning.primitives.values(), pruning.parameters)
    return [
        {
            "score": selection.score,
            **{
                column: pruning.primitives[selection.recipe_id][column]
                for column in columns
            },
            "recipe": selection.recipe_id,
        }
        for selection in found
    ]


def _made(tree: Tree, recipe: int) -> str:
    return tree.items[tree.recipes[recipe].item_id].name

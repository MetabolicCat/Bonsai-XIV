"""Pruning the tree down to what rules keep: see docs/pruning.md."""

from dataclasses import dataclass, field
from typing import Any

from bonsai.primitives import Primitives
from bonsai.rules import Rules, Selection
from bonsai.tree import Tree


@dataclass
class Kept:
    """A kept recipe: the rules that selected it, the recipes it serves."""

    recipe_id: int
    rules: list[tuple[str, Selection]] = field(default_factory=list)
    needed_by: set[int] = field(default_factory=set)


@dataclass
class Hoarded:
    """A base ingredient of kept recipes, and how it is obtained."""

    item_id: int
    kinds: set[str]
    needed_by: set[int] = field(default_factory=set)


@dataclass
class Pruning:
    primitives: dict[int, dict[str, Any]]
    selections: dict[str, list[Selection]]
    kept: dict[int, Kept]
    hoard: dict[int, Hoarded]
    parameters: dict[str, Any] = field(default_factory=dict)

    @property
    def pruned(self) -> list[int]:
        """The recipes not kept."""
        return [recipe for recipe in self.primitives if recipe not in self.kept]


def prune(tree: Tree, rules: Rules) -> Pruning:
    """Keep the recipes `rules` select, and what they need."""
    primitives = Primitives(tree, rules.parameters)
    values = {id: primitives.of(recipe) for id, recipe in sorted(tree.recipes.items())}
    selections = {
        rule.name: rules.select(rule, values.values()) for rule in rules.enabled
    }
    kept: dict[int, Kept] = {}
    for name, selected in selections.items():
        for selection in selected:
            kept.setdefault(
                selection.recipe_id, Kept(selection.recipe_id)
            ).rules.append((name, selection))
    hoard: dict[int, Hoarded] = {}
    pending = list(kept)
    while pending:
        recipe = pending.pop()
        for item in tree.recipes[recipe].ingredients:
            made_by = tree.preferred_recipe(item)
            if made_by is None:
                kinds = {source.kind for source in tree.sources.get(item, [])}
                hoard.setdefault(item, Hoarded(item, kinds)).needed_by.add(recipe)
                continue
            if made_by.id not in kept:
                kept[made_by.id] = Kept(made_by.id)
                pending.append(made_by.id)
            kept[made_by.id].needed_by.add(recipe)
    return Pruning(values, selections, kept, hoard, primitives.parameters)

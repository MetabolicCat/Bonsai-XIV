"""The values rules are written with, for each recipe: see docs/pruning.md."""

from collections.abc import Mapping
from functools import cache
from typing import Any, ClassVar

from bonsai.tree import Market, Recipe, Tree

DEFAULT_PARAMETERS: dict[str, Any] = {
    "price_cap": 3,
    "level_band": 10,
    "level_caps": [50, 60, 70, 80, 90, 100],
}

# How a base ingredient is obtained, by the kinds of its sources.
VENDORS = {"gil_shop", "special_shop", "trade"}
GATHERING = {"gathering", "fishing", "gardening"}

GIL = 1


class Primitives:
    """The primitives of the recipes of a tree, under parameters."""

    NAMES: ClassVar[list[str]] = [
        "recipe_id",
        "item_id",
        "name",
        "job",
        "level",
        "stars",
        "level_band",
        "expert",
        "master_book",
        "amount",
        "burden",
        "ingredients",
        "crystals",
        "stack_size",
        "stackable",
        "can_be_hq",
        "marketable",
        "untradable",
        "ui_category",
        "item_level",
        "equip_level",
        "level_cap",
        "leve",
        "leve_level",
        "min_listing",
        "average_price",
        "price",
        "velocity",
        "turnover",
        "craft_cost",
        "profit",
        "leaves",
        "vendor_leaves",
        "gathered_leaves",
        "farmed_leaves",
        "unsourced_leaves",
    ]

    def __init__(self, tree: Tree, parameters: Mapping[str, Any]) -> None:
        self._tree = tree
        self.parameters = DEFAULT_PARAMETERS | dict(parameters)
        self._unit_cost = cache(self._cheapest)

    def of(self, recipe: Recipe) -> dict[str, Any]:
        tree, parameters = self._tree, self.parameters
        item = tree.items[recipe.item_id]
        ingredients = {
            ingredient: amount
            for ingredient, amount in recipe.ingredients.items()
            if not tree.items[ingredient].crystal
        }
        band = parameters["level_band"]
        leves = tree.leves.get(item.id, [])
        market = tree.market.get((item.id, item.can_be_hq))
        price = _price(market, parameters["price_cap"])
        velocity = market.daily_velocity if market else None
        craft_cost = self.craft_cost(recipe)
        leaves = [
            leaf
            for leaf in tree.base_ingredients(recipe.id)
            if not tree.items[leaf].crystal
        ]
        kinds = [
            {source.kind for source in tree.sources.get(leaf, [])} for leaf in leaves
        ]
        return {
            "recipe_id": recipe.id,
            "item_id": item.id,
            "name": item.name,
            "job": recipe.job,
            "level": recipe.level,
            "stars": recipe.stars,
            "level_band": (recipe.level - 1) // band * band + 1,
            "expert": recipe.expert,
            "master_book": recipe.master_book,
            "amount": recipe.amount,
            "burden": sum(ingredients.values()),
            "ingredients": len(ingredients),
            "crystals": sum(recipe.ingredients.values()) - sum(ingredients.values()),
            "stack_size": item.stack_size,
            "stackable": item.stack_size > 1,
            "can_be_hq": item.can_be_hq,
            "marketable": item.marketable,
            "untradable": item.untradable,
            "ui_category": item.ui_category,
            "item_level": item.item_level,
            "equip_level": item.equip_level,
            "level_cap": next(
                (cap for cap in parameters["level_caps"] if cap >= item.equip_level),
                None,
            ),
            "leve": bool(leves),
            "leve_level": min((leve.level for leve in leves), default=None),
            "min_listing": market.min_listing if market else None,
            "average_price": market.average_price if market else None,
            "price": price,
            "velocity": velocity,
            "turnover": price * velocity
            if price is not None and velocity is not None
            else None,
            "craft_cost": craft_cost,
            "profit": price * recipe.amount - craft_cost
            if price is not None and craft_cost is not None
            else None,
            "leaves": len(leaves),
            "vendor_leaves": sum(bool(k & VENDORS) for k in kinds),
            "gathered_leaves": sum(bool(k & GATHERING) for k in kinds),
            "farmed_leaves": sum(
                bool(k) and not k & (VENDORS | GATHERING) for k in kinds
            ),
            "unsourced_leaves": sum(not k for k in kinds),
        }

    def craft_cost(self, recipe: Recipe) -> float | None:
        """Gil to make one craft, each ingredient bought where cheapest."""
        total = 0.0
        for ingredient, amount in recipe.ingredients.items():
            cost = self._unit_cost(ingredient)
            if cost is None:
                return None
            total += amount * cost
        return total

    def _cheapest(self, item: int) -> float | None:
        """Gil for one `item`: from a vendor, the market, or crafting it."""
        tree = self._tree
        costs: list[float] = [
            source.costs[0][1] / (source.amount or 1)
            for source in tree.sources.get(item, [])
            if source.kind == "gil_shop" and source.costs and source.costs[0][0] == GIL
        ]
        costs += [
            market.min_listing
            for hq in (False, True)
            if (market := tree.market.get((item, hq))) and market.min_listing
        ]
        recipe = tree.preferred_recipe(item)
        if recipe is not None and (made := self.craft_cost(recipe)) is not None:
            costs.append(made / recipe.amount)
        return min(costs, default=None)


def _price(market: Market | None, cap: float) -> float | None:
    """The average sale price, capped at `cap` times the lowest listing."""
    if market is None or market.average_price is None:
        return None
    if market.min_listing is None:
        return market.average_price
    return min(market.average_price, cap * market.min_listing)

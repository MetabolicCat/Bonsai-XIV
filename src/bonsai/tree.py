"""The built tree, loaded in memory to be walked: see docs/tree.md."""

import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path


@dataclass(frozen=True)
class Item:
    id: int
    name: str
    stack_size: int
    can_be_hq: bool
    untradable: bool
    marketable: bool
    ui_category: str | None
    item_level: int
    equip_level: int

    @property
    def crystal(self) -> bool:
        """A crystal, shard or cluster."""
        return self.ui_category == "Crystal"


@dataclass(frozen=True)
class Recipe:
    id: int
    item_id: int
    amount: int
    job: str
    level: int
    stars: int
    master_book: bool
    expert: bool
    ingredients: dict[int, int] = field(hash=False, compare=False)


@dataclass(frozen=True)
class Source:
    """A way to obtain an item: see the source and cost tables."""

    kind: str
    ref: int | None
    amount: int | None
    costs: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class Leve:
    id: int
    level: int
    amount: int


@dataclass(frozen=True)
class Market:
    min_listing: int | None
    average_price: float | None
    daily_velocity: float | None


class Tree:
    """Items, the recipes linking them, and how to obtain the others."""

    def __init__(
        self,
        items: dict[int, Item],
        recipes: dict[int, Recipe],
        sources: dict[int, list[Source]],
        leves: dict[int, list[Leve]],
        market: dict[tuple[int, bool], Market],
    ) -> None:
        self.items = items
        self.recipes = recipes
        self.sources = sources
        self.leves = leves
        self.market = market
        self._recipes_of: dict[int, list[Recipe]] = defaultdict(list)
        for recipe in sorted(recipes.values(), key=lambda recipe: recipe.id):
            self._recipes_of[recipe.item_id].append(recipe)
        self.base_ingredients = cache(self._base_ingredients)

    @classmethod
    def load(cls, database: Path) -> "Tree":
        with sqlite3.connect(database) as db:
            tree = cls(_items(db), _recipes(db), _sources(db), _leves(db), _market(db))
        db.close()
        return tree

    def recipes_of(self, item: int) -> list[Recipe]:
        return self._recipes_of.get(item, [])

    def preferred_recipe(self, item: int) -> Recipe | None:
        """The recipe an item is made by: its lowest-level one."""
        recipes = self.recipes_of(item)
        return min(recipes, key=lambda r: (r.level, r.id)) if recipes else None

    def _base_ingredients(self, recipe: int) -> dict[int, float]:
        """The base ingredients one craft of `recipe` needs.

        Craftable ingredients are made by their preferred recipe, in
        fractions of a craft: the average over many crafts.
        """
        needs: dict[int, float] = defaultdict(float)
        for item, amount in self.recipes[recipe].ingredients.items():
            made_by = self.preferred_recipe(item)
            if made_by is None:
                needs[item] += amount
                continue
            crafts = amount / made_by.amount
            for base, count in self.base_ingredients(made_by.id).items():
                needs[base] += crafts * count
        return dict(needs)


def _items(db: sqlite3.Connection) -> dict[int, Item]:
    return {
        id: Item(
            id,
            name,
            stack_size,
            bool(can_be_hq),
            bool(untradable),
            bool(marketable),
            ui_category,
            item_level,
            equip_level,
        )
        for (
            id,
            name,
            stack_size,
            can_be_hq,
            untradable,
            marketable,
            ui_category,
            item_level,
            equip_level,
        ) in db.execute(
            "SELECT id, name, stack_size, can_be_hq, untradable, marketable,"
            " ui_category, item_level, equip_level FROM item"
        )
    }


def _recipes(db: sqlite3.Connection) -> dict[int, Recipe]:
    ingredients: dict[int, dict[int, int]] = defaultdict(dict)
    for recipe, item, amount in db.execute(
        "SELECT recipe_id, item_id, amount FROM ingredient"
    ):
        ingredients[recipe][item] = amount
    return {
        id: Recipe(
            id,
            item,
            amount,
            job,
            level,
            stars,
            bool(master_book),
            bool(expert),
            ingredients[id],
        )
        for id, item, amount, job, level, stars, master_book, expert in db.execute(
            "SELECT id, item_id, amount, job, level, stars, master_book, expert"
            " FROM recipe"
        )
    }


def _sources(db: sqlite3.Connection) -> dict[int, list[Source]]:
    costs: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for source, item, amount in db.execute(
        "SELECT source_id, item_id, amount FROM cost"
    ):
        costs[source].append((item, amount))
    sources: dict[int, list[Source]] = defaultdict(list)
    for id, item, kind, ref, amount in db.execute(
        "SELECT id, item_id, kind, ref, amount FROM source ORDER BY id"
    ):
        sources[item].append(Source(kind, ref, amount, tuple(costs[id])))
    return dict(sources)


def _leves(db: sqlite3.Connection) -> dict[int, list[Leve]]:
    leves: dict[int, list[Leve]] = defaultdict(list)
    for id, level, item, amount in db.execute(
        "SELECT id, level, item_id, amount FROM leve ORDER BY id"
    ):
        leves[item].append(Leve(id, level, amount))
    return dict(leves)


def _market(db: sqlite3.Connection) -> dict[tuple[int, bool], Market]:
    return {
        (item, bool(hq)): Market(*values)
        for item, hq, *values in db.execute(
            "SELECT item_id, hq, min_listing, average_price, daily_velocity FROM market"
        )
    }

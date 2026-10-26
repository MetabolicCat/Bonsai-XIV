"""Building the tree from the cached sources: see docs/tree.md."""

import sqlite3
from pathlib import Path

from bonsai.cache import Cache
from bonsai.sources import datamining

SCHEMA = """
CREATE TABLE item (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    stack_size INTEGER NOT NULL,
    can_be_hq BOOLEAN NOT NULL,
    untradable BOOLEAN NOT NULL,
    marketable BOOLEAN NOT NULL,
    ui_category TEXT,
    item_level INTEGER NOT NULL,
    equip_level INTEGER NOT NULL
);
CREATE TABLE recipe (
    id INTEGER PRIMARY KEY,
    item_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    job TEXT NOT NULL,
    level INTEGER NOT NULL,
    stars INTEGER NOT NULL,
    master_book BOOLEAN NOT NULL,
    expert BOOLEAN NOT NULL
);
CREATE INDEX recipe_item ON recipe (item_id);
CREATE TABLE ingredient (
    recipe_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    PRIMARY KEY (recipe_id, item_id)
);
CREATE INDEX ingredient_item ON ingredient (item_id);
"""

# A recipe has up to this many ingredients, crystals included.
INGREDIENT_SLOTS = 8


def build(cache: Cache) -> None:
    """Write the tree to `cache.database`, from the cache only."""
    version = cache.version(datamining.NAME)
    if version is None:
        raise RuntimeError("no game data in the cache: run `bonsai refresh game`")
    sheets = cache.directory(datamining.NAME, version)

    cache.database.unlink(missing_ok=True)
    with sqlite3.connect(cache.database) as db:
        db.executescript(SCHEMA)
        _items(db, sheets)
        _recipes(db, sheets)
    db.close()


def _items(db: sqlite3.Connection, sheets: Path) -> None:
    ui_categories = {
        row["#"]: row["Name"]
        for row in datamining.rows(sheets, "ItemUICategory")
        if row["Name"]
    }
    db.executemany(
        "INSERT INTO item VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            (
                int(row["#"]),
                row["Name"],
                int(row["StackSize"]),
                row["CanBeHq"] == "True",
                row["IsUntradable"] == "True",
                row["ItemSearchCategory"] != "0",
                ui_categories.get(row["ItemUICategory"]),
                int(row["LevelItem"]),
                int(row["LevelEquip"]),
            )
            for row in datamining.rows(sheets, "Item")
            if row["Name"]
        ),
    )


def _recipes(db: sqlite3.Connection, sheets: Path) -> None:
    jobs = {row["#"]: row["Name"] for row in datamining.rows(sheets, "CraftType")}
    levels = {
        row["#"]: (int(row["ClassJobLevel"]), int(row["Stars"]))
        for row in datamining.rows(sheets, "RecipeLevelTable")
    }
    for row in datamining.rows(sheets, "Recipe"):
        if row["ItemResult"] == "0":
            continue
        recipe_id = int(row["#"])
        level, stars = levels[row["RecipeLevelTable"]]
        db.execute(
            "INSERT INTO recipe VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                recipe_id,
                int(row["ItemResult"]),
                int(row["AmountResult"]),
                jobs[row["CraftType"]],
                level,
                stars,
                row["SecretRecipeBook"] != "0",
                row["IsExpert"] == "True",
            ),
        )
        db.executemany(
            "INSERT INTO ingredient VALUES (?, ?, ?)",
            (
                (recipe_id, int(item), int(amount))
                for item, amount in (
                    (row[f"Ingredient[{i}]"], row[f"AmountIngredient[{i}]"])
                    for i in range(INGREDIENT_SLOTS)
                )
                if item != "0" and amount != "0"
            ),
        )

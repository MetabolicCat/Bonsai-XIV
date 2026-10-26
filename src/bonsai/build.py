"""Building the tree from the cached sources: see docs/tree.md."""

import sqlite3
from collections.abc import Iterator
from pathlib import Path

from bonsai.cache import Cache
from bonsai.sources import datamining, teamcraft, universalis

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
CREATE TABLE source (
    id INTEGER PRIMARY KEY,
    item_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    ref INTEGER,
    amount INTEGER
);
CREATE INDEX source_item ON source (item_id);
CREATE TABLE cost (
    source_id INTEGER NOT NULL,
    item_id INTEGER,
    amount INTEGER NOT NULL
);
CREATE INDEX cost_source ON cost (source_id);
CREATE TABLE leve (
    id INTEGER NOT NULL,
    level INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    amount INTEGER NOT NULL
);
CREATE INDEX leve_item ON leve (item_id);
CREATE TABLE market (
    item_id INTEGER NOT NULL,
    hq BOOLEAN NOT NULL,
    min_listing INTEGER,
    average_price REAL,
    daily_velocity REAL,
    PRIMARY KEY (item_id, hq)
);
CREATE TABLE meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

# A recipe has up to this many ingredients, crystals included.
INGREDIENT_SLOTS = 8

# A special shop has up to this many trades, each giving up to
# RECEIVE_SLOTS items for up to COST_SLOTS costs.
TRADE_SLOTS = 60
RECEIVE_SLOTS = 2
COST_SLOTS = 3

# A crafting leve asks for up to this many different items.
TURN_IN_SLOTS = 4

GIL = 1

# In a special shop with a currency type, a cost below this id is an
# index into another sheet that depends on the currency type and the
# patch, not an item: it is recorded as an unknown currency.
CURRENCY_INDEXES = 10

# Teamcraft's name for the shops of the SpecialShop sheet.
SPECIAL_SHOP = "SpecialShop"


def build(cache: Cache) -> None:
    """Write the tree to `cache.database`, from the cache only."""
    sheets = _current(cache, datamining.NAME)
    extracts = _current(cache, teamcraft.NAME)

    cache.database.unlink(missing_ok=True)
    with sqlite3.connect(cache.database) as db:
        db.executescript(SCHEMA)
        _items(db, sheets)
        _recipes(db, sheets)
        _sources(db, sheets)
        _gil_shops(db, sheets)
        _trades(db, sheets, extracts)
        _leves(db, sheets)
        for item, kind, ref in teamcraft.sources(extracts):
            _add_source(db, item, kind, ref)
        # Quest event items and unnamed placeholders are not in the tree.
        db.execute(
            "DELETE FROM cost WHERE source_id IN (SELECT id FROM source"
            " WHERE item_id NOT IN (SELECT id FROM item))"
        )
        db.execute("DELETE FROM source WHERE item_id NOT IN (SELECT id FROM item)")
        meta = {
            "datamining_version": sheets.name,
            "teamcraft_version": extracts.name,
        }
        market_version = cache.version(universalis.NAME)
        if market_version is not None:
            market = cache.directory(universalis.NAME, market_version)
            db.executemany(
                "INSERT INTO market VALUES (?, ?, ?, ?, ?)",
                universalis.prices(market),
            )
            meta |= universalis.meta(market)
        db.executemany("INSERT INTO meta VALUES (?, ?)", meta.items())
    db.close()


def _current(cache: Cache, source: str) -> Path:
    version = cache.version(source)
    if version is None:
        raise RuntimeError(f"no {source} data in the cache: run `bonsai refresh game`")
    return cache.directory(source, version)


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
                (recipe_id, item, amount)
                for item, amount in _slots(
                    row, "Ingredient", "AmountIngredient", INGREDIENT_SLOTS
                )
            ),
        )


def _sources(db: sqlite3.Connection, sheets: Path) -> None:
    for kind, sheet in [
        ("gathering", "GatheringItem"),
        ("fishing", "FishParameter"),
        ("fishing", "SpearfishingItem"),
    ]:
        for row in datamining.rows(sheets, sheet):
            if row["Item"] != "0":
                _add_source(db, int(row["Item"]), kind, int(row["#"]))


def _gil_shops(db: sqlite3.Connection, sheets: Path) -> None:
    prices = {row["#"]: int(row["PriceMid"]) for row in datamining.rows(sheets, "Item")}
    # A row is a subrow of its shop: "<shop>.<index>".
    sold = {
        (row["Item"], row["#"].split(".")[0])
        for row in datamining.rows(sheets, "GilShopItem")
        if row["Item"] != "0"
    }
    for item, shop in sorted(sold):
        _add_source(db, int(item), "gil_shop", int(shop), 1, [(GIL, prices[item])])


def _trades(db: sqlite3.Connection, sheets: Path, extracts: Path) -> None:
    """Shop trades: Teamcraft's, and the sheet's for shops Teamcraft lacks.

    Teamcraft resolves the costs that the SpecialShop sheet holds as
    indexes into other sheets (tomestones, scrips); it also has trades
    from shops other than special shops, such as grand company ones.
    """
    trades = list(teamcraft.trades(extracts))
    known = {(t.item, t.shop) for t in trades if t.shop_type == SPECIAL_SHOP}
    for trade in trades:
        kind = "special_shop" if trade.shop_type == SPECIAL_SHOP else "trade"
        _add_source(db, trade.item, kind, trade.shop, trade.amount, trade.costs)
    for trade in _special_shops(sheets):
        if (trade.item, trade.shop) not in known:
            _add_source(
                db, trade.item, "special_shop", trade.shop, trade.amount, trade.costs
            )


def _special_shops(sheets: Path) -> Iterator[teamcraft.Trade]:
    for row in datamining.rows(sheets, "SpecialShop"):
        indexes = row["UseCurrencyType"] != "0"
        for trade in range(TRADE_SLOTS):
            costs = [
                (None if indexes and item < CURRENCY_INDEXES else item, amount)
                for item, amount in _slots(
                    row,
                    f"Item[{trade}].ItemCost",
                    f"Item[{trade}].CurrencyCost",
                    COST_SLOTS,
                )
            ]
            for item, amount in _slots(
                row, f"Item[{trade}].Item", f"Item[{trade}].ReceiveCount", RECEIVE_SLOTS
            ):
                yield teamcraft.Trade(item, SPECIAL_SHOP, int(row["#"]), amount, costs)


def _leves(db: sqlite3.Connection, sheets: Path) -> None:
    levels = {
        row["#"]: int(row["ClassJobLevel"]) for row in datamining.rows(sheets, "Leve")
    }
    for row in datamining.rows(sheets, "CraftLeve"):
        if row["Leve"] == "0":
            continue
        db.executemany(
            "INSERT INTO leve VALUES (?, ?, ?, ?)",
            (
                (int(row["Leve"]), levels[row["Leve"]], item, amount)
                for item, amount in _slots(row, "Item", "ItemCount", TURN_IN_SLOTS)
            ),
        )


def _slots(
    row: dict[str, str], item: str, amount: str, count: int
) -> Iterator[tuple[int, int]]:
    """The (item, amount) pairs of a row's `count` slots that are filled."""
    for i in range(count):
        pair = int(row[f"{item}[{i}]"]), int(row[f"{amount}[{i}]"])
        if all(pair):
            yield pair


def _add_source(
    db: sqlite3.Connection,
    item: int,
    kind: str,
    ref: int | None,
    amount: int | None = None,
    costs: list[tuple[int | None, int]] | None = None,
) -> None:
    source = db.execute(
        "INSERT INTO source (item_id, kind, ref, amount) VALUES (?, ?, ?, ?)",
        (item, kind, ref, amount),
    ).lastrowid
    db.executemany(
        "INSERT INTO cost VALUES (?, ?, ?)",
        ((source, cost_item, cost_amount) for cost_item, cost_amount in costs or []),
    )

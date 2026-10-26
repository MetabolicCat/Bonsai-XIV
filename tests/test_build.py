import pytest
from tree import built, named, sources
from upstream import Upstream

from bonsai.cache import Cache


def test_items_are_built_from_the_item_sheet(upstream: Upstream, cache: Cache) -> None:
    upstream.sheets["Item"] = [
        {"#": 5057, "Name": "Iron Ingot", "StackSize": 999},
    ]

    db = built(upstream, cache)

    assert db.execute("SELECT id, name, stack_size FROM item").fetchall() == [
        (5057, "Iron Ingot", 999)
    ]


def test_items_carry_what_pruning_needs_to_know(
    upstream: Upstream, cache: Cache
) -> None:
    upstream.sheets["ItemUICategory"] = [{"#": 46, "Name": "Meal"}]
    upstream.sheets["Item"] = [
        {
            "#": 4650,
            "Name": "Boiled Egg",
            "StackSize": 999,
            "CanBeHq": "True",
            "IsUntradable": "False",
            "ItemSearchCategory": 45,
            "ItemUICategory": 46,
            "LevelItem": 5,
            "LevelEquip": 1,
        },
        {
            "#": 2,
            "Name": "Fire Shard",
            "StackSize": 9999,
            "CanBeHq": "False",
            "IsUntradable": "True",
            "ItemSearchCategory": 0,
            "ItemUICategory": 0,
            "LevelItem": 1,
            "LevelEquip": 1,
        },
    ]

    db = built(upstream, cache)

    assert db.execute(
        "SELECT id, can_be_hq, untradable, marketable, ui_category,"
        " item_level, equip_level FROM item ORDER BY id"
    ).fetchall() == [
        (2, False, True, False, None, 1, 1),
        (4650, True, False, True, "Meal", 5, 1),
    ]


def test_recipes_link_an_item_to_its_ingredients(
    upstream: Upstream, cache: Cache
) -> None:
    upstream.sheets["CraftType"] = [{"#": 1, "Name": "Smithing"}]
    upstream.sheets["RecipeLevelTable"] = [{"#": 16, "ClassJobLevel": 16, "Stars": 0}]
    upstream.sheets["Recipe"] = [
        {"#": 0, "ItemResult": 0},
        {
            "#": 43,
            "CraftType": 1,
            "ItemResult": 5057,
            "AmountResult": 1,
            "RecipeLevelTable": 16,
            "Ingredient[0]": 5111,
            "AmountIngredient[0]": 3,
            "Ingredient[6]": 2,
            "AmountIngredient[6]": 1,
            "SecretRecipeBook": 0,
            "IsExpert": "False",
        },
    ]

    db = built(upstream, cache)

    assert db.execute("SELECT * FROM recipe").fetchall() == [
        (43, 5057, 1, "Smithing", 16, 0, False, False)
    ]
    assert db.execute("SELECT * FROM ingredient ORDER BY item_id").fetchall() == [
        (43, 2, 1),
        (43, 5111, 3),
    ]


def test_recipe_level_and_master_book(upstream: Upstream, cache: Cache) -> None:
    upstream.sheets["CraftType"] = [{"#": 7, "Name": "Cooking"}]
    upstream.sheets["RecipeLevelTable"] = [{"#": 690, "ClassJobLevel": 100, "Stars": 2}]
    upstream.sheets["Recipe"] = [
        {
            "#": 35000,
            "CraftType": 7,
            "ItemResult": 44000,
            "AmountResult": 3,
            "RecipeLevelTable": 690,
            "SecretRecipeBook": 12,
            "IsExpert": "True",
        },
    ]

    db = built(upstream, cache)

    assert db.execute("SELECT * FROM recipe").fetchall() == [
        (35000, 44000, 3, "Cooking", 100, 2, True, True)
    ]


def test_gathered_and_fished_items_have_a_source(
    upstream: Upstream, cache: Cache
) -> None:
    upstream.sheets["Item"] = named(4776, 5111, 7684)
    upstream.sheets["GatheringItem"] = [{"#": 0, "Item": 0}, {"#": 30, "Item": 5111}]
    upstream.sheets["FishParameter"] = [{"#": 1, "Item": 4776}]
    upstream.sheets["SpearfishingItem"] = [{"#": 20000, "Item": 7684}]

    db = built(upstream, cache)

    assert sources(db) == [
        (4776, "fishing", 1, None, ()),
        (5111, "gathering", 30, None, ()),
        (7684, "fishing", 20000, None, ()),
    ]


def test_shops_record_what_a_trade_costs(upstream: Upstream, cache: Cache) -> None:
    upstream.sheets["Item"] = [
        {"#": 5111, "Name": "Iron Ore", "PriceMid": 18},
        *named(6968, 6969),
    ]
    upstream.sheets["GilShopItem"] = [
        {"#": "262144.0", "Item": 5111},
        {"#": "262145.3", "Item": 5111},
    ]
    upstream.sheets["SpecialShop"] = [
        {
            "#": 1769485,
            "Item[0].Item[0]": 6968,
            "Item[0].ReceiveCount[0]": 1,
            "Item[0].ItemCost[0]": 7000,
            "Item[0].CurrencyCost[0]": 10,
            "Item[0].ItemCost[1]": 28,
            "Item[0].CurrencyCost[1]": 5,
            "Item[1].Item[0]": 6969,
            "Item[1].ReceiveCount[0]": 1,
            "Item[1].ItemCost[0]": 7000,
            "Item[1].CurrencyCost[0]": 20,
            "Item[2].Item[0]": 6968,
            "Item[2].ReceiveCount[0]": 2,
            "Item[2].ItemCost[0]": 29,
            "Item[2].CurrencyCost[0]": 3,
        },
    ]

    db = built(upstream, cache)

    assert sources(db) == [
        (5111, "gil_shop", 262144, 1, ((1, 18),)),
        (5111, "gil_shop", 262145, 1, ((1, 18),)),
        (6968, "special_shop", 1769485, 1, ((28, 5), (7000, 10))),
        (6968, "special_shop", 1769485, 2, ((29, 3),)),
        (6969, "special_shop", 1769485, 1, ((7000, 20),)),
    ]


def test_teamcraft_trades_replace_the_sheet_for_the_shops_it_knows(
    upstream: Upstream, cache: Cache
) -> None:
    upstream.sheets["Item"] = named(5111, 7294, 7295)
    upstream.sheets["SpecialShop"] = [
        {
            "#": 1769500,
            "Item[0].Item[0]": 7294,
            "Item[0].ReceiveCount[0]": 1,
            # The tomestone, as an index the game resolves elsewhere.
            "Item[0].ItemCost[0]": 1,
            "Item[0].CurrencyCost[0]": 100,
        },
        {
            "#": 1769501,
            "Item[0].Item[0]": 7295,
            "Item[0].ReceiveCount[0]": 1,
            "Item[0].ItemCost[0]": 28,
            "Item[0].CurrencyCost[0]": 50,
        },
    ]

    def trade(
        shop: dict[str, object], item: int, *costs: tuple[int, int]
    ) -> dict[str, object]:
        return {
            **shop,
            "trades": [
                {
                    "currencies": [{"id": i, "amount": a} for i, a in costs],
                    "items": [{"id": item, "amount": 1}, {"id": 99999, "amount": 1}],
                }
            ],
        }

    upstream.extracts = {
        "7294": {
            "sources": [
                {
                    "type": 2,
                    "data": [
                        trade({"id": 1769500, "type": "SpecialShop"}, 7294, (28, 100))
                    ],
                }
            ]
        },
        "5111": {
            "sources": [
                {
                    "type": 2,
                    "data": [
                        trade({"id": 1441793, "type": "GCShop"}, 5111, (20, 200)),
                        trade({}, 5111, (29894, 10)),
                    ],
                }
            ]
        },
    }

    db = built(upstream, cache)

    assert sources(db) == [
        (5111, "trade", None, 1, ((29894, 10),)),
        (5111, "trade", 1441793, 1, ((20, 200),)),
        (7294, "special_shop", 1769500, 1, ((28, 100),)),
        (7295, "special_shop", 1769501, 1, ((28, 50),)),
    ]


def test_crafting_leves_record_their_turn_ins(upstream: Upstream, cache: Cache) -> None:
    upstream.sheets["Leve"] = [{"#": 36, "ClassJobLevel": 5}]
    upstream.sheets["CraftLeve"] = [
        {"#": 0, "Leve": 0},
        {"#": 917505, "Leve": 36, "Item[0]": 1823, "ItemCount[0]": 3},
    ]

    db = built(upstream, cache)

    assert db.execute("SELECT * FROM leve").fetchall() == [(36, 5, 1823, 3)]


@pytest.mark.parametrize(
    ("type", "data", "kind", "refs"),
    [
        (10, [{"id": 38}, {"id": 112}], "drop", [38, 112]),
        (6, [9, 52], "instance", [9, 52]),
        (8, {"seedItemId": 15865, "duration": 18}, "gardening", [15865]),
        (18, [68639], "quest", [68639]),
        (9, [{"type": 1, "name": {"en": "Sea of Ash 1", "id": 35}}], "voyage", [35]),
        (13, [6688, 6689], "treasure", [6688, 6689]),
        (5, [33319], "desynthesis", [33319]),
        (4, [33153], "reduction", [33153]),
        (15, [{"id": 70, "lvl": 1}], "venture", [70]),
        (14, [{"id": 506, "level": 50}], "fate", [506]),
    ],
)
def test_other_ways_to_obtain_an_item_come_from_teamcraft(
    upstream: Upstream,
    cache: Cache,
    type: int,
    data: object,
    kind: str,
    refs: list[int],
) -> None:
    upstream.sheets["Item"] = named(2, 5551)
    upstream.extracts = {
        "5551": {
            "id": 5551,
            "sources": [
                {"type": 3, "data": [{"npcId": 1000217, "price": 63}]},
                {"type": type, "data": data},
            ],
        },
        "2": {"id": 2},
    }

    db = built(upstream, cache)

    assert sources(db) == [(5551, kind, ref, None, ()) for ref in refs]


def test_sources_of_items_without_a_name_are_left_out(
    upstream: Upstream, cache: Cache
) -> None:
    upstream.sheets["Item"] = [
        {"#": 5111, "Name": "Iron Ore"},
        {"#": 8219, "Name": ""},
    ]
    upstream.sheets["GatheringItem"] = [
        {"#": 30, "Item": 5111},
        {"#": 31, "Item": 8219},
        {"#": 32, "Item": 2003558},
    ]

    db = built(upstream, cache)

    assert sources(db) == [(5111, "gathering", 30, None, ())]


def test_currency_indexes_teamcraft_cannot_resolve_are_unknown_costs(
    upstream: Upstream, cache: Cache
) -> None:
    upstream.sheets["Item"] = named(44000, 44001)
    upstream.sheets["SpecialShop"] = [
        {
            "#": 1770417,
            "UseCurrencyType": 16,
            "Item[0].Item[0]": 44000,
            "Item[0].ReceiveCount[0]": 1,
            "Item[0].ItemCost[0]": 1,
            "Item[0].CurrencyCost[0]": 20,
            "Item[0].ItemCost[1]": 25,
            "Item[0].CurrencyCost[1]": 3,
        },
        {
            "#": 1769000,
            "UseCurrencyType": 0,
            "Item[0].Item[0]": 44001,
            "Item[0].ReceiveCount[0]": 1,
            "Item[0].ItemCost[0]": 2,
            "Item[0].CurrencyCost[0]": 5,
        },
    ]

    db = built(upstream, cache)

    assert db.execute(
        "SELECT s.item_id, c.item_id, c.amount FROM source s"
        " JOIN cost c ON c.source_id = s.id ORDER BY s.item_id, c.amount"
    ).fetchall() == [(44000, 25, 3), (44000, None, 20), (44001, 2, 5)]


def shop(shop: int, item: int, cost: int, amount: int) -> dict[str, object]:
    """A special shop with a currency type, selling `item` for one cost."""
    return {
        "#": shop,
        "UseCurrencyType": 16,
        "Item[0].Item[0]": item,
        "Item[0].ReceiveCount[0]": 1,
        "Item[0].ItemCost[0]": cost,
        "Item[0].CurrencyCost[0]": amount,
    }


def test_an_unknown_currency_takes_the_price_the_item_has_elsewhere(
    upstream: Upstream, cache: Cache
) -> None:
    upstream.sheets["Item"] = named(27737, 28)
    upstream.sheets["SpecialShop"] = [
        shop(1770417, 27737, 1, 5),
        shop(1770418, 27737, 2, 5),
        shop(1770053, 27737, 28, 5),
    ]

    db = built(upstream, cache)

    assert sources(db) == [
        (27737, "special_shop", 1770053, 1, ((28, 5),)),
        (27737, "special_shop", 1770417, 1, ((28, 5),)),
        (27737, "special_shop", 1770418, 1, ((28, 5),)),
    ]


def test_an_unknown_currency_stays_unknown_when_other_prices_disagree(
    upstream: Upstream, cache: Cache
) -> None:
    upstream.sheets["Item"] = named(27737, 28, 33913)
    upstream.sheets["SpecialShop"] = [
        shop(1770417, 27737, 1, 5),
        shop(1770053, 27737, 28, 5),
        shop(1770054, 27737, 33913, 5),
    ]

    db = built(upstream, cache)

    assert (27737, "special_shop", 1770417, 1, ((None, 5),)) in sources(db)


def test_an_unknown_currency_is_the_one_whose_price_matches(
    upstream: Upstream, cache: Cache
) -> None:
    upstream.sheets["Item"] = named(27737, 28, 33913)
    upstream.sheets["SpecialShop"] = [
        shop(1770417, 27737, 1, 5),
        shop(1770053, 27737, 28, 5),
        shop(1770054, 27737, 33913, 50),
    ]

    db = built(upstream, cache)

    assert (27737, "special_shop", 1770417, 1, ((28, 5),)) in sources(db)

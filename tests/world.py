"""A small game world described by the tests, built into a real tree."""

from upstream import Row, Upstream

from bonsai.build import build
from bonsai.cache import Cache
from bonsai.refresh import refresh_game, refresh_market
from bonsai.tree import Tree

JOBS = ["Woodworking", "Smithing", "Armorcraft", "Goldsmithing"]
JOBS += ["Leatherworking", "Clothcraft", "Alchemy", "Cooking"]


class World:
    """Items, recipes and their sources, served by a fake upstream."""

    def __init__(self, upstream: Upstream, cache: Cache) -> None:
        self._upstream = upstream
        self._cache = cache
        self._items: dict[int, Row] = {}
        self._categories: dict[str, int] = {}
        self._recipes: list[Row] = []
        self._levels: dict[tuple[int, int], int] = {}
        self._gil_shops: list[Row] = []
        self._gathered: list[Row] = []
        self._leves: list[Row] = []
        self._leve_levels: list[Row] = []
        self._extracts: dict[str, dict[str, list[dict[str, object]]]] = {}

    def item(
        self,
        id: int,
        name: str | None = None,
        *,
        stack: int = 999,
        hq: bool = False,
        marketable: bool = True,
        category: str | None = None,
        equip: int = 1,
    ) -> int:
        self._items[id] = {
            "#": id,
            "Name": name or f"Item {id}",
            "StackSize": stack,
            "CanBeHq": str(hq),
            "ItemSearchCategory": 1 if marketable else 0,
            "ItemUICategory": self._category(category) if category else 0,
            "LevelEquip": equip,
        }
        return id

    def crystal(self, id: int) -> int:
        return self.item(id, category="Crystal", marketable=False)

    def recipe(
        self,
        id: int,
        item: int,
        ingredients: dict[int, int],
        *,
        job: str = "Smithing",
        level: int = 1,
        stars: int = 0,
        amount: int = 1,
        expert: bool = False,
        book: bool = False,
    ) -> int:
        row: Row = {
            "#": id,
            "CraftType": JOBS.index(job),
            "ItemResult": item,
            "AmountResult": amount,
            "RecipeLevelTable": self._levels.setdefault(
                (level, stars), len(self._levels) + 1
            ),
            "SecretRecipeBook": 1 if book else 0,
            "IsExpert": str(expert),
        }
        for slot, (ingredient, count) in enumerate(ingredients.items()):
            row[f"Ingredient[{slot}]"] = ingredient
            row[f"AmountIngredient[{slot}]"] = count
        self._recipes.append(row)
        return id

    def sold(self, item: int, price: int) -> None:
        """Sold by a vendor for `price` gil."""
        self._items[item]["PriceMid"] = price
        self._gil_shops.append(
            {"#": f"{262144 + len(self._gil_shops)}.0", "Item": item}
        )

    def gathered(self, item: int) -> None:
        self._gathered.append({"#": len(self._gathered) + 1, "Item": item})

    def dropped(self, item: int, monster: int = 1) -> None:
        self._source(item, {"type": 10, "data": [{"id": monster}]})

    def leve(self, leve: int, item: int, level: int, amount: int = 1) -> None:
        self._leve_levels.append({"#": leve, "ClassJobLevel": level})
        self._leves.append(
            {"#": leve, "Leve": leve, "Item[0]": item, "ItemCount[0]": amount}
        )

    def market(
        self,
        item: int,
        listing: int | None,
        average: float,
        velocity: float,
        *,
        hq: bool = False,
    ) -> None:
        data = self._upstream.market.setdefault(item, {"nq": {}, "hq": {}})
        quality = data["hq" if hq else "nq"]
        if listing is not None:
            quality["minListing"] = {"region": {"price": listing}}
        quality["averageSalePrice"] = {"region": {"price": average}}
        quality["dailySaleVelocity"] = {"region": {"quantity": velocity}}

    def tree(self) -> Tree:
        """Fetch, build and load the tree of this world."""
        up = self._upstream
        up.sheets["Item"] = list(self._items.values())
        up.sheets["ItemUICategory"] = [
            {"#": id, "Name": name} for name, id in self._categories.items()
        ]
        up.sheets["CraftType"] = [{"#": i, "Name": job} for i, job in enumerate(JOBS)]
        up.sheets["RecipeLevelTable"] = [
            {"#": id, "ClassJobLevel": level, "Stars": stars}
            for (level, stars), id in self._levels.items()
        ]
        up.sheets["Recipe"] = self._recipes
        up.sheets["GilShopItem"] = self._gil_shops
        up.sheets["GatheringItem"] = self._gathered
        up.sheets["CraftLeve"] = self._leves
        up.sheets["Leve"] = self._leve_levels
        up.extracts = self._extracts
        with up.client() as client:
            refresh_game(client, self._cache)
            build(self._cache)
            if up.market:
                refresh_market(client, self._cache, "Japan")
        build(self._cache)
        return Tree.load(self._cache.database)

    def _category(self, name: str) -> int:
        return self._categories.setdefault(name, len(self._categories) + 1)

    def _source(self, item: int, source: dict[str, object]) -> None:
        self._extracts.setdefault(str(item), {"sources": []})["sources"].append(source)

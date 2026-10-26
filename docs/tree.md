# The tree

`bonsai build` writes the tree to `bonsai.sqlite` in the cache
directory. It is rebuilt from scratch every time, from the cached
sources only (see [sources.md](sources.md)).

Strictly speaking it is a graph, not a tree: an ingredient feeds many
recipes, and an item can have several recipes (one per crafting job,
for instance). Items are its vertices; a recipe links the item it
makes to the items it consumes.

- **Nodes** are items with at least one recipe.
- **Leaves** are items with no recipe. Their `source` rows say how to
  obtain them; a leaf with none has no source Bonsai knows of.

## Tables

### `item`

Every named item of the game.

| Column | Type | Meaning |
|---|---|---|
| `id` | integer | item id, shared by every source |
| `name` | text | English name |
| `stack_size` | integer | how many fit in one inventory slot |
| `can_be_hq` | boolean | has a high-quality version |
| `untradable` | boolean | cannot be traded to other players |
| `marketable` | boolean | can be sold on the market board |
| `ui_category` | text | category shown in game (`Meal`, `Lumber`, …) |
| `item_level` | integer | item level |
| `equip_level` | integer | level required to use or equip it |

### `recipe`

| Column | Type | Meaning |
|---|---|---|
| `id` | integer | recipe id |
| `item_id` | integer | the item it makes |
| `amount` | integer | how many items one craft makes |
| `job` | text | crafting job (`Woodworking`, `Cooking`, …) |
| `level` | integer | job level of the recipe |
| `stars` | integer | difficulty stars beyond the level |
| `master_book` | boolean | needs a master recipe book |
| `expert` | boolean | expert recipe |

### `ingredient`

| Column | Type | Meaning |
|---|---|---|
| `recipe_id` | integer | the recipe |
| `item_id` | integer | the item it consumes |
| `amount` | integer | how many per craft |

Crystals, shards and clusters are ingredients like any other.

### `source`

The ways to obtain an item other than crafting it. Only items of the
`item` table have sources: quest event items and unnamed placeholders
are left out.

| Column | Type | Meaning |
|---|---|---|
| `item_id` | integer | the item |
| `kind` | text | see below |
| `ref` | integer | id of the shop, gathering item, fish, monster or duty |
| `cost_item_id` | integer | item paid, for shops (1 is gil) |
| `cost_amount` | integer | how many are paid per trade, for shops |

A special shop trade with several costs has one row per cost, all of
them paid together.

| `kind` | From | `ref` |
|---|---|---|
| `gathering` | `GatheringItem` | gathering item id |
| `fishing` | `FishParameter`, `SpearfishingItem` | fish parameter or spearfishing item id |
| `gil_shop` | `GilShopItem` | gil shop id |
| `special_shop` | `SpecialShop` | special shop id |
| `drop` | Teamcraft | monster id |
| `instance` | Teamcraft | duty (instance content) id |

### `leve`

Crafting leve turn-ins.

| Column | Type | Meaning |
|---|---|---|
| `id` | integer | leve id |
| `level` | integer | leve level |
| `item_id` | integer | item to turn in |
| `amount` | integer | how many |

### `market`

Market data of the latest Universalis snapshot, one row per item and
quality; items that never sold have no row.

| Column | Type | Meaning |
|---|---|---|
| `item_id` | integer | the item |
| `hq` | boolean | high quality |
| `min_listing` | integer | lowest price listed, in gil |
| `average_price` | real | average sale price, in gil |
| `daily_velocity` | real | items sold per day |

### `meta`

Key-value facts about the build.

| Key | Value |
|---|---|
| `datamining_version` | commit of ffxiv-datamining |
| `teamcraft_version` | commit of Teamcraft |
| `market_scope` | Universalis region, data center or world |
| `market_fetched_at` | time of the market snapshot (UTC, ISO 8601) |

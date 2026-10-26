# Golden sources

Bonsai builds its tree from three sources. Each one is downloaded
verbatim into the cache (`sources/` in the cache directory) and stamped
with the version it was fetched at, so that `bonsai build` never needs
the network and the same cache always gives the same tree.

| Source | What it provides | Version | Changes |
|---|---|---|---|
| [xivapi/ffxiv-datamining] | Items, recipes, shops, gathering, fishing, leves | git commit | each game patch |
| [ffxiv-teamcraft] | Drops, duty loot, trades and other sources | git commit | continuously, crowdsourced |
| [Universalis] | Market prices and sale velocity | fetch time | continuously |

[xivapi/ffxiv-datamining]: https://github.com/xivapi/ffxiv-datamining
[ffxiv-teamcraft]: https://github.com/ffxiv-teamcraft/ffxiv-teamcraft
[Universalis]: https://universalis.app

## Game data: ffxiv-datamining

The game's own data sheets, exported as CSV (`csv/en/<Sheet>.csv`, one
header row, numeric ids for every reference). This is the authority
for everything the game files contain.

| Sheet | Used for |
|---|---|
| `Item` | name, stack size, tradability, market board category, UI category, item and equip level, HQ |
| `Recipe` | result, amount, craft type, ingredients and amounts, level table, master book, expert flag |
| `RecipeLevelTable` | recipe job level and stars |
| `CraftType` | crafting job of a recipe |
| `GilShopItem` | items sold for gil (price: `Item.PriceMid`) |
| `SpecialShop` | items traded for other items, where Teamcraft has none |
| `GatheringItem` | items gathered by miner and botanist |
| `FishParameter`, `SpearfishingItem` | items caught by fisher |
| `CraftLeve`, `Leve` | crafting leve turn-ins and their level |

**Update:** `bonsai refresh game` asks GitHub for the head commit of the
default branch, and downloads the sheets at that commit when it is not
the one already cached. The repository follows the game's patches.

For special shops, Teamcraft's trades are used instead of the
`SpecialShop` sheet where it has them (see below); the sheet covers the
shops Teamcraft lacks. In those, some costs are indexes into currency
sheets that changed meaning from patch to patch (which tomestone is
"the current one"). Since vendors all charge the same price for an
item, such a cost takes the price of the item's other trades for the
same amount, when they all agree; otherwise it is recorded as an
unknown currency, to be filled in by hand where it matters: see
[overrides.md](overrides.md). On today's data, no recipe ingredient is
left with an unknown currency.

## Other sources: Teamcraft

The game files hold no drop tables. Teamcraft crowdsources them from
its users and publishes them, MIT licensed, in its repository as
`libs/data/src/lib/extracts/extracts.json`: for every item, the list of
its sources. Bonsai reads from it:

- monster drops, duty loot, FATEs, treasure maps, ventures, voyages,
  gardening, desynthesis, aetherial reduction and quests;
- shop trades. For special shops it resolves the costs that the
  `SpecialShop` sheet holds as indexes into other sheets (tomestones,
  scrips); it also has shops outside that sheet, such as grand company
  ones.

Gil shops come from the game data; Teamcraft's vendor entries are not
read.

**Update:** same as the game data, at the head of Teamcraft's default
branch, fetched together by `bonsai refresh game`.

**Known gap:** crowdsourced data is incomplete. An item with no source
at all in the tree is reported as such, rather than guessed; a missing
source can be added by hand: see [overrides.md](overrides.md).

## Market: Universalis

Aggregated market data from the
[Universalis API](https://docs.universalis.app/), per item: lowest
listing, average sale price and daily sale velocity, for NQ and HQ.

**Scope:** a Universalis region, data center or world. The default is
the `Japan` region, which is the whole Japanese physical data center
(Elemental, Gaia, Mana and Meteor): players can
travel to every world of their physical data center, not only those
of their logical one (since 13 October 2026, for Japan only).

**Update:** `bonsai refresh market` fetches every marketable item of
the tree (100 items per request) and keeps the snapshot under its fetch
time; `bonsai build` uses the most recent snapshot. Prices move by the
hour, so this is refreshed far more often than the game data.

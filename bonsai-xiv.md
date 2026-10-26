# Bonsai XIV

**A decision tool for what is actually worth hoarding in FFXIV.**

Bonsai maintains a dependency tree of every craftable item and prunes it down to the recipes and materials that are genuinely worth your time, inventory, and gil — and, by extension, tells you which base ingredients are worth stockpiling.

---

## 1. The Recipe Tree

Model all craftables as a directed tree:

- **Leaves** — base ingredients that cannot be crafted, obtained by:
  - Gathering
  - Fishing
  - Farming from dungeons / content
  - Purchasing with gil
  - Purchasing with special currencies
- **Nodes** — recipes; each node consumes its children (ingredients/sub-crafts) and produces its parent item.

The tree is the source of truth from which all pruning decisions are derived.

## 2. Pruning Rules

Starting from the full tree, **remove** a recipe (and, transitively, any ingredient branch that becomes unreachable) unless it qualifies as *useful* under at least one of the criteria below.

These criteria are not simple booleans. Each one is a **candidate-selection problem**: within a goal (e.g. "advance craft-count for this job and level range"), many recipes qualify, and the tool must pick the *best* one(s) by weighing several factors. Selecting a representative recipe effectively blesses its entire ingredient sub-tree; the rest can be pruned.

### 2.1 Usefulness criteria

1. **Log completion** — it is loggable and has already been crafted at least once for the crafting log achievement.
2. **Direct gil-maker** — it sells well on the market board: high `price × volume`.
3. **Precursor** — it is a sub-craft (or ingredient) of one or more crafts that are themselves good gil-makers (`price × volume`).
4. **Level-range craft-count achievements** — it helps reach the "craft #N items in this level range" achievements. A craft qualifies here only if it is actually practical to mass-produce, i.e. it sells well or is used for leves.
5. **Crafting leve achievements** — it is used to turn in crafting leves (for "leves #N" achievements).
6. **Raiding / level-cap consumables** — it is a consumable useful at some level cap (relevant because of ultimates and level-capped content such as BLU, treasure maps, field operations, etc.). Note: higher-level food is often still used when its price is reasonable.

Items failing every rule are pruned.

### 2.2 Factors (worked example: craft-count)

Within a single goal, choosing the best recipe depends on factors such as:

- **Ingredient burden** — how many ingredients does the recipe require?
- **Sourcing difficulty** — does it require monster-farmed ingredients? These are slower to obtain, and expensive when they cannot be bought from a vendor.
- **Stackability** — does the output stack? At the quantities these goals demand (1,000+ crafts), stacking matters a great deal, both for inventory and for how fast the product can be sold. Non-stackable outputs can be compensated by a better price, but only up to a point.
- **Natural sink** — is there demand that absorbs the output (most notably, is it a leve turn-in)? Without a sink, market-board sales tend to be slow unless the item belongs to the current expansion.

These factors are not exclusive to craft-count goals: price, volume, sourcing difficulty, stackability, and existing sinks inform every criterion above. They are noted here as the canonical example of how much structure each rule hides.

## 3. Output

- A pruned recipe tree containing only useful crafts and their prerequisite branches.
- The set of **base ingredients worth hoarding**, derived from the leaves that remain reachable in the pruned tree.

## 4. Explicit Non-Goals

- No implementation details in this document — this captures the problem and the intended behavior only.

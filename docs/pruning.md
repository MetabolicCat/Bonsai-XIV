# Pruning

`bonsai prune` reads the tree (see [tree.md](tree.md)) and a rules file,
and keeps the recipes the rules select, with everything they need. What
is left out is pruned. The base ingredients the kept recipes need are
the ones worth hoarding.

The rules file is `rules.toml` in the current directory, or the one
given with `--rules`. The repository's holds a first take on the
criteria of [bonsai-xiv.md](../bonsai-xiv.md).

## How a rule selects recipes

Each rule is a **candidate-selection problem**: among the recipes that
qualify, it picks the best ones by a score, within each group.

```toml
[[rule]]
name = "Craft count"
where = "practical"                # which recipes are candidates
group = ["job", "level_band"]      # pick within each group
score = "turnover / burden"        # higher is better
keep = 1                           # how many per group
```

| Key | Default | Meaning |
|---|---|---|
| `name` | required | shown in the results |
| `where` | `"true"` | an expression: the recipes for which it is true are candidates |
| `group` | `[]` | expressions: candidates with the same values compete together |
| `score` | `"0"` | an expression: the candidates with the highest scores are kept |
| `keep` | all | how many candidates each group keeps |
| `enabled` | `true` | `false` skips the rule |

A candidate whose score is unknown ranks after the others. Ties keep
the lower recipe id, so that the same tree and rules always give the
same result.

## Keeping a recipe keeps what it needs

A kept recipe keeps its ingredients. A craftable ingredient is made by
its preferred recipe, which is kept too, down to the base ingredients.
That covers the *precursor* criterion: the sub-crafts of a kept recipe
are kept, whichever rule kept it.

The **preferred recipe** of an item is its lowest-level one, the lowest
id among those. Primitives that look at what a recipe needs, such as
`craft_cost` and `farmed_leaves`, follow preferred recipes the same
way.

## Results

- The kept recipes, each with the rules that selected it, or the kept
  recipe it is a sub-craft of.
- The **hoard**: the base ingredients the kept recipes need, each with
  how many kept recipes need it and how it is obtained.
- How much of the tree is pruned.

## Expressions

`where`, `group` and `score` are expressions over the **primitives** of
a recipe, below, and the **parameters** of the rules file. They are a
small subset of Python:

- numbers, strings, `true`/`false` (or `True`/`False`), `none`;
- `+ - * / // %`, comparisons, `and`, `or`, `not`,
  `in` and `not in` with a list: `ui_category in ["Meal", "Medicine"]`;
- `x if condition else y`;
- the functions `min`, `max`, `abs`, `log` (natural), `sqrt`, `round`
  and `coalesce(a, b, …)`, which gives its first known argument.

A primitive can be unknown (`none`): a price with no market data, for
instance. Unknown spreads: arithmetic on it is unknown, a comparison
with it is false, and `coalesce(turnover, 0)` replaces it.

## Parameters

A `[parameters]` table sets the values the primitives depend on, and
any value the rules want to name:

```toml
[parameters]
price_cap = 3        # see price
level_band = 10      # see level_band
min_velocity = 1     # a name the rules use
```

| Parameter | Default | Used by |
|---|---|---|
| `price_cap` | 3 | `price` |
| `level_band` | 10 | `level_band` |
| `level_caps` | `[50, 60, 70, 80, 90, 100]` | `level_cap` |

## Primitives

All primitives describe one recipe; most describe the item it makes.

### The recipe

| Primitive | Meaning |
|---|---|
| `recipe_id`, `item_id`, `name` | ids, and the name of the item made |
| `job` | crafting job: `Woodworking`, `Cooking`, … |
| `level`, `stars` | job level and difficulty stars |
| `level_band` | first level of the recipe's band of `level_band` levels: 1, 11, 21, … |
| `expert`, `master_book` | expert recipe; needs a master recipe book |
| `amount` | items one craft makes |
| `burden` | ingredient units per craft, crystals excluded |
| `ingredients` | distinct ingredients, crystals excluded |
| `crystals` | crystal, shard and cluster units per craft |

### The item made

| Primitive | Meaning |
|---|---|
| `stack_size`, `stackable` | stack size; whether it is over 1 |
| `can_be_hq`, `marketable`, `untradable` | from the item |
| `ui_category` | `Meal`, `Medicine`, `Lumber`, … |
| `item_level`, `equip_level` | item level; level to use or equip it |
| `level_cap` | the lowest of `level_caps` at or above `equip_level` |
| `leve`, `leve_level` | it is turned in for a crafting leve; the lowest such leve's level |

### Market

Market primitives use the high-quality market for an item that can be
HQ, the normal-quality one otherwise.

| Primitive | Meaning |
|---|---|
| `min_listing` | lowest price listed |
| `average_price` | average sale price, as Universalis gives it |
| `price` | `average_price`, capped at `price_cap` × `min_listing` |
| `velocity` | items sold per day |
| `turnover` | `price` × `velocity`: gil per day the market absorbs |

The cap is there for items sold to move gil between players: one sale
at millions for an item listed at a few hundred gil makes its average
meaningless. With no listing, `price` is the average.

### What the recipe needs

These follow preferred recipes down to the base ingredients (the
leaves).

| Primitive | Meaning |
|---|---|
| `craft_cost` | gil to make one craft, buying each ingredient at its cheapest: vendor, market (`min_listing`), or making it |
| `profit` | `price` × `amount` − `craft_cost` |
| `leaves` | distinct base ingredients, crystals excluded |
| `vendor_leaves` | those sold by a vendor, for gil or another currency |
| `gathered_leaves` | those gathered, fished or grown |
| `farmed_leaves` | those neither sold nor gathered: dropped, duty loot, ventures, … |
| `unsourced_leaves` | those with no known source |

## Not yet

- Log completion (criterion 1) needs the crafting log of a character:
  it waits for the player data import.
- Costs in currencies other than gil (tomestones, scrips) do not count
  in `craft_cost`.

# Overrides

The sources are sometimes wrong or incomplete: a shop Teamcraft does
not know, whose costs the game data holds as currency indexes; a drop
nobody reported. Overrides correct the `source` and `cost` tables of the
tree (see [tree.md](tree.md)) by hand.

## Files

`bonsai build` reads, in this order, the ones that exist:

1. `overrides.toml` in the current directory: the repository's, shared
   and reviewed like code;
2. `$XDG_CONFIG_HOME/bonsai-xiv/overrides.toml`
   (`~/.config/bonsai-xiv/overrides.toml` by default): personal ones.

A later file wins: its entries for an item, kind and ref replace the
earlier file's for the same item, kind and ref. `bonsai status` lists
the files read.

## Entries

Each entry is a `[[source]]` table:

| Key | Required | Meaning |
|---|---|---|
| `item` | yes | item id |
| `kind` | yes | a `source` kind, such as `special_shop` |
| `ref` | no | what `kind` says, such as the shop id |
| `amount` | no | items received per trade, for shops |
| `costs` | no | what a trade costs, all paid together: `[{ item = …, amount = … }]` |
| `remove` | no | `true` removes the sources of that item, kind and ref |

The entries for an item, kind and ref replace every source the build
found for them, or add them where it found none; an item sold by
several trades in one shop takes one entry per trade. An entry with
`remove = true` stands alone for its item, kind and ref.

The build stops on an entry for an unknown item, cost item or kind, so
that a typo cannot go unnoticed. Write the item's name in a comment:
ids are easy to mistype.

```toml
# An item for 20 Allagan Tomestones of Poetics (28), in a shop Teamcraft
# lacks, whose costs the game data holds as a currency index.
[[source]]
item = 44000
kind = "special_shop"
ref = 1770417
amount = 1
costs = [{ item = 28, amount = 20 }]

# A vendor that no longer sells this item.
[[source]]
item = 5111
kind = "gil_shop"
ref = 262173
remove = true
```

The ids above illustrate the format; they are not corrections.

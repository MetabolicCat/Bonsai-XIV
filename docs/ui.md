# The pruning UI

A page to experiment with rules: edit them, and see at once what they
keep. It is a [marimo](https://marimo.io) notebook, `ui/pruning.py`.

```sh
make ui         # run it as an app, in the browser
make ui-edit    # open it as a notebook, to change the page itself
```

The first run installs marimo, an optional dependency (the `ui` group).
It needs a built tree: `bonsai refresh game` first, and `bonsai refresh
market` for the market primitives.

## The page

- **Cache directory** and **rules file**: where the tree and the rules
  are read from; the same defaults as the `bonsai` command.
- **Rules**: the rules file, in an editor. Each change applies as you
  type; a mistake shows instead of the results, naming the rule. **Save**
  writes the editor back to the rules file.
- **Summary**: what each rule selected, how much is kept and pruned, the
  size of the hoard.
- **Tabs**: one per rule, with its picks group by group; the kept
  recipes, with the rules or the recipe each is kept for; the hoard,
  the most needed first. Tables sort, filter and download.
- **Explore**: a `where` and a `score` over every recipe, with the
  primitives of your choice as columns: a rule to try before writing it.

Rules, parameters and primitives are described in
[pruning.md](pruning.md).

"""Experiment with pruning rules: edit them, see what they keep.

A marimo notebook: `make ui` runs it as an app, `make ui-edit` opens it
as a notebook. See docs/ui.md.
"""

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="full", app_title="Bonsai XIV: pruning")


@app.cell
def _():
    from pathlib import Path

    import marimo as mo

    from bonsai import paths, report
    from bonsai.cache import Cache
    from bonsai.primitives import Primitives
    from bonsai.pruning import prune
    from bonsai.rules import Rules
    from bonsai.tree import Tree

    return Cache, Path, Primitives, Rules, Tree, mo, paths, prune, report


@app.cell
def _(mo, paths):
    cache_dir = mo.ui.text(
        value=str(paths.cache_dir()), label="Cache directory", full_width=True
    )
    rules_file = mo.ui.text(value="rules.toml", label="Rules file", full_width=True)
    mo.hstack([cache_dir, rules_file], widths="equal")
    return cache_dir, rules_file


@app.cell
def _(Cache, Path, Tree, cache_dir, mo):
    _database = Cache(Path(cache_dir.value)).database
    mo.stop(
        not _database.exists(),
        mo.callout(
            mo.md(f"No tree in `{cache_dir.value}`: run `bonsai refresh game`."),
            kind="warn",
        ),
    )
    tree = Tree.load(_database)
    return (tree,)


@app.cell
def _(Path, mo, rules_file):
    _path = Path(rules_file.value)
    editor = mo.ui.code_editor(
        value=_path.read_text(encoding="utf-8") if _path.exists() else "",
        language="toml",
        min_height=320,
        max_height=640,
        debounce=600,
        label="Rules: changes apply as you type; save to keep them",
    )
    save = mo.ui.run_button(label="Save to the rules file")
    mo.vstack([editor, save])
    return editor, save


@app.cell
def _(Path, editor, mo, rules_file, save):
    mo.stop(not save.value)
    Path(rules_file.value).write_text(editor.value, encoding="utf-8")
    mo.callout(mo.md(f"Saved to `{rules_file.value}`."), kind="success")


@app.cell
def _(Rules, editor, mo, prune, tree):
    try:
        _rules = Rules.parse(editor.value, "rules")
        _error = None
    except ValueError as error:
        _rules, _error = None, str(error)
    mo.stop(_rules is None, mo.callout(_error, kind="danger"))
    pruning = prune(tree, _rules)
    return (pruning,)


@app.cell
def _(mo, pruning, report, tree):
    _totals = report.summary(tree, pruning)
    _per_rule = "".join(
        f"| {name} | {count} |\n" for name, count in _totals["rules"].items()
    )
    mo.md(
        f"**Kept {_totals['kept']} recipes of {_totals['recipes']}**, pruned"
        f" {_totals['pruned']}; **{_totals['hoard']} base ingredients to hoard**."
        f"\n\n| Rule | Selected |\n|---|---|\n{_per_rule}"
    )


@app.cell
def _(mo):
    # The tab shown survives the tabs being rebuilt when the rules change.
    get_tab, set_tab = mo.state(None)
    return get_tab, set_tab


@app.cell
def _(get_tab, mo, pruning, report, set_tab, tree):
    _table = {"selection": None, "page_size": 25}
    _tabs = {
        **{
            f"Rule: {name}": mo.ui.table(
                report.selections(tree, pruning, name), **_table
            )
            for name in pruning.selections
        },
        "Kept": mo.ui.table(report.kept(tree, pruning), **_table),
        "Hoard": mo.ui.table(report.hoard(tree, pruning), **_table),
    }
    mo.ui.tabs(
        _tabs,
        value=get_tab() if get_tab() in _tabs else None,
        on_change=set_tab,
    )


@app.cell
def _(Primitives, mo):
    where = mo.ui.text(value="marketable", label="where", full_width=True)
    score = mo.ui.text(value="turnover", label="score", full_width=True)
    columns = mo.ui.multiselect(
        options=Primitives.NAMES,
        value=["name", "job", "level", "price", "velocity", "turnover", "profit"],
        label="columns",
    )
    return columns, score, where


@app.cell
def _(columns, mo, pruning, report, score, where):
    try:
        _rows = report.explore(pruning, where.value, score.value, columns.value)
        _found = mo.ui.table(_rows, selection=None, page_size=25)
    except ValueError as error:
        _found = mo.callout(str(error), kind="danger")
    mo.vstack(
        [
            mo.md(
                "### Explore\n\nTry a `where` and a `score` over every recipe"
                " before making them a rule. The names are the primitives of"
                " docs/pruning.md."
            ),
            mo.hstack([where, score], widths="equal"),
            columns,
            _found,
        ]
    )


if __name__ == "__main__":
    app.run()

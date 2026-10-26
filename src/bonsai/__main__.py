"""The `bonsai` command line."""

import argparse
import os
import sqlite3
import sys
from contextlib import nullcontext
from importlib.metadata import version
from pathlib import Path

import httpx

from bonsai import overrides
from bonsai.build import build
from bonsai.cache import Cache
from bonsai.pruning import prune
from bonsai.refresh import refresh_game, refresh_market
from bonsai.rules import Rules
from bonsai.sources import datamining, teamcraft, universalis
from bonsai.tree import Tree

DEFAULT_SCOPE = "Japan"


def main(argv: list[str] | None = None, client: httpx.Client | None = None) -> int:
    args = _parser().parse_args(argv)
    cache = Cache(args.cache_dir)
    try:
        if args.command == "status":
            _status(cache)
            return 0
        if args.command == "prune":
            _prune(cache, args.rules, args.show)
            return 0
        if args.command == "refresh":
            with nullcontext(client) if client else _client() as http:
                if args.what == "game":
                    downloaded = refresh_game(http, cache)
                    print(f"downloaded: {', '.join(downloaded) or 'nothing new'}")
                else:
                    count = refresh_market(http, cache, args.scope, _show_progress)
                    print(file=sys.stderr)
                    print(f"priced {count} items in {args.scope}")
        build(cache, _override_files())
        return 0
    except (RuntimeError, ValueError, httpx.HTTPError) as error:
        print(f"bonsai: {error}", file=sys.stderr)
        return 1


def _show_progress(done: int, total: int) -> None:
    print(f"\rpricing items: {done}/{total}", end="", file=sys.stderr, flush=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bonsai", description="Build and refresh the FFXIV recipe tree."
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=_default_cache_dir(),
        help="where the sources and the tree are kept (default: %(default)s)",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    refresh = commands.add_parser("refresh", help="fetch sources, then build")
    what = refresh.add_subparsers(dest="what", required=True)
    what.add_parser("game", help="game data, when its sources moved")
    market = what.add_parser("market", help="market prices of the tree's items")
    market.add_argument(
        "--scope",
        default=DEFAULT_SCOPE,
        help="Universalis region, data center or world (default: %(default)s)",
    )
    commands.add_parser("build", help="rebuild the tree from the cache, offline")
    commands.add_parser("status", help="show what the cache holds")
    prune = commands.add_parser("prune", help="keep what the rules select")
    prune.add_argument(
        "--rules",
        type=Path,
        default=Path("rules.toml"),
        help="the rules file (default: %(default)s)",
    )
    prune.add_argument(
        "--show", choices=["kept", "hoard"], help="list the kept recipes or the hoard"
    )
    return parser


def _default_cache_dir() -> Path:
    return _xdg("XDG_CACHE_HOME", ".cache") / "bonsai-xiv"


def _override_files() -> list[Path]:
    """The shared overrides, then the personal ones: those that exist."""
    files = [
        Path("overrides.toml"),
        _xdg("XDG_CONFIG_HOME", ".config") / "bonsai-xiv" / "overrides.toml",
    ]
    return [path for path in files if path.exists()]


def _xdg(variable: str, default: str) -> Path:
    directory = os.environ.get(variable)
    return Path(directory) if directory else Path.home() / default


def _client() -> httpx.Client:
    return httpx.Client(
        headers={
            "User-Agent": f"bonsai-xiv/{version('bonsai-xiv')}"
            " (+https://github.com/RKI027/Bonsai-XIV)"
        },
        timeout=60,
        follow_redirects=True,
    )


def _status(cache: Cache) -> None:
    for source in (datamining.NAME, teamcraft.NAME):
        print(f"{source:<12} {cache.version(source) or 'not fetched'}")
    print(f"{universalis.NAME:<12} {_market_status(cache)}")
    print(f"{'tree':<12} {_tree_status(cache)}")
    print(f"{'overrides':<12} {_overrides_status()}")


def _market_status(cache: Cache) -> str:
    market = cache.version(universalis.NAME)
    if market is None:
        return "not fetched"
    meta = universalis.meta(cache.directory(universalis.NAME, market))
    return f"{meta['market_scope']}, fetched at {meta['market_fetched_at']}"


def _prune(cache: Cache, rules_file: Path, show: str | None) -> None:
    if not rules_file.exists():
        raise RuntimeError(f"no rules file {rules_file}: see docs/pruning.md")
    if not cache.database.exists():
        raise RuntimeError("no tree: run `bonsai refresh game` first")
    tree = Tree.load(cache.database)
    pruning = prune(tree, Rules.load(rules_file))
    width = max((len(name) for name in pruning.selections), default=0)
    for name, selected in pruning.selections.items():
        print(f"{name:<{width}}  {len(selected)} selected")
    print(
        f"kept {len(pruning.kept)} recipes of {len(tree.recipes)},"
        f" pruned {len(pruning.pruned)}; {len(pruning.hoard)} base ingredients to hoard"
    )

    def made(recipe: int) -> str:
        return tree.items[tree.recipes[recipe].item_id].name

    rows: list[tuple[str, str, str]] = []
    if show == "hoard":
        for hoarded in sorted(
            pruning.hoard.values(),
            key=lambda h: (-len(h.needed_by), tree.items[h.item_id].name),
        ):
            rows.append(
                (
                    tree.items[hoarded.item_id].name,
                    f"needed by {len(hoarded.needed_by)}",
                    ", ".join(sorted(hoarded.kinds)) or "no known source",
                )
            )
    elif show == "kept":
        for kept in sorted(
            pruning.kept.values(),
            key=lambda k: (not k.rules, -tree.recipes[k.recipe_id].level, k.recipe_id),
        ):
            recipe = tree.recipes[kept.recipe_id]
            reasons = [f"{rule} #{selection.rank}" for rule, selection in kept.rules]
            reasons += [f"for {made(r)}" for r in sorted(kept.needed_by)]
            rows.append(
                (made(recipe.id), f"{recipe.job} {recipe.level}", ", ".join(reasons))
            )
    widths = [max((len(row[i]) for row in rows), default=0) for i in range(2)]
    for first, second, third in rows:
        print(f"{first:<{widths[0]}}  {second:<{widths[1]}}  {third}")


def _overrides_status() -> str:
    files = []
    for path in _override_files():
        count = len(overrides.entries(path))
        files.append(f"{path} ({count} source{'s' if count != 1 else ''})")
    return ", ".join(files) or "none"


def _tree_status(cache: Cache) -> str:
    if not cache.database.exists():
        return "not built"
    with sqlite3.connect(cache.database) as db:
        (items,) = db.execute("SELECT count(*) FROM item").fetchone()
        (recipes,) = db.execute("SELECT count(*) FROM recipe").fetchone()
    db.close()
    return f"{items} items, {recipes} recipes"


if __name__ == "__main__":
    sys.exit(main())

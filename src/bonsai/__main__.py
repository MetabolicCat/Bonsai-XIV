"""The `bonsai` command line."""

import argparse
import os
import sqlite3
import sys
from contextlib import nullcontext
from importlib.metadata import version
from pathlib import Path

import httpx

from bonsai.build import build
from bonsai.cache import Cache
from bonsai.refresh import refresh_game, refresh_market
from bonsai.sources import datamining, teamcraft, universalis

DEFAULT_SCOPE = "Japan"


def main(argv: list[str] | None = None, client: httpx.Client | None = None) -> int:
    args = _parser().parse_args(argv)
    cache = Cache(args.cache_dir)
    try:
        if args.command == "status":
            _status(cache)
            return 0
        if args.command == "refresh":
            with nullcontext(client) if client else _client() as http:
                if args.what == "game":
                    downloaded = refresh_game(http, cache)
                    print(f"downloaded: {', '.join(downloaded) or 'nothing new'}")
                else:
                    count = refresh_market(http, cache, args.scope)
                    print(f"priced {count} items in {args.scope}")
        build(cache)
        return 0
    except (RuntimeError, httpx.HTTPError) as error:
        print(f"bonsai: {error}", file=sys.stderr)
        return 1


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
    return parser


def _default_cache_dir() -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME")
    return (Path(xdg) if xdg else Path.home() / ".cache") / "bonsai-xiv"


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


def _market_status(cache: Cache) -> str:
    market = cache.version(universalis.NAME)
    if market is None:
        return "not fetched"
    meta = universalis.meta(cache.directory(universalis.NAME, market))
    return f"{meta['market_scope']}, fetched at {meta['market_fetched_at']}"


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

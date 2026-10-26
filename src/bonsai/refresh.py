"""Bringing the cached sources up to date."""

import sqlite3
from datetime import UTC, datetime

import httpx

from bonsai.cache import Cache
from bonsai.sources import datamining, teamcraft, universalis


def refresh_game(client: httpx.Client, cache: Cache) -> list[str]:
    """Download the game data sources that moved since the last refresh.

    Returns the names of the sources downloaded.
    """
    downloaded = []
    for source in (datamining, teamcraft):
        commit = source.head(client)
        if commit == cache.version(source.NAME):
            continue
        with cache.download(source.NAME, commit) as directory:
            source.fetch(client, commit, directory)
        downloaded.append(source.NAME)
    return downloaded


def refresh_market(
    client: httpx.Client,
    cache: Cache,
    scope: str,
    progress: universalis.Progress | None = None,
) -> int:
    """Download the market data in `scope` of the tree's marketable items.

    `scope` is a Universalis region, data center or world. Returns the
    number of items asked for. `progress` is called after each request
    with the number of items done and the total.
    """
    if not cache.database.exists():
        raise RuntimeError("no tree to price: run `bonsai refresh game` first")
    with sqlite3.connect(cache.database) as db:
        items = [
            item
            for (item,) in db.execute(
                """
                SELECT id FROM item
                WHERE marketable AND (
                    id IN (SELECT item_id FROM recipe)
                    OR id IN (SELECT item_id FROM ingredient)
                )
                ORDER BY id
                """
            )
        ]
    db.close()
    fetched_at = datetime.now(UTC)
    version = fetched_at.strftime("%Y%m%dT%H%M%SZ")
    with cache.download(universalis.NAME, version) as directory:
        universalis.fetch(client, scope, items, fetched_at, directory, progress)
    return len(items)

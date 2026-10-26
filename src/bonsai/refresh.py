"""Bringing the cached sources up to date."""

import httpx

from bonsai.cache import Cache
from bonsai.sources import datamining


def refresh_game(client: httpx.Client, cache: Cache) -> None:
    """Download the game data at the head of its source."""
    commit = datamining.head(client)
    datamining.fetch(client, commit, cache.directory(datamining.NAME, commit))
    cache.set_version(datamining.NAME, commit)

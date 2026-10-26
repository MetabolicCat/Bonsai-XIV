"""Bringing the cached sources up to date."""

import httpx

from bonsai.cache import Cache
from bonsai.sources import datamining, teamcraft


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

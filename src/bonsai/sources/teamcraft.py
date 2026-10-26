"""Crowdsourced item sources, from Teamcraft: monster drops, duty loot."""

import json
from collections.abc import Iterator
from pathlib import Path

import httpx

from bonsai.sources import github

NAME = "teamcraft"
REPOSITORY = "ffxiv-teamcraft/ffxiv-teamcraft"
EXTRACTS = "libs/data/src/lib/extracts/extracts.json"

# Teamcraft's DataType values for the sources Bonsai imports.
DROPS = 10
INSTANCES = 6


def head(client: httpx.Client) -> str:
    return github.head_commit(client, REPOSITORY)


def fetch(client: httpx.Client, commit: str, directory: Path) -> None:
    """Download the item sources at `commit` into `directory`."""
    content = github.raw_file(client, REPOSITORY, commit, EXTRACTS)
    (directory / "extracts.json").write_bytes(content)


def sources(directory: Path) -> Iterator[tuple[int, str, int]]:
    """The (item, kind, ref) of every drop and instance source."""
    extracts = json.loads((directory / "extracts.json").read_text(encoding="utf-8"))
    for item, extract in extracts.items():
        for source in extract.get("sources", []):
            if source["type"] == DROPS:
                for monster in source["data"]:
                    yield int(item), "drop", monster["id"]
            elif source["type"] == INSTANCES:
                for instance in source["data"]:
                    yield int(item), "instance", instance

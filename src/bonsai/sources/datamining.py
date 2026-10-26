"""The game's data sheets, from xivapi/ffxiv-datamining."""

import csv
from collections.abc import Iterator
from pathlib import Path

import httpx

from bonsai.sources import github

NAME = "datamining"
REPOSITORY = "xivapi/ffxiv-datamining"
SHEETS = [
    "CraftLeve",
    "CraftType",
    "FishParameter",
    "GatheringItem",
    "GilShopItem",
    "Item",
    "ItemUICategory",
    "Leve",
    "Recipe",
    "RecipeLevelTable",
    "SpearfishingItem",
    "SpecialShop",
]


def head(client: httpx.Client) -> str:
    return github.head_commit(client, REPOSITORY)


def fetch(client: httpx.Client, commit: str, directory: Path) -> None:
    """Download every sheet Bonsai uses, at `commit`, into `directory`."""
    for sheet in SHEETS:
        content = github.raw_file(client, REPOSITORY, commit, f"csv/en/{sheet}.csv")
        (directory / f"{sheet}.csv").write_bytes(content)


def rows(directory: Path, sheet: str) -> Iterator[dict[str, str]]:
    with open(directory / f"{sheet}.csv", newline="", encoding="utf-8") as f:
        yield from csv.DictReader(f)

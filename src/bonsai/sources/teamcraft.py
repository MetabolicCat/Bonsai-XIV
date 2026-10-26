"""Crowdsourced item sources, from Teamcraft: drops, trades, and more."""

import json
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, NamedTuple

import httpx

from bonsai.sources import github

NAME = "teamcraft"
REPOSITORY = "ffxiv-teamcraft/ffxiv-teamcraft"
EXTRACTS = "libs/data/src/lib/extracts/extracts.json"

# Teamcraft's DataType values.
TRADES = 2

# The other DataType values Bonsai imports, by the kind of source they
# become, with how to read a source's ref from one of its entries.
KINDS: dict[int, tuple[str, Callable[[Any], int]]] = {
    4: ("reduction", int),
    5: ("desynthesis", int),
    6: ("instance", int),
    8: ("gardening", lambda garden: int(garden["seedItemId"])),
    9: ("voyage", lambda voyage: int(voyage["name"]["id"])),
    10: ("drop", lambda monster: int(monster["id"])),
    13: ("treasure", int),
    14: ("fate", lambda fate: int(fate["id"])),
    15: ("venture", lambda venture: int(venture["id"])),
    18: ("quest", int),
}


class Trade(NamedTuple):
    """`amount` of `item`, from a shop, for all of `costs` (item, amount).

    A cost's item is None when the currency is unknown.
    """

    item: int
    shop_type: str | None
    shop: int | None
    amount: int
    costs: list[tuple[int | None, int]]


def head(client: httpx.Client) -> str:
    return github.head_commit(client, REPOSITORY)


def fetch(client: httpx.Client, commit: str, directory: Path) -> None:
    """Download the item sources at `commit` into `directory`."""
    content = github.raw_file(client, REPOSITORY, commit, EXTRACTS)
    (directory / "extracts.json").write_bytes(content)


def sources(directory: Path) -> Iterator[tuple[int, str, int]]:
    """The (item, kind, ref) of every source of a kind in KINDS."""
    for item, source in _sources(directory):
        if source["type"] in KINDS:
            kind, ref = KINDS[source["type"]]
            # Gardening holds one entry, every other type a list of them.
            data = source["data"]
            for entry in data if isinstance(data, list) else [data]:
                yield item, kind, ref(entry)


def trades(directory: Path) -> Iterator[Trade]:
    """Every shop trade, with its costs resolved to items."""
    for item, source in _sources(directory):
        if source["type"] != TRADES:
            continue
        for shop in source["data"]:
            for trade in shop["trades"]:
                costs: list[tuple[int | None, int]] = [
                    (c["id"], c["amount"]) for c in trade["currencies"]
                ]
                for received in trade["items"]:
                    if received["id"] == item:
                        yield Trade(
                            item,
                            shop.get("type"),
                            shop.get("id"),
                            received["amount"],
                            costs,
                        )


def _sources(directory: Path) -> Iterator[tuple[int, dict[str, Any]]]:
    extracts = json.loads((directory / "extracts.json").read_text(encoding="utf-8"))
    for item, extract in extracts.items():
        for source in extract.get("sources", []):
            yield int(item), source

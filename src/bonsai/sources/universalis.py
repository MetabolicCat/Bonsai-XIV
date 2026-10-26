"""Market prices and sale velocity, from Universalis."""

import json
from collections.abc import Iterator
from datetime import datetime
from itertools import batched
from pathlib import Path
from typing import Any

import httpx

NAME = "universalis"
API = "https://universalis.app/api/v2"

# The most items the aggregated endpoint answers for in one request.
BATCH = 100

# The scopes an aggregated answer can hold, narrowest first: the
# narrowest one present is the scope that was asked for.
SCOPES = ("world", "dc", "region")

ISO_TIME = "%Y-%m-%dT%H:%M:%SZ"


def fetch(
    client: httpx.Client,
    scope: str,
    items: list[int],
    fetched_at: datetime,
    directory: Path,
) -> None:
    """Download the market data of `items` in `scope` into `directory`."""
    results = []
    for batch in batched(items, BATCH):
        response = client.get(f"{API}/aggregated/{scope}/{','.join(map(str, batch))}")
        response.raise_for_status()
        results.extend(response.json()["results"])
    snapshot = {
        "scope": scope,
        "fetched_at": fetched_at.strftime(ISO_TIME),
        "results": results,
    }
    (directory / "market.json").write_text(json.dumps(snapshot), encoding="utf-8")


def meta(directory: Path) -> dict[str, str]:
    """The scope and fetch time of the snapshot in `directory`."""
    snapshot = _snapshot(directory)
    return {
        "market_scope": snapshot["scope"],
        "market_fetched_at": snapshot["fetched_at"],
    }


def prices(
    directory: Path,
) -> Iterator[tuple[int, bool, int | None, float | None, float | None]]:
    """The (item, hq, min listing, average price, daily velocity) rows."""
    for result in _snapshot(directory)["results"]:
        for quality, hq in (("nq", False), ("hq", True)):
            data = result.get(quality, {})
            row = (
                _narrowest(data.get("minListing"), "price"),
                _narrowest(data.get("averageSalePrice"), "price"),
                _narrowest(data.get("dailySaleVelocity"), "quantity"),
            )
            if any(value is not None for value in row):
                yield (result["itemId"], hq, *row)


def _narrowest(values: dict[str, Any] | None, key: str) -> Any:
    for scope in SCOPES:
        if values and scope in values:
            return values[scope][key]
    return None


def _snapshot(directory: Path) -> dict[str, Any]:
    snapshot: dict[str, Any] = json.loads(
        (directory / "market.json").read_text(encoding="utf-8")
    )
    return snapshot

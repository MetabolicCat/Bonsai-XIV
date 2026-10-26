"""Building a tree from a fake upstream, and reading it back."""

import sqlite3

from upstream import Upstream

from bonsai.build import build
from bonsai.cache import Cache
from bonsai.refresh import refresh_game


def built(upstream: Upstream, cache: Cache) -> sqlite3.Connection:
    with upstream.client() as client:
        refresh_game(client, cache)
    build(cache)
    return sqlite3.connect(cache.database)


def named(*items: int) -> list[dict[str, object]]:
    return [{"#": item, "Name": f"Item {item}"} for item in items]


Source = tuple[int, str, int | None, int | None, tuple[tuple[int, int], ...]]


def sources(db: sqlite3.Connection) -> list[Source]:
    """Every (item, kind, ref, amount received, costs) source."""
    rows = db.execute(
        "SELECT s.id, s.item_id, s.kind, s.ref, s.amount, c.item_id, c.amount"
        " FROM source s LEFT JOIN cost c ON c.source_id = s.id"
    ).fetchall()
    found: dict[int, tuple[int, str, int | None, int | None]] = {}
    costs: dict[int, list[tuple[int, int]]] = {}
    for id, item, kind, ref, amount, cost_item, cost_amount in rows:
        found[id] = (item, kind, ref, amount)
        costs.setdefault(id, [])
        if cost_item is not None:
            costs[id].append((cost_item, cost_amount))
    return sorted(
        ((*found[id], tuple(sorted(costs[id]))) for id in found),
        key=lambda source: (source[0], source[1], source[2] or 0, source[4]),
    )

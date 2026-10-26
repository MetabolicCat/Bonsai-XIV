"""Building the tree from the cached sources: see docs/tree.md."""

import sqlite3

from bonsai.cache import Cache
from bonsai.sources import datamining

SCHEMA = """
CREATE TABLE item (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    stack_size INTEGER NOT NULL
);
"""


def build(cache: Cache) -> None:
    """Write the tree to `cache.database`, from the cache only."""
    version = cache.version(datamining.NAME)
    if version is None:
        raise RuntimeError("no game data in the cache: run `bonsai refresh game`")
    sheets = cache.directory(datamining.NAME, version)

    cache.database.unlink(missing_ok=True)
    with sqlite3.connect(cache.database) as db:
        db.executescript(SCHEMA)
        db.executemany(
            "INSERT INTO item VALUES (?, ?, ?)",
            (
                (int(row["#"]), row["Name"], int(row["StackSize"]))
                for row in datamining.rows(sheets, "Item")
                if row["Name"]
            ),
        )
    db.close()

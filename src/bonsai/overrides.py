"""Hand corrections to the sources of the tree: see docs/overrides.md."""

import tomllib
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any, NamedTuple

# The sources an override is about: item, kind and ref.
Key = tuple[int, str, int | None]


class Override(NamedTuple):
    item: int
    kind: str
    ref: int | None
    amount: int | None
    costs: list[tuple[int | None, int]]
    remove: bool

    @property
    def key(self) -> Key:
        return self.item, self.kind, self.ref


class Overrides(NamedTuple):
    """The overrides for one item, kind and ref, and the file they are from."""

    path: Path
    entries: list[Override]


def load(paths: Sequence[Path], kinds: Iterable[str]) -> dict[Key, Overrides]:
    """The overrides of `paths`, a later file winning over an earlier one."""
    known = set(kinds)
    merged: dict[Key, Overrides] = {}
    for path in paths:
        found: dict[Key, Overrides] = {}
        for number, entry in enumerate(entries(path), start=1):
            override = _parse(path, number, entry, known)
            found.setdefault(override.key, Overrides(path, [])).entries.append(override)
        for key, overrides in found.items():
            if len(overrides.entries) > 1 and any(o.remove for o in overrides.entries):
                raise ValueError(
                    f"{path}: a source with remove = true must stand alone"
                    f" for item {key[0]}, kind {key[1]!r}, ref {key[2]}"
                )
        merged |= found
    return merged


def entries(path: Path) -> list[dict[str, Any]]:
    """The raw source entries of the overrides file at `path`."""
    try:
        with open(path, "rb") as f:
            found: list[dict[str, Any]] = tomllib.load(f).get("source", [])
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f"{path}: {error}") from error
    return found


def _parse(path: Path, number: int, entry: dict[str, Any], kinds: set[str]) -> Override:
    try:
        override = Override(
            item=int(entry["item"]),
            kind=str(entry["kind"]),
            ref=None if entry.get("ref") is None else int(entry["ref"]),
            amount=None if entry.get("amount") is None else int(entry["amount"]),
            costs=[
                (int(cost["item"]), int(cost["amount"]))
                for cost in entry.get("costs", [])
            ],
            remove=bool(entry.get("remove", False)),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"{path}: source {number}: missing or bad {error}") from error
    if override.kind not in kinds:
        raise ValueError(f"{path}: source {number}: unknown kind {override.kind!r}")
    return override

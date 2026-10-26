"""Rules: which recipes are worth keeping. See docs/pruning.md."""

import tomllib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bonsai.expressions import Expression
from bonsai.primitives import DEFAULT_PARAMETERS, Primitives

RULE_KEYS = {"name", "where", "group", "score", "keep", "enabled"}


@dataclass(frozen=True)
class Rule:
    """Among the recipes `where` is true of, the `keep` best by `score`.

    Candidates compete within groups: those with the same `group` values.
    """

    name: str
    where: Expression
    group: list[Expression]
    score: Expression
    keep: int | None
    enabled: bool = True


@dataclass(frozen=True)
class Selection:
    """A recipe a rule kept: its group, score and rank in the group."""

    recipe_id: int
    group: tuple[Any, ...]
    score: Any
    rank: int


@dataclass(frozen=True)
class Rules:
    parameters: dict[str, Any]
    rules: list[Rule] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> "Rules":
        return cls.parse(path.read_text(encoding="utf-8"), str(path))

    @classmethod
    def parse(cls, text: str, origin: str = "rules") -> "Rules":
        """The rules of a TOML `text`; mistakes name `origin` and the rule."""
        try:
            data = tomllib.loads(text)
        except tomllib.TOMLDecodeError as error:
            raise ValueError(f"{origin}: {error}") from error
        for table in data.keys() - {"parameters", "rule"}:
            raise ValueError(f"{origin}: unknown table {table!r}")
        parameters = dict(data.get("parameters", {}))
        for name in parameters.keys() & set(Primitives.NAMES):
            raise ValueError(f"{origin}: parameter {name!r} is a primitive")
        known = set(Primitives.NAMES) | parameters.keys() | DEFAULT_PARAMETERS.keys()
        rules = [
            _rule(f"{origin}: rule", number, entry, known)
            for number, entry in enumerate(data.get("rule", []), start=1)
        ]
        return cls(parameters, rules)

    @property
    def enabled(self) -> list[Rule]:
        return [rule for rule in self.rules if rule.enabled]

    def select(
        self, rule: Rule, candidates: Iterable[Mapping[str, Any]]
    ) -> list[Selection]:
        return select(rule, candidates, DEFAULT_PARAMETERS | self.parameters)


def select(
    rule: Rule,
    candidates: Iterable[Mapping[str, Any]],
    parameters: Mapping[str, Any] | None = None,
) -> list[Selection]:
    """The candidates `rule` keeps, group by group, best first.

    Unknown scores rank last; ties keep the lower recipe id.
    """
    groups: dict[tuple[Any, ...], list[tuple[Any, int]]] = {}
    for candidate in candidates:
        values = {**(parameters or {}), **candidate}
        if not rule.where(values):
            continue
        group = tuple(_hashable(expression(values)) for expression in rule.group)
        groups.setdefault(group, []).append(
            (rule.score(values), candidate["recipe_id"])
        )
    selected = []
    for group, scored in groups.items():
        scored.sort(
            key=lambda entry: (entry[0] is None, _descending(entry[0]), entry[1])
        )
        for rank, (score, recipe) in enumerate(scored[: rule.keep], start=1):
            selected.append(Selection(recipe, group, score, rank))
    return selected


def _rule(origin: str, number: int, entry: dict[str, Any], known: set[str]) -> Rule:
    if "name" not in entry:
        raise ValueError(f"{origin} {number}: missing name")
    where = f"{origin} {entry['name']!r}"
    for key in entry.keys() - RULE_KEYS:
        raise ValueError(f"{where}: unknown key {key!r}")
    keep = entry.get("keep")
    if keep is not None and keep < 1:
        raise ValueError(f"{where}: keep must be at least 1")
    try:
        expressions = {
            "where": Expression(str(entry.get("where", "true"))),
            "score": Expression(str(entry.get("score", "0"))),
        }
        sources = entry.get("group", [])
        # One expression can stand for a list of it.
        sources = [sources] if isinstance(sources, str) else sources
        group = [Expression(str(source)) for source in sources]
    except ValueError as error:
        raise ValueError(f"{where}: {error}") from error
    for expression in [*expressions.values(), *group]:
        for name in sorted(expression.names - known):
            raise ValueError(f"{where}: unknown name {name!r} in {expression.source!r}")
    return Rule(
        name=str(entry["name"]),
        where=expressions["where"],
        group=group,
        score=expressions["score"],
        keep=keep,
        enabled=bool(entry.get("enabled", True)),
    )


def _hashable(value: Any) -> Any:
    return tuple(value) if isinstance(value, list) else value


def _descending(score: Any) -> Any:
    """A sort key putting higher scores first, for numbers and strings."""
    if score is None:
        return 0
    if isinstance(score, str):
        return tuple(-ord(character) for character in score)
    return -score

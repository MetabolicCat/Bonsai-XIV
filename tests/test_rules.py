from pathlib import Path
from typing import Any

import pytest

from bonsai.rules import Rules, select


def rules(tmp_path: Path, text: str) -> Rules:
    path = tmp_path / "rules.toml"
    path.write_text(text)
    return Rules.load(path)


def recipe(id: int, **values: Any) -> dict[str, Any]:
    return {"recipe_id": id, **values}


def test_a_rule_keeps_the_best_candidates_of_each_group(tmp_path: Path) -> None:
    (rule,) = rules(
        tmp_path,
        """
        [[rule]]
        name = "Craft count"
        where = "velocity >= 1"
        group = ["job"]
        score = "price * velocity"
        keep = 1
        """,
    ).rules
    candidates = [
        recipe(1, job="Cooking", price=10, velocity=5),
        recipe(2, job="Cooking", price=100, velocity=1),
        recipe(3, job="Cooking", price=1000, velocity=0.5),
        recipe(4, job="Alchemy", price=1, velocity=1),
    ]

    assert [(s.recipe_id, s.group, s.score) for s in select(rule, candidates)] == [
        (2, ("Cooking",), 100),
        (4, ("Alchemy",), 1),
    ]


def test_by_default_a_rule_keeps_every_candidate(tmp_path: Path) -> None:
    (rule,) = rules(tmp_path, '[[rule]]\nname = "All"\n').rules

    assert [s.recipe_id for s in select(rule, [recipe(2), recipe(1)])] == [1, 2]


def test_unknown_scores_rank_last_and_ties_keep_the_lower_id(tmp_path: Path) -> None:
    (rule,) = rules(
        tmp_path, '[[rule]]\nname = "Best"\nscore = "turnover"\nkeep = 3\n'
    ).rules
    candidates = [
        recipe(1, turnover=None),
        recipe(2, turnover=5),
        recipe(3, turnover=5),
        recipe(4, turnover=1),
    ]

    assert [s.recipe_id for s in select(rule, candidates)] == [2, 3, 4]


def test_parameters_are_named_values_of_the_rules(tmp_path: Path) -> None:
    loaded = rules(
        tmp_path,
        """
        [parameters]
        min_velocity = 2
        price_cap = 5

        [[rule]]
        name = "Sells"
        where = "velocity >= min_velocity"
        """,
    )
    candidates = [recipe(1, velocity=1), recipe(2, velocity=3)]

    assert loaded.parameters == {"min_velocity": 2, "price_cap": 5}
    assert [s.recipe_id for s in loaded.select(loaded.rules[0], candidates)] == [2]


def test_disabled_rules_are_left_out(tmp_path: Path) -> None:
    loaded = rules(
        tmp_path,
        '[[rule]]\nname = "On"\n[[rule]]\nname = "Off"\nenabled = false\n',
    )

    assert [rule.name for rule in loaded.enabled] == ["On"]


@pytest.mark.parametrize(
    ("text", "error"),
    [
        ('[[rule]]\nwhere = "true"\n', "rule 1: missing name"),
        ('[[rule]]\nname = "R"\nwhere = "1 +"\n', "rule 'R': bad expression"),
        ('[[rule]]\nname = "R"\nscore = "pirce"\n', "rule 'R': unknown name 'pirce'"),
        ('[[rule]]\nname = "R"\nkeep = 0\n', "rule 'R': keep must be at least 1"),
        ('[[rule]]\nname = "R"\nwehre = "true"\n', "rule 'R': unknown key 'wehre'"),
        ("[parameters]\njob = 1\n", "parameter 'job' is a primitive"),
        ("[rules]\n", "unknown table 'rules'"),
        ("[[rule]\n", "rules.toml"),
    ],
)
def test_mistakes_are_reported_with_the_rule(
    tmp_path: Path, text: str, error: str
) -> None:
    with pytest.raises(ValueError, match=error):
        rules(tmp_path, text)


def test_a_group_of_one_expression_can_be_written_alone(tmp_path: Path) -> None:
    (rule,) = rules(tmp_path, '[[rule]]\nname = "R"\ngroup = "job"\nkeep = 1\n').rules

    assert [s.group for s in select(rule, [recipe(1, job="Cooking")])] == [("Cooking",)]

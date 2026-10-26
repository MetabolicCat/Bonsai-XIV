import math

import pytest

from bonsai.expressions import Expression


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("1 + 2 * 3", 7),
        ("price * velocity", 300.0),
        ("price / 0", None),
        ("level // 10 * 10 + 1", 31),
        ("-level", -35),
        ("level >= 30 and job == 'Cooking'", True),
        ("not leve", True),
        ("leve or level > 50", False),
        ("1 < level < 50", True),
        ("job in ['Cooking', 'Alchemy']", True),
        ("job not in ('Cooking',)", False),
        ("100 if leve else 0", 0),
        ("max(price, 20) + min(1, 2)", 101.0),
        ("abs(-2) + round(2.6) + round(1.234, 1)", 6.2),
        ("log(1) + sqrt(16)", 4.0),
        ("true and not false", True),
        ("True", True),
        ("none", None),
    ],
)
def test_expressions_compute_from_named_values(source: str, expected: object) -> None:
    values = {
        "price": 100.0,
        "velocity": 3.0,
        "level": 35,
        "job": "Cooking",
        "leve": False,
    }

    assert Expression(source)(values) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("unknown * 2", None),
        ("unknown + 1 > 0", False),
        ("unknown < 1", False),
        ("not unknown > 1", True),
        ("unknown == none", True),
        ("max(unknown, 1)", None),
        ("coalesce(unknown, 0)", 0),
        ("coalesce(unknown, none)", None),
        ("log(0)", None),
        ("sqrt(-1)", None),
        ("unknown in [1, 2]", False),
    ],
)
def test_an_unknown_value_spreads(source: str, expected: object) -> None:
    assert Expression(source)({"unknown": None}) == expected


def test_an_expression_knows_the_names_it_uses() -> None:
    assert Expression("price * velocity if leve else coalesce(x, 1)").names == {
        "price",
        "velocity",
        "leve",
        "x",
    }


@pytest.mark.parametrize(
    "source",
    [
        "__import__('os')",
        "price.real",
        "[x for x in y]",
        "open('f')",
        "lambda: 1",
        "price[0]",
        "max(x, key=y)",
        "x = 1",
        "1 +",
        "{1: 2}",
        "b'bytes'",
    ],
)
def test_anything_else_is_refused(source: str) -> None:
    with pytest.raises(ValueError, match="expression"):
        Expression(source)


def test_an_unknown_name_is_an_error_when_evaluated() -> None:
    with pytest.raises(ValueError, match="unknown name 'pirce'"):
        Expression("pirce * 2")({"price": 1})


def test_math_domain_is_not_an_error() -> None:
    assert Expression("log(x)")({"x": math.e}) == pytest.approx(1)


def test_an_expression_can_span_lines() -> None:
    assert Expression("\n    (1 + 2)\n    * 3\n")({}) == 9

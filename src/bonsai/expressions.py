"""The expressions rules are written in: see docs/pruning.md.

A small subset of Python, parsed but never handed to Python to run: only
the constructs below are evaluated, over named values. An unknown value
(None) spreads: arithmetic on it is unknown, and comparing it is false.
"""

import ast
import math
import operator
from collections.abc import Callable, Mapping
from typing import Any

CONSTANTS = {"true": True, "false": False, "none": None}

ARITHMETIC: dict[type[ast.operator], Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
}

COMPARISONS: dict[type[ast.cmpop], Callable[[Any, Any], bool]] = {
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
}


def _known(function: Callable[..., Any]) -> Callable[..., Any]:
    """`function`, unknown when an argument is unknown or out of its domain."""

    def call(*args: Any) -> Any:
        if any(arg is None for arg in args):
            return None
        try:
            return function(*args)
        except (ValueError, ZeroDivisionError):
            return None

    return call


FUNCTIONS: dict[str, Callable[..., Any]] = {
    "min": _known(min),
    "max": _known(max),
    "abs": _known(abs),
    "log": _known(math.log),
    "sqrt": _known(math.sqrt),
    "round": _known(round),
    "coalesce": lambda *args: next((arg for arg in args if arg is not None), None),
}


class Expression:
    """An expression, checked when created, evaluated over named values."""

    def __init__(self, source: str) -> None:
        self.source = source
        try:
            tree = ast.parse(source.strip(), mode="eval")
        except SyntaxError as error:
            raise ValueError(f"bad expression {source!r}: {error.msg}") from error
        self.names: set[str] = set()
        self._check(tree.body)
        self._tree = tree.body

    def __call__(self, values: Mapping[str, Any]) -> Any:
        return self._evaluate(self._tree, values)

    def __repr__(self) -> str:
        return f"Expression({self.source!r})"

    def _check(self, node: ast.AST) -> None:
        match node:
            case ast.Constant(value=constant) if constant is None or isinstance(
                constant, bool | int | float | str
            ):
                pass
            case ast.Name(id=name):
                if name not in CONSTANTS:
                    self.names.add(name)
            case ast.BinOp(op=op) if type(op) in ARITHMETIC:
                self._check(node.left)
                self._check(node.right)
            case ast.UnaryOp(op=ast.Not() | ast.USub() | ast.UAdd()):
                self._check(node.operand)
            case ast.BoolOp(values=operands):
                for operand in operands:
                    self._check(operand)
            case ast.Compare(ops=ops) if all(type(op) in COMPARISONS for op in ops):
                self._check(node.left)
                for comparator in node.comparators:
                    self._check(comparator)
            case ast.IfExp():
                for part in (node.test, node.body, node.orelse):
                    self._check(part)
            case ast.List(elts=elements) | ast.Tuple(elts=elements):
                for element in elements:
                    self._check(element)
            case ast.Call(func=ast.Name(id=name), keywords=[]) if name in FUNCTIONS:
                for arg in node.args:
                    self._check(arg)
            case _:
                raise ValueError(
                    f"bad expression {self.source!r}: {ast.unparse(node)!r}"
                    " is not allowed"
                )

    def _evaluate(self, node: ast.AST, values: Mapping[str, Any]) -> Any:
        match node:
            case ast.Constant(value=constant):
                return constant
            case ast.Name(id=name) if name in CONSTANTS:
                return CONSTANTS[name]
            case ast.Name(id=name):
                if name not in values:
                    raise ValueError(f"{self.source!r}: unknown name {name!r}")
                return values[name]
            case ast.BinOp(op=op):
                left = self._evaluate(node.left, values)
                right = self._evaluate(node.right, values)
                return _known(ARITHMETIC[type(op)])(left, right)
            case ast.UnaryOp(op=ast.Not()):
                return not self._evaluate(node.operand, values)
            case ast.UnaryOp(op=op):
                operand = self._evaluate(node.operand, values)
                if operand is None:
                    return None
                return -operand if isinstance(op, ast.USub) else +operand
            case ast.BoolOp(op=ast.And()):
                result = True
                for operand in node.values:
                    result = self._evaluate(operand, values)
                    if not result:
                        return result
                return result
            case ast.BoolOp():
                result = False
                for operand in node.values:
                    result = self._evaluate(operand, values)
                    if result:
                        return result
                return result
            case ast.Compare():
                return self._compare(node, values)
            case ast.IfExp():
                if self._evaluate(node.test, values):
                    return self._evaluate(node.body, values)
                return self._evaluate(node.orelse, values)
            case ast.List(elts=elements) | ast.Tuple(elts=elements):
                return [self._evaluate(element, values) for element in elements]
            case ast.Call(func=ast.Name(id=name)):
                args = [self._evaluate(arg, values) for arg in node.args]
                return FUNCTIONS[name](*args)
        raise AssertionError(f"unchecked node {ast.dump(node)}")

    def _compare(self, node: ast.Compare, values: Mapping[str, Any]) -> bool:
        left = self._evaluate(node.left, values)
        for op, comparator in zip(node.ops, node.comparators, strict=True):
            right = self._evaluate(comparator, values)
            # Only equality compares an unknown value: none == none.
            unknown = left is None or right is None
            if unknown and not isinstance(op, ast.Eq | ast.NotEq):
                return False
            if not COMPARISONS[type(op)](left, right):
                return False
            left = right
        return True

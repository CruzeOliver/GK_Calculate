"""Pure calculation and validation logic for the data-analysis calculator."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Mapping


class Field(str, Enum):
    BASE = "base"
    CURRENT = "current"
    AMOUNT = "amount"
    RATE = "rate"


@dataclass(frozen=True)
class CalculationResult:
    base: float
    current: float
    amount: float
    rate: float
    calculated_fields: frozenset[Field]


class CalculationError(ValueError):
    """Raised when user input cannot produce a meaningful result."""


def _parse_values(values: Mapping[Field, str]) -> dict[Field, float]:
    parsed: dict[Field, float] = {}
    try:
        for field, text in values.items():
            stripped = text.strip()
            if stripped:
                parsed[field] = float(stripped)
    except (TypeError, ValueError) as exc:
        raise CalculationError("请输入有效数字") from exc

    if any(not math.isfinite(value) for value in parsed.values()):
        raise CalculationError("请输入有限数值")
    return parsed


def _validate_known_values(parsed: Mapping[Field, float]) -> None:
    if Field.BASE in parsed and parsed[Field.BASE] < 0:
        raise CalculationError("基期不能小于 0")
    if Field.CURRENT in parsed and parsed[Field.CURRENT] < 0:
        raise CalculationError("现期不能小于 0")


def _validate_result(result: CalculationResult) -> None:
    if not all(
        math.isfinite(value)
        for value in (result.base, result.current, result.amount, result.rate)
    ):
        raise CalculationError("计算结果不是有限数值")
    if result.base < 0:
        raise CalculationError("基期不能小于 0")
    if result.current < 0:
        raise CalculationError("现期不能小于 0")


def calculate(values: Mapping[Field, str]) -> CalculationResult:
    """Calculate all four values from any valid pair of known values."""

    parsed = _parse_values(values)
    if len(parsed) != 2:
        if len(parsed) > 2:
            raise CalculationError("请只输入两个已知量")
        raise CalculationError("请输入两个已知量")

    _validate_known_values(parsed)
    known = frozenset(parsed)
    if known == {Field.BASE, Field.CURRENT}:
        base, current = parsed[Field.BASE], parsed[Field.CURRENT]
        amount = current - base
        rate = _rate_from_base_and_amount(base, amount)
    elif known == {Field.BASE, Field.RATE}:
        base, rate = parsed[Field.BASE], parsed[Field.RATE]
        amount = base * rate / 100.0
        current = base + amount
    elif known == {Field.BASE, Field.AMOUNT}:
        base, amount = parsed[Field.BASE], parsed[Field.AMOUNT]
        current = base + amount
        rate = _rate_from_base_and_amount(base, amount)
    elif known == {Field.CURRENT, Field.RATE}:
        current, rate = parsed[Field.CURRENT], parsed[Field.RATE]
        denominator = 1.0 + rate / 100.0
        if math.isclose(denominator, 0.0, abs_tol=1e-12):
            raise CalculationError("增长率为 -100% 时无法计算基期")
        base = current / denominator
        amount = current - base
    elif known == {Field.CURRENT, Field.AMOUNT}:
        current, amount = parsed[Field.CURRENT], parsed[Field.AMOUNT]
        base = current - amount
        rate = _rate_from_base_and_amount(base, amount)
    else:
        rate, amount = parsed[Field.RATE], parsed[Field.AMOUNT]
        if math.isclose(rate, 0.0, abs_tol=1e-12):
            if math.isclose(amount, 0.0, abs_tol=1e-12):
                raise CalculationError("条件不足，无法确定基期和现期")
            raise CalculationError("增长率为 0 时增长量必须为 0")
        base = amount * 100.0 / rate
        current = base + amount

    calculated_fields = frozenset(set(Field) - set(known))
    result = CalculationResult(base, current, amount, rate, calculated_fields)
    _validate_result(result)
    return result


def _rate_from_base_and_amount(base: float, amount: float) -> float:
    if math.isclose(base, 0.0, abs_tol=1e-12):
        raise CalculationError("基期为 0，无法计算增长率")
    return amount / base * 100.0

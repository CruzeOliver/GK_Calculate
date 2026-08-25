"""Pure calculation and validation logic for the data-analysis calculator."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Mapping


class Field(str, Enum):
    BASE = "base"
    CURRENT = "current"
    RATE = "rate"


@dataclass(frozen=True)
class CalculationResult:
    base: float
    current: float
    rate: float
    calculated_field: Field


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
    if not all(math.isfinite(value) for value in (result.base, result.current, result.rate)):
        raise CalculationError("计算结果不是有限数值")
    if result.base < 0:
        raise CalculationError("基期不能小于 0")
    if result.current < 0:
        raise CalculationError("现期不能小于 0")


def calculate(values: Mapping[Field, str]) -> CalculationResult:
    """Calculate the single missing value among base, current and rate."""

    parsed = _parse_values(values)
    if len(parsed) != 2:
        if len(parsed) > 2:
            raise CalculationError("请只输入两个已知量")
        raise CalculationError("请输入两个已知量")

    _validate_known_values(parsed)
    missing = next(field for field in Field if field not in parsed)

    if missing is Field.CURRENT:
        base = parsed[Field.BASE]
        rate = parsed[Field.RATE]
        current = base * (1.0 + rate / 100.0)
    elif missing is Field.BASE:
        current = parsed[Field.CURRENT]
        rate = parsed[Field.RATE]
        denominator = 1.0 + rate / 100.0
        if math.isclose(denominator, 0.0, abs_tol=1e-12):
            raise CalculationError("增长率为 -100% 时无法计算基期")
        base = current / denominator
    else:
        base = parsed[Field.BASE]
        current = parsed[Field.CURRENT]
        if math.isclose(base, 0.0, abs_tol=1e-12):
            raise CalculationError("基期为 0，无法计算增长率")
        rate = (current / base - 1.0) * 100.0

    result = CalculationResult(base, current, rate, missing)
    _validate_result(result)
    return result

"""Exam-friendly approximation steps for positive growth calculations."""

from __future__ import annotations

from dataclasses import dataclass
import math


FRIENDLY_COEFFICIENTS = (1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0)


@dataclass(frozen=True)
class AllocationStep:
    base: float
    amount: float
    subtotal: float
    remainder: float


@dataclass(frozen=True)
class AllocationPlan:
    current: float
    rate: float
    steps: tuple[AllocationStep, ...]
    estimated_base: float
    estimated_amount: float
    remainder: float


def _friendly_bases(limit: float) -> list[float]:
    exponent = math.floor(math.log10(limit))
    candidates = [
        coefficient * (10.0**power)
        for power in range(exponent - 2, exponent + 1)
        for coefficient in FRIENDLY_COEFFICIENTS
        if 0 < coefficient * (10.0**power) <= limit
    ]
    return sorted(set(candidates), reverse=True)


def _select_base(remainder: float, factor: float, scaled_rate: float) -> float:
    limit = remainder / factor
    if limit <= 0:
        raise ValueError("数值超出假设分配精度范围")
    for candidate in _friendly_bases(limit):
        if candidate + candidate * scaled_rate <= remainder:
            return candidate

    candidate = limit
    while candidate > 0 and candidate + candidate * scaled_rate > remainder:
        candidate = math.nextafter(candidate, 0.0)
    return candidate


def allocate_assumptions(
    current: float,
    rate: float,
    *,
    max_steps: int = 3,
    tolerance_ratio: float = 0.01,
) -> AllocationPlan:
    """Approximate base and growth using up to three mental-math-friendly steps."""

    if not math.isfinite(current) or current <= 0:
        raise ValueError("现期必须为正数")
    if not math.isfinite(rate) or rate <= 0:
        raise ValueError("假设分配法仅适用于正增长")
    if max_steps <= 0:
        raise ValueError("分配次数必须为正数")

    scaled_rate = rate / 100.0
    factor = 1.0 + scaled_rate
    threshold = current * tolerance_ratio
    remainder = current
    steps: list[AllocationStep] = []

    for _ in range(max_steps):
        base = _select_base(remainder, factor, scaled_rate)
        amount = base * scaled_rate
        subtotal = base + amount
        remainder = max(0.0, remainder - subtotal)
        steps.append(AllocationStep(base, amount, subtotal, remainder))
        if remainder <= threshold:
            break

    estimated_base = sum(step.base for step in steps)
    estimated_amount = sum(step.amount for step in steps)
    return AllocationPlan(
        current=current,
        rate=rate,
        steps=tuple(steps),
        estimated_base=estimated_base,
        estimated_amount=estimated_amount,
        remainder=remainder,
    )


def _number(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def format_allocation(plan: AllocationPlan) -> str:
    lines = [f"现期={_number(plan.current)}，增长率={_number(plan.rate)}%", ""]
    for index, step in enumerate(plan.steps, start=1):
        lines.append(
            f"第{index}次：{_number(step.base)} + {_number(step.amount)} "
            f"= {_number(step.subtotal)}，余 {_number(step.remainder)}"
        )
    lines.extend(
        [
            "",
            f"近似基期：{_number(plan.estimated_base)}",
            f"近似增长量：{_number(plan.estimated_amount)}",
            f"近似现期：{_number(plan.estimated_base + plan.estimated_amount)}"
            f"（余 {_number(plan.remainder)}）",
        ]
    )
    return "\n".join(lines)

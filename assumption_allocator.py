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


def format_allocation_html(plan: AllocationPlan) -> str:
    step_blocks: list[str] = []
    pending = plan.current
    for index, step in enumerate(plan.steps, start=1):
        step_blocks.append(
            f"""
            <div class="allocation-tree" style="margin:6px 0 10px 0;">
              <div align="center"><b>第{index}次：待分配 {_number(pending)}</b></div>
              <div align="center" style="color:#6c757d;">│</div>
              <table width="92%" align="center" cellspacing="0" cellpadding="3">
                <tr>
                  <td width="50%" align="center"
                      style="border-top:1px solid #8aa4bd; border-right:1px solid #8aa4bd;">
                    <span style="color:#5b6570;">假设基期</span>
                    <div style="font-weight:bold; color:#075ea8;">{_number(step.base)}</div>
                  </td>
                  <td width="50%" align="center" style="border-top:1px solid #8aa4bd;">
                    <span style="color:#5b6570;">增长量</span>
                    <div style="font-weight:bold; color:#c62828;">{_number(step.amount)}</div>
                  </td>
                </tr>
              </table>
              <div align="center" style="color:#444;">
                小计 {_number(step.subtotal)}，余 {_number(step.remainder)}
              </div>
            </div>
            """
        )
        pending = step.remainder

    return f"""
    <div style="font-family:'Noto Sans SC'; font-size:9pt; color:#333;">
      <div align="center" style="font-size:10pt; margin-bottom:6px;">
        <b>现期={_number(plan.current)}，增长率={_number(plan.rate)}%</b>
      </div>
      {''.join(step_blocks)}
      <div style="border-top:1px solid #ced4da; margin-top:8px; padding-top:6px;">
        <b>估算汇总</b><br>
        近似基期：{_number(plan.estimated_base)}<br>
        近似增长量：{_number(plan.estimated_amount)}<br>
        近似现期：{_number(plan.estimated_base + plan.estimated_amount)}
        （余 {_number(plan.remainder)}）
      </div>
    </div>
    """

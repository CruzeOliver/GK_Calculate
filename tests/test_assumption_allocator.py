import math

import pytest

from assumption_allocator import allocate_assumptions, format_allocation


def test_three_step_allocation_uses_exam_friendly_numbers():
    plan = allocate_assumptions(180.0, 24.0)

    assert [step.base for step in plan.steps] == [100.0, 40.0, 5.0]
    assert [step.amount for step in plan.steps] == pytest.approx([24.0, 9.6, 1.2])
    assert plan.estimated_base == pytest.approx(145.0)
    assert plan.estimated_amount == pytest.approx(34.8)
    assert plan.remainder == pytest.approx(0.2)


def test_allocation_stops_when_remainder_is_within_one_percent():
    plan = allocate_assumptions(1200.0, 18.0)

    assert [step.base for step in plan.steps] == [1000.0, 15.0]
    assert plan.remainder == pytest.approx(2.3)
    assert plan.remainder <= plan.current * 0.01


def test_allocation_respects_step_limit():
    plan = allocate_assumptions(180.0, 24.0, max_steps=2)

    assert len(plan.steps) == 2
    assert plan.remainder == pytest.approx(6.4)


def test_formatted_allocation_contains_each_step_and_summary():
    text = format_allocation(allocate_assumptions(180.0, 24.0))

    assert "现期=180，增长率=24%" in text
    assert "第1次：100 + 24 = 124，余 56" in text
    assert "第3次：5 + 1.2 = 6.2，余 0.2" in text
    assert "近似基期：145" in text
    assert "近似增长量：34.8" in text


@pytest.mark.parametrize("current", [1e-15, 5e-324])
def test_tiny_allocations_make_positive_progress_without_overshoot(current):
    plan = allocate_assumptions(current, 24.0)
    previous_remainder = current

    for step in plan.steps:
        assert step.base > 0
        assert step.subtotal > 0
        assert step.subtotal <= previous_remainder
        assert step.remainder < previous_remainder
        previous_remainder = step.remainder


def test_extreme_finite_values_do_not_overflow():
    plan = allocate_assumptions(1e308, 1e308)

    assert math.isfinite(plan.estimated_base)
    assert math.isfinite(plan.estimated_amount)
    assert math.isfinite(plan.remainder)


def test_candidate_just_above_remainder_is_rejected():
    current = math.nextafter(124.0, -math.inf)

    plan = allocate_assumptions(current, 24.0)

    assert plan.steps[0].base < 100.0
    assert plan.steps[0].subtotal <= current


def test_unrepresentable_base_reports_domain_error():
    with pytest.raises(ValueError, match="超出假设分配精度范围"):
        allocate_assumptions(5e-324, 1e100)

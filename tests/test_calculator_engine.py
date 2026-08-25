import pytest

from calculator_engine import CalculationError, Field, calculate


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ({Field.BASE: "100", Field.CURRENT: "112"}, (100.0, 112.0, 12.0, 12.0)),
        ({Field.BASE: "100", Field.RATE: "12"}, (100.0, 112.0, 12.0, 12.0)),
        ({Field.BASE: "100", Field.AMOUNT: "12"}, (100.0, 112.0, 12.0, 12.0)),
        ({Field.CURRENT: "112", Field.RATE: "12"}, (100.0, 112.0, 12.0, 12.0)),
        ({Field.CURRENT: "112", Field.AMOUNT: "12"}, (100.0, 112.0, 12.0, 12.0)),
        ({Field.RATE: "12", Field.AMOUNT: "12"}, (100.0, 112.0, 12.0, 12.0)),
    ],
)
def test_calculate_each_missing_field(values, expected):
    result = calculate(values)
    assert (result.base, result.current, result.amount, result.rate) == pytest.approx(expected)
    assert result.calculated_fields == frozenset(set(Field) - set(values))


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ({Field.BASE: "0", Field.CURRENT: "1"}, "基期为 0"),
        ({Field.CURRENT: "0", Field.RATE: "-100"}, "-100%"),
        ({Field.BASE: "-1", Field.RATE: "10"}, "基期不能小于 0"),
        ({Field.CURRENT: "-1", Field.RATE: "10"}, "现期不能小于 0"),
        ({Field.BASE: "abc", Field.RATE: "10"}, "请输入有效数字"),
        ({Field.BASE: "nan", Field.RATE: "10"}, "请输入有限数值"),
        ({Field.BASE: "100"}, "请输入两个已知量"),
        ({Field.AMOUNT: "0", Field.RATE: "0"}, "条件不足"),
        ({Field.AMOUNT: "10", Field.RATE: "0"}, "增长率为 0"),
    ],
)
def test_invalid_inputs_raise_readable_errors(values, message):
    with pytest.raises(CalculationError, match=message):
        calculate(values)

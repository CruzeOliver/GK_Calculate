from pathlib import Path

from PySide6.QtCore import QFile, QObject
from PySide6.QtUiTools import QUiLoader

from calculator_engine import CalculationResult, Field


def test_ui_file_loads_and_exposes_required_widgets(qapp):
    ui_file = QFile(str(Path("ui/calculator.ui")))
    assert ui_file.open(QFile.ReadOnly)
    window = QUiLoader().load(ui_file)
    ui_file.close()

    assert window is not None
    for name in (
        "chartContainer",
        "baseInput",
        "currentInput",
        "rateInput",
        "calculateButton",
        "clearButton",
        "logMessage",
    ):
        assert window.findChild(QObject, name) is not None


def test_chart_updates_annotation_and_can_clear(qtbot):
    from chart_widget import PeriodChart

    chart = PeriodChart()
    qtbot.addWidget(chart)
    result = CalculationResult(100.0, 112.0, 12.0, Field.CURRENT)

    chart.update_result(result)

    assert chart.annotation.toPlainText() == "↑ 增长 12.00%"
    assert len(chart.bar_item.opts["height"]) == 2

    chart.clear_chart()

    assert chart.annotation.toPlainText() == ""
    assert chart.bar_item is None


def test_chart_describes_negative_and_zero_growth(qtbot):
    from chart_widget import PeriodChart

    chart = PeriodChart()
    qtbot.addWidget(chart)

    chart.update_result(CalculationResult(100.0, 92.0, -8.0, Field.RATE))
    assert chart.annotation.toPlainText() == "↓ 下降 8.00%"

    chart.update_result(CalculationResult(100.0, 100.0, 0.0, Field.RATE))
    assert chart.annotation.toPlainText() == "— 持平 0.00%"

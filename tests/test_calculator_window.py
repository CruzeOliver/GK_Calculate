from pathlib import Path

from PySide6.QtCore import QFile, QObject, Qt
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


def test_two_inputs_lock_missing_field_and_edit_invalidates_result(qtbot):
    from calculator_window import CalculatorWindow

    window = CalculatorWindow()
    qtbot.addWidget(window)
    window.base_input.setText("100")
    window.rate_input.setText("12")
    assert window.current_input.isReadOnly()

    qtbot.mouseClick(window.calculate_button, Qt.LeftButton)
    assert window.current_input.text() == "112.00"

    window.base_input.setText("200")
    assert window.current_input.text() == ""
    assert window.current_input.isReadOnly()

    window.rate_input.clear()
    assert not window.current_input.isReadOnly()


def test_calculate_updates_result_chart_and_log(qtbot):
    from calculator_window import CalculatorWindow

    window = CalculatorWindow()
    qtbot.addWidget(window)
    window.base_input.setText("100")
    window.rate_input.setText("12")

    qtbot.mouseClick(window.calculate_button, Qt.LeftButton)

    assert window.current_input.text() == "112.00"
    assert "基期 100.00，现期 112.00，增长率 12.00%" in window.log_message.toPlainText()
    assert window.chart.bar_item is not None


def test_clear_resets_inputs_log_and_chart(qtbot):
    from calculator_window import CalculatorWindow

    window = CalculatorWindow()
    qtbot.addWidget(window)
    window.base_input.setText("100")
    window.rate_input.setText("12")
    qtbot.mouseClick(window.calculate_button, Qt.LeftButton)

    qtbot.mouseClick(window.clear_button, Qt.LeftButton)

    assert all(not widget.text() for widget in window.inputs.values())
    assert all(not widget.isReadOnly() for widget in window.inputs.values())
    assert window.log_message.toPlainText() == ""
    assert window.chart.bar_item is None


def test_calculation_error_is_appended_without_updating_chart(qtbot):
    from calculator_window import CalculatorWindow

    window = CalculatorWindow()
    qtbot.addWidget(window)
    window.base_input.setText("0")
    window.current_input.setText("1")

    qtbot.mouseClick(window.calculate_button, Qt.LeftButton)

    assert "基期为 0，无法计算增长率" in window.log_message.toPlainText()
    assert window.chart.bar_item is None

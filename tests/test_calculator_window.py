from pathlib import Path

from PySide6.QtCore import QFile, QObject, Qt
from PySide6.QtUiTools import QUiLoader

from calculator_engine import CalculationResult, Field


def test_entry_module_exposes_main():
    import Calculate

    assert callable(Calculate.main)


def test_entry_configures_windows_font_directory(monkeypatch):
    import Calculate

    monkeypatch.delenv("QT_QPA_FONTDIR", raising=False)
    monkeypatch.setenv("WINDIR", r"C:\Windows")

    Calculate._configure_qt_font_directory()

    assert Path(Calculate.os.environ["QT_QPA_FONTDIR"]) == Path(r"C:\Windows\Fonts")


def test_entry_applies_consistent_application_font(qapp):
    import Calculate

    Calculate._apply_application_font(qapp)

    assert qapp.font().family() == "Noto Sans SC"


def test_entry_loads_stylesheet_from_application_directory(qapp, monkeypatch, tmp_path):
    import Calculate

    stylesheet = "QWidget { background-color: #123456; }"
    (tmp_path / "style.qss").write_text(stylesheet, encoding="utf-8")
    monkeypatch.setattr(Calculate, "__file__", str(tmp_path / "Calculate.py"))
    qapp.setStyleSheet("")

    loaded = Calculate._load_stylesheet(qapp)

    assert loaded is True
    assert qapp.styleSheet() == stylesheet


def test_entry_keeps_current_style_when_stylesheet_is_missing(qapp, monkeypatch, tmp_path):
    import Calculate

    existing_style = "QWidget { color: #222222; }"
    monkeypatch.setattr(Calculate, "__file__", str(tmp_path / "Calculate.py"))
    qapp.setStyleSheet(existing_style)

    loaded = Calculate._load_stylesheet(qapp)

    assert loaded is False
    assert qapp.styleSheet() == existing_style


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
        "amountInput",
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
    result = CalculationResult(
        100.0, 112.0, 12.0, 12.0, frozenset({Field.CURRENT, Field.AMOUNT})
    )

    chart.update_result(result)

    assert chart.annotation.toPlainText() == "↑ 增长 12.00%"
    assert len(chart.bar_item.opts["height"]) == 2
    assert chart.amount_label.toPlainText() == "增长量 +12.00"
    assert chart.growth_item.opts["y0"][0] == 100.0
    assert chart.growth_item.opts["height"][0] == 12.0

    chart.clear_chart()

    assert chart.annotation.toPlainText() == ""
    assert chart.bar_item is None
    assert chart.growth_item is None


def test_chart_describes_negative_and_zero_growth(qtbot):
    from chart_widget import PeriodChart

    chart = PeriodChart()
    qtbot.addWidget(chart)

    chart.update_result(
        CalculationResult(100.0, 92.0, -8.0, -8.0, frozenset({Field.AMOUNT, Field.RATE}))
    )
    assert chart.annotation.toPlainText() == "↓ 下降 8.00%"
    assert chart.amount_label.toPlainText() == "增长量 -8.00"
    assert chart.growth_item.opts["y0"][0] == 92.0
    assert chart.growth_item.opts["height"][0] == 8.0

    chart.update_result(
        CalculationResult(100.0, 100.0, 0.0, 0.0, frozenset({Field.AMOUNT, Field.RATE}))
    )
    assert chart.annotation.toPlainText() == "— 持平 0.00%"


def test_two_inputs_lock_missing_field_and_edit_invalidates_result(qtbot):
    from calculator_window import CalculatorWindow

    window = CalculatorWindow()
    qtbot.addWidget(window)
    window.base_input.setText("100")
    window.rate_input.setText("12")
    assert window.current_input.isReadOnly()
    assert window.amount_input.isReadOnly()

    qtbot.mouseClick(window.calculate_button, Qt.LeftButton)
    assert window.current_input.text() == "112.00"
    assert window.amount_input.text() == "12.00"

    window.base_input.setText("200")
    assert window.current_input.text() == ""
    assert window.amount_input.text() == ""
    assert window.current_input.isReadOnly()
    assert window.amount_input.isReadOnly()

    window.rate_input.clear()
    assert not window.current_input.isReadOnly()
    assert not window.amount_input.isReadOnly()


def test_calculate_updates_result_chart_and_log(qtbot):
    from calculator_window import CalculatorWindow

    window = CalculatorWindow()
    qtbot.addWidget(window)
    window.base_input.setText("100")
    window.rate_input.setText("12")

    qtbot.mouseClick(window.calculate_button, Qt.LeftButton)

    assert window.current_input.text() == "112.00"
    assert window.amount_input.text() == "12.00"
    assert (
        "基期 100.00，现期 112.00，增长量 12.00，增长率 12.00%"
        in window.log_message.toPlainText()
    )
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

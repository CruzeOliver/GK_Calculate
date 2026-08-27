"""Qt window controller for the data-analysis calculator."""

from __future__ import annotations

from html import escape
from pathlib import Path

from PySide6.QtCore import QFile, QIODevice
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QFrame,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QTextEdit,
)

from calculator_engine import CalculationError, CalculationResult, Field, calculate
from chart_widget import PeriodChart
from assumption_allocator import allocate_assumptions, format_allocation


class CalculatorWindow(QMainWindow):
    """Load the Designer UI and coordinate calculation interactions."""

    def __init__(self) -> None:
        super().__init__()
        loaded_window = self._load_ui()
        central_widget = loaded_window.takeCentralWidget()
        if central_widget is None:
            raise RuntimeError("界面文件缺少 centralwidget")
        self.setCentralWidget(central_widget)
        self.setWindowTitle(loaded_window.windowTitle())
        self.resize(loaded_window.size())
        self.setMinimumSize(loaded_window.minimumSize())

        self.base_input = self._required_widget(QLineEdit, "baseInput")
        self.current_input = self._required_widget(QLineEdit, "currentInput")
        self.amount_input = self._required_widget(QLineEdit, "amountInput")
        self.rate_input = self._required_widget(QLineEdit, "rateInput")
        self.allocation_process = self._required_widget(QPlainTextEdit, "allocationProcess")
        self.calculate_button = self._required_widget(QPushButton, "calculateButton")
        self.clear_button = self._required_widget(QPushButton, "clearButton")
        self.log_message = self._required_widget(QTextEdit, "logMessage")
        chart_container = self._required_widget(QFrame, "chartContainer")

        self.chart = PeriodChart(chart_container)
        chart_container.layout().addWidget(self.chart)

        self.inputs: dict[Field, QLineEdit] = {
            Field.BASE: self.base_input,
            Field.CURRENT: self.current_input,
            Field.AMOUNT: self.amount_input,
            Field.RATE: self.rate_input,
        }
        self.calculated_fields: frozenset[Field] = frozenset()
        self._updating = False

        for field, widget in self.inputs.items():
            widget.textChanged.connect(lambda _text, changed=field: self._input_changed(changed))
        self.calculate_button.clicked.connect(self.calculate_requested)
        self.clear_button.clicked.connect(self.clear_all)
        self._sync_input_state()

    @staticmethod
    def _load_ui() -> QMainWindow:
        ui_path = Path(__file__).resolve().parent / "ui" / "calculator.ui"
        ui_file = QFile(str(ui_path))
        if not ui_file.open(QIODevice.ReadOnly):
            raise RuntimeError(f"无法打开界面文件：{ui_path}")
        try:
            loaded = QUiLoader().load(ui_file)
        finally:
            ui_file.close()
        if not isinstance(loaded, QMainWindow):
            raise RuntimeError(f"无法加载界面文件：{ui_path}")
        return loaded

    def _required_widget(self, widget_type, name: str):
        widget = self.findChild(widget_type, name)
        if widget is None:
            raise RuntimeError(f"界面文件缺少控件：{name}")
        return widget

    def _input_changed(self, changed_field: Field) -> None:
        if self._updating:
            return
        if self.calculated_fields and changed_field not in self.calculated_fields:
            with self._programmatic_update():
                for field in self.calculated_fields:
                    self.inputs[field].clear()
            self.calculated_fields = frozenset()
            self.allocation_process.clear()
        self._sync_input_state()

    def _sync_input_state(self) -> None:
        nonempty = [field for field, widget in self.inputs.items() if widget.text().strip()]
        pending_fields: frozenset[Field] = frozenset()
        if not self.calculated_fields and len(nonempty) == 2:
            pending_fields = frozenset(set(Field) - set(nonempty))

        for field, widget in self.inputs.items():
            read_only = field in pending_fields or field in self.calculated_fields
            widget.setReadOnly(read_only)
            widget.setProperty("pendingResult", field in pending_fields)
            widget.setStyleSheet("background-color: #eeeeee;" if read_only else "")

    def calculate_requested(self) -> None:
        values = {
            field: widget.text()
            for field, widget in self.inputs.items()
            if widget.text().strip()
        }
        for field in self.calculated_fields:
            values.pop(field, None)

        try:
            result = calculate(values)
        except CalculationError as exc:
            self._append_error(str(exc))
            return

        with self._programmatic_update():
            self.base_input.setText(f"{result.base:.2f}")
            self.current_input.setText(f"{result.current:.2f}")
            self.amount_input.setText(f"{result.amount:.2f}")
            self.rate_input.setText(f"{result.rate:.2f}")
        self.calculated_fields = result.calculated_fields
        self._sync_input_state()
        self.chart.update_result(result)
        self._update_allocation(result)
        self._append_success(result)

    def clear_all(self) -> None:
        with self._programmatic_update():
            for widget in self.inputs.values():
                widget.clear()
        self.calculated_fields = frozenset()
        self.log_message.clear()
        self.allocation_process.clear()
        self.chart.clear_chart()
        self._sync_input_state()

    def _append_success(self, result: CalculationResult) -> None:
        self.log_message.append(
            "计算完成："
            f"基期 {result.base:.2f}，"
            f"现期 {result.current:.2f}，"
            f"增长量 {result.amount:.2f}，"
            f"增长率 {result.rate:.2f}%"
        )

    def _append_error(self, message: str) -> None:
        self.log_message.append(f'<span style="color:#c62828;">错误：{escape(message)}</span>')

    def _update_allocation(self, result: CalculationResult) -> None:
        if result.rate <= 0:
            self.allocation_process.setPlainText("假设分配法暂仅适用于正增长")
            return
        try:
            plan = allocate_assumptions(result.current, result.rate)
        except ValueError as exc:
            self.allocation_process.setPlainText(str(exc))
            return
        self.allocation_process.setPlainText(format_allocation(plan))

    class _UpdateGuard:
        def __init__(self, window: "CalculatorWindow") -> None:
            self.window = window

        def __enter__(self) -> None:
            self.window._updating = True

        def __exit__(self, exc_type, exc_value, traceback) -> None:
            self.window._updating = False

    def _programmatic_update(self) -> "CalculatorWindow._UpdateGuard":
        return self._UpdateGuard(self)

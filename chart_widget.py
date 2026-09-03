"""pyqtgraph widget for comparing base-period and current-period values."""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QVBoxLayout, QWidget
import pyqtgraph as pg

from calculator_engine import CalculationResult


def _rate_text(rate: float) -> str:
    if rate > 0:
        return f"↑ 增长 {rate:.2f}%"
    if rate < 0:
        return f"↓ 下降 {abs(rate):.2f}%"
    return "— 持平 0.00%"


class PeriodChart(QWidget):
    """A two-bar chart with a separate growth-rate annotation."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.plot_widget = pg.PlotWidget()
        layout.addWidget(self.plot_widget)
        self.plot_item = self.plot_widget.getPlotItem()
        self.plot_widget.setBackground("w")
        self.plot_item.showGrid(x=False, y=True, alpha=0.25)
        self.plot_item.setLabel("left", "数值")
        self.plot_item.getAxis("bottom").setTicks([[(0, "基期"), (1, "现期")]])
        self.plot_item.setMouseEnabled(x=False, y=False)
        self.plot_item.hideButtons()

        self.annotation = pg.TextItem("", anchor=(0.5, 0.5), color="#222222")
        self.plot_item.addItem(self.annotation)
        self.amount_label = pg.TextItem("", anchor=(0.5, 0.5), color="#FFFFFF")
        amount_font = QFont()
        amount_font.setBold(True)
        self.amount_label.setFont(amount_font)
        self.plot_item.addItem(self.amount_label)
        self.bar_item: pg.BarGraphItem | None = None
        self.growth_item: pg.BarGraphItem | None = None
        self.value_labels: list[pg.TextItem] = []
        self.plot_item.setXRange(-0.75, 1.75, padding=0)
        self.plot_item.setYRange(0, 1, padding=0)

    def update_result(self, result: CalculationResult) -> None:
        self.clear_chart()
        heights = [result.base, result.current]
        self.bar_item = pg.BarGraphItem(
            x=[0, 1],
            height=heights,
            width=0.55,
            brushes=[pg.mkBrush("#4C78A8"), pg.mkBrush("#F58518")],
        )
        self.plot_item.addItem(self.bar_item)

        growth_bottom = result.base if result.amount >= 0 else result.current
        self.growth_item = pg.BarGraphItem(
            x=[0],
            y0=[growth_bottom],
            height=[abs(result.amount)],
            width=0.55,
            brush=pg.mkBrush("#D32F2F"),
        )
        self.plot_item.addItem(self.growth_item)

        maximum = max(heights)
        scale = maximum if maximum > 0 else 1.0
        for x_position, value in enumerate(heights):
            label = pg.TextItem(f"{value:.2f}", anchor=(0.5, 0.5), color="#FFFFFF")
            label_font = QFont()
            label_font.setBold(True)
            label.setFont(label_font)
            label.setPos(x_position, value / 2.0)
            self.plot_item.addItem(label)
            self.value_labels.append(label)

        self.annotation.setText(_rate_text(result.rate))
        self.annotation.setPos(0.5, scale * 1.18)
        amount_text = "增长量 0.00" if result.amount == 0 else f"增长量 {result.amount:+.2f}"
        self.amount_label.setText(amount_text)
        self.amount_label.setPos(0.0, growth_bottom + abs(result.amount) / 2.0)
        self.plot_item.setYRange(0, scale * 1.32, padding=0)

    def clear_chart(self) -> None:
        if self.bar_item is not None:
            self.plot_item.removeItem(self.bar_item)
            self.bar_item = None
        if self.growth_item is not None:
            self.plot_item.removeItem(self.growth_item)
            self.growth_item = None
        for label in self.value_labels:
            self.plot_item.removeItem(label)
        self.value_labels.clear()
        self.annotation.setText("")
        self.amount_label.setText("")
        self.plot_item.setYRange(0, 1, padding=0)

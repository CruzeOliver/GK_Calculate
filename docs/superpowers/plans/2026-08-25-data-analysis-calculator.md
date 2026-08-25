# 公考资料分析计算器 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个通过 PySide6 `.ui` 文件加载界面、可由任意两个已知量计算基期/现期/增长率，并用 pyqtgraph 和日志展示结果的桌面程序。

**Architecture:** 将无界面的公式与校验放在 `calculator_engine.py`，将 pyqtgraph 封装为独立图表组件，将 `.ui` 加载和交互状态集中在窗口控制器中。`Calculate.py` 只负责创建应用和启动窗口，以便计算逻辑可以脱离 Qt 单独测试。

**Tech Stack:** Python 3.10+、PySide6、pyqtgraph、pytest、pytest-qt

**Spec:** `docs/superpowers/specs/2026-08-25-data-analysis-calculator-design.md`

## Global Constraints

- 所有显示结果统一保留两位小数，内部计算不得提前截断精度。
- 基期和现期必须大于或等于 `0`；增长率允许负数。
- 用户输入增长率 `12` 表示 `12%`。
- 使用 `QUiLoader` 在运行时加载 `ui/calculator.ui`。
- 图表采用基期/现期双柱，增长率使用文字和方向符号标注。
- 错误写入日志，不显示模态错误对话框。
- 当前目录已初始化 Git；用户已明确授权直接在 `main` 分支实施，并按任务保留提交。

---

## File Map

- `Calculate.py`：应用入口，仅创建 `QApplication`、`CalculatorWindow` 并进入事件循环。
- `calculator_engine.py`：字段枚举、计算结果模型、解析、校验和三种反推公式。
- `chart_widget.py`：创建、更新、清空 pyqtgraph 图表。
- `calculator_window.py`：加载 `.ui`、校验控件、管理输入状态、执行计算、更新日志和图表。
- `ui/calculator.ui`：主窗口布局及标准 Qt 控件。
- `tests/test_calculator_engine.py`：计算模块单元测试。
- `tests/test_calculator_window.py`：输入锁定、计算、清除和日志交互测试。
- `requirements.txt`：运行和测试依赖。

### Task 1: 纯计算引擎

**Files:**
- Create: `calculator_engine.py`
- Create: `tests/test_calculator_engine.py`

**Interfaces:**
- Consumes: 无。
- Produces: `Field(str, Enum)`；`CalculationResult`；`CalculationError`；`calculate(values: Mapping[Field, str]) -> CalculationResult`。

- [ ] **Step 1: 写正常公式的失败测试**

```python
import pytest

from calculator_engine import Field, calculate


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ({Field.BASE: "100", Field.RATE: "12"}, (100.0, 112.0, 12.0)),
        ({Field.CURRENT: "112", Field.RATE: "12"}, (100.0, 112.0, 12.0)),
        ({Field.BASE: "100", Field.CURRENT: "92"}, (100.0, 92.0, -8.0)),
    ],
)
def test_calculate_each_missing_field(values, expected):
    result = calculate(values)
    assert (result.base, result.current, result.rate) == pytest.approx(expected)
```

- [ ] **Step 2: 运行测试并确认因模块不存在而失败**

Run: `python -m pytest tests/test_calculator_engine.py::test_calculate_each_missing_field -v`

Expected: FAIL，错误包含 `ModuleNotFoundError: No module named 'calculator_engine'`。

- [ ] **Step 3: 实现字段、结果模型和三种公式**

```python
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
    pass


def calculate(values: Mapping[Field, str]) -> CalculationResult:
    parsed = {field: float(text.strip()) for field, text in values.items() if text.strip()}
    if len(parsed) != 2:
        raise CalculationError("请输入两个已知量")

    missing = next(field for field in Field if field not in parsed)
    if missing is Field.CURRENT:
        base, rate = parsed[Field.BASE], parsed[Field.RATE]
        current = base * (1.0 + rate / 100.0)
    elif missing is Field.BASE:
        current, rate = parsed[Field.CURRENT], parsed[Field.RATE]
        denominator = 1.0 + rate / 100.0
        if math.isclose(denominator, 0.0, abs_tol=1e-12):
            raise CalculationError("增长率为 -100% 时无法计算基期")
        base = current / denominator
    else:
        base, current = parsed[Field.BASE], parsed[Field.CURRENT]
        if math.isclose(base, 0.0, abs_tol=1e-12):
            raise CalculationError("基期为 0，无法计算增长率")
        rate = (current / base - 1.0) * 100.0

    result = CalculationResult(base, current, rate, missing)
    _validate_result(result)
    return result
```

- [ ] **Step 4: 添加边界条件的失败测试**

```python
from calculator_engine import CalculationError


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
    ],
)
def test_invalid_inputs_raise_readable_errors(values, message):
    with pytest.raises(CalculationError, match=message):
        calculate(values)
```

- [ ] **Step 5: 补全解析和结果校验**

将 `float(...)` 转换包装为 `CalculationError("请输入有效数字")`；解析后拒绝 `math.isfinite(value) == False`；计算前分别拒绝负的基期和现期；计算后由 `_validate_result` 拒绝非有限结果以及负的基期或现期。

- [ ] **Step 6: 运行引擎测试**

Run: `python -m pytest tests/test_calculator_engine.py -v`

Expected: 全部 PASS。

- [ ] **Step 7: 提交（仅在已初始化 Git 时）**

```bash
git add calculator_engine.py tests/test_calculator_engine.py
git commit -m "feat: add period growth calculation engine"
```

### Task 2: Qt Designer 界面文件

**Files:**
- Create: `ui/calculator.ui`
- Create: `tests/test_calculator_window.py`

**Interfaces:**
- Consumes: PySide6 `QUiLoader`。
- Produces: 名为 `chartContainer`、`baseInput`、`currentInput`、`rateInput`、`calculateButton`、`clearButton`、`logMessage` 的控件。

- [ ] **Step 1: 写 `.ui` 可加载性的失败测试**

```python
from pathlib import Path

from PySide6.QtCore import QFile
from PySide6.QtUiTools import QUiLoader


def test_ui_file_loads_and_exposes_required_widgets(qapp):
    ui_file = QFile(str(Path("ui/calculator.ui")))
    assert ui_file.open(QFile.ReadOnly)
    window = QUiLoader().load(ui_file)
    ui_file.close()
    assert window is not None
    for name in (
        "chartContainer", "baseInput", "currentInput", "rateInput",
        "calculateButton", "clearButton", "logMessage",
    ):
        assert window.findChild(object, name) is not None
```

- [ ] **Step 2: 运行测试并确认 `.ui` 不存在**

Run: `python -m pytest tests/test_calculator_window.py::test_ui_file_loads_and_exposes_required_widgets -v`

Expected: FAIL，因为 `ui/calculator.ui` 无法打开。

- [ ] **Step 3: 创建 `ui/calculator.ui`**

使用 Qt Designer XML 定义 `QMainWindow`：中央控件使用垂直 `QSplitter`；上方使用水平 `QSplitter`，`stretchFactor` 为 `7` 和 `3`；左侧 `chartContainer` 使用 `QVBoxLayout`；右侧用 `QFormLayout` 放置三个 `QLineEdit`，增长率行增加固定 `%` 标签；下方放只读 `QTextEdit`。设置窗口标题“公考资料分析计算器”、初始尺寸 `1000 × 700`、最小尺寸 `760 × 520`。

- [ ] **Step 4: 运行 `.ui` 加载测试**

Run: `python -m pytest tests/test_calculator_window.py::test_ui_file_loads_and_exposes_required_widgets -v`

Expected: PASS。

- [ ] **Step 5: 提交（仅在已初始化 Git 时）**

```bash
git add ui/calculator.ui tests/test_calculator_window.py
git commit -m "feat: add calculator designer interface"
```

### Task 3: pyqtgraph 图表组件

**Files:**
- Create: `chart_widget.py`
- Modify: `tests/test_calculator_window.py`

**Interfaces:**
- Consumes: `pyqtgraph.PlotWidget`、`calculator_engine.CalculationResult`。
- Produces: `PeriodChart(QWidget)`；`update_result(result: CalculationResult) -> None`；`clear_chart() -> None`。

- [ ] **Step 1: 写图表更新和清空的失败测试**

```python
from calculator_engine import CalculationResult, Field
from chart_widget import PeriodChart


def test_chart_updates_annotation_and_can_clear(qtbot):
    chart = PeriodChart()
    qtbot.addWidget(chart)
    result = CalculationResult(100.0, 112.0, 12.0, Field.CURRENT)
    chart.update_result(result)
    assert chart.annotation.toPlainText() == "↑ 增长 12.00%"
    assert len(chart.bar_item.opts["height"]) == 2
    chart.clear_chart()
    assert chart.annotation.toPlainText() == ""
    assert chart.bar_item is None
```

- [ ] **Step 2: 运行测试并确认图表模块不存在**

Run: `python -m pytest tests/test_calculator_window.py::test_chart_updates_annotation_and_can_clear -v`

Expected: FAIL，错误包含 `ModuleNotFoundError: No module named 'chart_widget'`。

- [ ] **Step 3: 实现 `PeriodChart`**

组件内部创建 `PlotWidget`，启用浅色背景、左侧网格和底部类别轴。`update_result` 先清空旧数据，再用 `BarGraphItem(x=[0, 1], height=[base, current], width=0.55)` 创建双柱，为两个柱顶添加 `TextItem` 数值标签，并根据增长率生成以下文本：

```python
def _rate_text(rate: float) -> str:
    if rate > 0:
        return f"↑ 增长 {rate:.2f}%"
    if rate < 0:
        return f"↓ 下降 {abs(rate):.2f}%"
    return "— 持平 0.00%"
```

`clear_chart` 移除柱体、数值标签和增长率标注，并重置引用。

- [ ] **Step 4: 运行图表测试**

Run: `python -m pytest tests/test_calculator_window.py::test_chart_updates_annotation_and_can_clear -v`

Expected: PASS。

- [ ] **Step 5: 提交（仅在已初始化 Git 时）**

```bash
git add chart_widget.py tests/test_calculator_window.py
git commit -m "feat: add period comparison chart"
```

### Task 4: 窗口控制器与输入状态机

**Files:**
- Create: `calculator_window.py`
- Modify: `tests/test_calculator_window.py`

**Interfaces:**
- Consumes: `calculate(values)`、`Field`、`CalculationError`、`PeriodChart` 和 `.ui` 控件名称。
- Produces: `CalculatorWindow(QMainWindow)`；`calculated_field: Field | None`；`calculate_requested()`；`clear_all()`。

- [ ] **Step 1: 写输入锁定和恢复的失败测试**

```python
from PySide6.QtCore import Qt

from calculator_window import CalculatorWindow


def test_two_inputs_lock_missing_field_and_edit_invalidates_result(qtbot):
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
```

- [ ] **Step 2: 运行测试并确认窗口模块不存在**

Run: `python -m pytest tests/test_calculator_window.py::test_two_inputs_lock_missing_field_and_edit_invalidates_result -v`

Expected: FAIL，错误包含 `ModuleNotFoundError: No module named 'calculator_window'`。

- [ ] **Step 3: 实现 `.ui` 加载和控件绑定**

`CalculatorWindow.__init__` 使用基于 `Path(__file__).resolve().parent` 的绝对路径加载 `.ui`，将加载出的中央控件移入自身；通过 `findChild` 获取控件并公开为 `base_input`、`current_input`、`rate_input`、`calculate_button`、`clear_button` 和 `log_message`。将 `PeriodChart` 插入 `chartContainer` 的布局。

- [ ] **Step 4: 实现输入状态机**

维护：

```python
self.inputs = {
    Field.BASE: self.base_input,
    Field.CURRENT: self.current_input,
    Field.RATE: self.rate_input,
}
self.calculated_field: Field | None = None
self._updating = False
```

每个 `textEdited` 信号传入对应字段。若编辑的是已知字段且已有计算结果，在 `_updating` 保护下清空旧结果并将 `calculated_field` 设为 `None`。随后统计非空输入：恰好两个时将唯一空框设为只读并应用 `pendingResult` 动态属性；不足两个时恢复所有框可写；结果状态下只保持结果框只读。

- [ ] **Step 5: 写计算、日志和清除测试**

```python
def test_calculate_updates_result_chart_and_log(qtbot):
    window = CalculatorWindow()
    qtbot.addWidget(window)
    window.base_input.setText("100")
    window.rate_input.setText("12")
    qtbot.mouseClick(window.calculate_button, Qt.LeftButton)
    assert window.current_input.text() == "112.00"
    assert "基期 100.00，现期 112.00，增长率 12.00%" in window.log_message.toPlainText()
    assert window.chart.bar_item is not None


def test_clear_resets_inputs_log_and_chart(qtbot):
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
```

- [ ] **Step 6: 实现计算、格式化日志和清除**

`calculate_requested` 收集三个输入框的非空文本并调用 `calculate`。成功时用 `_updating` 保护写入三个格式化值，将 `calculated_field` 设置为结果字段，调用 `chart.update_result`，并追加成功日志。捕获 `CalculationError` 后使用红色 HTML 追加转义后的错误文本，不修改图表。`clear_all` 清空输入、日志和图表，并恢复状态。

- [ ] **Step 7: 运行全部窗口测试**

Run: `python -m pytest tests/test_calculator_window.py -v`

Expected: 全部 PASS。

- [ ] **Step 8: 提交（仅在已初始化 Git 时）**

```bash
git add calculator_window.py tests/test_calculator_window.py
git commit -m "feat: connect calculator window interactions"
```

### Task 5: 应用入口、依赖与整体验证

**Files:**
- Modify: `Calculate.py`
- Create: `requirements.txt`

**Interfaces:**
- Consumes: `CalculatorWindow`。
- Produces: `main() -> int` 和可直接运行的桌面程序。

- [ ] **Step 1: 写入口实现**

```python
import sys

from PySide6.QtWidgets import QApplication

from calculator_window import CalculatorWindow


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    window = CalculatorWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: 声明依赖**

```text
PySide6>=6.7,<7
pyqtgraph>=0.13.7,<1
pytest>=8,<9
pytest-qt>=4.4,<5
```

- [ ] **Step 3: 运行完整自动化测试**

Run: `python -m pytest -v`

Expected: 所有引擎、图表和窗口测试 PASS，且无未处理异常。

- [ ] **Step 4: 执行无窗口阻塞的启动冒烟测试**

Run: `python -c "from PySide6.QtCore import QTimer; from PySide6.QtWidgets import QApplication; from calculator_window import CalculatorWindow; app=QApplication([]); w=CalculatorWindow(); w.show(); QTimer.singleShot(250, app.quit); raise SystemExit(app.exec())"`

Expected: 进程在约 250ms 后以退出码 `0` 结束，终端无 traceback。

- [ ] **Step 5: 手工验收关键路径**

Run: `python Calculate.py`

依次验证：窗口布局约为 `7:3`；三种已知量组合均能计算；负增长显示向下标注；修改已知值会清除旧结果；连续计算会追加日志；错误以红色日志出现；清除按钮重置输入、日志和图表；缩放窗口时布局和图表不重叠。

- [ ] **Step 6: 提交（仅在已初始化 Git 时）**

```bash
git add Calculate.py requirements.txt
git commit -m "feat: deliver data analysis calculator application"
```

from pathlib import Path

from PySide6.QtCore import QFile, QObject
from PySide6.QtUiTools import QUiLoader


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

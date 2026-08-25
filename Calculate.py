"""Application entry point for the data-analysis calculator."""

import os
from pathlib import Path
import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from calculator_window import CalculatorWindow


def _configure_qt_font_directory() -> None:
    if sys.platform == "win32" and "QT_QPA_FONTDIR" not in os.environ:
        windows_dir = Path(os.environ.get("WINDIR", r"C:\Windows"))
        os.environ["QT_QPA_FONTDIR"] = str(windows_dir / "Fonts")


def _apply_application_font(app: QApplication) -> None:
    app.setFont(QFont("Noto Sans SC", 10))


def _load_stylesheet(app: QApplication) -> bool:
    stylesheet_path = Path(__file__).resolve().parent / "style.qss"
    try:
        stylesheet = stylesheet_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    app.setStyleSheet(stylesheet)
    return True


def main() -> int:
    _configure_qt_font_directory()
    app = QApplication.instance() or QApplication(sys.argv)
    _apply_application_font(app)
    _load_stylesheet(app)
    window = CalculatorWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

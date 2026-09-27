"""Paleta e QSS do tutorial-editor do LGC."""

from PySide6.QtWidgets import QApplication, QWidget

PAGE_BG = "#11151a"
CARD_BG = "#14191f"
META_BG = "#1a1f26"
EDITOR_BG = "#0e1217"
RAIL_BG = "#10151b"
STATUS_BG = "#0c1015"
STATUS_FG = "#7d8a96"
TEXT = "#dce4ec"
TEXT_STRONG = "#e8ecf0"
ACCENT = "#3d9d6a"
TOOLBAR_BG = "#2f8a58"
TOOLBAR_FG = "#f4fff8"
LINK = "#7dcea0"
CODE_BG = "#07090c"
BORDER = "rgba(61, 157, 106, 0.22)"

DARK_QSS = f"""
QMainWindow, QWidget#workspace {{
  background: {PAGE_BG};
  color: {TEXT};
}}
QMenuBar {{
  background: {META_BG};
  color: {TEXT_STRONG};
  border-bottom: 1px solid {BORDER};
  padding: 2px 6px;
}}
QMenuBar::item {{
  padding: 4px 10px;
  border-radius: 4px;
}}
QMenuBar::item:selected {{
  background: rgba(61, 157, 106, 0.28);
}}
QMenu {{
  background: {META_BG};
  color: {TEXT_STRONG};
  border: 1px solid rgba(61, 157, 106, 0.35);
  padding: 4px;
}}
QMenu::item {{
  padding: 6px 18px;
  border-radius: 4px;
}}
QMenu::item:selected {{
  background: rgba(61, 157, 106, 0.22);
}}
QPlainTextEdit#mdEditor {{
  background: {EDITOR_BG};
  color: {TEXT};
  border: none;
  padding: 10px 12px;
  selection-background-color: rgba(61, 157, 106, 0.35);
  selection-color: {TEXT_STRONG};
}}
QTextBrowser#mdPreview {{
  background: {META_BG};
  color: #d5dde6;
  border: none;
  outline: none;
  border-left: 1px solid rgba(61, 157, 106, 0.16);
  padding: 12px 14px;
}}
QToolBar#formatBar {{
  background: {TOOLBAR_BG};
  color: {TOOLBAR_FG};
  border: none;
  spacing: 2px;
  padding: 0 6px;
  min-height: 38px;
}}
QToolBar#formatBar QToolButton {{
  background: transparent;
  color: {TOOLBAR_FG};
  border: none;
  border-radius: 3px;
  min-width: 32px;
  min-height: 32px;
  font-weight: 700;
  font-size: 14px;
}}
QToolBar#formatBar QToolButton:hover,
QToolBar#formatBar QToolButton:pressed,
QToolBar#formatBar QToolButton:checked {{
  background: rgba(0, 0, 0, 0.18);
}}
QToolBar#formatBar QToolButton::menu-indicator {{
  image: none;
  width: 0;
}}
QWidget#insertRail {{
  background: {RAIL_BG};
  border-right: 1px solid rgba(61, 157, 106, 0.16);
}}
QWidget#insertRail QToolButton {{
  background: transparent;
  color: #b7c4cf;
  border: none;
  border-radius: 4px;
  min-width: 34px;
  min-height: 34px;
  font-size: 13px;
}}
QWidget#insertRail QToolButton:hover {{
  background: rgba(61, 157, 106, 0.18);
  color: {TEXT_STRONG};
}}
QWidget#statusBar {{
  background: {STATUS_BG};
  color: {STATUS_FG};
}}
QWidget#statusBar QLabel {{
  color: {STATUS_FG};
  font-size: 11px;
  letter-spacing: 0.3px;
}}
QSplitter::handle {{
  background: rgba(61, 157, 106, 0.16);
  width: 1px;
}}
QScrollBar:vertical {{
  background: transparent;
  width: 10px;
  margin: 0;
}}
QScrollBar::handle:vertical {{
  background: rgba(61, 157, 106, 0.35);
  min-height: 24px;
  border-radius: 4px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
  height: 0;
}}
"""

LIGHT_QSS = """
QMainWindow, QWidget#workspace {
  background: #f4f6f5;
  color: #222222;
}
QMenuBar {
  background: #eef2ef;
  color: #1a1f26;
  border-bottom: 1px solid rgba(61, 157, 106, 0.25);
}
QMenuBar::item:selected {
  background: rgba(61, 157, 106, 0.18);
}
QMenu {
  background: #ffffff;
  color: #1a1f26;
  border: 1px solid rgba(61, 157, 106, 0.3);
}
QMenu::item:selected {
  background: rgba(61, 157, 106, 0.18);
}
QPlainTextEdit#mdEditor {
  background: #ffffff;
  color: #222222;
  border: none;
  padding: 10px 12px;
  selection-background-color: rgba(61, 157, 106, 0.28);
}
QTextBrowser#mdPreview {
  background: #f7f9f8;
  color: #222222;
  border: none;
  outline: none;
  border-left: 1px solid rgba(61, 157, 106, 0.2);
  padding: 12px 14px;
}
QToolBar#formatBar {
  background: #2f8a58;
  color: #f4fff8;
  border: none;
  spacing: 2px;
  padding: 0 6px;
  min-height: 38px;
}
QToolBar#formatBar QToolButton {
  background: transparent;
  color: #f4fff8;
  border: none;
  border-radius: 3px;
  min-width: 32px;
  min-height: 32px;
  font-weight: 700;
  font-size: 14px;
}
QToolBar#formatBar QToolButton:hover,
QToolBar#formatBar QToolButton:pressed,
QToolBar#formatBar QToolButton:checked {
  background: rgba(0, 0, 0, 0.18);
}
QToolBar#formatBar QToolButton::menu-indicator {
  image: none;
  width: 0;
}
QWidget#insertRail {
  background: #e8eeea;
  border-right: 1px solid rgba(61, 157, 106, 0.2);
}
QWidget#insertRail QToolButton {
  background: transparent;
  color: #3a4a42;
  border: none;
  border-radius: 4px;
  min-width: 34px;
  min-height: 34px;
}
QWidget#insertRail QToolButton:hover {
  background: rgba(61, 157, 106, 0.18);
}
QWidget#statusBar {
  background: #e4eae6;
}
QWidget#statusBar QLabel {
  color: #5a6a62;
  font-size: 11px;
}
QSplitter::handle {
  background: rgba(61, 157, 106, 0.2);
  width: 1px;
}
"""


def configure_app(app: QApplication) -> None:
    app.setStyle("Fusion")


def apply_theme(widget: QWidget, theme: str) -> None:
    widget.setStyleSheet(DARK_QSS if theme == "dark" else LIGHT_QSS)

"""Temas claro e escuro no estilo Remember Me."""

from PySide6.QtWidgets import QApplication, QWidget

# Escuro: laranja em destaque sobre preto, cinza e branco.
_RM_PAGE = "#0e0c0b"
_RM_META = "#161412"
_RM_EDITOR = "#100e0d"
_RM_RAIL = "#12100f"
_RM_STATUS = "#0a0908"
_RM_STATUS_FG = "#9a8f86"
_RM_TEXT = "#ece6e0"
_RM_STRONG = "#fff8f2"
_RM_BAR = "#e85d04"
_RM_BAR_FG = "#fff8f0"
_RM_ORANGE = "255, 106, 26"

DARK_QSS = f"""
QMainWindow {{
  background: {_RM_PAGE};
  color: {_RM_TEXT};
  border: 1px solid rgba({_RM_ORANGE}, 0.4);
}}
QWidget#workspace {{
  background: {_RM_PAGE};
  color: {_RM_TEXT};
}}
QWidget#titleBar {{
  background: {_RM_META};
  color: {_RM_STRONG};
  border-bottom: 1px solid rgba({_RM_ORANGE}, 0.28);
}}
QWidget#titleBar QLabel#titleCaption {{
  color: {_RM_STRONG};
  font-size: 12px;
  font-weight: 600;
}}
QWidget#titleBar QToolButton {{
  background: transparent;
  color: {_RM_STRONG};
  border: none;
  border-radius: 4px;
  font-size: 14px;
}}
QWidget#titleBar QToolButton:hover {{
  background: rgba({_RM_ORANGE}, 0.28);
}}
QWidget#titleBar QToolButton#titleClose:hover {{
  background: #c0392b;
  color: #ffffff;
}}
QMenuBar {{
  background: {_RM_META};
  color: {_RM_STRONG};
  border-bottom: 1px solid rgba({_RM_ORANGE}, 0.28);
  padding: 2px 6px;
}}
QMenuBar::item {{
  padding: 4px 10px;
  border-radius: 4px;
}}
QMenuBar::item:selected {{
  background: rgba({_RM_ORANGE}, 0.28);
}}
QMenu {{
  background: {_RM_META};
  color: {_RM_STRONG};
  border: 1px solid rgba({_RM_ORANGE}, 0.4);
  padding: 4px;
}}
QMenu::item {{
  padding: 6px 18px;
  border-radius: 4px;
}}
QMenu::item:selected {{
  background: rgba({_RM_ORANGE}, 0.22);
}}
QPlainTextEdit#mdEditor {{
  background: {_RM_EDITOR};
  color: {_RM_TEXT};
  border: none;
  padding: 10px 12px;
  selection-background-color: rgba({_RM_ORANGE}, 0.35);
  selection-color: {_RM_STRONG};
}}
QTextBrowser#mdPreview {{
  background: {_RM_META};
  color: #e8e4df;
  border: none;
  outline: none;
  border-left: 1px solid rgba({_RM_ORANGE}, 0.2);
  padding: 12px 14px;
}}
QToolBar#formatBar {{
  background: {_RM_BAR};
  color: {_RM_BAR_FG};
  border: none;
  spacing: 2px;
  padding: 0 6px;
  min-height: 38px;
}}
QToolBar#formatBar QToolButton {{
  background: transparent;
  color: {_RM_BAR_FG};
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
  background: rgba(0, 0, 0, 0.22);
}}
QToolBar#formatBar QToolButton::menu-indicator {{
  image: none;
  width: 0;
}}
QWidget#insertRail {{
  background-color: #2a2a2c;
  border: none;
}}
QWidget#insertRail QToolButton {{
  background: transparent;
  color: #f2f2f3;
  border: none;
  border-radius: 4px;
  min-width: 34px;
  min-height: 34px;
  font-size: 13px;
}}
QWidget#insertRail QToolButton:hover {{
  background: rgba(255, 255, 255, 0.08);
  color: #ffffff;
}}
QWidget#filesRail {{
  background: {_RM_RAIL};
  border-right: 1px solid rgba({_RM_ORANGE}, 0.2);
}}
QLabel#filesTitle {{
  color: #ffb347;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.8px;
  padding: 6px 8px;
}}
QWidget#filesHeader QToolButton#filesToggle {{
  background: transparent;
  color: #ffb347;
  border: none;
  border-radius: 4px;
  min-width: 24px;
  min-height: 24px;
  font-size: 14px;
  font-weight: 700;
}}
QWidget#filesHeader QToolButton#filesToggle:hover {{
  background: rgba({_RM_ORANGE}, 0.22);
  color: {_RM_STRONG};
}}
QLabel#filesFolder {{
  color: {_RM_STATUS_FG};
  font-size: 11px;
  padding: 0 12px 8px;
}}
QLabel#filesEmpty {{
  color: {_RM_STATUS_FG};
  font-size: 12px;
  padding: 4px 12px 12px;
}}
QTreeWidget#filesTree {{
  background: transparent;
  border: none;
  color: {_RM_TEXT};
  outline: none;
  padding: 2px 6px 8px;
}}
QTreeWidget#filesTree::item {{
  padding: 4px 6px;
  border-radius: 4px;
}}
QTreeWidget#filesTree::item:hover {{
  background: rgba({_RM_ORANGE}, 0.18);
}}
QTreeWidget#filesTree::item:selected {{
  background: rgba({_RM_ORANGE}, 0.3);
  color: {_RM_STRONG};
}}
QTreeWidget#filesTree::branch {{
  background: transparent;
}}
QWidget#outlineRail {{
  background: {_RM_RAIL};
  border-left: 1px solid rgba({_RM_ORANGE}, 0.2);
}}
QLabel#outlineTitle {{
  color: #ffb347;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.8px;
  padding: 10px 12px 6px;
}}
QLabel#outlineEmpty {{
  color: {_RM_STATUS_FG};
  font-size: 12px;
  padding: 4px 12px 12px;
}}
QListWidget#outlineList {{
  background: transparent;
  border: none;
  color: {_RM_TEXT};
  outline: none;
  padding: 2px 6px 8px;
}}
QListWidget#outlineList::item {{
  padding: 5px 8px;
  border-radius: 4px;
}}
QListWidget#outlineList::item:hover {{
  background: rgba({_RM_ORANGE}, 0.18);
}}
QListWidget#outlineList::item:selected {{
  background: rgba({_RM_ORANGE}, 0.3);
  color: {_RM_STRONG};
}}
QWidget#statusBar {{
  background-color: #111111;
  color: #ffffff;
  border: none;
}}
QWidget#statusBar QLabel {{
  color: #ffffff;
  font-size: 11px;
  letter-spacing: 0.3px;
}}
QSplitter::handle {{
  background: rgba({_RM_ORANGE}, 0.22);
  width: 1px;
}}
QScrollBar:vertical {{
  background: transparent;
  width: 10px;
  margin: 0;
}}
QScrollBar::handle:vertical {{
  background: rgba({_RM_ORANGE}, 0.4);
  min-height: 24px;
  border-radius: 4px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
  height: 0;
}}
"""

# Claro: branco no fundo, preto nos títulos, laranja só como acento.
_RML_PAGE = "#f2f2f3"
_RML_META = "#ffffff"
_RML_EDITOR = "#ffffff"
_RML_RAIL = "#efeff0"
_RML_BAR = "#111111"
_RML_BAR_FG = "#ffffff"
_RML_TEXT = "#1a1a1a"
_RML_MUTED = "#6e6e6e"
_RML_ORANGE = "232, 93, 4"

LIGHT_QSS = f"""
QMainWindow {{
  background: {_RML_PAGE};
  color: {_RML_TEXT};
  border: 1px solid #d4d4d6;
}}
QWidget#workspace {{
  background: {_RML_PAGE};
  color: {_RML_TEXT};
}}
QWidget#titleBar {{
  background: {_RML_META};
  color: {_RML_TEXT};
  border-bottom: 1px solid #e4e4e6;
}}
QWidget#titleBar QLabel#titleCaption {{
  color: {_RML_TEXT};
  font-size: 12px;
  font-weight: 600;
}}
QWidget#titleBar QToolButton {{
  background: transparent;
  color: {_RML_TEXT};
  border: none;
  border-radius: 4px;
  font-size: 14px;
}}
QWidget#titleBar QToolButton:hover {{
  background: rgba({_RML_ORANGE}, 0.16);
}}
QWidget#titleBar QToolButton#titleClose:hover {{
  background: #c0392b;
  color: #ffffff;
}}
QMenuBar {{
  background: {_RML_META};
  color: {_RML_TEXT};
  border-bottom: 1px solid #e4e4e6;
  padding: 2px 6px;
}}
QMenuBar::item {{
  padding: 4px 10px;
  border-radius: 4px;
}}
QMenuBar::item:selected {{
  background: rgba({_RML_ORANGE}, 0.16);
}}
QMenu {{
  background: {_RML_META};
  color: {_RML_TEXT};
  border: 1px solid #e4e4e6;
  padding: 4px;
}}
QMenu::item {{
  padding: 6px 18px;
  border-radius: 4px;
}}
QMenu::item:selected {{
  background: rgba({_RML_ORANGE}, 0.16);
}}
QPlainTextEdit#mdEditor {{
  background: {_RML_EDITOR};
  color: {_RML_TEXT};
  border: none;
  padding: 10px 12px;
  selection-background-color: rgba({_RML_ORANGE}, 0.22);
  selection-color: {_RML_TEXT};
}}
QTextBrowser#mdPreview {{
  background: {_RML_META};
  color: {_RML_TEXT};
  border: none;
  outline: none;
  border-left: 1px solid #e4e4e6;
  padding: 12px 14px;
}}
QToolBar#formatBar {{
  background: {_RML_BAR};
  color: {_RML_BAR_FG};
  border: none;
  spacing: 2px;
  padding: 0 6px;
  min-height: 38px;
}}
QToolBar#formatBar QToolButton {{
  background: transparent;
  color: {_RML_BAR_FG};
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
  background: rgba({_RML_ORANGE}, 0.85);
  color: {_RML_BAR_FG};
}}
QToolBar#formatBar QToolButton::menu-indicator {{
  image: none;
  width: 0;
}}
QWidget#insertRail {{
  background-color: #e85d04;
  border: none;
}}
QWidget#insertRail QToolButton {{
  background: transparent;
  color: #fff8f0;
  border: none;
  border-radius: 4px;
  min-width: 34px;
  min-height: 34px;
  font-size: 13px;
}}
QWidget#insertRail QToolButton:hover {{
  background: rgba(0, 0, 0, 0.18);
  color: #ffffff;
}}
QWidget#filesRail {{
  background: #2a2a2c;
  border-right: none;
}}
QLabel#filesTitle {{
  background: #2a2a2c;
  color: #f2f2f3;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.8px;
  padding: 6px 8px;
}}
QWidget#filesHeader QToolButton#filesToggle {{
  background: transparent;
  color: #f2f2f3;
  border: none;
  border-radius: 4px;
  min-width: 24px;
  min-height: 24px;
  font-size: 14px;
  font-weight: 700;
}}
QWidget#filesHeader QToolButton#filesToggle:hover {{
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
}}
QLabel#filesFolder {{
  background: #2a2a2c;
  color: #9a9a9e;
  font-size: 11px;
  padding: 0 12px 8px;
}}
QLabel#filesEmpty {{
  color: #9a9a9e;
  font-size: 12px;
  padding: 4px 12px 12px;
}}
QTreeWidget#filesTree {{
  background: #2a2a2c;
  border: none;
  color: #f2f2f3;
  outline: none;
  padding: 2px 6px 8px;
}}
QTreeWidget#filesTree::item {{
  padding: 4px 6px;
  border-radius: 4px;
}}
QTreeWidget#filesTree::item:hover {{
  background: rgba(255, 255, 255, 0.08);
}}
QTreeWidget#filesTree::item:selected {{
  background: #e85d04;
  color: #ffffff;
}}
QTreeWidget#filesTree::branch {{
  background: #2a2a2c;
}}
QWidget#outlineRail {{
  background: #2a2a2c;
  border-left: none;
}}
QLabel#outlineTitle {{
  background: #2a2a2c;
  color: #f2f2f3;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.8px;
  padding: 10px 12px;
}}
QLabel#outlineEmpty {{
  color: #9a9a9e;
  font-size: 12px;
  padding: 4px 12px 12px;
}}
QListWidget#outlineList {{
  background: #2a2a2c;
  border: none;
  color: #f2f2f3;
  outline: none;
  padding: 2px 6px 8px;
}}
QListWidget#outlineList::item {{
  padding: 5px 8px;
  border-radius: 4px;
}}
QListWidget#outlineList::item:hover {{
  background: rgba(255, 255, 255, 0.08);
}}
QListWidget#outlineList::item:selected {{
  background: #e85d04;
  color: #ffffff;
}}
QWidget#statusBar {{
  background-color: #111111;
  color: #ffffff;
  border: none;
}}
QWidget#statusBar QLabel {{
  color: #ffffff;
  font-size: 11px;
  letter-spacing: 0.3px;
}}
QSplitter::handle {{
  background: #e4e4e6;
  width: 1px;
}}
QScrollBar:vertical {{
  background: #e8e8ea;
  width: 10px;
  margin: 0;
}}
QScrollBar::handle:vertical {{
  background: #b4b4b8;
  min-height: 24px;
  border-radius: 4px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
  height: 0;
}}
"""


def configure_app(app: QApplication) -> None:
    app.setStyle("Fusion")


def apply_theme(widget: QWidget, theme: str) -> None:
    widget.setStyleSheet(LIGHT_QSS if theme == "light" else DARK_QSS)

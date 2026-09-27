from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QSizePolicy,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.callouts import CALLOUT_DOTS, CALLOUT_KINDS, CALLOUT_LABELS, callout_fence
from app.editor import MarkdownEditor


def _dot_icon(color: str) -> QIcon:
    pix = QPixmap(12, 12)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(color))
    painter.drawEllipse(1, 1, 10, 10)
    painter.end()
    return QIcon(pix)


def _split_icon(color: str = "#f4fff8") -> QIcon:
    pix = QPixmap(20, 20)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(color))
    painter.drawRoundedRect(2, 3, 7, 14, 1, 1)
    painter.drawRoundedRect(11, 3, 7, 6, 1, 1)
    painter.drawRoundedRect(11, 11, 7, 6, 1, 1)
    painter.end()
    return QIcon(pix)


def _format_button(
    text: str,
    tooltip: str,
    *,
    italic: bool = False,
    strike: bool = False,
) -> QToolButton:
    btn = QToolButton()
    btn.setText(text)
    btn.setToolTip(tooltip)
    btn.setAutoRaise(True)
    btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    font = btn.font()
    font.setBold(True)
    font.setItalic(italic)
    font.setStrikeOut(strike)
    btn.setFont(font)
    return btn


def _image_icon(color: str = "#b7c4cf") -> QIcon:
    pix = QPixmap(20, 20)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QColor(color))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(2, 4, 16, 12, 2, 2)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(color))
    painter.drawEllipse(12, 6, 3, 3)
    painter.drawPolygon(
        [
            QPoint(3, 15),
            QPoint(8, 9),
            QPoint(11, 12),
            QPoint(13, 10),
            QPoint(17, 15),
        ]
    )
    painter.end()
    return QIcon(pix)


def _rail_button(text: str, tooltip: str) -> QToolButton:
    btn = QToolButton()
    btn.setText(text)
    btn.setToolTip(tooltip)
    btn.setAutoRaise(True)
    btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    font = QFont("monospace")
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setPointSize(10)
    font.setBold(True)
    btn.setFont(font)
    return btn


class FormatToolbar(QToolBar):
    preview_toggled = Signal(bool)

    def __init__(self, editor: MarkdownEditor, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("formatBar")
        self.setMovable(False)
        self.setFloatable(False)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)

        bold = _format_button("B", "Negrito (Ctrl+B)")
        bold.clicked.connect(lambda: editor.wrap_markup("**", placeholder="negrito"))
        italic = _format_button("I", "Itálico (Ctrl+I)", italic=True)
        italic.clicked.connect(lambda: editor.wrap_markup("*", placeholder="itálico"))
        strike = _format_button("S", "Rasurado", strike=True)
        strike.clicked.connect(lambda: editor.wrap_markup("~~", placeholder="rasurado"))

        heading = _format_button("H", "Títulos")
        heading.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(heading)
        for level in range(1, 6):
            label = f"{'#' * level} Título {level:02d}" if level == 5 else f"{'#' * level} Título {level}"
            action = menu.addAction(label)
            action.triggered.connect(lambda _checked=False, lv=level: editor.apply_heading(lv))
        heading.setMenu(menu)

        info = _format_button("i", "Info / Warning / Danger / Record")
        info.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        callout_menu = QMenu(info)
        for kind in CALLOUT_KINDS:
            action = callout_menu.addAction(_dot_icon(CALLOUT_DOTS[kind]), f"{CALLOUT_LABELS[kind]}   {callout_fence(kind)}")
            action.triggered.connect(lambda _checked=False, k=kind: editor.apply_callout(k))
        info.setMenu(callout_menu)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedHeight(18)
        sep.setStyleSheet("color: rgba(255, 255, 255, 0.28);")

        self.addWidget(bold)
        self.addWidget(italic)
        self.addWidget(strike)
        self.addWidget(sep)
        self.addWidget(heading)
        self.addWidget(info)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.addWidget(spacer)

        preview_btn = QToolButton()
        preview_btn.setIcon(_split_icon())
        preview_btn.setAutoRaise(True)
        preview_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        preview_btn.setCheckable(True)
        preview_btn.setChecked(True)
        preview_btn.setToolTip("Ocultar pré-visualização")
        preview_btn.toggled.connect(self._on_preview_toggled)
        self.addWidget(preview_btn)
        self._preview_btn = preview_btn

    def _on_preview_toggled(self, visible: bool) -> None:
        self._preview_btn.setToolTip(
            "Ocultar pré-visualização" if visible else "Mostrar pré-visualização"
        )
        self.preview_toggled.emit(visible)


class InsertRail(QWidget):
    image_requested = Signal()

    def __init__(self, editor: MarkdownEditor, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("insertRail")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        self.setFixedWidth(42)

        link = _rail_button("[]", "Inserir ligação")
        link.clicked.connect(editor.insert_link)
        image = QToolButton()
        image.setIcon(_image_icon("#fff8f0"))
        image.setAutoRaise(True)
        image.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        image.setToolTip("Inserir imagem")
        image.clicked.connect(self.image_requested.emit)
        inline = _rail_button("`x`", "Comando inline")
        inline.clicked.connect(editor.insert_inline_code)
        block = _rail_button("{ }", "Bloco de código")
        block.clicked.connect(editor.insert_code_block)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 8, 4, 8)
        layout.setSpacing(4)
        layout.addWidget(link, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(image, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(inline, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(block, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)


class StatusBar(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("statusBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        self.setFixedHeight(24)

        self._kind = QLabel("Markdown")
        self._cursor = QLabel("Ln 1, Col 1")
        self._flash = QTimer(self)
        self._flash.setSingleShot(True)
        self._flash.timeout.connect(lambda: self._kind.setText("Markdown"))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.addWidget(self._kind)
        layout.addStretch(1)
        layout.addWidget(self._cursor)

    def set_cursor(self, line: int, col: int) -> None:
        self._cursor.setText(f"Ln {line}, Col {col}")

    def flash(self, message: str, ms: int = 1400) -> None:
        self._kind.setText(message)
        self._flash.start(ms)

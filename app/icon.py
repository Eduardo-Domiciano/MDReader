from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap


def icon_path() -> Path:
    return Path(__file__).resolve().with_name("icon.png")


def render_icon_pixmap(size: int = 256) -> QPixmap:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    margin = max(size // 16, 4)
    box = QRect(margin, margin, size - margin * 2, size - margin * 2)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#111111"))
    radius = max(size // 8, 8)
    painter.drawRoundedRect(box, radius, radius)
    bar = QRect(margin, margin, size - margin * 2, max(size // 5, 10))
    painter.setBrush(QColor("#e85d04"))
    painter.drawRoundedRect(bar, radius, radius)
    painter.fillRect(bar.adjusted(0, radius, 0, 0), QColor("#e85d04"))
    font = QFont("sans-serif")
    font.setBold(True)
    font.setPixelSize(max(int(size * 0.36), 12))
    painter.setFont(font)
    painter.setPen(QColor("#fff8f0"))
    text_box = QRect(margin, bar.bottom() - size // 32, size - margin * 2, size - bar.height() - margin)
    painter.drawText(text_box, int(Qt.AlignmentFlag.AlignCenter), "MD_")
    painter.end()
    return pix


def app_icon() -> QIcon:
    stored = icon_path()
    source = QPixmap(str(stored)) if stored.is_file() else QPixmap()
    icon = QIcon()
    for size in (16, 20, 24, 32, 48, 64, 128, 256):
        if not source.isNull():
            icon.addPixmap(
                source.scaled(
                    size,
                    size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            icon.addPixmap(render_icon_pixmap(size))
    return icon

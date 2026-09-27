from __future__ import annotations

import re
from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

_ATX_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_FENCE_RE = re.compile(r"^(```+|~~~+)")
_SETEXT_H1_RE = re.compile(r"^={2,}\s*$")
_SETEXT_H2_RE = re.compile(r"^-{2,}\s*$")
_MARKUP_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)|[*_~`]+")


@dataclass(frozen=True)
class Heading:
    level: int
    title: str
    line: int
    index: int


def _plain_title(text: str) -> str:
    return _MARKUP_RE.sub(lambda match: match.group(1) or "", text).strip()


def extract_headings(source: str) -> list[Heading]:
    lines = source.splitlines()
    headings: list[Heading] = []
    in_fence = False
    fence_char = ""
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        fence = _FENCE_RE.match(stripped)
        if fence:
            marker = fence.group(1)[0]
            if not in_fence:
                in_fence = True
                fence_char = marker
            elif marker == fence_char:
                in_fence = False
                fence_char = ""
            i += 1
            continue
        if in_fence or stripped.startswith(">"):
            i += 1
            continue
        atx = _ATX_RE.match(line)
        if atx:
            title = _plain_title(atx.group(2))
            if title:
                headings.append(Heading(len(atx.group(1)), title, i, len(headings)))
            i += 1
            continue
        if i + 1 < len(lines) and line.strip():
            underline = lines[i + 1]
            if _SETEXT_H1_RE.match(underline):
                title = _plain_title(line.strip())
                if title:
                    headings.append(Heading(1, title, i, len(headings)))
                i += 2
                continue
            if _SETEXT_H2_RE.match(underline):
                title = _plain_title(line.strip())
                if title:
                    headings.append(Heading(2, title, i, len(headings)))
                i += 2
                continue
        i += 1
    return headings


class OutlineRail(QWidget):
    heading_activated = Signal(int, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("outlineRail")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        self.setMinimumWidth(156)
        self.setMaximumWidth(320)

        title = QLabel("ÍNDICE")
        title.setObjectName("outlineTitle")

        self._empty = QLabel("Sem títulos")
        self._empty.setObjectName("outlineEmpty")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self._list = QListWidget()
        self._list.setObjectName("outlineList")
        self._list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.setTextElideMode(Qt.TextElideMode.ElideRight)
        self._list.setSpacing(1)
        self._list.itemClicked.connect(self._on_item)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(title)
        layout.addWidget(self._empty)
        layout.addWidget(self._list, 1)
        self.set_headings([])

    def set_headings(self, headings: list[Heading]) -> None:
        self._list.clear()
        if not headings:
            self._empty.show()
            self._list.hide()
            return
        self._empty.hide()
        self._list.show()
        for heading in headings:
            indent = "    " * (heading.level - 1)
            item = QListWidgetItem(f"{indent}{heading.title}")
            item.setData(Qt.ItemDataRole.UserRole, heading.index)
            item.setData(Qt.ItemDataRole.UserRole + 1, heading.line)
            item.setToolTip(heading.title)
            self._list.addItem(item)

    def _on_item(self, item: QListWidgetItem) -> None:
        index = item.data(Qt.ItemDataRole.UserRole)
        line = item.data(Qt.ItemDataRole.UserRole + 1)
        if index is not None and line is not None:
            self.heading_activated.emit(int(index), int(line))

from __future__ import annotations

import re

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QFont, QTextCursor
from PySide6.QtWidgets import QPlainTextEdit

from app.callouts import callout_fence, expand_callout_range, is_callout_fence_line
from app.images import is_image_path, markdown_image_dest

_HEADING_RE = re.compile(r"^#{1,6}\s*")


class MarkdownEditor(QPlainTextEdit):
    """Área de texto com fonte monoespaçada e inserção estilo LGC."""

    image_dropped = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("mdEditor")
        font = QFont("monospace")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(11)
        self.setFont(font)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4)
        self.setPlaceholderText("Escreva Markdown aqui…")
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.setAcceptDrops(True)

    def cursor_line_col(self) -> tuple[int, int]:
        cursor = self.textCursor()
        return cursor.blockNumber() + 1, cursor.positionInBlock() + 1

    def go_to_line(self, line: int) -> None:
        block = self.document().findBlockByNumber(line)
        if not block.isValid():
            return
        cursor = self.textCursor()
        cursor.setPosition(block.position())
        self.setTextCursor(cursor)
        self.centerCursor()

    def _replace_and_select(self, next_text: str, sel_start: int, sel_end: int) -> None:
        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.insertText(next_text)
        cursor.setPosition(sel_start)
        cursor.setPosition(sel_end, QTextCursor.MoveMode.KeepAnchor)
        cursor.endEditBlock()
        self.setTextCursor(cursor)
        self.setFocus()

    def wrap_markup(self, start: str, end: str | None = None, placeholder: str = "texto") -> None:
        closer = start if end is None else end
        text = self.toPlainText()
        cursor = self.textCursor()
        start_pos = cursor.selectionStart()
        end_pos = cursor.selectionEnd()
        selected = text[start_pos:end_pos]
        already = (
            bool(selected)
            and start_pos >= len(start)
            and text[start_pos - len(start) : start_pos] == start
            and text[end_pos : end_pos + len(closer)] == closer
        )
        if already:
            next_text = text[: start_pos - len(start)] + selected + text[end_pos + len(closer) :]
            sel_start = start_pos - len(start)
            sel_end = sel_start + len(selected)
        else:
            inner = selected or placeholder
            next_text = text[:start_pos] + start + inner + closer + text[end_pos:]
            sel_start = start_pos + len(start)
            sel_end = sel_start + len(inner)
        self._replace_and_select(next_text, sel_start, sel_end)

    def apply_heading(self, level: int) -> None:
        level = max(1, min(level, 5))
        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(
            QTextCursor.MoveOperation.EndOfBlock,
            QTextCursor.MoveMode.KeepAnchor,
        )
        line = cursor.selectedText()
        text = _HEADING_RE.sub("", line).strip()
        if not text:
            text = f"Título {level:02d}" if level == 5 else f"Título {level}"
        cursor.insertText(f"{'#' * level} {text}")
        cursor.endEditBlock()
        self.setTextCursor(cursor)
        self.setFocus()

    def apply_callout(self, kind: str) -> None:
        text = self.toPlainText()
        cursor = self.textCursor()
        from_, to = expand_callout_range(text, cursor.selectionStart(), cursor.selectionEnd())
        block = text[from_:to]
        lines = block.split("\n") if block else [""]
        content = [line for line in lines if not is_callout_fence_line(line)] or [""]
        quoted: list[str] = []
        for line in content:
            if line.startswith("> "):
                quoted.append(line)
            elif line.startswith(">"):
                quoted.append(f"> {line[1:].lstrip()}")
            else:
                quoted.append(f"> {line}" if line else "> nota")
        next_block = "\n".join(quoted) + f"\n\n{callout_fence(kind)}"
        next_text = text[:from_] + next_block + text[to:]
        first = quoted[0]
        inner_start = from_ + 2
        self._replace_and_select(next_text, inner_start, from_ + len(first))

    def insert_link(self) -> None:
        self.wrap_markup("[", "](https://)", "ligação")

    def insert_image(self, source: str, alt: str | None = None) -> None:
        dest = markdown_image_dest(source)
        text = self.toPlainText()
        cursor = self.textCursor()
        start_pos = cursor.selectionStart()
        end_pos = cursor.selectionEnd()
        selected = text[start_pos:end_pos]
        alt_text = selected or alt or Path(source).stem or "imagem"
        prefix = "\n" if start_pos > 0 and text[start_pos - 1] != "\n" else ""
        suffix = "\n" if end_pos >= len(text) or text[end_pos] != "\n" else ""
        snippet = f"{prefix}![{alt_text}]({dest}){suffix}"
        next_text = text[:start_pos] + snippet + text[end_pos:]
        after = start_pos + len(snippet)
        self._replace_and_select(next_text, after, after)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if any(is_image_path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [
            url.toLocalFile()
            for url in event.mimeData().urls()
            if url.isLocalFile() and is_image_path(url.toLocalFile())
        ]
        if not paths:
            super().dropEvent(event)
            return
        for path in paths:
            self.image_dropped.emit(path)
        event.acceptProposedAction()

    def insert_inline_code(self) -> None:
        self.wrap_markup("`", placeholder="comando")

    def insert_code_block(self) -> None:
        text = self.toPlainText()
        cursor = self.textCursor()
        start_pos = cursor.selectionStart()
        end_pos = cursor.selectionEnd()
        selected = text[start_pos:end_pos] or "código"
        prefix = "\n" if start_pos > 0 and text[start_pos - 1] != "\n" else ""
        block = f"{prefix}```\n{selected}\n```\n"
        next_text = text[:start_pos] + block + text[end_pos:]
        sel_start = start_pos + len(prefix) + 4
        self._replace_and_select(next_text, sel_start, sel_start + len(selected))

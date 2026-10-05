from __future__ import annotations

import html
import re
import secrets
from pathlib import Path
from typing import Protocol
from urllib.parse import quote, unquote

import bleach
from markdown_it import MarkdownIt
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.util import ClassNotFound
from PySide6.QtCore import QRectF, Qt, QTimer, QUrl, QUrlQuery, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QDesktopServices,
    QFont,
    QPainter,
    QPaintEvent,
    QPen,
    QTextCursor,
    QTextLength,
    QTextOption,
    QTextTable,
)
from PySide6.QtWidgets import QApplication, QTextBrowser, QWidget

from app.callouts import apply_blockquote_callouts
from app.diagrams import FenceKind, diagram_image_html, resolve_fence
from app.images import apply_image_sizes, normalize_wiki_images, resolve_local_image_srcs

_PRE_SPLIT_RE = re.compile(
    r"(<pre\b[^>]*>[\s\S]*?</pre>|<table\b[^>]*class=\"md-codeblock\"[^>]*>[\s\S]*?</table>)",
    re.IGNORECASE,
)
_HEADING_HTML_RE = re.compile(r"<h([1-6])>([\s\S]*?)</h\1>", re.IGNORECASE)
_CODE_RE = re.compile(r"<code\b[^>]*>([\s\S]*?)</code>", re.IGNORECASE)
_COPY_PAYLOADS: dict[str, str] = {}
_COPY_BTN_STYLE = (
    "color:#c5d0db;background-color:#10151b;text-decoration:none;"
    "padding:4px 10px;border:1px solid #6b7580;border-radius:4px;"
    "font-size:12px;font-weight:650;"
)
_INLINE_CODE_STYLE = (
    "background-color:transparent;color:transparent;text-decoration:none;"
    "padding:0;border:none;border-radius:0;"
    "font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;"
    "font-size:0.84em;font-weight:650;"
)
_CMD_TEXT = QColor("#ffe8d2")
_CMD_FILL = QColor("#000000")
_CMD_BORDER = QColor("#e85d04")

ALLOWED_TAGS = [
    "a",
    "abbr",
    "b",
    "blockquote",
    "br",
    "code",
    "div",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "img",
    "li",
    "ol",
    "p",
    "pre",
    "del",
    "s",
    "span",
    "strong",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "ul",
]

ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "name", "id"],
    "img": ["src", "alt", "title", "width", "height"],
    "td": ["align", "id", "width"],
    "th": ["align", "id", "width"],
    "code": ["class", "id", "title"],
    "div": ["class", "id"],
    "span": ["class", "id", "title"],
    "pre": ["class", "id", "title"],
    "blockquote": ["class", "id"],
    "p": ["id", "class"],
    "h1": ["id"],
    "h2": ["id"],
    "h3": ["id"],
    "h4": ["id"],
    "h5": ["id"],
    "h6": ["id"],
    "ul": ["id"],
    "ol": ["id"],
    "li": ["id"],
    "table": ["id", "class", "width"],
    "hr": ["id"],
}


def _formatter(theme: str) -> HtmlFormatter:
    style = "default" if theme == "light" else "native"
    return HtmlFormatter(nowrap=True, cssclass="highlight", style=style)


_LABEL_SPAN_RE = re.compile(
    r'<span class="md-(?:label|diagram)" title="([^"]*)"></span>',
    re.IGNORECASE,
)


def _label_span(kind: FenceKind) -> str:
    if not kind.label:
        return ""
    css = "md-diagram" if kind.diagram_source is not None else "md-label"
    title = html.escape(kind.label, quote=True)
    return f'<span class="{css}" title="{title}"></span>'


def _highlight_code(code: str, language: str, attrs: str) -> str:
    kind = resolve_fence(language, attrs, code)
    if kind.diagram_source is not None:
        return _label_span(kind) + html.escape(kind.diagram_source)
    lexer_name = kind.lexer
    if not lexer_name and not language:
        try:
            lexer_name = guess_lexer(code).aliases[0] if code.strip() else None
        except ClassNotFound:
            lexer_name = None
    if not lexer_name:
        return _label_span(kind) + html.escape(code)
    try:
        colored = highlight(code, get_lexer_by_name(lexer_name), _formatter("dark"))
    except ClassNotFound:
        colored = html.escape(code)
    return _label_span(kind) + colored


def _source_line_ids(md: MarkdownIt) -> None:
    def add_ids(state) -> None:
        skip = {"tbody_open", "thead_open", "tr_open", "td_open", "th_open"}
        for token in state.tokens:
            if token.map is None or token.type in skip:
                continue
            if token.nesting != 1 and token.type not in {"fence", "hr", "code_block"}:
                continue
            token.attrSet("id", f"src-{token.map[0]}")

    md.core.ruler.push("source_line_ids", add_ids)


_MD = (
    MarkdownIt("commonmark", {"html": False, "highlight": _highlight_code})
    .enable("strikethrough")
    .enable("table")
)
_source_line_ids(_MD)


class PreviewSurface(Protocol):
    code_copied: Signal

    def widget(self) -> QWidget: ...

    def set_html(
        self,
        document: str,
        base_url: QUrl | None = None,
        *,
        keep_scroll: bool = True,
        theme: str = "dark",
    ) -> None: ...

    def scroll_to_heading(self, index: int) -> None: ...

    def scroll_to_source_line(self, line: int) -> None: ...


class CopyCodeBrowser(QTextBrowser):
    code_copied = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("mdPreview")
        self.setOpenExternalLinks(False)
        self.setOpenLinks(False)
        self.setReadOnly(True)
        self.setCursorWidth(0)
        self.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
            | Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        self.anchorClicked.connect(self._on_anchor)
        option = self.document().defaultTextOption()
        option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.document().setDefaultTextOption(option)
        self._cmd_text = _CMD_TEXT
        self._cmd_fill = _CMD_FILL
        self._cmd_border = _CMD_BORDER

    def set_command_colors(self, theme: str) -> None:
        self._cmd_text = _CMD_TEXT
        self._cmd_fill = _CMD_FILL
        self._cmd_border = _CMD_BORDER

    def flatten_command_formats(self) -> None:
        cursor = self.textCursor()
        ranges: list[tuple[int, int]] = []
        block = self.document().begin()
        while block.isValid():
            it = block.begin()
            while not it.atEnd():
                fragment = it.fragment()
                if fragment.charFormat().anchorHref().startswith("mdcopy:"):
                    ranges.append((fragment.position(), fragment.position() + fragment.length()))
                it += 1
            block = block.next()
        for start, end in ranges:
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            fmt = cursor.charFormat()
            fmt.setBackground(QBrush(Qt.BrushStyle.NoBrush))
            fmt.setForeground(QColor(0, 0, 0, 0))
            cursor.setCharFormat(fmt)

    def _on_anchor(self, url: QUrl) -> None:
        if url.scheme() in {"mdcopy", "mdblock"}:
            query = QUrlQuery(url)
            key = query.queryItemValue("id")
            text = _COPY_PAYLOADS.get(key) if key else unquote(query.queryItemValue("t"))
            if text:
                QApplication.clipboard().setText(text)
                self.code_copied.emit(text)
            self._clear_caret()
            return
        if url.scheme() in {"http", "https", "mailto"}:
            QDesktopServices.openUrl(url)

    def _clear_caret(self) -> None:
        bar = self.verticalScrollBar()
        saved = bar.value()
        cursor = self.textCursor()
        cursor.clearSelection()
        self.setTextCursor(cursor)
        self.setExtraSelections([])
        bar.setValue(saved)

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QPainter(self.viewport())
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
            for box, text_rect, text, font in self._command_chips():
                rect = box.toRect()
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(self._cmd_fill)
                painter.drawRect(rect)
                painter.setPen(QPen(self._cmd_border, 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(rect.adjusted(1, 1, -1, -1))
                painter.setPen(self._cmd_text)
                painter.setFont(font)
                painter.drawText(text_rect.toRect(), int(Qt.AlignmentFlag.AlignCenter), text)
        finally:
            painter.end()

    def _chip_rect_ok(self, rect: QRectF) -> bool:
        if rect.width() <= 0 or rect.height() <= 0:
            return False
        viewport = self.viewport().rect()
        if rect.height() > max(viewport.height() * 0.35, 48):
            return False
        if rect.width() > viewport.width() + 24:
            return False
        return True

    def _in_code_table(self, position: int) -> bool:
        cursor = self.textCursor()
        last = max(self.document().characterCount() - 1, 0)
        cursor.setPosition(min(max(position, 0), last))
        table = cursor.currentTable()
        if table is None or table.columns() < 2:
            return False
        return table.cellAt(0, 1).firstCursorPosition().block().text().strip() == "Copiar"

    def _line_cursor_x(self, line, pos_in_block: int) -> float:
        value = line.cursorToX(pos_in_block)
        return float(value[0] if isinstance(value, tuple) else value)

    def _command_line_rects(self, start: int, end: int) -> list[tuple[QRectF, int, int]]:
        if end <= start:
            return []
        doc = self.document()
        engine = doc.documentLayout()
        if engine is None:
            return []
        shift_x = -self.horizontalScrollBar().value()
        shift_y = -self.verticalScrollBar().value()
        rects: list[tuple[QRectF, int, int]] = []
        pos = start
        for _ in range(32):
            if pos >= end:
                break
            block = doc.findBlock(pos)
            if not block.isValid():
                break
            layout = block.layout()
            if layout is None:
                break
            pos_in_block = pos - block.position()
            line = layout.lineForTextPosition(pos_in_block)
            if not line.isValid():
                break
            line_end = line.textStart() + line.textLength()
            frag_end = min(end - block.position(), line_end)
            if frag_end <= pos_in_block:
                pos = block.position() + pos_in_block + 1
                continue
            x1 = self._line_cursor_x(line, pos_in_block)
            x2 = self._line_cursor_x(line, frag_end)
            block_rect = engine.blockBoundingRect(block)
            rect = QRectF(
                block_rect.left() + min(x1, x2) + shift_x,
                block_rect.top() + line.y() + shift_y,
                max(abs(x2 - x1), 1.0),
                max(line.height(), 1.0),
            )
            if self._chip_rect_ok(rect):
                rects.append((rect, pos, block.position() + frag_end))
            pos = block.position() + frag_end
        return rects

    def _range_text(self, start: int, end: int) -> str:
        cursor = self.textCursor()
        last = max(self.document().characterCount() - 1, 0)
        cursor.setPosition(min(max(start, 0), last))
        cursor.setPosition(min(max(end, 0), last), QTextCursor.MoveMode.KeepAnchor)
        return (
            cursor.selectedText()
            .replace("\u2028", "")
            .replace("\u2029", "")
            .replace("\ufffc", "")
        )

    def _command_chips(self) -> list[tuple[QRectF, QRectF, str, QFont]]:
        chips: list[tuple[QRectF, QRectF, str, QFont, str]] = []
        block = self.document().begin()
        while block.isValid():
            it = block.begin()
            while not it.atEnd():
                fragment = it.fragment()
                fmt = fragment.charFormat()
                href = fmt.anchorHref()
                if href.startswith("mdcopy:") and not self._in_code_table(fragment.position()):
                    start = fragment.position()
                    end = start + fragment.length()
                    for text_rect, frag_start, frag_end in self._command_line_rects(start, end):
                        label = self._range_text(frag_start, frag_end)
                        if not label:
                            continue
                        box = text_rect.adjusted(-3, -2, 3, 2)
                        if chips and chips[-1][4] == href:
                            prev_box, prev_text, prev_label, prev_font, _href = chips[-1]
                            same_line = abs(prev_box.center().y() - box.center().y()) < max(
                                prev_box.height(), box.height()
                            ) * 0.6
                            adjacent = prev_box.right() + 6 >= box.left()
                            if same_line and adjacent:
                                merged = prev_text.united(text_rect)
                                if self._chip_rect_ok(merged):
                                    chips[-1] = (
                                        prev_box.united(box),
                                        merged,
                                        prev_label + label,
                                        prev_font,
                                        href,
                                    )
                                    continue
                        chips.append((box, text_rect, label, fmt.font(), href))
                it += 1
            block = block.next()
        return [(box, text_rect, text, font) for box, text_rect, text, font, _href in chips]


class TextBrowserPreview:
    """Preview leve com QTextBrowser — suficiente para a primeira versão."""

    def __init__(self, parent: QWidget | None = None) -> None:
        self._view = CopyCodeBrowser(parent)
        self.code_copied = self._view.code_copied

    def widget(self) -> QWidget:
        return self._view

    def scroll_to_heading(self, index: int) -> None:
        view = self._view
        doc = view.document()
        name = f"toc-{index}"
        target = None
        found = 0
        block = doc.begin()
        while block.isValid():
            names: list[str] = []
            it = block.begin()
            while not it.atEnd():
                names.extend(it.fragment().charFormat().anchorNames())
                it += 1
            is_heading = block.blockFormat().headingLevel() > 0 or name in names
            if is_heading:
                if name in names or found == index:
                    target = block
                    break
                found += 1
            block = block.next()
        if target is None:
            view.scrollToAnchor(name)
            return
        self._scroll_block_into_view(target)

    def scroll_to_source_line(self, line: int) -> None:
        view = self._view
        doc = view.document()
        best_line = -1
        next_line: int | None = None
        target = None
        block = doc.begin()
        while block.isValid():
            names: list[str] = []
            it = block.begin()
            while not it.atEnd():
                names.extend(it.fragment().charFormat().anchorNames())
                it += 1
            for name in names:
                if not name.startswith("src-"):
                    continue
                try:
                    number = int(name[4:])
                except ValueError:
                    continue
                if number <= line and number >= best_line:
                    best_line = number
                    target = block
                elif number > line and (next_line is None or number < next_line):
                    next_line = number
            block = block.next()
        if target is None:
            return
        span = max((next_line - best_line) if next_line is not None else 1, 1)
        frac = 0.0 if span <= 1 else min(max((line - best_line) / span, 0.0), 1.0)
        rect = doc.documentLayout().blockBoundingRect(target)
        y = int(rect.top() + frac * max(rect.height() - 8, 0))
        self._scroll_y_into_view(y)

    def _scroll_block_into_view(self, block) -> None:
        top = int(self._view.document().documentLayout().blockBoundingRect(block).top())
        self._scroll_y_into_view(top)

    def _scroll_y_into_view(self, y: int) -> None:
        view = self._view
        bar = view.verticalScrollBar()
        viewport = view.viewport().height()
        top = bar.value()
        bottom = top + viewport
        if top + 16 <= y <= bottom - 40:
            return
        desired = y - max(viewport // 4, 16)
        bar.setValue(min(max(desired, bar.minimum()), bar.maximum()))

    def set_html(
        self,
        document: str,
        base_url: QUrl | None = None,
        *,
        keep_scroll: bool = True,
        theme: str = "dark",
    ) -> None:
        view = self._view
        view.set_command_colors(theme)
        vbar = view.verticalScrollBar()
        hbar = view.horizontalScrollBar()
        saved = (vbar.value(), hbar.value()) if keep_scroll else (0, 0)
        if base_url is not None and base_url.isLocalFile():
            view.setSearchPaths([base_url.toLocalFile()])
        else:
            view.setSearchPaths([])
        view.setHtml(document)
        view.flatten_command_formats()
        _fit_preview_tables(view)
        _fit_preview_images(view)
        _tighten_image_blocks(view)

        def restore() -> None:
            vbar.setValue(min(saved[0], vbar.maximum()))
            hbar.setValue(min(saved[1], hbar.maximum()))
            _fit_preview_images(view)
            _tighten_image_blocks(view)

        restore()
        QTimer.singleShot(0, restore)


def create_preview(parent: QWidget | None = None) -> PreviewSurface:
    return TextBrowserPreview(parent)


def _plain_code_text(inner: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", inner)).replace("\n", "").strip()


def _plain_block_text(chunk: str) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", "", chunk))
    return text[:-1] if text.endswith("\n") else text


def _pre_inner_html(chunk: str) -> str:
    inner = re.sub(r"^<pre\b[^>]*>", "", chunk, count=1, flags=re.IGNORECASE)
    inner = re.sub(r"</pre>\s*$", "", inner, count=1, flags=re.IGNORECASE)
    inner = re.sub(r"^<code\b[^>]*>", "", inner, count=1, flags=re.IGNORECASE)
    inner = re.sub(r"</code>\s*$", "", inner, count=1, flags=re.IGNORECASE)
    inner = _LABEL_SPAN_RE.sub("", inner, count=1)
    if inner.endswith("\n"):
        inner = inner[:-1]
    return inner.replace("\n", "<br>")


def _chunk_label(chunk: str) -> str:
    match = _LABEL_SPAN_RE.search(chunk)
    if match:
        return html.unescape(match.group(1))
    lang = re.search(r'\blanguage-([^\s"]+)', chunk)
    if lang:
        return html.unescape(lang.group(1))
    return "Código"


def _replace_outer_pre(body: str, replace) -> str:
    lower = body.lower()
    out: list[str] = []
    i = 0
    while i < len(body):
        start = lower.find("<pre", i)
        if start == -1:
            out.append(body[i:])
            break
        out.append(body[i:start])
        pos = body.find(">", start) + 1
        depth = 1
        while depth and pos < len(body):
            nxt_open = lower.find("<pre", pos)
            nxt_close = lower.find("</pre>", pos)
            if nxt_close == -1:
                out.append(body[start:])
                return "".join(out)
            if nxt_open != -1 and nxt_open < nxt_close:
                depth += 1
                pos = nxt_open + 4
            else:
                depth -= 1
                if depth == 0:
                    end = nxt_close + 6
                    out.append(replace(body[start:end]))
                    i = end
                    break
                pos = nxt_close + 6
        else:
            out.append(body[start:])
            break
    return "".join(out)


def wrap_fenced_code_blocks(body: str, accent: str = "#e85d04", theme: str = "dark") -> str:
    """Envolve ```código``` numa caixa com botão Copiar no topo direito."""

    def wrap_chunk(chunk: str) -> str:
        text = _plain_block_text(chunk)
        key = secrets.token_hex(8)
        _COPY_PAYLOADS[key] = text
        href = f"mdblock:?id={key}"
        copy = f'<a href="{href}" class="md-codeblock__copy" style="{_COPY_BTN_STYLE}">Copiar</a>'
        label = html.escape(_chunk_label(chunk))
        diagram = _LABEL_SPAN_RE.search(chunk)
        image = None
        if diagram and "md-diagram" in diagram.group(0):
            image = diagram_image_html(text, theme, _chunk_label(chunk))
        if image:
            body_html = image
        else:
            body_html = _pre_inner_html(chunk)
        src = re.search(r'\sid="(src-\d+)"', chunk)
        anchor = f'<a name="{src.group(1)}"></a>' if src else ""
        return (
            f"{anchor}"
            f'<table class="md-codeblock" width="100%" border="1" bordercolor="{accent}" '
            'cellspacing="0" cellpadding="8" bgcolor="#000000" '
            f'style="background-color:#000000;margin:12px 0;border:2px solid {accent};">'
            "<tr>"
            '<td bgcolor="#000000" style="background-color:#000000;color:#9aa3ad;'
            f'padding:8px 10px;font-size:12px;font-weight:650;">{label}</td>'
            '<td bgcolor="#000000" align="right" style="background-color:#000000;'
            f'padding:8px 10px;">{copy}</td>'
            "</tr>"
            '<tr><td colspan="2" bgcolor="#000000" style="background-color:#000000;'
            'padding:10px 12px 12px 12px;color:#d7efe0;'
            'font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;'
            f'font-size:13px;">{body_html}</td></tr>'
            "</table>"
        )

    return _replace_outer_pre(body, wrap_chunk)


def linkify_inline_code(body: str) -> str:
    """Transforma `comando` em chip verde clicável (copia o texto)."""

    def replace_code(match: re.Match[str]) -> str:
        inner = match.group(1)
        text = _plain_code_text(inner)
        if not text:
            return match.group(0)
        href = "mdcopy:?t=" + quote(text, safe="")
        return f'<a href="{href}" class="md-cmd" style="{_INLINE_CODE_STYLE}">{html.escape(text)}</a>'

    parts: list[str] = []
    for part in _PRE_SPLIT_RE.split(body):
        lowered = part.lower()
        if lowered.startswith("<pre") or 'class="md-codeblock"' in lowered:
            parts.append(part)
        else:
            parts.append(_CODE_RE.sub(replace_code, part))
    return "".join(parts)


_TD_ALIGN_RE = re.compile(
    r"<(t[dh])(\s[^>]*)?\sstyle=\"text-align:(\w+)\"([^>]*)>",
    re.IGNORECASE,
)


def apply_table_align(body: str) -> str:
    """Converte text-align do markdown-it no atributo align, que o Qt respeita."""

    def replace(match: re.Match[str]) -> str:
        tag, before, align, after = match.group(1), match.group(2) or "", match.group(3), match.group(4)
        before = re.sub(r'\sstyle="[^"]*"', "", before)
        after = re.sub(r'\sstyle="[^"]*"', "", after)
        return f'<{tag}{before} align="{align}"{after}>'

    return _TD_ALIGN_RE.sub(replace, body)


def _fit_preview_tables(view: QTextBrowser) -> None:
    def walk(frame) -> None:
        iterator = frame.begin()
        while not iterator.atEnd():
            child = iterator.currentFrame()
            if child is not None:
                if isinstance(child, QTextTable):
                    if child.columns() < 2:
                        copy = ""
                    else:
                        copy = child.cellAt(0, 1).firstCursorPosition().block().text().strip()
                    if copy != "Copiar":
                        fmt = child.format()
                        fmt.setWidth(QTextLength(QTextLength.Type.PercentageLength, 100))
                        cols = child.columns()
                        if cols:
                            share = 100.0 / cols
                            fmt.setColumnWidthConstraints(
                                [QTextLength(QTextLength.Type.PercentageLength, share)] * cols
                            )
                        child.setFormat(fmt)
                else:
                    walk(child)
            iterator += 1

    walk(view.document().rootFrame())


def _fit_preview_images(view: QTextBrowser) -> None:
    """Ajusta largura/altura das imagens para o viewport — o Qt reserva a altura nativa."""
    doc = view.document()
    max_w = max(float(view.viewport().width() - 28), 120.0)
    cursor = QTextCursor(doc)
    block = doc.begin()
    while block.isValid():
        it = block.begin()
        while not it.atEnd():
            fragment = it.fragment()
            fmt = fragment.charFormat()
            if fragment.isValid() and fmt.isImageFormat():
                image = fmt.toImageFormat()
                width = float(image.width())
                height = float(image.height())
                if width <= 0 or height <= 0:
                    name = image.name()
                    if name:
                        size = doc.resource(doc.ResourceType.ImageResource, QUrl(name))
                        if size is not None and hasattr(size, "width"):
                            width = float(size.width()) if width <= 0 else width
                            height = float(size.height()) if height <= 0 else height
                if width > max_w and width > 0 and height > 0:
                    scale = max_w / width
                    image.setWidth(max_w)
                    image.setHeight(height * scale)
                    cursor.setPosition(fragment.position())
                    cursor.setPosition(
                        fragment.position() + fragment.length(),
                        QTextCursor.MoveMode.KeepAnchor,
                    )
                    cursor.setCharFormat(image)
                elif width > 0 and height > 0:
                    # Garante altura explícita para o layout não deixar vão sobrando.
                    image.setWidth(width)
                    image.setHeight(height)
                    cursor.setPosition(fragment.position())
                    cursor.setPosition(
                        fragment.position() + fragment.length(),
                        QTextCursor.MoveMode.KeepAnchor,
                    )
                    cursor.setCharFormat(image)
            it += 1
        block = block.next()


def _tighten_image_blocks(view: QTextBrowser) -> None:
    """Remove margem extra em parágrafos que só têm imagem."""
    doc = view.document()
    block = doc.begin()
    while block.isValid():
        only_image = False
        has_text = False
        it = block.begin()
        while not it.atEnd():
            fragment = it.fragment()
            if not fragment.isValid():
                it += 1
                continue
            if fragment.charFormat().isImageFormat():
                only_image = True
            elif fragment.text().strip():
                has_text = True
            it += 1
        if only_image and not has_text:
            fmt = block.blockFormat()
            fmt.setTopMargin(4)
            fmt.setBottomMargin(4)
            cursor = QTextCursor(block)
            cursor.setBlockFormat(fmt)
        block = block.next()


_IMG_ONLY_P_RE = re.compile(
    r"<p(\b[^>]*)?>\s*(<a\b[^>]*>\s*)?(<img\b[^>]*>)\s*(</a>)?\s*</p>",
    re.IGNORECASE,
)


def mark_image_paragraphs(body: str) -> str:
    def replace(match: re.Match[str]) -> str:
        attrs = match.group(1) or ""
        before = match.group(2) or ""
        img = match.group(3)
        after = match.group(4) or ""
        if "class=" in attrs:
            attrs = re.sub(r'class="([^"]*)"', r'class="\1 md-img"', attrs, count=1)
        else:
            attrs = f'{attrs} class="md-img"'
        return f"<p{attrs}>{before}{img}{after}</p>"

    return _IMG_ONLY_P_RE.sub(replace, body)


def markdown_to_body(source: str, theme: str = "dark") -> str:
    _COPY_PAYLOADS.clear()
    normalized, sizes = normalize_wiki_images(source)
    cleaned = bleach.clean(
        apply_table_align(_MD.render(normalized)),
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=["http", "https", "mailto", "file"],
        strip=True,
    )
    cleaned = mark_image_paragraphs(apply_image_sizes(cleaned, sizes))
    accent = "#e85d04"
    return inject_heading_anchors(
        linkify_inline_code(wrap_fenced_code_blocks(apply_blockquote_callouts(cleaned, theme), accent, theme))
    )


def inject_heading_anchors(body: str) -> str:
    index = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal index
        level = match.group(1)
        inner = match.group(2)
        name = f"toc-{index}"
        index += 1
        return f'<h{level}><a name="{name}"></a>{inner}</h{level}>'

    return _HEADING_HTML_RE.sub(replace, body)


def wrap_preview_html(body: str, theme: str = "dark") -> str:
    if theme == "light":
        bg, fg, heading, muted = "#ffffff", "#1a1a1a", "#111111", "#6e6e6e"
        link, link_hover = "#e85d04", "#ff8a3d"
        code_bg, code_fg = "#111111", "#f5f5f5"
        border = "rgba(17, 17, 17, 0.12)"
        quote_bg = "rgba(232, 93, 4, 0.06)"
        th_bg = "rgba(232, 93, 4, 0.08)"
        heading_rule = "rgba(17, 17, 17, 0.18)"
        quote_border = "rgba(232, 93, 4, 0.85)"
        accent = "#e85d04"
    else:
        bg, fg, heading, muted = "#161412", "#e8e4df", "#fff6ee", "#b8ada3"
        link, link_hover = "#ff8a3d", "#ffc14d"
        code_bg, code_fg = "#070605", "#ffe8d2"
        border = "rgba(255, 106, 26, 0.35)"
        quote_bg = "rgba(255, 106, 26, 0.08)"
        th_bg = "rgba(255, 106, 26, 0.12)"
        heading_rule = "rgba(255, 106, 26, 0.45)"
        quote_border = "rgba(255, 106, 26, 0.65)"
        accent = "#e85d04"
    pygments_css = _formatter(theme).get_style_defs(".highlight")

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  html, body {{
    margin: 0;
    padding: 0;
    background: {bg};
    color: {fg};
    font-family: system-ui, "Segoe UI", sans-serif;
    font-size: 0.9rem;
    line-height: 1.55;
    word-break: break-word;
  }}
  body {{ padding: 4px 6px 24px; }}
  h1, h2, h3, h4, h5, h6 {{
    margin: 1.1em 0 0.45em;
    font-weight: 650;
    letter-spacing: -0.02em;
    color: {heading};
    line-height: 1.25;
  }}
  h1 {{
    font-size: 1.35rem;
    padding-bottom: 0.35em;
    border-bottom: 1px solid {heading_rule};
  }}
  h2 {{
    font-size: 1.15rem;
    padding-bottom: 0.3em;
    border-bottom: 1px solid {border};
  }}
  h3 {{ font-size: 1.02rem; }}
  h4 {{ font-size: 0.95rem; }}
  p {{ margin: 0.55em 0; }}
  ul, ol {{ margin: 0.55em 0; padding-left: 1.35rem; }}
  a {{ color: {link}; text-decoration: underline; text-underline-offset: 2px; }}
  a:hover {{ color: {link_hover}; }}
  hr {{
    margin: 1.1em 0;
    border: none;
    border-top: 1px solid {border};
  }}
  blockquote {{
    margin: 0.75em 0;
    padding: 0.55rem 0.85rem;
    border-left: 3px solid {quote_border};
    color: {muted};
    background: {quote_bg};
    border-radius: 0 0.3rem 0.3rem 0;
  }}
  blockquote.is-info,
  blockquote.is-warning,
  blockquote.is-danger,
  blockquote.is-record {{
    color: {heading};
  }}
  blockquote.is-info {{
    border-left-color: #3d8fd9;
    background: rgba(61, 143, 217, 0.14);
  }}
  blockquote.is-warning {{
    border-left-color: #e09a3e;
    background: rgba(224, 154, 62, 0.14);
  }}
  blockquote.is-danger {{
    border-left-color: #d45454;
    background: rgba(212, 84, 84, 0.14);
  }}
  blockquote.is-record {{
    border-left-color: #9b6dd6;
    background: rgba(155, 109, 214, 0.16);
  }}
  code {{
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 0.84em;
    padding: 0.12em 0.35em;
    border-radius: 0.25rem;
    background: rgba(0, 0, 0, 0.35);
    color: {code_fg};
  }}
  :not(pre) > code,
  a.md-cmd {{
    padding: 0;
    border: none;
    border-radius: 0;
    background: transparent;
    color: transparent;
    text-decoration: none;
    font-weight: 650;
    cursor: pointer;
  }}
  pre {{
    margin: 0;
    padding: 0;
    overflow-x: auto;
    border: none;
    background: transparent;
    color: {code_fg};
  }}
  pre code {{
    padding: 0;
    background: transparent;
    border: none;
    color: inherit;
    font-size: 0.82rem;
  }}
  table.md-codeblock {{
    border: 2px solid {accent};
    border-radius: 0;
    background: #000000;
    margin: 0.75em 0;
  }}
  table.md-codeblock td {{
    border: none;
    background: #000000;
  }}
  a.md-codeblock__copy {{
    color: #c5d0db;
    background: #10151b;
    text-decoration: none;
    font-size: 12px;
    font-weight: 650;
  }}
  table {{
    width: 100%;
    table-layout: fixed;
    margin: 0.75em 0;
    border-collapse: collapse;
    font-size: 0.85rem;
  }}
  th, td {{
    padding: 0.4rem 0.55rem;
    border: 1px solid {border};
    word-wrap: break-word;
    overflow-wrap: anywhere;
  }}
  table.md-codeblock {{
    table-layout: auto;
  }}
  table.md-codeblock td {{
    border: none;
  }}
  th {{ background: {th_bg}; font-weight: 650; }}
  img {{
    max-width: 100%;
    height: auto;
    vertical-align: top;
    margin: 0.2em 0;
    border-radius: 0.35rem;
  }}
  p.md-img {{
    margin: 0.25em 0;
    line-height: 1;
  }}
  strong {{ font-weight: 650; color: {heading}; }}
  {pygments_css}
</style>
</head>
<body>
{body}
</body>
</html>
"""


def render_preview(source: str, theme: str = "dark", base_dir: Path | None = None) -> str:
    body = resolve_local_image_srcs(markdown_to_body(source, theme), base_dir)
    return wrap_preview_html(body, theme)

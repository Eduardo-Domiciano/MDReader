from __future__ import annotations

import html
import re
import secrets
from typing import Protocol
from urllib.parse import quote, unquote

import bleach
from markdown_it import MarkdownIt
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.util import ClassNotFound
from PySide6.QtCore import QRectF, Qt, QUrl, QUrlQuery, Signal
from PySide6.QtGui import (
    QColor,
    QDesktopServices,
    QFont,
    QFontMetrics,
    QPainter,
    QPaintEvent,
    QPen,
    QTextCursor,
)
from PySide6.QtWidgets import QApplication, QTextBrowser, QWidget

from app.callouts import apply_blockquote_callouts

_PRE_SPLIT_RE = re.compile(r"(<pre\b[^>]*>[\s\S]*?</pre>)", re.IGNORECASE)
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
_CMD_TEXT = QColor("#0f1419")
_CMD_FILL = QColor("#3d9d6a")
_CMD_BORDER = QColor("#000000")

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
    "a": ["href", "title"],
    "img": ["src", "alt", "title"],
    "td": ["align"],
    "th": ["align"],
    "code": ["class"],
    "div": ["class"],
    "span": ["class"],
    "pre": ["class"],
    "blockquote": ["class"],
}


def _formatter(theme: str) -> HtmlFormatter:
    style = "native" if theme == "dark" else "default"
    return HtmlFormatter(nowrap=True, cssclass="highlight", style=style)


def _highlight_code(code: str, language: str, _attrs: str) -> str:
    try:
        lexer = get_lexer_by_name(language) if language else guess_lexer(code)
    except ClassNotFound:
        return html.escape(code)
    return highlight(code, lexer, _formatter("dark"))


_MD = (
    MarkdownIt("commonmark", {"html": False, "highlight": _highlight_code})
    .enable("strikethrough")
    .enable("table")
)


class PreviewSurface(Protocol):
    code_copied: Signal

    def widget(self) -> QWidget: ...

    def set_html(self, document: str, base_url: QUrl | None = None) -> None: ...

    def scroll_to_heading(self, index: int) -> None: ...


class CopyCodeBrowser(QTextBrowser):
    code_copied = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("mdPreview")
        self.setOpenExternalLinks(False)
        self.setOpenLinks(False)
        self.setReadOnly(True)
        self.setCursorWidth(0)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse)
        self.anchorClicked.connect(self._on_anchor)

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
        cursor = self.textCursor()
        cursor.clearSelection()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.setTextCursor(cursor)
        self.setExtraSelections([])

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QPainter(self.viewport())
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
            for box, text_rect, text, font in self._command_chips():
                painter.setPen(QPen(_CMD_BORDER, 2))
                painter.setBrush(_CMD_FILL)
                painter.drawRect(box.toRect())
                painter.setPen(_CMD_TEXT)
                painter.setFont(font)
                painter.drawText(text_rect.toRect(), int(Qt.AlignmentFlag.AlignCenter), text)
        finally:
            painter.end()

    def _command_chips(self) -> list[tuple[QRectF, QRectF, str, QFont]]:
        cursor = self.textCursor()
        chips: list[tuple[QRectF, QRectF, str, QFont]] = []
        block = self.document().begin()
        while block.isValid():
            it = block.begin()
            while not it.atEnd():
                fragment = it.fragment()
                fmt = fragment.charFormat()
                if fmt.anchorHref().startswith("mdcopy:"):
                    label = (
                        fragment.text()
                        .replace("\u2028", "")
                        .replace("\u2029", "")
                        .replace("\ufffc", "")
                    )
                    start = fragment.position()
                    after = min(start + fragment.length(), max(self.document().characterCount() - 1, 0))
                    cursor.setPosition(start)
                    left = self.cursorRect(cursor)
                    cursor.setPosition(after)
                    right = self.cursorRect(cursor)
                    text_rect = QRectF(left.united(right))
                    metrics = QFontMetrics(fmt.font())
                    needed_w = metrics.horizontalAdvance(label)
                    needed_h = metrics.height()
                    if text_rect.width() < needed_w:
                        text_rect.setWidth(float(needed_w))
                    if text_rect.height() < needed_h:
                        extra = needed_h - text_rect.height()
                        text_rect.adjust(0, -extra / 2, 0, extra / 2)
                    box = text_rect.adjusted(-3, -2, 3, 2)
                    chips.append((box, text_rect, label, fmt.font()))
                it += 1
            block = block.next()
        return chips


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
        top = int(doc.documentLayout().blockBoundingRect(target).top())
        bar = view.verticalScrollBar()
        bar.setValue(min(max(top - 8, bar.minimum()), bar.maximum()))

    def set_html(self, document: str, base_url: QUrl | None = None) -> None:
        if base_url is not None and base_url.isLocalFile():
            self._view.setSearchPaths([base_url.toLocalFile()])
        else:
            self._view.setSearchPaths([])
        self._view.setHtml(document)


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
    if inner.endswith("\n"):
        inner = inner[:-1]
    return inner.replace("\n", "<br>")


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


def wrap_fenced_code_blocks(body: str) -> str:
    """Envolve ```código``` numa caixa com botão Copiar no topo direito."""

    def wrap_chunk(chunk: str) -> str:
        text = _plain_block_text(chunk)
        key = secrets.token_hex(8)
        _COPY_PAYLOADS[key] = text
        href = f"mdblock:?id={key}"
        copy = f'<a href="{href}" class="md-codeblock__copy" style="{_COPY_BTN_STYLE}">Copiar</a>'
        body_html = _pre_inner_html(chunk)
        return (
            '<table class="md-codeblock" width="100%" border="1" bordercolor="#3d9d6a" '
            'cellspacing="0" cellpadding="8" bgcolor="#000000" '
            'style="background-color:#000000;margin:12px 0;border:2px solid #3d9d6a;">'
            "<tr>"
            '<td bgcolor="#000000" style="background-color:#000000;color:#9aa3ad;'
            'padding:8px 10px;font-size:12px;font-weight:650;">Código</td>'
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
        if part.lower().startswith("<pre"):
            parts.append(part)
        else:
            parts.append(_CODE_RE.sub(replace_code, part))
    return "".join(parts)


def markdown_to_body(source: str) -> str:
    _COPY_PAYLOADS.clear()
    cleaned = bleach.clean(
        _MD.render(source),
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=["http", "https", "mailto"],
        strip=True,
    )
    return inject_heading_anchors(
        linkify_inline_code(wrap_fenced_code_blocks(apply_blockquote_callouts(cleaned)))
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
    dark = theme == "dark"
    bg = "#1a1f26" if dark else "#f7f9f8"
    fg = "#d5dde6" if dark else "#2a3036"
    heading = "#e8ecf0" if dark else "#14191f"
    muted = "#c5d0db" if dark else "#4a5560"
    link = "#7dcea0" if dark else "#2f8a58"
    link_hover = "#a8e0c0" if dark else "#3d9d6a"
    code_bg = "#07090c" if dark else "#eef2ef"
    code_fg = "#d7efe0" if dark else "#14191f"
    border = "rgba(61, 157, 106, 0.28)"
    quote_bg = "rgba(0, 0, 0, 0.2)" if dark else "rgba(61, 157, 106, 0.08)"
    th_bg = "rgba(61, 157, 106, 0.12)"
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
    border-bottom: 1px solid rgba(61, 157, 106, 0.35);
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
    border-left: 3px solid rgba(61, 157, 106, 0.55);
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
    border: 2px solid #3d9d6a;
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
    margin: 0.75em 0;
    border-collapse: collapse;
    font-size: 0.85rem;
  }}
  th, td {{
    padding: 0.4rem 0.55rem;
    border: 1px solid {border};
    text-align: left;
  }}
  table.md-codeblock td {{
    border: none;
  }}
  th {{ background: {th_bg}; font-weight: 650; }}
  img {{ max-width: 100%; height: auto; border-radius: 0.35rem; }}
  strong {{ font-weight: 650; color: {heading}; }}
  {pygments_css}
</style>
</head>
<body>
{body}
</body>
</html>
"""


def render_preview(source: str, theme: str = "dark") -> str:
    return wrap_preview_html(markdown_to_body(source), theme)

from __future__ import annotations

import re

CALLOUT_KINDS = ("info", "warning", "danger", "record")
CALLOUT_LABELS = {
    "info": "Info",
    "warning": "Warning",
    "danger": "Danger",
    "record": "Record",
}
CALLOUT_DOTS = {
    "info": "#3d8fd9",
    "warning": "#e09a3e",
    "danger": "#d45454",
    "record": "#9b6dd6",
}
CALLOUT_INLINE_STYLE = {
    "info": "border-left: 3px solid #3d8fd9; background-color: rgba(61, 143, 217, 0.14); color: #e8ecf0;",
    "warning": "border-left: 3px solid #e09a3e; background-color: rgba(224, 154, 62, 0.14); color: #e8ecf0;",
    "danger": "border-left: 3px solid #d45454; background-color: rgba(212, 84, 84, 0.14); color: #e8ecf0;",
    "record": "border-left: 3px solid #9b6dd6; background-color: rgba(155, 109, 214, 0.16); color: #e8ecf0;",
}

_KIND_GROUP = "info|warning|danger|record"
CALLOUT_FENCE_RE = re.compile(
    rf"^\s*(?:>\s*)?\{{\s*\.?(?:is[.-])?({_KIND_GROUP})\s*\}}\s*$",
    re.IGNORECASE,
)
CALLOUT_HTML_RE = re.compile(
    rf"\{{\s*\.?(?:is[.-])?({_KIND_GROUP})\s*\}}",
    re.IGNORECASE,
)
_AFTER_BLOCK_RE = re.compile(
    rf"(<blockquote\b[^>]*>[\s\S]*?</blockquote>)\s*<p>\s*(\{{\s*\.?(?:is[.-])?(?:{_KIND_GROUP})\s*\}})\s*</p>",
    re.IGNORECASE,
)
_FENCE_FIRST_P_RE = re.compile(
    rf"<blockquote(\b[^>]*)>\s*<p>\s*(\{{\s*\.?(?:is[.-])?(?:{_KIND_GROUP})\s*\}})\s*</p>",
    re.IGNORECASE,
)
_FENCE_IN_P_RE = re.compile(
    rf"<blockquote(\b[^>]*)>\s*<p>\s*(\{{\s*\.?(?:is[.-])?(?:{_KIND_GROUP})\s*\}})\s*(?:<br\s*/?>|\s+)",
    re.IGNORECASE,
)


def callout_fence(kind: str) -> str:
    return f"{{.is-{kind}}}"


def is_callout_fence_line(line: str) -> bool:
    return bool(CALLOUT_FENCE_RE.match(line))


def parse_callout_kind(value: str) -> str | None:
    match = CALLOUT_FENCE_RE.match(value) or CALLOUT_HTML_RE.search(value.strip())
    if not match:
        return None
    kind = match.group(1).lower()
    return kind if kind in CALLOUT_KINDS else None


def _line_bounds(text: str, pos: int) -> tuple[int, int]:
    start = text.rfind("\n", 0, max(0, pos)) + 1
    end = text.find("\n", pos)
    if end == -1:
        end = len(text)
    return start, end


def expand_callout_range(text: str, start: int, end: int) -> tuple[int, int]:
    caret = max(0, start)
    from_, _ = _line_bounds(text, caret)
    sel_end = max(caret, end - (1 if end > start else 0))
    _, to = _line_bounds(text, sel_end)
    first_end = _line_bounds(text, from_)[1]
    first_line = text[from_:first_end]

    if is_callout_fence_line(first_line) and not first_line.startswith(">"):
        while from_ > 0:
            prev_s, prev_e = _line_bounds(text, from_ - 1)
            if not text[prev_s:prev_e].startswith(">"):
                break
            from_ = prev_s
        return from_, to

    while from_ > 0:
        prev_s, prev_e = _line_bounds(text, from_ - 1)
        if not text[prev_s:prev_e].startswith(">"):
            break
        from_ = prev_s

    while to < len(text):
        next_s, next_e = _line_bounds(text, min(to + 1, len(text) - 1))
        next_line = text[next_s:next_e]
        if next_line.startswith(">"):
            to = next_e
            continue
        if is_callout_fence_line(next_line):
            to = next_e
        break
    return from_, to


def _with_callout_class(open_tag: str, kind: str) -> str:
    cls = f"is-{kind}"
    if re.search(r"\bclass\s*=", open_tag, re.IGNORECASE):
        def _replace(match: re.Match[str]) -> str:
            quote = match.group(1)
            parts = [p for p in match.group(2).split() if not re.match(r"^is-(info|warning|danger|record)$", p)]
            if cls not in parts:
                parts.append(cls)
            return f"class={quote}{' '.join(parts)}{quote}"

        open_tag = re.sub(r"class=(['\"])([^'\"]*)\1", _replace, open_tag, count=1, flags=re.IGNORECASE)
    else:
        open_tag = re.sub(r"<blockquote\b", f'<blockquote class="{cls}"', open_tag, count=1, flags=re.IGNORECASE)
    style = CALLOUT_INLINE_STYLE[kind]
    if re.search(r"\bstyle\s*=", open_tag, re.IGNORECASE):
        return open_tag
    return re.sub(r"<blockquote\b", f'<blockquote style="{style}"', open_tag, count=1, flags=re.IGNORECASE)


def apply_blockquote_callouts(html: str) -> str:
    def after_block(match: re.Match[str]) -> str:
        kind = parse_callout_kind(match.group(2))
        if not kind:
            return match.group(0)
        return re.sub(
            r"<blockquote\b[^>]*>",
            lambda tag: _with_callout_class(tag.group(0), kind),
            match.group(1),
            count=1,
            flags=re.IGNORECASE,
        )

    def fence_first(match: re.Match[str]) -> str:
        kind = parse_callout_kind(match.group(2))
        if not kind:
            return match.group(0)
        return _with_callout_class(f"<blockquote{match.group(1)}>", kind)

    def fence_in_p(match: re.Match[str]) -> str:
        kind = parse_callout_kind(match.group(2))
        if not kind:
            return match.group(0)
        return f"{_with_callout_class(f'<blockquote{match.group(1)}>', kind)}<p>"

    out = _AFTER_BLOCK_RE.sub(after_block, html)
    out = _FENCE_FIRST_P_RE.sub(fence_first, out)
    return _FENCE_IN_P_RE.sub(fence_in_p, out)

"""Nomes de linguagem dos blocos e desenho de diagramas Mermaid."""

from __future__ import annotations

import hashlib
import html
import re
import tempfile
import warnings
from dataclasses import dataclass
from pathlib import Path

_CODE_LANGS: dict[str, tuple[str, str]] = {
    "bash": ("bash", "Bash"),
    "sh": ("bash", "Bash"),
    "shell": ("bash", "Bash"),
    "python": ("python", "Python"),
    "py": ("python", "Python"),
    "html": ("html", "HTML"),
    "http": ("http", "HTTP"),
    "node.js": ("javascript", "Node.js"),
    "nodejs": ("javascript", "Node.js"),
    "node": ("javascript", "Node.js"),
    "node js": ("javascript", "Node.js"),
    "javascript": ("javascript", "JavaScript"),
    "js": ("javascript", "JavaScript"),
    "typescript": ("typescript", "TypeScript"),
    "ts": ("typescript", "TypeScript"),
    "type script": ("typescript", "TypeScript"),
    "go": ("go", "Go"),
    "golang": ("go", "Go"),
}

_DIAGRAM_PREAMBLE: dict[str, str] = {
    "mermaid": "",
    "mermeide": "",
    "erdiagram": "erDiagram",
    "erdiagrama": "erDiagram",
    "er diagrama": "erDiagram",
    "sequencediagram": "sequenceDiagram",
    "sequencediagrama": "sequenceDiagram",
    "sequence diagrama": "sequenceDiagram",
    "sequence diagram": "sequenceDiagram",
}

_FLOW_RE = re.compile(r"^flowchart(?:\s+([a-z]{2}))?$")
_DIAGRAM_LINE_RE = re.compile(
    r"^(?:erdiagram|erdiagrama|sequencediagram|sequencediagrama|flowchart(?:\s+[a-z]{2})?|graph(?:\s+[a-z]{2})?)\b",
    re.IGNORECASE,
)
_FLOW_DIRS = {"TD", "TB", "LR", "RL", "BT"}
_ATTR_COLUMN = {
    "attribute-type": 0,
    "attribute-name": 1,
    "attribute-keys": 2,
    "attribute-comment": 3,
}
_LINE_PX = 20.0


@dataclass(frozen=True)
class FenceKind:
    lexer: str | None = None
    label: str | None = None
    diagram_source: str | None = None


def fence_info_key(language: str, attrs: str) -> str:
    raw = f"{language} {attrs}".strip().lower().replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", raw)


def _first_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _with_preamble(code: str, preamble: str) -> str:
    body = code.strip("\n")
    if not preamble:
        return body
    first = _first_line(body).lower()
    head = preamble.split()[0].lower()
    if first.startswith(head):
        return body
    if head == "flowchart" and first.startswith("graph"):
        return body
    return f"{preamble}\n{body}" if body else preamble


def _diagram_preamble(key: str) -> str | None:
    if key in _DIAGRAM_PREAMBLE:
        return _DIAGRAM_PREAMBLE[key]
    match = _FLOW_RE.match(key)
    if not match:
        return None
    direction = (match.group(1) or "td").upper()
    if direction not in _FLOW_DIRS:
        direction = "TD"
    return f"flowchart {direction}"


def resolve_fence(language: str, attrs: str, code: str) -> FenceKind:
    key = fence_info_key(language, attrs)
    preamble = _diagram_preamble(key)
    if preamble is not None:
        return FenceKind(label="Mermaid", diagram_source=_with_preamble(code, preamble))
    if key in _CODE_LANGS:
        lexer, label = _CODE_LANGS[key]
        return FenceKind(lexer=lexer, label=label)
    if not key and _DIAGRAM_LINE_RE.match(_first_line(code)):
        return FenceKind(label="Mermaid", diagram_source=code.strip("\n"))
    if language:
        return FenceKind(lexer=language, label=language)
    return FenceKind()


def render_diagram_png(source: str, theme: str) -> Path | None:
    """Desenha o diagrama e devolve o PNG em cache. None se o fonte não renderizar."""
    text = source.strip()
    if not text:
        return None
    dark = theme != "light"
    mermaid_theme = "dark" if dark else "default"
    background = "#161412" if dark else "#ffffff"
    label_fill = "#ffe8d2" if dark else "#1a1a1a"
    digest = hashlib.sha256(
        f"v7\n{mermaid_theme}\n{background}\n{label_fill}\n{text}".encode()
    ).hexdigest()
    folder = Path(tempfile.gettempdir()) / "mdreader-diagrams"
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / f"{digest}.png"
    if dest.is_file() and dest.stat().st_size > 0:
        return dest
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning, module=r"mmdc(\.|$)")
            import mmdc
            from mmdc.raster import render_png

            svg = mmdc.render(text, theme=mermaid_theme).svg()
            fitted, width = _fit_diagram_svg(svg, label_fill)
            scale = min(max(1100 / max(width, 1), 1.5), 8)
            png = render_png(fitted, scale=scale, background=background)
    except Exception:
        return None
    if not png:
        return None
    tmp = dest.with_suffix(".tmp")
    tmp.write_bytes(png)
    tmp.replace(dest)
    return dest


def _fit_diagram_svg(svg: str, label_fill: str) -> tuple[str, float]:
    """Inclui o desenho inteiro no quadro e põe os rótulos por cima das caixas."""
    from xml.etree import ElementTree as ET

    namespace = "http://www.w3.org/2000/svg"

    def tag(name: str) -> str:
        return f"{{{namespace}}}{name}"

    root = ET.fromstring(svg)
    holders = list(root.iter())
    for parent in holders:
        labels = [
            child
            for child in list(parent)
            if child.tag == tag("g") and "label" in child.attrib.get("class", "")
        ]
        for label in labels:
            parent.remove(label)
            parent.append(label)
    for parent in list(root.iter()):
        edges = [
            child
            for child in list(parent)
            if child.tag == tag("g") and "edgeLabels" in child.attrib.get("class", "").split()
        ]
        for edge in edges:
            parent.remove(edge)
            parent.append(edge)
    parents = {child: parent for parent in root.iter() for child in list(parent)}
    for text in list(root.iter(tag("text"))):
        lines = _wrapped_lines(text, tag)
        if lines:
            _place_wrapped_text(text, lines, parents, tag, label_fill)

    bounds = [1e9, 1e9, -1e9, -1e9]
    inside_defs = set()
    for defs in root.iter(tag("defs")):
        inside_defs.update(defs.iter())

    def add(x: float, y: float) -> None:
        bounds[0] = min(bounds[0], x)
        bounds[1] = min(bounds[1], y)
        bounds[2] = max(bounds[2], x)
        bounds[3] = max(bounds[3], y)

    def walk(el: ET.Element, tx: float, ty: float) -> None:
        match = re.search(
            r"translate\(\s*([-\d.]+)(?:[,\s]+([-\d.]+))?\s*\)",
            el.attrib.get("transform", ""),
        )
        if match:
            tx += float(match.group(1))
            ty += float(match.group(2) or 0)
        name = el.tag.split("}")[-1]
        if name == "rect":
            width = float(el.attrib.get("width") or 0)
            height = float(el.attrib.get("height") or 0)
            if width > 1 and height > 1:
                x = float(el.attrib.get("x") or 0)
                y = float(el.attrib.get("y") or 0)
                add(tx + x, ty + y)
                add(tx + x + width, ty + y + height)
        elif name == "polygon":
            nums = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", el.attrib.get("points", ""))]
            for index in range(0, len(nums) - 1, 2):
                add(tx + nums[index], ty + nums[index + 1])
        elif name in {"circle", "ellipse"}:
            cx = float(el.attrib.get("cx") or 0)
            cy = float(el.attrib.get("cy") or 0)
            radius = float(el.attrib.get("r") or el.attrib.get("rx") or 6)
            add(tx + cx - radius, ty + cy - radius)
            add(tx + cx + radius, ty + cy + radius)
        elif name == "path" and el not in inside_defs:
            nums = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", el.attrib.get("d", ""))]
            for index in range(0, len(nums) - 1, 2):
                add(tx + nums[index], ty + nums[index + 1])
        for child in list(el):
            walk(child, tx, ty)

    walk(root, 0, 0)
    if bounds[0] > bounds[2]:
        return svg, 320
    pad = 32
    x, y, x2, y2 = bounds
    width = x2 - x + 2 * pad
    height = y2 - y + 2 * pad
    root.set("viewBox", f"{x - pad:.2f} {y - pad:.2f} {width:.2f} {height:.2f}")
    root.set("width", f"{width:.0f}")
    root.set("height", f"{height:.0f}")
    root.attrib.pop("style", None)
    return ET.tostring(root, encoding="unicode"), width


def _wrapped_lines(text, tag) -> list[str] | None:
    """Linhas de um rótulo Mermaid. None se o texto já está em pixels."""
    from xml.etree import ElementTree as ET

    outers = [
        child
        for child in list(text)
        if child.tag == tag("tspan") and "text-outer-tspan" in child.attrib.get("class", "").split()
    ]
    if not outers:
        return None
    if re.search(r"-?\d+(?:\.\d+)?em\b", ET.tostring(text, encoding="unicode")) is None:
        return None
    lines: list[str] = []
    for outer in outers:
        words: list[str] = []
        for inner in outer.iter(tag("tspan")):
            if inner is outer:
                continue
            words.extend((inner.text or "").split())
        if not words:
            words.extend((outer.text or "").split())
        line = " ".join(words).strip()
        if line:
            lines.append(line)
    return lines


def _place_wrapped_text(text, lines: list[str], parents: dict, tag, label_fill: str) -> None:
    """Uma frase por linha, dentro da caixa. No ER, cada coluna no seu lugar."""
    from xml.etree import ElementTree as ET

    label = _ancestor_with_class(text, parents, "label")
    classes = label.attrib.get("class", "").split() if label is not None else []
    node = _ancestor_with_class(text, parents, "node")
    column = next((index for name, index in _ATTR_COLUMN.items() if name in classes), None)
    anchor = "middle"
    anchor_x = 0.0
    text_y = -(len(lines) - 1) * _LINE_PX / 2
    if column is not None and node is not None:
        center = _column_center(node, column, tag)
        if center is not None:
            anchor_x = center
    else:
        background = _sized_rect(label, tag) if label is not None else None
        box = _sized_rect(node, tag, "label-container") if node is not None else None
        if background is not None:
            x, y, width, height = background
            anchor = "middle"
            anchor_x = x + width / 2
            text_y = y + height / 2 - (len(lines) - 1) * _LINE_PX / 2
        elif box is not None and label is not None:
            _, y, _, height = box
            text_y = (y + height / 2) - _translate(label)[1] - (len(lines) - 1) * _LINE_PX / 2
        elif "name" in classes and node is not None and label is not None:
            header = _header_center_y(node, tag)
            if header is not None:
                _set_translate(label, 0.0, header)
    for child in list(text):
        text.remove(child)
    text.text = None
    text.set("y", f"{text_y:.2f}")
    text.set("text-anchor", anchor)
    text.set("fill", label_fill)
    previous = text.attrib.get("style", "").strip().strip(";")
    extra = f"text-anchor:{anchor};dominant-baseline:middle;fill:{label_fill}"
    text.set("style", f"{previous};{extra}" if previous else extra)
    for index, line in enumerate(lines):
        span = ET.Element(tag("tspan"))
        span.text = line
        span.set("x", f"{anchor_x:.2f}")
        span.set("dy", "0" if index == 0 else f"{_LINE_PX:.2f}")
        text.append(span)


def _ancestor_with_class(el, parents: dict, token: str):
    node = parents.get(el)
    while node is not None:
        classes = node.attrib.get("class", "").split()
        if token == "node" and "node" in classes and "nodes" not in classes:
            return node
        if token != "node" and token in classes:
            return node
        node = parents.get(node)
    return None


def _translate(el) -> tuple[float, float]:
    match = re.search(
        r"translate\(\s*([-\d.]+)(?:[,\s]+([-\d.]+))?\s*\)",
        el.attrib.get("transform", ""),
    )
    if not match:
        return 0.0, 0.0
    return float(match.group(1)), float(match.group(2) or 0)


def _set_translate(el, x: float, y: float) -> None:
    raw = el.attrib.get("transform", "")
    match = re.search(r"translate\(\s*[-\d.]+(?:[,\s]+[-\d.]+)?\s*\)", raw)
    replacement = f"translate({x:.2f}, {y:.2f})"
    if match:
        el.attrib["transform"] = raw[: match.start()] + replacement + raw[match.end() :]
    else:
        el.attrib["transform"] = replacement


def _sized_rect(root, tag, class_name: str | None = None) -> tuple[float, float, float, float] | None:
    if root is None:
        return None
    best = None
    for el in root.iter(tag("rect")):
        if class_name and class_name not in el.attrib.get("class", "").split():
            continue
        width = float(el.attrib.get("width") or 0)
        height = float(el.attrib.get("height") or 0)
        if width <= 1 or height <= 1:
            continue
        area = width * height
        if best is None or area > best[0]:
            x = float(el.attrib.get("x") or 0)
            y = float(el.attrib.get("y") or 0)
            best = (area, x, y, width, height)
    if best is None:
        return None
    return best[1:]


def _header_center_y(node, tag) -> float | None:
    outline = None
    for path in node.iter(tag("path")):
        nums = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", path.attrib.get("d", ""))]
        if len(nums) < 4:
            continue
        px, py = nums[0::2], nums[1::2]
        width, height = max(px) - min(px), max(py) - min(py)
        if width < 20 or height < 20:
            continue
        area = width * height
        if outline is None or area > outline[0]:
            outline = (area, min(py), max(py), width)
    if outline is None:
        return None
    _, top, bottom, width = outline
    seams = []
    for group in node.iter(tag("g")):
        if "divider" not in group.attrib.get("class", "").split():
            continue
        for path in group.iter(tag("path")):
            nums = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", path.attrib.get("d", ""))]
            if len(nums) < 4:
                continue
            px, py = nums[0::2], nums[1::2]
            if max(py) - min(py) < 2 and max(px) - min(px) > width * 0.5:
                seams.append(sum(py) / len(py))
    below = [y for y in seams if y > top + 4]
    if not below:
        return (top + bottom) / 2
    return (top + min(below)) / 2


def _column_center(node, column: int, tag) -> float | None:
    xs: list[float] = []
    for el in node.iter(tag("path")):
        nums = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", el.attrib.get("d", ""))]
        xs.extend(nums[0::2])
    for el in node.iter(tag("rect")):
        width = float(el.attrib.get("width") or 0)
        if width > 1:
            x = float(el.attrib.get("x") or 0)
            xs.extend((x, x + width))
    if len(xs) < 2:
        return None
    left, right = min(xs), max(xs)
    cuts: list[float] = []
    for group in node.iter(tag("g")):
        if "divider" not in group.attrib.get("class", "").split():
            continue
        for path in group.iter(tag("path")):
            nums = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", path.attrib.get("d", ""))]
            if len(nums) < 4:
                continue
            px, py = nums[0::2], nums[1::2]
            if max(px) - min(px) < 2 and max(py) - min(py) > 8:
                cuts.append(sum(px) / len(px))
    edges = [left, *[x for x in sorted(cuts) if left + 4 < x < right - 4], right]
    index = min(column, len(edges) - 2)
    return (edges[index] + edges[index + 1]) / 2


def diagram_image_html(source: str, theme: str, label: str) -> str | None:
    path = render_diagram_png(source, theme)
    if path is None:
        return None
    src = html.escape(path.as_posix(), quote=True)
    alt = html.escape(label, quote=True)
    return f'<img src="{src}" alt="{alt}">'

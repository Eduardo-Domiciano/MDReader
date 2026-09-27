from __future__ import annotations

import html
import re
import shutil
import sys
from pathlib import Path

_FENCE_RE = re.compile(r"^(```+|~~~+)")
_WIKI_IMG_RE = re.compile(
    r"!\[([^\]]*)\]\("
    r"(<(?:[^>\\]|\\.)+>|[^)\s]+)"
    r'(?:\s+"([^"]*)")?'
    r"\s+(=[0-9.%]*x[0-9.%]*)"
    r"\)"
)
_SIZE_RE = re.compile(r"^=([0-9.]+%?)?x([0-9.]+%?)?$")
_IMG_TAG_RE = re.compile(r"<img\b([^>]*?)(/?)>", re.IGNORECASE)
_SRC_RE = re.compile(r'\bsrc="([^"]*)"', re.IGNORECASE)
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"}
IMAGES_FOLDER = "img"


def is_image_path(path: str | Path) -> bool:
    return Path(path).suffix.lower() in IMAGE_SUFFIXES


def markdown_image_dest(source: str) -> str:
    if re.search(r"[\s()]", source):
        return f"<{source}>"
    return source


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def images_dir() -> Path:
    folder = app_root() / IMAGES_FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def stored_image_ref(path: Path) -> str:
    return f"{IMAGES_FOLDER}/{path.name}"


def store_image(source: Path) -> Path:
    """Copia a imagem para a pasta do executável e devolve o arquivo guardado."""
    original = source.expanduser().resolve()
    dest_dir = images_dir()
    try:
        original.relative_to(dest_dir)
        return original
    except ValueError:
        pass
    target = dest_dir / original.name
    stem, suffix = original.stem, original.suffix
    index = 2
    while target.exists():
        if target.resolve() == original:
            return target
        target = dest_dir / f"{stem}-{index}{suffix}"
        index += 1
    shutil.copy2(original, target)
    return target


def relative_image_path(image: Path, document: Path | None) -> str:
    resolved = image.expanduser().resolve()
    try:
        return resolved.relative_to(app_root()).as_posix()
    except ValueError:
        pass
    if document is not None:
        try:
            return resolved.relative_to(document.parent.resolve()).as_posix()
        except ValueError:
            pass
    return resolved.as_posix()


def _unwrap_dest(dest: str) -> str:
    if dest.startswith("<") and dest.endswith(">"):
        return dest[1:-1]
    return dest


def parse_wiki_size(token: str) -> tuple[str | None, str | None]:
    match = _SIZE_RE.match(token)
    if not match:
        return None, None
    return match.group(1), match.group(2)


def _rewrite_line(line: str, sizes: list[tuple[str, str | None, str | None]]) -> str:
    def replace(match: re.Match[str]) -> str:
        alt, dest, title, size = match.group(1), match.group(2), match.group(3), match.group(4)
        width, height = parse_wiki_size(size)
        if width or height:
            sizes.append((_unwrap_dest(dest), width, height))
        if title:
            return f'![{alt}]({dest} "{title}")'
        return f"![{alt}]({dest})"

    parts: list[str] = []
    for part in re.split(r"(`+[^`]*`+)", line):
        if part.startswith("`"):
            parts.append(part)
        else:
            parts.append(_WIKI_IMG_RE.sub(replace, part))
    return "".join(parts)


def normalize_wiki_images(source: str) -> tuple[str, list[tuple[str, str | None, str | None]]]:
    """Converte `![alt](src =100x50)` em Markdown comum e guarda os tamanhos."""
    lines = source.splitlines(keepends=True)
    sizes: list[tuple[str, str | None, str | None]] = []
    out: list[str] = []
    in_fence = False
    fence_char = ""
    for line in lines:
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
            out.append(line)
            continue
        out.append(line if in_fence else _rewrite_line(line, sizes))
    return "".join(out), sizes


def apply_image_sizes(body: str, sizes: list[tuple[str, str | None, str | None]]) -> str:
    pending = list(sizes)

    def replace(match: re.Match[str]) -> str:
        nonlocal pending
        attrs = match.group(1)
        closing = match.group(2)
        src_match = _SRC_RE.search(attrs)
        if not src_match or not pending:
            return match.group(0)
        src = html.unescape(src_match.group(1))
        expected, width, height = pending[0]
        if src != expected:
            return match.group(0)
        pending.pop(0)
        extra: list[str] = []
        if width:
            extra.append(f'width="{html.escape(width, quote=True)}"')
        if height:
            extra.append(f'height="{html.escape(height, quote=True)}"')
        if not extra:
            return match.group(0)
        spacer = "" if attrs.endswith(" ") or not attrs else " "
        return f"<img{attrs}{spacer}{' '.join(extra)}{closing}>"

    return _IMG_TAG_RE.sub(replace, body)


def resolve_local_image_srcs(body: str, base_dir: Path | None) -> str:
    def replace(match: re.Match[str]) -> str:
        attrs = match.group(1)
        closing = match.group(2)
        src_match = _SRC_RE.search(attrs)
        if not src_match:
            return match.group(0)
        src = html.unescape(src_match.group(1))
        if src.startswith(("http://", "https://", "data:", "file:")):
            return match.group(0)
        path = Path(src).expanduser()
        if not path.is_absolute():
            candidates = [app_root() / path, images_dir() / path.name]
            if base_dir is not None:
                candidates.append(base_dir / path)
            path = next((item for item in candidates if item.is_file()), path)
        if not path.is_file():
            return match.group(0)
        url = path.resolve().as_uri()
        new_attrs = _SRC_RE.sub(f'src="{html.escape(url, quote=True)}"', attrs, count=1)
        return f"<img{new_attrs}{closing}>"

    return _IMG_TAG_RE.sub(replace, body)

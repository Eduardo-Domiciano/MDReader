from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

MD_SUFFIXES = {".md", ".markdown", ".mdown"}
_MAX_DEPTH = 8
_ARROW_CLOSED = "▸"
_ARROW_OPEN = "▾"
_NAME_ROLE = Qt.ItemDataRole.UserRole + 1
_IS_DIR_ROLE = Qt.ItemDataRole.UserRole + 2


def is_markdown(path: Path) -> bool:
    return path.suffix.lower() in MD_SUFFIXES


def _dir_has_markdown(path: Path, depth: int = 0) -> bool:
    if depth > _MAX_DEPTH:
        return False
    try:
        entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except OSError:
        return False
    for entry in entries:
        if entry.name.startswith("."):
            continue
        if entry.is_file() and is_markdown(entry):
            return True
        if entry.is_dir() and _dir_has_markdown(entry, depth + 1):
            return True
    return False


def _folder_label(name: str, expanded: bool) -> str:
    arrow = _ARROW_OPEN if expanded else _ARROW_CLOSED
    return f"{arrow}  {name}"


class FilesRail(QWidget):
    file_activated = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("filesRail")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        self.setMinimumWidth(160)
        self.setMaximumWidth(360)
        self._root: Path | None = None
        self._selected: Path | None = None

        self._title = QLabel("ARQUIVOS")
        self._title.setObjectName("filesTitle")

        self._collapse_all = QToolButton()
        self._collapse_all.setObjectName("filesToggle")
        self._collapse_all.setText("▴")
        self._collapse_all.setToolTip("Fechar todas as pastas")
        self._collapse_all.setAutoRaise(True)
        self._collapse_all.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._collapse_all.clicked.connect(self.collapse_all)

        self._expand_all = QToolButton()
        self._expand_all.setObjectName("filesToggle")
        self._expand_all.setText("▾")
        self._expand_all.setToolTip("Abrir todas as pastas")
        self._expand_all.setAutoRaise(True)
        self._expand_all.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._expand_all.clicked.connect(self.expand_all)

        header = QWidget()
        header.setObjectName("filesHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(4, 4, 4, 0)
        header_layout.setSpacing(0)
        header_layout.addWidget(self._title, 1)
        header_layout.addWidget(self._collapse_all)
        header_layout.addWidget(self._expand_all)

        self._folder = QLabel("")
        self._folder.setObjectName("filesFolder")
        self._folder.setWordWrap(True)

        self._empty = QLabel("Nenhum Markdown nesta pasta")
        self._empty.setObjectName("filesEmpty")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self._tree = QTreeWidget()
        self._tree.setObjectName("filesTree")
        self._tree.setHeaderHidden(True)
        self._tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._tree.setRootIsDecorated(False)
        self._tree.setAnimated(True)
        self._tree.setUniformRowHeights(True)
        self._tree.setIndentation(14)
        self._tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._tree.setTextElideMode(Qt.TextElideMode.ElideRight)
        self._tree.itemClicked.connect(self._on_item)
        self._tree.itemExpanded.connect(self._on_expand_change)
        self._tree.itemCollapsed.connect(self._on_expand_change)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(header)
        layout.addWidget(self._folder)
        layout.addWidget(self._empty)
        layout.addWidget(self._tree, 1)
        self.hide()

    def root(self) -> Path | None:
        return self._root

    def set_root(self, path: Path | None) -> None:
        self._root = path.resolve() if path is not None else None
        if self._root is None:
            self._folder.clear()
            self._tree.clear()
            self._empty.hide()
            self._tree.hide()
            self.hide()
            return
        self._folder.setText(self._root.name)
        self._folder.setToolTip(str(self._root))
        self.show()
        self.refresh()

    def watched_dirs(self) -> list[str]:
        if self._root is None or not self._root.is_dir():
            return []
        dirs = [str(self._root)]
        for item in self._tree.findItems("", Qt.MatchFlag.MatchContains | Qt.MatchFlag.MatchRecursive):
            path = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(path, Path) and path.is_dir():
                dirs.append(str(path))
        return dirs

    def refresh(self) -> None:
        selected = self._selected
        expanded: set[str] = set()
        for item in self._tree.findItems("", Qt.MatchFlag.MatchContains | Qt.MatchFlag.MatchRecursive):
            path = item.data(0, Qt.ItemDataRole.UserRole)
            if item.isExpanded() and isinstance(path, Path):
                expanded.add(str(path.resolve()))
        self._tree.clear()
        if self._root is None or not self._root.is_dir():
            self._empty.setText("Pasta inacessível")
            self._empty.show()
            self._tree.hide()
            return
        count = self._fill(self._tree.invisibleRootItem(), self._root, 0)
        if count == 0:
            self._empty.setText("Nenhum Markdown nesta pasta")
            self._empty.show()
            self._tree.hide()
            return
        self._empty.hide()
        self._tree.show()
        for item in self._tree.findItems("", Qt.MatchFlag.MatchContains | Qt.MatchFlag.MatchRecursive):
            path = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(path, Path) and str(path.resolve()) in expanded:
                item.setExpanded(True)
                self._sync_folder_label(item)
        if selected is not None:
            self.select_path(selected)

    def select_path(self, path: Path | None) -> None:
        self._selected = path.resolve() if path is not None else None
        self._tree.clearSelection()
        if self._selected is None:
            return
        target = str(self._selected)
        for item in self._tree.findItems("", Qt.MatchFlag.MatchContains | Qt.MatchFlag.MatchRecursive):
            value = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(value, Path) and str(value.resolve()) == target:
                self._tree.setCurrentItem(item)
                parent = item.parent()
                while parent is not None:
                    parent.setExpanded(True)
                    self._sync_folder_label(parent)
                    parent = parent.parent()
                return

    def expand_all(self) -> None:
        self._tree.blockSignals(True)
        try:
            for item in self._folder_items():
                item.setExpanded(True)
                self._sync_folder_label(item)
        finally:
            self._tree.blockSignals(False)

    def collapse_all(self) -> None:
        self._tree.blockSignals(True)
        try:
            for item in self._folder_items():
                item.setExpanded(False)
                self._sync_folder_label(item)
        finally:
            self._tree.blockSignals(False)

    def _folder_items(self) -> list[QTreeWidgetItem]:
        items: list[QTreeWidgetItem] = []
        for item in self._tree.findItems("", Qt.MatchFlag.MatchContains | Qt.MatchFlag.MatchRecursive):
            if item.data(0, _IS_DIR_ROLE):
                items.append(item)
        return items

    def _make_folder_item(self, name: str, path: Path) -> QTreeWidgetItem:
        item = QTreeWidgetItem([_folder_label(name, False)])
        item.setData(0, Qt.ItemDataRole.UserRole, path.resolve())
        item.setData(0, _NAME_ROLE, name)
        item.setData(0, _IS_DIR_ROLE, True)
        item.setToolTip(0, str(path))
        font = QFont(item.font(0))
        font.setBold(True)
        item.setFont(0, font)
        item.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
        return item

    def _make_file_item(self, name: str, path: Path) -> QTreeWidgetItem:
        item = QTreeWidgetItem([name])
        item.setData(0, Qt.ItemDataRole.UserRole, path.resolve())
        item.setData(0, _NAME_ROLE, name)
        item.setData(0, _IS_DIR_ROLE, False)
        item.setToolTip(0, str(path))
        item.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.DontShowIndicator)
        return item

    def _sync_folder_label(self, item: QTreeWidgetItem) -> None:
        if not item.data(0, _IS_DIR_ROLE):
            return
        name = item.data(0, _NAME_ROLE)
        if not isinstance(name, str):
            return
        item.setText(0, _folder_label(name, item.isExpanded()))

    def _on_expand_change(self, item: QTreeWidgetItem) -> None:
        self._sync_folder_label(item)

    def _fill(self, parent: QTreeWidgetItem, folder: Path, depth: int) -> int:
        if depth > _MAX_DEPTH:
            return 0
        try:
            entries = sorted(folder.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError:
            return 0
        count = 0
        for entry in entries:
            if entry.name.startswith("."):
                continue
            if entry.is_dir():
                if not _dir_has_markdown(entry, depth + 1):
                    continue
                item = self._make_folder_item(entry.name, entry)
                parent.addChild(item)
                child_count = self._fill(item, entry, depth + 1)
                if child_count == 0:
                    parent.removeChild(item)
                else:
                    count += child_count
                    item.setExpanded(False)
                    self._sync_folder_label(item)
            elif entry.is_file() and is_markdown(entry):
                parent.addChild(self._make_file_item(entry.name, entry))
                count += 1
        return count

    def _on_item(self, item: QTreeWidgetItem, _column: int) -> None:
        if item.data(0, _IS_DIR_ROLE):
            item.setExpanded(not item.isExpanded())
            self._sync_folder_label(item)
            return
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(path, Path) and path.is_file():
            self.file_activated.emit(path)

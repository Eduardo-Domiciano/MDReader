from __future__ import annotations

from pathlib import Path
import time

from PySide6.QtCore import QEvent, QFileSystemWatcher, QPoint, QTimer, Qt, QUrl
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence, QMouseEvent, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.chrome import FormatToolbar, InsertRail, StatusBar, TitleBar
from app.icon import app_icon
from app.editor import MarkdownEditor
from app.images import relative_image_path, store_image
from app.outline import OutlineRail, extract_headings
from app.preview import create_preview, render_preview
from app.theme import apply_theme, configure_app

WELCOME_MARKDOWN = """# MDReader

Escreva Markdown à esquerda e veja o resultado à direita.

## Títulos

# Título 1
## Título 2
### Título 3
#### Título 4
##### Título 5

## Formatação

Texto em **negrito**, em *itálico* e ~~rasurado~~.

## Ligação e código

Uma [ligação](https://example.com) e um comando inline: `ls -la`.

## Imagem

Escolha um arquivo no botão da barra esquerda, ou arraste a imagem para o editor.

```markdown
![legenda](arquivo.png)
![legenda](arquivo.png =240x)
![legenda](arquivo.png =100%x)
```

```python
print("olá, markdown")
```

## Avisos

> Informação útil para o leitor.

{.is-info}

> Atenção: verifique antes de continuar.

{.is-warning}

> Perigo: esta ação não pode ser desfeita.

{.is-danger}

> Anotação para consulta posterior.

{.is-record}

## Atalhos

- **Ctrl+N** — novo arquivo
- **Ctrl+O** — abrir
- **Ctrl+S** — salvar
- **Ctrl+B** — negrito
- **Ctrl+I** — itálico
"""

PREVIEW_DEBOUNCE_MS = 200


class MainWindow(QMainWindow):
    _RESIZE_MARGIN = 6

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowMinMaxButtonsHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowIcon(app_icon())
        self.setMouseTracking(True)
        self.resize(1280, 700)
        self._path: Path | None = None
        self._dirty = False
        self._theme = "dark"
        self._updating = False
        self._external_change = False
        self._ignore_watch_until = 0.0
        self._watcher = QFileSystemWatcher(self)
        self._watcher.fileChanged.connect(self._on_disk_changed)

        self.editor = MarkdownEditor()
        self.preview = create_preview()
        self.outline = OutlineRail()
        self.outline.heading_activated.connect(self._go_to_heading)
        self.status = StatusBar()

        toolbar = FormatToolbar(self.editor)
        toolbar.preview_toggled.connect(self.set_preview_visible)
        rail = InsertRail(self.editor)
        rail.image_requested.connect(self._pick_image)
        rail.reload_requested.connect(self.reload_file)
        self.editor.image_dropped.connect(self._insert_image_file)

        self.preview_pane = QSplitter(Qt.Orientation.Horizontal)
        self.preview_pane.setObjectName("previewPane")
        self.preview_pane.addWidget(self.preview.widget())
        self.preview_pane.addWidget(self.outline)
        self.preview_pane.setSizes([420, 200])
        self.preview_pane.setStretchFactor(0, 1)
        self.preview_pane.setStretchFactor(1, 0)
        self.preview_pane.setChildrenCollapsible(False)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.editor)
        self.splitter.addWidget(self.preview_pane)
        self.splitter.setSizes([550, 620])
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setChildrenCollapsible(False)
        self._preview_sizes = [550, 620]

        main_row = QWidget()
        main_row.setObjectName("workspace")
        row_layout = QHBoxLayout(main_row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(0)
        row_layout.addWidget(rail)
        row_layout.addWidget(self.splitter, 1)

        root = QWidget()
        root.setObjectName("workspace")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(toolbar)
        root_layout.addWidget(main_row, 1)
        root_layout.addWidget(self.status)
        self.setCentralWidget(root)

        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(PREVIEW_DEBOUNCE_MS)
        self._preview_timer.timeout.connect(self._refresh_preview)

        self.editor.textChanged.connect(self._on_text_changed)
        self.editor.cursorPositionChanged.connect(self._update_status)
        self.editor.cursorPositionChanged.connect(self._sync_preview_to_editor)
        self.preview.code_copied.connect(lambda: self.status.flash("Copiado"))
        QShortcut(QKeySequence.StandardKey.Bold, self, self._bold)
        QShortcut(QKeySequence.StandardKey.Italic, self, self._italic)

        self._build_menus()
        self.title_bar = TitleBar(self)
        header = QWidget()
        header.setObjectName("titleHeader")
        header.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)
        header_layout.addWidget(self.title_bar)
        header_layout.addWidget(self.menuBar())
        self.setMenuWidget(header)
        apply_theme(self, self._theme)
        self._set_editor_text(WELCOME_MARKDOWN, dirty=False)
        self._refresh_preview()
        self._update_title()
        self._update_status()

    def set_preview_visible(self, visible: bool) -> None:
        pane = self.preview_pane
        if visible:
            pane.show()
            self.splitter.setSizes(self._preview_sizes or [550, 620])
            self._refresh_preview()
        else:
            self._preview_sizes = self.splitter.sizes()
            pane.hide()

    def _go_to_heading(self, index: int, line: int) -> None:
        self.preview.scroll_to_heading(index)
        self.editor.go_to_line(line)

    def _bold(self) -> None:
        self.editor.wrap_markup("**", placeholder="negrito")

    def _italic(self) -> None:
        self.editor.wrap_markup("*", placeholder="itálico")

    def _build_menus(self) -> None:
        arquivo = self.menuBar().addMenu("&Arquivo")
        arquivo.addAction(self._action("&Novo", self.new_file, QKeySequence.StandardKey.New))
        arquivo.addAction(self._action("&Abrir…", self.open_file, QKeySequence.StandardKey.Open))
        arquivo.addAction(self._action("&Salvar", self.save_file, QKeySequence.StandardKey.Save))
        arquivo.addAction(
            self._action("Salvar &como…", self.save_file_as, QKeySequence.StandardKey.SaveAs)
        )
        arquivo.addSeparator()
        arquivo.addAction(self._action("&Sair", self.close, QKeySequence.StandardKey.Quit))

        visualizar = self.menuBar().addMenu("&Visualizar")
        visualizar.addAction(self._action("Tema &escuro", lambda: self.set_theme("dark")))
        visualizar.addAction(self._action("Tema &claro", lambda: self.set_theme("light")))

    def _action(self, text: str, slot, shortcut=None) -> QAction:
        action = QAction(text, self)
        if shortcut is not None:
            action.setShortcut(shortcut)
        action.triggered.connect(slot)
        return action

    def _on_text_changed(self) -> None:
        if self._updating:
            return
        if not self._dirty:
            self._dirty = True
            self._update_title()
        self._preview_timer.start()
        self._update_status()

    def _update_status(self) -> None:
        line, col = self.editor.cursor_line_col()
        self.status.set_cursor(line, col)

    def _refresh_preview(self, *, keep_scroll: bool = True) -> None:
        source = self.editor.toPlainText()
        base_dir = self._path.parent if self._path is not None else None
        html = render_preview(source, self._theme, base_dir)
        base = None
        if self._path is not None:
            base = QUrl.fromLocalFile(str(self._path.parent) + "/")
        self.preview.set_html(html, base, keep_scroll=keep_scroll, theme=self._theme)
        self.outline.set_headings(extract_headings(source))
        if keep_scroll:
            QTimer.singleShot(0, self._sync_preview_to_editor)

    def _sync_preview_to_editor(self) -> None:
        if self._updating or not self.preview_pane.isVisible():
            return
        self.preview.scroll_to_source_line(self.editor.textCursor().blockNumber())

    def _pick_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Inserir imagem",
            str(self._path.parent) if self._path else "",
            "Imagens (*.png *.jpg *.jpeg *.gif *.webp *.bmp *.svg);;Todos os arquivos (*)",
        )
        if path:
            self._insert_image_file(path)

    def _insert_image_file(self, path: str) -> None:
        try:
            stored = store_image(Path(path))
        except OSError as exc:
            QMessageBox.critical(self, "Erro ao guardar imagem", str(exc))
            return
        self.editor.insert_image(relative_image_path(stored, self._path))

    def set_theme(self, theme: str) -> None:
        self._theme = theme
        apply_theme(self, theme)
        self._refresh_preview()

    def _set_editor_text(self, text: str, *, dirty: bool) -> None:
        self._updating = True
        self.editor.setPlainText(text)
        self._updating = False
        self._dirty = dirty
        self._update_title()
        self._update_status()

    def _update_title(self) -> None:
        name = self._path.name if self._path else "Sem título"
        mark = "*" if self._dirty else ""
        title = f"{mark}{name} — MDReader"
        self.setWindowTitle(title)
        if hasattr(self, "title_bar"):
            self.title_bar.set_title(title)

    def _confirm_discard(self) -> bool:
        if not self._dirty:
            return True
        answer = QMessageBox.question(
            self,
            "Alterações não salvas",
            "Deseja salvar as alterações?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if answer == QMessageBox.StandardButton.Cancel:
            return False
        if answer == QMessageBox.StandardButton.Save:
            return self.save_file()
        return True

    def _watch_file(self, path: Path | None) -> None:
        for existing in list(self._watcher.files()):
            self._watcher.removePath(existing)
        self._external_change = False
        if path is not None and path.is_file():
            self._watcher.addPath(str(path))

    def _on_disk_changed(self, changed: str) -> None:
        target = Path(changed)
        if time.monotonic() < self._ignore_watch_until:
            if target.is_file() and changed not in self._watcher.files():
                self._watcher.addPath(changed)
            return
        if self._path is None or target.resolve() != self._path.resolve():
            return
        try:
            disk = target.read_text(encoding="utf-8")
        except OSError:
            self.status.flash("Arquivo inacessível no disco")
            return
        if disk == self.editor.toPlainText():
            if changed not in self._watcher.files() and target.is_file():
                self._watcher.addPath(changed)
            return
        self._external_change = True
        if self._dirty:
            self.status.flash("Arquivo mudou no disco. Recarregar (R) perde as alterações locais", 4500)
        else:
            self.status.flash("Arquivo mudou no disco. Clique em (R) para recarregar", 4500)
        if changed not in self._watcher.files() and target.is_file():
            self._watcher.addPath(changed)

    def reload_file(self) -> None:
        if self._path is None:
            self.status.flash("Nenhum arquivo aberto")
            return
        if not self._path.is_file():
            QMessageBox.warning(self, "Recarregar", "O arquivo não existe mais no disco.")
            return
        if self._dirty:
            answer = QMessageBox.warning(
                self,
                "Recarregar arquivo",
                "Há alterações locais. Se recarregar, elas serão perdidas.\n\nDeseja recarregar do disco?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        try:
            text = self._path.read_text(encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, "Erro ao recarregar", str(exc))
            return
        self._set_editor_text(text, dirty=False)
        self._external_change = False
        self._watch_file(self._path)
        self._refresh_preview()
        self.status.flash("Arquivo recarregado")

    def new_file(self) -> None:
        if not self._confirm_discard():
            return
        self._path = None
        self._watch_file(None)
        self._set_editor_text("", dirty=False)
        self._refresh_preview(keep_scroll=False)

    def open_file(self) -> None:
        if not self._confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir Markdown",
            str(self._path.parent) if self._path else "",
            "Markdown (*.md *.markdown *.mdown);;Todos os arquivos (*)",
        )
        if not path:
            return
        opened = Path(path)
        try:
            text = opened.read_text(encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, "Erro ao abrir", str(exc))
            return
        self._path = opened
        self._watch_file(opened)
        self._set_editor_text(text, dirty=False)
        self._refresh_preview(keep_scroll=False)

    def save_file(self) -> bool:
        if self._path is None:
            return self.save_file_as()
        return self._write_to(self._path)

    def save_file_as(self) -> bool:
        suggested = str(self._path) if self._path else "sem-titulo.md"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar Markdown",
            suggested,
            "Markdown (*.md *.markdown);;Todos os arquivos (*)",
        )
        if not path:
            return False
        target = Path(path)
        if target.suffix == "":
            target = target.with_suffix(".md")
        if self._write_to(target):
            self._path = target
            self._watch_file(target)
            self._update_title()
            self._refresh_preview()
            return True
        return False

    def _write_to(self, path: Path) -> bool:
        self._ignore_watch_until = time.monotonic() + 1.0
        try:
            path.write_text(self.editor.toPlainText(), encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, "Erro ao salvar", str(exc))
            return False
        self._dirty = False
        self._external_change = False
        self._watch_file(path)
        self._update_title()
        return True

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._confirm_discard():
            event.accept()
        else:
            event.ignore()

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange and hasattr(self, "title_bar"):
            self.title_bar.sync_max_button()

    def eventFilter(self, watched, event: QEvent) -> bool:
        if isinstance(watched, QWidget) and watched.window() is self:
            if self._handle_frame_mouse(watched, event):
                return True
        return super().eventFilter(watched, event)

    def _edges_at(self, pos: QPoint) -> Qt.Edges:
        rect = self.rect()
        margin = self._RESIZE_MARGIN
        edges = Qt.Edges()
        if pos.x() <= margin:
            edges |= Qt.Edge.LeftEdge
        if pos.x() >= rect.width() - margin:
            edges |= Qt.Edge.RightEdge
        if pos.y() <= margin:
            edges |= Qt.Edge.TopEdge
        if pos.y() >= rect.height() - margin:
            edges |= Qt.Edge.BottomEdge
        return edges

    def _handle_frame_mouse(self, watched: QWidget, event: QEvent) -> bool:
        if self.isMaximized() or not isinstance(event, QMouseEvent):
            return False
        if isinstance(watched, QToolButton) and watched.objectName().startswith("title"):
            return False
        pos = self.mapFromGlobal(event.globalPosition().toPoint())
        edges = self._edges_at(pos)
        if event.type() == QEvent.Type.MouseMove:
            self._update_resize_cursor(edges)
            return False
        if (
            event.type() == QEvent.Type.MouseButtonPress
            and event.button() == Qt.MouseButton.LeftButton
            and edges
        ):
            handle = self.windowHandle()
            if handle is not None:
                handle.startSystemResize(edges)
                return True
        return False

    def _update_resize_cursor(self, edges: Qt.Edges) -> None:
        if not edges:
            self.unsetCursor()
            return
        left = bool(edges & Qt.Edge.LeftEdge)
        right = bool(edges & Qt.Edge.RightEdge)
        top = bool(edges & Qt.Edge.TopEdge)
        bottom = bool(edges & Qt.Edge.BottomEdge)
        if (left and top) or (right and bottom):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif (right and top) or (left and bottom):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif left or right:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        else:
            self.setCursor(Qt.CursorShape.SizeVerCursor)


def run() -> None:
    import sys

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("MDReader")
    app.setDesktopFileName("mdreader")
    icon = app_icon()
    app.setWindowIcon(icon)
    configure_app(app)
    window = MainWindow()
    window.show()
    window.setWindowIcon(icon)
    app.installEventFilter(window)
    sys.exit(app.exec())

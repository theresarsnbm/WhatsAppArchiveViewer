from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QInputDialog,
    QLabel,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.archive import ChatEntry, list_chats
from app.importer import import_chat_export
from app.parser import Message, parse_chat_file
from app.settings import (
    get_archive_root,
    get_own_names,
    set_archive_root,
    set_own_names,
)
from app.ui.message_delegate import MessageDelegate
from app.ui.message_model import MessageListModel


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("WhatsApp Archive Viewer")
        self.resize(1200, 760)

        self._entries: list[ChatEntry] = []
        self._current_entry: ChatEntry | None = None
        self._model: MessageListModel | None = None
        self._parsed_cache: dict[
            tuple[Path, tuple[str, ...]], tuple[float, list[Message]]
        ] = {}

        self.chat_list = QListWidget()
        self.chat_list.currentItemChanged.connect(self._on_chat_selected)

        self.header_label = QLabel("Kein Chat ausgewählt")
        self.header_label.setObjectName("chatHeader")
        self.header_label.setWordWrap(True)

        self.message_view = QListView()
        self.message_view.setObjectName("messageView")
        self.message_view.setUniformItemSizes(False)
        self.message_view.setVerticalScrollMode(
            QListView.ScrollMode.ScrollPerPixel
        )
        self.message_view.setSelectionMode(
            QListView.SelectionMode.NoSelection
        )
        self.message_view.setWordWrap(False)
        self.message_view.setSpacing(0)
        self.message_view.clicked.connect(self._on_message_clicked)

        self._delegate = MessageDelegate(self.message_view)
        self.message_view.setItemDelegate(self._delegate)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(8)
        right_layout.addWidget(self.header_label)
        right_layout.addWidget(self.message_view, 1)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.chat_list)
        splitter.addWidget(right_panel)
        splitter.setSizes([280, 920])
        splitter.setChildrenCollapsible(False)

        self.setCentralWidget(splitter)

        self._create_actions()
        self._create_menus()
        self._create_toolbar()
        self.statusBar().showMessage("Bereit")

        self.refresh_chats()

    # ------------------------------------------------------------ Aufbau

    def _create_actions(self) -> None:
        self.import_action = QAction("Chat importieren…", self)
        self.import_action.setShortcut("Ctrl+O")
        self.import_action.triggered.connect(self.import_chat)

        self.refresh_action = QAction("Aktualisieren", self)
        self.refresh_action.setShortcut("F5")
        self.refresh_action.triggered.connect(self.refresh_chats)

        self.own_name_action = QAction("Eigene Namen festlegen…", self)
        self.own_name_action.triggered.connect(self.change_own_names)

        self.change_archive_action = QAction("Archivordner ändern…", self)
        self.change_archive_action.triggered.connect(self.change_archive_root)

        self.quit_action = QAction("Beenden", self)
        self.quit_action.setShortcut("Ctrl+Q")
        self.quit_action.triggered.connect(self.close)

    def _create_menus(self) -> None:
        file_menu = self.menuBar().addMenu("Datei")
        file_menu.addAction(self.import_action)
        file_menu.addSeparator()
        file_menu.addAction(self.own_name_action)
        file_menu.addAction(self.change_archive_action)
        file_menu.addSeparator()
        file_menu.addAction(self.quit_action)

        view_menu = self.menuBar().addMenu("Ansicht")
        view_menu.addAction(self.refresh_action)

    def _create_toolbar(self) -> None:
        toolbar = self.addToolBar("Aktionen")
        toolbar.setMovable(False)
        toolbar.addAction(self.import_action)
        toolbar.addAction(self.refresh_action)

    # ------------------------------------------------------------ Daten

    def refresh_chats(self) -> None:
        self._entries = list_chats()
        self.chat_list.clear()

        for entry in self._entries:
            item = QListWidgetItem(entry.name)
            item.setToolTip(
                f"{entry.version_count} Version(en) · "
                f"{entry.media_count} Medien\n{entry.folder}"
            )
            item.setData(Qt.ItemDataRole.UserRole, entry)
            self.chat_list.addItem(item)

        self.statusBar().showMessage(
            f"{len(self._entries)} Chat(s) in {get_archive_root()}"
        )

        if not self._entries:
            self.header_label.setText(
                "Noch keine Chats im Archiv.\n"
                "Klicke oben auf „Chat importieren…“."
            )
            self.message_view.setModel(None)

    def _on_chat_selected(
        self,
        current: QListWidgetItem | None,
        previous: QListWidgetItem | None = None,
    ) -> None:
        if current is None:
            return

        self.show_chat(current.data(Qt.ItemDataRole.UserRole))

    def show_chat(self, entry: ChatEntry) -> None:
        self._current_entry = entry
        display_file = entry.display_file

        if display_file is None:
            self.header_label.setText(f"{entry.name}\nKeine Textdatei gefunden.")
            self.message_view.setModel(None)
            return

        own_names = tuple(get_own_names())
        messages = self.load_messages(display_file, own_names)

        self.header_label.setText(
            f"{entry.name}\n"
            f"{entry.version_count} Version(en) · {entry.media_count} Medien · "
            f"{display_file.name}"
        )

        self._model = MessageListModel(messages, self.message_view)
        self._delegate.clear_cache()
        self.message_view.setModel(self._model)
        QTimer.singleShot(0, self.message_view.scrollToBottom)

        self.statusBar().showMessage(
            f"{entry.name}: {len(messages)} Nachrichten · "
            f"eigene Namen: {', '.join(own_names)}",
            6000,
        )

    def load_messages(
        self,
        chat_file: Path,
        own_names: tuple[str, ...],
    ) -> list[Message]:
        try:
            mtime = chat_file.stat().st_mtime
        except OSError:
            mtime = 0.0

        key = (chat_file, own_names)
        cached = self._parsed_cache.get(key)
        if cached is not None and cached[0] == mtime:
            return cached[1]

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            messages = parse_chat_file(chat_file, own_names=list(own_names))
        except Exception as error:
            messages = []
            self.statusBar().showMessage(f"Fehler beim Lesen: {error}", 8000)
        finally:
            QApplication.restoreOverrideCursor()

        self._parsed_cache[key] = (mtime, messages)
        return messages

    # ------------------------------------------------------------ Aktionen

    def change_own_names(self) -> None:
        current = ", ".join(get_own_names())

        text, accepted = QInputDialog.getText(
            self,
            "Eigene Namen",
            "Schreibweisen deiner eigenen Nachrichten,\n"
            "durch Komma getrennt:",
            text=current,
        )

        if not accepted:
            return

        names = [part.strip() for part in text.split(",") if part.strip()]

        try:
            set_own_names(names)
        except ValueError as error:
            QMessageBox.warning(self, "Eigene Namen", str(error))
            return

        self._parsed_cache.clear()

        if self._current_entry is not None:
            self.show_chat(self._current_entry)

    def _on_message_clicked(self, index) -> None:
        if not index.isValid():
            return

        message = index.data(MessageListModel.MessageRole)
        if message is None or not message.attachments:
            return

        for attachment in message.attachments:
            if attachment.exists:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(attachment.path)))
                return

        QMessageBox.information(
            self,
            "Datei nicht gefunden",
            "Die Anhänge dieser Nachricht liegen nicht im Media-Ordner.",
        )

    def change_archive_root(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self,
            "Neuen Archivordner auswählen",
            str(get_archive_root().parent),
        )

        if not selected:
            return

        try:
            new_root = set_archive_root(Path(selected))
        except (ValueError, OSError) as error:
            QMessageBox.critical(self, "Archivordner", str(error))
            return

        self._parsed_cache.clear()
        self.refresh_chats()

        QMessageBox.information(
            self,
            "Archivordner geändert",
            f"Neuer Archivordner:\n{new_root}\n\n"
            "Vorhandene Chats werden nicht verschoben.",
        )

    def import_chat(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self,
            "Entpackten WhatsApp-Export-Ordner auswählen",
            str(Path.home() / "Downloads"),
        )

        if not selected:
            return

        chat_name, accepted = QInputDialog.getText(
            self, "Chat importieren", "Name des Chats:"
        )

        if not accepted or not chat_name.strip():
            return

        try:
            result = import_chat_export(Path(selected), chat_name.strip())
        except Exception as error:
            QMessageBox.critical(self, "Import fehlgeschlagen", str(error))
            return

        self._parsed_cache.clear()
        self.refresh_chats()
        self._select_chat(result.chat_dir)

        message = (
            f"Chat-Ordner:\n{result.chat_dir}\n\n"
            f"Neue Textdatei: {result.imported_file.name}\n"
            f"Versionen: {result.version_count}"
        )

        if result.merge_result is not None:
            message += (
                f"\n\nMerge: {result.merged_file.name}\n"
                f"Eindeutige Nachrichten: {result.merge_result.unique_messages}\n"
                f"Duplikate entfernt: {result.merge_result.duplicates_removed}"
            )

        QMessageBox.information(self, "Import abgeschlossen", message)

    def _select_chat(self, folder: Path) -> None:
        for index in range(self.chat_list.count()):
            item = self.chat_list.item(index)
            entry: ChatEntry = item.data(Qt.ItemDataRole.UserRole)

            if entry.folder == folder:
                self.chat_list.setCurrentItem(item)
                return
from __future__ import annotations

from datetime import date

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt

from app.parser import Message


class MessageListModel(QAbstractListModel):
    MessageRole = Qt.ItemDataRole.UserRole + 1
    DayHeaderRole = Qt.ItemDataRole.UserRole + 2

    def __init__(self, messages: list[Message] | None = None, parent=None) -> None:
        super().__init__(parent)
        self._messages: list[Message] = []
        self._day_headers: list[date | None] = []
        self.set_messages(messages or [])

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._messages)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        row = index.row()
        message = self._messages[row]

        if role == self.MessageRole:
            return message
        if role == self.DayHeaderRole:
            return self._day_headers[row]
        if role == Qt.ItemDataRole.DisplayRole:
            return message.text
        if role == Qt.ItemDataRole.ToolTipRole:
            return f"{message.sender} · {message.timestamp:%d.%m.%y %H:%M}"

        return None

    def set_messages(self, messages: list[Message]) -> None:
        self.beginResetModel()
        self._messages = list(messages)
        self._day_headers = self._compute_day_headers(self._messages)
        self.endResetModel()

    @staticmethod
    def _compute_day_headers(messages: list[Message]) -> list[date | None]:
        headers: list[date | None] = []
        previous: date | None = None

        for message in messages:
            current = message.timestamp.date()
            headers.append(current if current != previous else None)
            previous = current

        return headers

    def message_at(self, row: int) -> Message | None:
        if 0 <= row < len(self._messages):
            return self._messages[row]
        return None

    @property
    def messages(self) -> list[Message]:
        return self._messages
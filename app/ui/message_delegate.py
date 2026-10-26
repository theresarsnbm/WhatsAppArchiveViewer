from __future__ import annotations

from datetime import date
from functools import lru_cache

from PySide6.QtCore import QModelIndex, QRect, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPixmap
from PySide6.QtWidgets import QStyleOptionViewItem, QStyledItemDelegate

from app.ui import theme
from app.ui.message_model import MessageListModel

THUMB_HEIGHT = 170
MEDIA_LINE_HEIGHT = 17
TIME_HEIGHT = 16
NAME_HEIGHT = 16
DAY_HEIGHT = 34

WEEKDAYS = (
    "Montag", "Dienstag", "Mittwoch", "Donnerstag",
    "Freitag", "Samstag", "Sonntag",
)


@lru_cache(maxsize=256)
def load_thumbnail(path: str, width: int) -> QPixmap | None:
    pixmap = QPixmap(path)
    if pixmap.isNull():
        return None

    return pixmap.scaled(
        width,
        THUMB_HEIGHT,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def format_day(day: date) -> str:
    return f"{WEEKDAYS[day.weekday()]}, {day:%d.%m.%Y}"


def split_attachments(message):
    images = [
        a for a in message.attachments if a.kind == "image" and a.exists
    ]
    others = [
        a for a in message.attachments if a.kind != "image" or not a.exists
    ]
    return images, others


class MessageDelegate(QStyledItemDelegate):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._height_cache: dict[tuple[int, int], int] = {}

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        message = index.data(MessageListModel.MessageRole)
        if message is None:
            return QSize(0, 0)

        width = self._bubble_width(option)
        key = (index.row(), width)
        height = self._height_cache.get(key)

        if height is None:
            has_day = index.data(MessageListModel.DayHeaderRole) is not None
            height = self._calculate_height(message, width, option.font, has_day)
            self._height_cache[key] = height

        return QSize(width + 2 * theme.ROW_MARGIN_X, height)

    def clear_cache(self) -> None:
        self._height_cache.clear()

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        message = index.data(MessageListModel.MessageRole)
        if message is None:
            return

        own = message.is_own_message
        day = index.data(MessageListModel.DayHeaderRole)
        width = self._bubble_width(option)
        meta_color = theme.COLOR_META_OWN if own else theme.COLOR_META

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        top = option.rect.top() + theme.ROW_MARGIN_Y

        if day is not None:
            self._paint_day_header(painter, option, day)
            top += DAY_HEIGHT

        left = (
            option.rect.right() - theme.ROW_MARGIN_X - width
            if own
            else option.rect.left() + theme.ROW_MARGIN_X
        )
        bubble_height = (
            option.rect.height() - 2 * theme.ROW_MARGIN_Y
            - (DAY_HEIGHT if day else 0)
        )
        bubble = QRect(left, top, width, bubble_height)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(theme.COLOR_OWN if own else theme.COLOR_OTHER)
        painter.drawRoundedRect(QRectF(bubble), theme.BUBBLE_RADIUS, theme.BUBBLE_RADIUS)

        inner = bubble.adjusted(
            theme.BUBBLE_PADDING_X,
            theme.BUBBLE_PADDING_Y,
            -theme.BUBBLE_PADDING_X,
            -theme.BUBBLE_PADDING_Y,
        )

        y = inner.top()

        if not own:
            painter.setPen(meta_color)
            painter.setFont(self._small_font(option.font, bold=True))
            painter.drawText(
                QRect(inner.left(), y, inner.width(), NAME_HEIGHT),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                message.sender,
            )
            y += NAME_HEIGHT

        y += self._paint_media(painter, option, inner, message, y, meta_color)

        text_bottom = inner.bottom() - TIME_HEIGHT

        if message.text and text_bottom > y:
            painter.setPen(theme.TEXT_OWN if own else theme.TEXT_OTHER)
            painter.setFont(QFont(option.font))
            painter.drawText(
                QRect(inner.left(), y, inner.width(), text_bottom - y),
                Qt.AlignmentFlag.AlignLeft
                | Qt.AlignmentFlag.AlignTop
                | Qt.TextFlag.TextWordWrap,
                message.text,
            )

        painter.setPen(meta_color)
        painter.setFont(self._small_font(option.font))
        painter.drawText(
            QRect(inner.left(), inner.bottom() - TIME_HEIGHT, inner.width(), TIME_HEIGHT),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            message.timestamp.strftime("%H:%M"),
        )

        painter.restore()

    # ---------------------------------------------------------------- Details

    def _paint_day_header(self, painter: QPainter, option, day: date) -> None:
        label = format_day(day)
        painter.setFont(self._small_font(option.font, bold=True))
        metrics = QFontMetrics(painter.font())
        width = metrics.horizontalAdvance(label) + 24

        rect = QRect(
            option.rect.center().x() - width // 2,
            option.rect.top() + 6,
            width,
            22,
        )

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(theme.DAY_CHIP)
        painter.drawRoundedRect(QRectF(rect), 11, 11)

        painter.setPen(theme.DAY_TEXT)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)

    def _paint_media(
        self,
        painter: QPainter,
        option,
        inner: QRect,
        message,
        y: int,
        meta_color: QColor,
    ) -> int:
        images, others = split_attachments(message)
        height = 0

        if images:
            thumb = load_thumbnail(str(images[0].path), inner.width())
            if thumb is not None:
                x = inner.left() + (inner.width() - thumb.width()) // 2
                painter.drawPixmap(x, y, thumb)
                height += thumb.height() + 6

                if len(images) > 1:
                    painter.setPen(meta_color)
                    painter.setFont(self._small_font(option.font))
                    painter.drawText(
                        QRect(inner.left(), y + thumb.height() + 2, inner.width(), 16),
                        Qt.AlignmentFlag.AlignLeft,
                        f"+{len(images) - 1} weitere Bilder",
                    )
                    height += 16

        if others:
            painter.setPen(meta_color)
            painter.setFont(self._small_font(option.font))
            line_y = y + height

            for attachment in others:
                painter.drawText(
                    QRect(inner.left(), line_y, inner.width(), MEDIA_LINE_HEIGHT),
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    self._attachment_label(attachment),
                )
                line_y += MEDIA_LINE_HEIGHT
                height += MEDIA_LINE_HEIGHT

        return height

    def _calculate_height(self, message, width: int, font: QFont, has_day: bool) -> int:
        metrics = QFontMetrics(font)
        text_width = width - 2 * theme.BUBBLE_PADDING_X
        text_rect = metrics.boundingRect(
            QRect(0, 0, text_width, 10000),
            int(Qt.TextFlag.TextWordWrap),
            message.text or " ",
        )

        height = (
            text_rect.height()
            + 2 * theme.BUBBLE_PADDING_Y
            + TIME_HEIGHT
            + 2 * theme.ROW_MARGIN_Y
        )

        if not message.is_own_message:
            height += NAME_HEIGHT

        images, others = split_attachments(message)
        if images:
            height += THUMB_HEIGHT + 6
            if len(images) > 1:
                height += 16

        height += MEDIA_LINE_HEIGHT * len(others)

        if has_day:
            height += DAY_HEIGHT

        return max(height, 48)

    def _bubble_width(self, option: QStyleOptionViewItem) -> int:
        widget = option.widget
        viewport_width = widget.viewport().width() if widget is not None else 800

        return int(min(560, max(220, viewport_width * 0.72)))

    def _small_font(self, base: QFont, bold: bool = False) -> QFont:
        font = QFont(base)
        font.setPointSizeF(base.pointSizeF() * 0.82)
        font.setBold(bold)
        return font

    def _attachment_label(self, attachment) -> str:
        prefix = {
            "video": "Video",
            "audio": "Audio",
            "document": "Dokument",
            "file": "Datei",
        }.get(attachment.kind, "Datei")

        state = "" if attachment.exists else " (fehlt)"
        return f"📎 {prefix}: {attachment.filename}{state}"
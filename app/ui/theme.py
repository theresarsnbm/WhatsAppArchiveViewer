from __future__ import annotations

from PySide6.QtGui import QColor

# Hintergründe
BACKGROUND = QColor("#0B141A")
SIDEBAR = QColor("#111B21")

# Blasen
COLOR_OWN = QColor("#005C4B")
COLOR_OTHER = QColor("#202C33")

# Text
TEXT_OWN = QColor("#E9EDEF")
TEXT_OTHER = QColor("#E9EDEF")
COLOR_META = QColor("#8696A0")
COLOR_META_OWN = QColor("#A7D8C9")

# Tagesheader
DAY_CHIP = QColor("#182229")
DAY_TEXT = QColor("#8696A0")

# Sonstiges
ACCENT = QColor("#00A884")

# Geometrie
BUBBLE_RADIUS = 12
BUBBLE_PADDING_X = 10
BUBBLE_PADDING_Y = 8
ROW_MARGIN_X = 12
ROW_MARGIN_Y = 5

APP_STYLESHEET = f"""
QMainWindow {{ background: {BACKGROUND.name()}; }}
QListWidget {{
    background: {SIDEBAR.name()};
    color: #E9EDEF;
    border: none;
    padding: 6px;
}}
QListWidget::item {{ padding: 8px; border-radius: 6px; }}
QListWidget::item:selected {{ background: #2A3942; }}
QLabel#chatHeader {{ color: #E9EDEF; font-weight: 600; }}
QListView#messageView {{ background: {BACKGROUND.name()}; border: none; }}
QStatusBar {{ background: {SIDEBAR.name()}; color: #8696A0; }}
QMenuBar {{ background: {SIDEBAR.name()}; color: #E9EDEF; }}
"""
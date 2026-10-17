from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication

DARK_QSS = """
QMainWindow, QWidget {
    background-color: #1e1e1e;
    color: #d4d4d4;
}
QPushButton {
    background-color: #0e639c;
    color: #ffffff;
    border: none;
    padding: 8px;
    border-radius: 4px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #1177bb;
}
QPushButton:disabled {
    background-color: #333333;
    color: #777777;
}
QLineEdit, QTextEdit, QSpinBox {
    background-color: #252526;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
    padding: 4px;
    border-radius: 2px;
}
QGroupBox {
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    margin-top: 1ex;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top center;
    padding: 0 3px;
}
QTabWidget::pane {
    border: 1px solid #3c3c3c;
}
QTabBar::tab {
    background: #2d2d2d;
    border: 1px solid #3c3c3c;
    padding: 6px 12px;
    color: #888888;
}
QTabBar::tab:selected {
    background: #1e1e1e;
    border-bottom-color: #1e1e1e;
    color: #ffffff;
}
QMenuBar {
    background-color: #1e1e1e;
    color: #d4d4d4;
}
QMenuBar::item:selected {
    background-color: #094771;
}
QMenu {
    background-color: #252526;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
}
QMenu::item:selected {
    background-color: #094771;
}
QRadioButton {
    color: #d4d4d4;
}
QSlider::groove:horizontal {
    background: #3c3c3c;
    height: 6px;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #0e639c;
    width: 14px;
    margin: -4px 0;
    border-radius: 7px;
}
"""

LIGHT_QSS = """
QMainWindow, QWidget {
    background-color: #f3f3f3;
    color: #1e1e1e;
}
QPushButton {
    background-color: #0078d4;
    color: #ffffff;
    border: none;
    padding: 8px;
    border-radius: 4px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #106ebe;
}
QPushButton:disabled {
    background-color: #cccccc;
    color: #666666;
}
QLineEdit, QTextEdit, QSpinBox {
    background-color: #ffffff;
    color: #1e1e1e;
    border: 1px solid #cccccc;
    padding: 4px;
    border-radius: 2px;
}
QGroupBox {
    border: 1px solid #cccccc;
    border-radius: 4px;
    margin-top: 1ex;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top center;
    padding: 0 3px;
}
QTabWidget::pane {
    border: 1px solid #cccccc;
}
QTabBar::tab {
    background: #e8e8e8;
    border: 1px solid #cccccc;
    padding: 6px 12px;
    color: #666666;
}
QTabBar::tab:selected {
    background: #f3f3f3;
    border-bottom-color: #f3f3f3;
    color: #1e1e1e;
}
QMenuBar {
    background-color: #f3f3f3;
    color: #1e1e1e;
}
QMenuBar::item:selected {
    background-color: #cce4f7;
}
QMenu {
    background-color: #ffffff;
    color: #1e1e1e;
    border: 1px solid #cccccc;
}
QMenu::item:selected {
    background-color: #cce4f7;
}
QRadioButton {
    color: #1e1e1e;
}
QSlider::groove:horizontal {
    background: #cccccc;
    height: 6px;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #0078d4;
    width: 14px;
    margin: -4px 0;
    border-radius: 7px;
}
"""


def resolve_theme(theme_name: str) -> str:
    if theme_name == "system":
        scheme = QGuiApplication.styleHints().colorScheme()
        return "dark" if scheme == Qt.ColorScheme.Dark else "light"
    return theme_name


def stylesheet_for(theme_name: str) -> str:
    resolved = resolve_theme(theme_name)
    return DARK_QSS if resolved == "dark" else LIGHT_QSS

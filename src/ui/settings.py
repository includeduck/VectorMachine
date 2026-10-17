from PySide6.QtCore import QSettings

ORG = "VectorMachine"
APP = "VectorMachine"
THEME_KEY = "theme"
DEFAULT_THEME = "dark"

VALID_THEMES = ("light", "dark", "system")


def get_theme() -> str:
    settings = QSettings(ORG, APP)
    theme = settings.value(THEME_KEY, DEFAULT_THEME, type=str)
    return theme if theme in VALID_THEMES else DEFAULT_THEME


def set_theme(theme: str) -> None:
    if theme not in VALID_THEMES:
        return
    settings = QSettings(ORG, APP)
    settings.setValue(THEME_KEY, theme)

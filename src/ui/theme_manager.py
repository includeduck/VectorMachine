"""Owns the active theme: the View > Theme menu, persistence and applying it."""

from PySide6.QtGui import QAction, QActionGroup

from src.core.debug_log import debug_log
from src.ui.settings import get_theme, set_theme
from src.ui.themes import palette_for, stylesheet_for

THEME_CHOICES = (
    ("light", "Light"),
    ("dark", "Dark"),
    ("system", "System"),
)


class ThemeManager:
    def __init__(self, window, results_panel, visualization_panel):
        self._window = window
        self._results_panel = results_panel
        self._visualization_panel = visualization_panel
        self._actions = {}
        self.current = get_theme()

    def build_menu(self, menu):
        """Add one checkable, mutually exclusive action per theme to ``menu``."""
        group = QActionGroup(self._window)
        group.setExclusive(True)
        for theme_name, label in THEME_CHOICES:
            action = QAction(label, self._window, checkable=True)
            action.setChecked(theme_name == self.current)
            action.triggered.connect(lambda checked, t=theme_name: self.select(t))
            group.addAction(action)
            menu.addAction(action)
            self._actions[theme_name] = action

    def select(self, theme_name):
        """User choice: persist it, then apply it."""
        set_theme(theme_name)
        self.apply(theme_name)

    def apply(self, theme_name):
        self.current = theme_name
        self._window.setStyleSheet(stylesheet_for(theme_name))
        palette = palette_for(theme_name)
        self._results_panel.set_accent(palette["accent"])
        self._visualization_panel.apply_palette(palette)
        for name, action in self._actions.items():
            action.setChecked(name == theme_name)
        debug_log("theme_manager.py:apply", "theme applied", {"theme": theme_name}, "G")

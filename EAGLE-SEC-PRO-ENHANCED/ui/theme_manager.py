"""
EAGLE-SEC PRO — Theme Manager v2.0
Loads the APEX PREDATOR theme. Exposes both a ThemeManager class
(for backwards-compat with main.py) and module-level apply_theme().
"""
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QFontDatabase

from core.logger import get_logger

logger = get_logger("theme_manager")

_THEME_PATH = Path(__file__).resolve().parent.parent / "assets" / "styles" / "dark_theme.qss"


def apply_theme(app: QApplication) -> bool:
    """Load and apply the APEX PREDATOR dark theme. Returns True on success."""
    try:
        qss = _THEME_PATH.read_text(encoding="utf-8")
        app.setStyleSheet(qss)
        _setup_fonts(app)
        logger.info("APEX PREDATOR theme applied successfully")
        return True
    except FileNotFoundError:
        logger.warning("Theme file not found at %s — using system defaults", _THEME_PATH)
        return False
    except Exception as e:
        logger.error("Theme application error: %s", e)
        return False


def _setup_fonts(app: QApplication):
    """Set global application font with fallback chain."""
    available = QFontDatabase.families()
    preferred = ["Cascadia Code", "Fira Code", "Consolas", "Courier New"]
    chosen = next((f for f in preferred if f in available), "monospace")
    base_font = QFont(chosen, 11)
    base_font.setStyleHint(QFont.StyleHint.Monospace)
    app.setFont(base_font)
    logger.debug("Application font: %s", chosen)


def reload_theme(app: QApplication) -> bool:
    """Hot-reload the theme (for live editing support)."""
    logger.info("Reloading theme...")
    return apply_theme(app)


class ThemeManager:
    """
    Class-based wrapper kept for backwards compatibility with main.py.
    Usage: ThemeManager(app)  — applies theme immediately on construction.
    """
    def __init__(self, app: QApplication):
        self._app = app
        self.apply()

    def apply(self) -> bool:
        return apply_theme(self._app)

    def reload(self) -> bool:
        return reload_theme(self._app)

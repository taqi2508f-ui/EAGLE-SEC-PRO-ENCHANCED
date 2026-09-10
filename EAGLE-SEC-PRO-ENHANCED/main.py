#!/usr/bin/env python3
"""
EAGLE-SEC PRO v1.0.0
Professional Web Security Testing Suite
Python 3.12 + PyQt6
"""
import sys
import os
import time
import traceback
from pathlib import Path

# Ensure the app root is in the Python path
APP_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_ROOT))

# Suppress SSL warnings in dev mode
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
try:
    import urllib3
    urllib3.disable_warnings()
except ImportError:
    pass

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QIcon


def check_dependencies() -> list[str]:
    """Return list of missing required packages."""
    required = {
        "PyQt6": "PyQt6",
    }
    missing = []
    for module, pkg in required.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(pkg)
    return missing


def main():
    # Check Python version
    if sys.version_info < (3, 10):
        print("EAGLE-SEC PRO requires Python 3.10 or newer.")
        print(f"Current version: {sys.version}")
        sys.exit(1)

    # Check PyQt6
    missing = check_dependencies()
    if missing:
        print(f"Missing dependencies: {', '.join(missing)}")
        print("Run: install_requirements.bat")
        sys.exit(1)

    # High DPI support (PyQt6 enables it by default)
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")

    app = QApplication(sys.argv)
    app.setApplicationName("EAGLE-SEC PRO")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("EAGLE-SEC")
    app.setStyle("Fusion")

    # Apply theme early so splash screen inherits it
    from ui.theme_manager import ThemeManager
    theme = ThemeManager(app)
    theme.apply()
    # ── Splash screen ────────────────────────────────────────────────
    from ui.splash_screen import SplashScreen
    splash = SplashScreen()
    splash.show()
    app.processEvents()

    # Loading steps
    steps = [
        (10, "Loading configuration..."),
        (20, "Initializing database..."),
        (30, "Starting proxy engine..."),
        (45, "Loading session manager..."),
        (55, "Initializing certificate manager..."),
        (65, "Loading plugins..."),
        (75, "Building user interface..."),
        (88, "Applying theme..."),
        (95, "Starting background services..."),
        (100, "Ready!"),
    ]

    def _progress_step(idx: int):
        if idx >= len(steps):
            _finish_loading()
            return
        pct, msg = steps[idx]
        splash.set_progress(pct, msg)
        app.processEvents()
        QTimer.singleShot(80, lambda: _progress_step(idx + 1))

    main_window_ref = [None]

    def _finish_loading():
        try:
            from ui.main_window import MainWindow
            win = MainWindow()
            main_window_ref[0] = win
            splash.finish(win)
            win.show()
            QTimer.singleShot(200, lambda: win.notif and win.notif.success(
                "EAGLE-SEC PRO started — Configure proxy at 127.0.0.1:8080"
            ))
        except Exception as e:
            splash.close()
            tb = traceback.format_exc()
            from core.logger import get_logger
            get_logger("main").critical("Startup error: %s\n%s", e, tb)
            box = QMessageBox()
            box.setIcon(QMessageBox.Icon.Critical)
            box.setWindowTitle("EAGLE-SEC PRO — Startup Error")
            box.setText(f"Failed to start EAGLE-SEC PRO:\n\n{e}")
            box.setDetailedText(tb)
            box.exec()
            sys.exit(1)

    # Start loading sequence
    QTimer.singleShot(100, lambda: _progress_step(0))

    # Install global exception hook
    def _except_hook(exc_type, exc_val, exc_tb):
        from core.logger import get_logger
        logger = get_logger("main")
        logger.critical(
            "Unhandled exception: %s",
            "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
        )
        sys.__excepthook__(exc_type, exc_val, exc_tb)

    sys.excepthook = _except_hook

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

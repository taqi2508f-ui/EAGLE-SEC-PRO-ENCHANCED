import json
import os
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / "logs"
REPORTS_DIR = BASE_DIR / "reports"
EXPORTS_DIR = BASE_DIR / "exports"
DB_DIR = BASE_DIR / "database"
PLUGINS_DIR = BASE_DIR / "plugins"
ASSETS_DIR = BASE_DIR / "assets"
CONFIG_DIR = BASE_DIR / "config"

for d in [LOGS_DIR, REPORTS_DIR, EXPORTS_DIR, DB_DIR / "data"]:
    d.mkdir(parents=True, exist_ok=True)

DEFAULT_SETTINGS = {
    "proxy": {
        "host": "127.0.0.1",
        "port": 8080,
        "intercept_enabled": False,
        "ssl_strip": False,
        "upstream_proxy": "",
        "timeout": 30,
    },
    "ui": {
        "theme": "dark",
        "accent_color": "#00D4FF",
        "font_size": 12,
        "font_family": "Consolas",
        "animations_enabled": True,
        "glassmorphism": True,
    },
    "general": {
        "autosave_interval": 60,
        "max_history": 10000,
        "check_updates": True,
        "startup_project": "",
        "language": "en",
    },
    "capture": {
        "include_filters": [],
        "exclude_filters": ["*.png", "*.jpg", "*.gif", "*.css", "*.js"],
        "log_body": True,
        "max_body_size": 10485760,
    },
    "notifications": {
        "enabled": True,
        "sound": False,
        "desktop": True,
    },
}

SETTINGS_FILE = CONFIG_DIR / "user_settings.json"


class AppSettings:
    def __init__(self):
        self._data: dict = {}
        self.load()

    def load(self):
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self._data = self._merge(DEFAULT_SETTINGS, saved)
            except Exception:
                self._data = dict(DEFAULT_SETTINGS)
        else:
            self._data = dict(DEFAULT_SETTINGS)

    def save(self):
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        val = self._data
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k, default)
            else:
                return default
        return val

    def set(self, key: str, value: Any):
        keys = key.split(".")
        d = self._data
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value
        self.save()

    def _merge(self, base: dict, override: dict) -> dict:
        result = dict(base)
        for k, v in override.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = self._merge(result[k], v)
            else:
                result[k] = v
        return result

    def reset(self):
        self._data = dict(DEFAULT_SETTINGS)
        self.save()


settings = AppSettings()

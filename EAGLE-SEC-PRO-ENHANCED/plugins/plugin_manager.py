import importlib
import importlib.util
import json
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Optional

from core.logger import get_logger

logger = get_logger("plugin_manager")

PLUGINS_DIR = Path(__file__).resolve().parent
PLUGIN_MANIFEST = "plugin.json"


class PluginBase:
    """Base class all plugins must extend."""
    plugin_id: str = ""
    name: str = ""
    version: str = "1.0.0"
    author: str = ""
    description: str = ""

    def on_load(self, api: "PluginAPI"): ...
    def on_unload(self): ...
    def on_request(self, req: dict) -> dict: return req
    def on_response(self, req: dict) -> dict: return req


class PluginAPI:
    """API surface exposed to plugins."""
    def __init__(self, manager: "PluginManager"):
        self._manager = manager
        self._hooks: dict[str, list[Callable]] = {}

    def register_hook(self, event: str, cb: Callable):
        self._hooks.setdefault(event, []).append(cb)

    def emit(self, event: str, *args, **kwargs):
        for cb in self._hooks.get(event, []):
            try:
                cb(*args, **kwargs)
            except Exception as e:
                logger.error("Plugin hook error [%s]: %s", event, e)

    def log(self, msg: str):
        logger.info("[plugin] %s", msg)


class LoadedPlugin:
    def __init__(self, plugin_id: str, manifest: dict, instance: PluginBase,
                 module_path: Path):
        self.plugin_id = plugin_id
        self.manifest = manifest
        self.instance = instance
        self.module_path = module_path
        self.enabled = True
        self.loaded_at = time.time()
        self.error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "plugin_id": self.plugin_id,
            "name": self.manifest.get("name", ""),
            "version": self.manifest.get("version", ""),
            "author": self.manifest.get("author", ""),
            "description": self.manifest.get("description", ""),
            "enabled": self.enabled,
            "loaded_at": self.loaded_at,
            "error": self.error,
        }


class PluginManager:
    def __init__(self, plugins_dir: Path = PLUGINS_DIR):
        self.plugins_dir = plugins_dir
        self._plugins: dict[str, LoadedPlugin] = {}
        self._api = PluginAPI(self)
        self._on_change_cb: list[Callable] = []

    def discover_and_load(self) -> list[str]:
        loaded = []
        for plugin_dir in sorted(self.plugins_dir.iterdir()):
            if not plugin_dir.is_dir():
                continue
            if plugin_dir.name.startswith("_") or plugin_dir.name == "__pycache__":
                continue
            manifest_path = plugin_dir / PLUGIN_MANIFEST
            if not manifest_path.exists():
                continue
            pid = self.load_plugin(plugin_dir)
            if pid:
                loaded.append(pid)
        logger.info("Discovered %d plugins", len(loaded))
        return loaded

    def load_plugin(self, plugin_dir: Path) -> Optional[str]:
        manifest_path = plugin_dir / PLUGIN_MANIFEST
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error("Invalid manifest in %s: %s", plugin_dir, e)
            return None

        plugin_id = manifest.get("id") or str(uuid.uuid4())[:8]
        entry = manifest.get("entry", "main.py")
        entry_path = plugin_dir / entry

        if not entry_path.exists():
            logger.error("Plugin entry not found: %s", entry_path)
            return None

        try:
            spec = importlib.util.spec_from_file_location(
                f"plugin_{plugin_id}", str(entry_path)
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"plugin_{plugin_id}"] = module
            spec.loader.exec_module(module)

            plugin_class = getattr(module, "Plugin", None)
            if not plugin_class:
                logger.error("No 'Plugin' class in %s", entry_path)
                return None

            instance = plugin_class()
            instance.plugin_id = plugin_id
            instance.on_load(self._api)

            loaded = LoadedPlugin(plugin_id, manifest, instance, entry_path)
            self._plugins[plugin_id] = loaded
            logger.info("Plugin loaded: %s v%s", manifest.get("name"), manifest.get("version"))
            self._notify_change()
            return plugin_id
        except Exception as e:
            logger.error("Plugin load error %s: %s", plugin_dir.name, e)
            lp = LoadedPlugin(plugin_id, manifest, PluginBase(), plugin_dir / entry)
            lp.enabled = False
            lp.error = str(e)
            self._plugins[plugin_id] = lp
            return plugin_id

    def unload_plugin(self, plugin_id: str) -> bool:
        if plugin_id not in self._plugins:
            return False
        try:
            self._plugins[plugin_id].instance.on_unload()
        except Exception:
            pass
        del self._plugins[plugin_id]
        self._notify_change()
        return True

    def reload_plugin(self, plugin_id: str) -> bool:
        if plugin_id not in self._plugins:
            return False
        plugin_dir = self._plugins[plugin_id].module_path.parent
        self.unload_plugin(plugin_id)
        return bool(self.load_plugin(plugin_dir))

    def enable_plugin(self, plugin_id: str, enabled: bool):
        if plugin_id in self._plugins:
            self._plugins[plugin_id].enabled = enabled
            self._notify_change()

    def get_plugins(self) -> list[dict]:
        return [p.to_dict() for p in self._plugins.values()]

    def process_request(self, req: dict) -> dict:
        for p in self._plugins.values():
            if p.enabled:
                try:
                    req = p.instance.on_request(req) or req
                except Exception as e:
                    logger.error("Plugin %s request error: %s", p.plugin_id, e)
        return req

    def process_response(self, req: dict) -> dict:
        for p in self._plugins.values():
            if p.enabled:
                try:
                    req = p.instance.on_response(req) or req
                except Exception as e:
                    logger.error("Plugin %s response error: %s", p.plugin_id, e)
        return req

    def on_change(self, cb: Callable):
        self._on_change_cb.append(cb)

    def _notify_change(self):
        for cb in self._on_change_cb:
            try:
                cb()
            except Exception:
                pass

    def install_from_zip(self, zip_path: str) -> Optional[str]:
        import zipfile, shutil
        try:
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(self.plugins_dir)
            logger.info("Plugin installed from %s", zip_path)
            return self.discover_and_load()[-1] if self.discover_and_load() else None
        except Exception as e:
            logger.error("Plugin install error: %s", e)
            return None

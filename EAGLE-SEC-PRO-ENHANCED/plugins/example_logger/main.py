"""
EAGLE-SEC PRO — Example Plugin: Request Logger
Demonstrates the plugin API. Logs every request to a local file.
"""
import time
from datetime import datetime
from pathlib import Path

LOG_FILE = Path(__file__).resolve().parent / "requests.log"


class Plugin:
    """Required class name for all EAGLE-SEC PRO plugins."""

    plugin_id = "example_logger"
    name = "Request Logger"
    version = "1.0.0"
    author = "EAGLE-SEC PRO"

    def __init__(self):
        self._api = None
        self._count = 0

    def on_load(self, api):
        """Called when plugin is loaded. Receive the PluginAPI handle."""
        self._api = api
        api.log(f"Request Logger v{self.version} loaded — writing to {LOG_FILE}")

    def on_unload(self):
        """Called when plugin is unloaded or reloaded."""
        if self._api:
            self._api.log("Request Logger unloaded")

    def on_request(self, req: dict) -> dict:
        """Called for every intercepted request. Must return the (optionally modified) req dict."""
        self._count += 1
        try:
            ts = datetime.fromtimestamp(req.get("timestamp", time.time())).strftime("%Y-%m-%d %H:%M:%S")
            line = f"[{ts}] #{self._count:05d} {req.get('method','?')} {req.get('url','?')}\n"
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass
        return req

    def on_response(self, req: dict) -> dict:
        """Called after a response is received. req contains both request + response."""
        return req

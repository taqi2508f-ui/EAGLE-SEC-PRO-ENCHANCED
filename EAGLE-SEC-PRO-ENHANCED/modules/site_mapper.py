import re
import time
import threading
from collections import defaultdict
from urllib.parse import urlparse, urljoin
from typing import Optional, Callable

from core.logger import get_logger

logger = get_logger("site_mapper")


class SiteNode:
    def __init__(self, url: str):
        self.url = url
        parsed = urlparse(url)
        self.scheme = parsed.scheme
        self.host = parsed.netloc
        self.path = parsed.path or "/"
        self.params = parsed.params
        self.query = parsed.query
        self.children: list["SiteNode"] = []
        self.methods: set[str] = set()
        self.status_codes: list[int] = []
        self.content_types: list[str] = []
        self.added_at: float = time.time()
        self.request_count: int = 0

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "host": self.host,
            "path": self.path,
            "query": self.query,
            "methods": list(self.methods),
            "status_codes": self.status_codes,
            "content_types": self.content_types,
            "request_count": self.request_count,
            "children": [c.to_dict() for c in self.children],
        }


class SiteMapper:
    def __init__(self):
        self._nodes: dict[str, SiteNode] = {}
        self._host_tree: dict[str, dict] = defaultdict(lambda: {"paths": {}, "node": None})
        self._lock = threading.Lock()
        self._on_update_cb: list[Callable] = []

    def add_request(self, req: dict):
        url = req.get("url", "")
        method = req.get("method", "GET")
        status = req.get("response", {}).get("status_code", 0) if req.get("response") else 0
        content_type = ""
        if req.get("response"):
            content_type = req["response"].get("headers", {}).get("Content-Type", "")

        with self._lock:
            if url not in self._nodes:
                node = SiteNode(url)
                self._nodes[url] = node
                self._insert_tree(node)
            node = self._nodes[url]
            node.methods.add(method)
            node.request_count += 1
            if status:
                node.status_codes.append(status)
            if content_type:
                node.content_types.append(content_type)

        for cb in self._on_update_cb:
            try:
                cb(self._nodes[url])
            except Exception:
                pass

    def _insert_tree(self, node: SiteNode):
        host = node.host
        parts = [p for p in node.path.split("/") if p]
        current = self._host_tree[host]["paths"]
        for part in parts:
            current = current.setdefault(part, {"_node": None, "_children": {}})["_children"]
        self._host_tree[host]["paths"].setdefault("_node", node)

    def get_hosts(self) -> list[str]:
        with self._lock:
            return sorted(self._host_tree.keys())

    def get_paths_for_host(self, host: str) -> list[str]:
        with self._lock:
            return sorted(
                url for url, node in self._nodes.items() if node.host == host
            )

    def get_node(self, url: str) -> Optional[SiteNode]:
        return self._nodes.get(url)

    def get_all_nodes(self) -> list[SiteNode]:
        with self._lock:
            return list(self._nodes.values())

    def search(self, query: str) -> list[SiteNode]:
        q = query.lower()
        with self._lock:
            return [n for n in self._nodes.values() if q in n.url.lower()]

    def on_update(self, cb: Callable):
        self._on_update_cb.append(cb)

    def clear(self):
        with self._lock:
            self._nodes.clear()
            self._host_tree.clear()

    def export_dict(self) -> dict:
        with self._lock:
            return {url: node.to_dict() for url, node in self._nodes.items()}

    def stats(self) -> dict:
        with self._lock:
            hosts = set(n.host for n in self._nodes.values())
            return {
                "total_urls": len(self._nodes),
                "total_hosts": len(hosts),
                "hosts": list(hosts),
            }

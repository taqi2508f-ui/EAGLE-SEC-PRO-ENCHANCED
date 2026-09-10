import asyncio
import socket
import ssl
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable, Optional
from urllib.parse import urlparse

from .logger import get_logger

logger = get_logger("proxy_engine")


@dataclass
class HttpRequest:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    method: str = ""
    url: str = ""
    host: str = ""
    port: int = 80
    path: str = "/"
    http_version: str = "HTTP/1.1"
    headers: dict = field(default_factory=dict)
    body: bytes = b""
    is_https: bool = False
    status: str = "pending"
    response: Optional["HttpResponse"] = None
    duration_ms: float = 0.0
    notes: str = ""
    tags: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "method": self.method,
            "url": self.url,
            "host": self.host,
            "port": self.port,
            "path": self.path,
            "http_version": self.http_version,
            "headers": self.headers,
            "body": self.body.decode("utf-8", errors="replace"),
            "is_https": self.is_https,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "notes": self.notes,
            "tags": self.tags,
            "response": self.response.to_dict() if self.response else None,
        }

    def raw(self) -> str:
        lines = [f"{self.method} {self.path} {self.http_version}"]
        for k, v in self.headers.items():
            lines.append(f"{k}: {v}")
        lines.append("")
        lines.append(self.body.decode("utf-8", errors="replace"))
        return "\r\n".join(lines)


@dataclass
class HttpResponse:
    status_code: int = 0
    status_text: str = ""
    http_version: str = "HTTP/1.1"
    headers: dict = field(default_factory=dict)
    body: bytes = b""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "status_code": self.status_code,
            "status_text": self.status_text,
            "http_version": self.http_version,
            "headers": self.headers,
            "body": self.body.decode("utf-8", errors="replace"),
            "timestamp": self.timestamp,
        }

    def raw(self) -> str:
        lines = [f"{self.http_version} {self.status_code} {self.status_text}"]
        for k, v in self.headers.items():
            lines.append(f"{k}: {v}")
        lines.append("")
        try:
            lines.append(self.body.decode("utf-8", errors="replace"))
        except Exception:
            lines.append("<binary body>")
        return "\r\n".join(lines)


class ProxyClientHandler:
    BUFFER = 65536

    def __init__(self, conn, addr, engine: "ProxyEngine"):
        self.conn = conn
        self.addr = addr
        self.engine = engine

    def handle(self):
        try:
            data = self.conn.recv(self.BUFFER)
            if not data:
                return
            first_line = data.split(b"\r\n")[0].decode("utf-8", errors="replace")
            parts = first_line.split()
            if len(parts) < 3:
                return

            method, target, version = parts[0], parts[1], parts[2]

            if method.upper() == "CONNECT":
                self._handle_connect(target, data, version)
            else:
                self._handle_http(method, target, version, data)
        except Exception as e:
            logger.debug("Handler error %s: %s", self.addr, e)
        finally:
            try:
                self.conn.close()
            except Exception:
                pass

    def _handle_connect(self, target: str, raw: bytes, version: str):
        host, _, port_str = target.partition(":")
        port = int(port_str) if port_str else 443
        try:
            self.conn.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            remote = socket.create_connection((host, port), timeout=self.engine.timeout)
            req = HttpRequest(method="CONNECT", url=f"https://{target}", host=host,
                              port=port, path="/", is_https=True, http_version=version)
            self.engine._on_request(req)
            self._tunnel(self.conn, remote, req)
        except Exception as e:
            logger.debug("CONNECT error for %s: %s", target, e)

    def _handle_http(self, method: str, target: str, version: str, raw: bytes):
        parsed = urlparse(target if target.startswith("http") else f"http://{target}")
        host = parsed.hostname or ""
        port = parsed.port or 80
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query

        headers, body = self._parse_headers_body(raw)
        req = HttpRequest(
            method=method, url=target, host=host, port=port,
            path=path, http_version=version, headers=headers,
            body=body, is_https=False,
        )

        if self.engine.intercept_enabled:
            req.status = "intercepted"
            self.engine._on_request(req)
            while req.status == "intercepted":
                time.sleep(0.05)
            if req.status == "dropped":
                return

        req.status = "forwarding"
        t0 = time.time()
        try:
            remote = socket.create_connection((host, port), timeout=self.engine.timeout)
            remote.sendall(raw)
            resp_data = b""
            while True:
                chunk = remote.recv(self.BUFFER)
                if not chunk:
                    break
                resp_data += chunk
                self.conn.sendall(chunk)
            remote.close()
            req.duration_ms = (time.time() - t0) * 1000
            req.response = self._parse_response(resp_data)
            req.status = "completed"
            self.engine._on_response(req)
        except Exception as e:
            req.status = "error"
            logger.debug("Forward error %s %s: %s", method, target, e)

    def _tunnel(self, client: socket.socket, remote: socket.socket, req: HttpRequest):
        import select
        client.settimeout(self.engine.timeout)
        remote.settimeout(self.engine.timeout)
        t0 = time.time()
        try:
            while True:
                r, _, _ = select.select([client, remote], [], [], 5.0)
                if not r:
                    break
                for s in r:
                    other = remote if s is client else client
                    try:
                        data = s.recv(self.BUFFER)
                        if not data:
                            return
                        other.sendall(data)
                    except Exception:
                        return
        finally:
            req.duration_ms = (time.time() - t0) * 1000
            req.status = "completed"
            self.engine._on_response(req)
            try:
                remote.close()
            except Exception:
                pass

    @staticmethod
    def _parse_headers_body(raw: bytes) -> tuple[dict, bytes]:
        parts = raw.split(b"\r\n\r\n", 1)
        header_section = parts[0].decode("utf-8", errors="replace")
        body = parts[1] if len(parts) > 1 else b""
        lines = header_section.split("\r\n")
        headers = {}
        for line in lines[1:]:
            if ":" in line:
                k, _, v = line.partition(":")
                headers[k.strip()] = v.strip()
        return headers, body

    @staticmethod
    def _parse_response(raw: bytes) -> HttpResponse:
        parts = raw.split(b"\r\n\r\n", 1)
        header_section = parts[0].decode("utf-8", errors="replace")
        body = parts[1] if len(parts) > 1 else b""
        lines = header_section.split("\r\n")
        resp = HttpResponse(body=body)
        if lines:
            status_parts = lines[0].split(" ", 2)
            if len(status_parts) >= 2:
                resp.http_version = status_parts[0]
                resp.status_code = int(status_parts[1]) if status_parts[1].isdigit() else 0
                resp.status_text = status_parts[2] if len(status_parts) > 2 else ""
        for line in lines[1:]:
            if ":" in line:
                k, _, v = line.partition(":")
                resp.headers[k.strip()] = v.strip()
        return resp


class ProxyEngine:
    def __init__(self, host: str = "127.0.0.1", port: int = 8080):
        self.host = host
        self.port = port
        self.timeout = 30
        self.intercept_enabled = False
        self.running = False
        self._server: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._on_request_cb: list[Callable] = []
        self._on_response_cb: list[Callable] = []
        self._requests: list[HttpRequest] = []
        self._lock = threading.Lock()

    def start(self) -> bool:
        if self.running:
            return True
        try:
            self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server.bind((self.host, self.port))
            self._server.listen(50)
            self._server.settimeout(1.0)
            self.running = True
            self._thread = threading.Thread(target=self._accept_loop, daemon=True)
            self._thread.start()
            logger.info("Proxy started on %s:%d", self.host, self.port)
            return True
        except Exception as e:
            logger.error("Proxy start failed: %s", e)
            return False

    def stop(self):
        self.running = False
        if self._server:
            try:
                self._server.close()
            except Exception:
                pass
        logger.info("Proxy stopped")

    def _accept_loop(self):
        while self.running:
            try:
                conn, addr = self._server.accept()
                t = threading.Thread(
                    target=ProxyClientHandler(conn, addr, self).handle,
                    daemon=True,
                )
                t.start()
            except socket.timeout:
                continue
            except Exception:
                break

    def on_request(self, cb: Callable):
        self._on_request_cb.append(cb)

    def on_response(self, cb: Callable):
        self._on_response_cb.append(cb)

    def _on_request(self, req: HttpRequest):
        with self._lock:
            self._requests.append(req)
        for cb in self._on_request_cb:
            try:
                cb(req)
            except Exception as e:
                logger.debug("Request callback error: %s", e)

    def _on_response(self, req: HttpRequest):
        for cb in self._on_response_cb:
            try:
                cb(req)
            except Exception as e:
                logger.debug("Response callback error: %s", e)

    def get_requests(self) -> list[HttpRequest]:
        with self._lock:
            return list(self._requests)

    def clear_requests(self):
        with self._lock:
            self._requests.clear()

    def forward_request(self, req: HttpRequest):
        req.status = "forwarding"

    def drop_request(self, req: HttpRequest):
        req.status = "dropped"

    @property
    def request_count(self) -> int:
        with self._lock:
            return len(self._requests)

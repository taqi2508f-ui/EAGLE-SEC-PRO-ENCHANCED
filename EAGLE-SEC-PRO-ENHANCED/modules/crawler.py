import asyncio
import re
import time
import threading
from typing import Callable, Optional, Set
from urllib.parse import urljoin, urlparse
import queue

from core.logger import get_logger

logger = get_logger("crawler")

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

try:
    import lxml  # noqa: F401
    _BS4_PARSER = "lxml"
except ImportError:
    _BS4_PARSER = "html.parser"


class CrawlResult:
    def __init__(self, url: str):
        self.url = url
        self.status_code: int = 0
        self.content_type: str = ""
        self.links: list[str] = []
        self.forms: list[dict] = []
        self.scripts: list[str] = []
        self.title: str = ""
        self.error: str = ""
        self.depth: int = 0
        self.timestamp: float = time.time()
        self.response_time_ms: float = 0.0
        self.body_size: int = 0

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "status_code": self.status_code,
            "content_type": self.content_type,
            "links": self.links,
            "forms": self.forms,
            "scripts": self.scripts,
            "title": self.title,
            "error": self.error,
            "depth": self.depth,
            "timestamp": self.timestamp,
            "response_time_ms": self.response_time_ms,
            "body_size": self.body_size,
        }


class WebCrawler:
    def __init__(self):
        self.target_url: str = ""
        self.max_depth: int = 3
        self.max_pages: int = 100
        self.delay_ms: int = 500
        self.follow_external: bool = False
        self.respect_robots: bool = True
        self.user_agent: str = "EAGLE-SEC PRO Crawler/1.0"
        self.timeout: int = 10

        self._visited: Set[str] = set()
        self._queue: list[tuple[str, int]] = []
        self._results: list[CrawlResult] = []
        self._running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        self._on_result_cb: list[Callable] = []
        self._on_done_cb: list[Callable] = []
        self._on_error_cb: list[Callable] = []

    def start(self, url: str):
        if self._running:
            return
        self.target_url = url
        self._visited.clear()
        self._queue = [(url, 0)]
        self._results.clear()
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Crawler started for %s", url)

    def stop(self):
        self._running = False
        logger.info("Crawler stopping...")

    def _run_loop(self):
        try:
            import requests as req_lib
            session = req_lib.Session()
            session.headers["User-Agent"] = self.user_agent
            parsed_target = urlparse(self.target_url)
            target_host = parsed_target.netloc

            while self._running and self._queue:
                if len(self._results) >= self.max_pages:
                    break

                url, depth = self._queue.pop(0)
                if url in self._visited or depth > self.max_depth:
                    continue

                self._visited.add(url)
                result = self._crawl_page(session, url, depth, target_host)
                with self._lock:
                    self._results.append(result)

                for cb in self._on_result_cb:
                    try:
                        cb(result)
                    except Exception:
                        pass

                for link in result.links:
                    if link not in self._visited:
                        self._queue.append((link, depth + 1))

                time.sleep(self.delay_ms / 1000.0)

        except Exception as e:
            logger.error("Crawler error: %s", e)
        finally:
            self._running = False
            for cb in self._on_done_cb:
                try:
                    cb(self._results)
                except Exception:
                    pass
            logger.info("Crawler finished. Pages: %d", len(self._results))

    def _crawl_page(self, session, url: str, depth: int, target_host: str) -> CrawlResult:
        result = CrawlResult(url)
        result.depth = depth
        try:
            import requests as req_lib
            t0 = time.time()
            resp = session.get(url, timeout=self.timeout, allow_redirects=True,
                               verify=False, stream=False)
            result.response_time_ms = (time.time() - t0) * 1000
            result.status_code = resp.status_code
            result.content_type = resp.headers.get("Content-Type", "")
            body = resp.text
            result.body_size = len(resp.content)

            if HAS_BS4 and "html" in result.content_type.lower():
                soup = BeautifulSoup(body, _BS4_PARSER)
                title_tag = soup.find("title")
                result.title = title_tag.get_text(strip=True) if title_tag else ""

                for tag in soup.find_all("a", href=True):
                    href = tag["href"].strip()
                    if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                        continue
                    abs_url = urljoin(url, href)
                    parsed = urlparse(abs_url)
                    if not self.follow_external and parsed.netloc != target_host:
                        continue
                    clean = abs_url.split("#")[0]
                    if clean and clean not in self._visited:
                        result.links.append(clean)

                for form in soup.find_all("form"):
                    result.forms.append({
                        "action": form.get("action", ""),
                        "method": form.get("method", "GET").upper(),
                        "inputs": [
                            {"name": i.get("name", ""), "type": i.get("type", "text")}
                            for i in form.find_all("input")
                        ],
                    })

                for script in soup.find_all("script", src=True):
                    result.scripts.append(script["src"])
        except Exception as e:
            result.error = str(e)
            logger.debug("Crawl error %s: %s", url, e)
        return result

    def on_result(self, cb: Callable):
        self._on_result_cb.append(cb)

    def on_done(self, cb: Callable):
        self._on_done_cb.append(cb)

    def on_error(self, cb: Callable):
        self._on_error_cb.append(cb)

    def get_results(self) -> list[CrawlResult]:
        with self._lock:
            return list(self._results)

    @property
    def is_running(self) -> bool:
        return self._running

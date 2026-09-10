import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional
from contextlib import contextmanager

from core.logger import get_logger

logger = get_logger("db_manager")

DB_PATH = Path(__file__).resolve().parent / "data" / "eagle_sec.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS projects (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT,
    created_at  REAL NOT NULL,
    updated_at  REAL NOT NULL,
    settings    TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS requests (
    id          TEXT PRIMARY KEY,
    project_id  TEXT,
    session_id  TEXT,
    timestamp   REAL,
    method      TEXT,
    url         TEXT,
    host        TEXT,
    port        INTEGER,
    path        TEXT,
    headers     TEXT,
    body        TEXT,
    is_https    INTEGER DEFAULT 0,
    status      TEXT,
    duration_ms REAL,
    notes       TEXT,
    tags        TEXT DEFAULT '[]',
    response    TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    project_id  TEXT,
    name        TEXT,
    created_at  REAL,
    updated_at  REAL,
    notes       TEXT,
    tags        TEXT DEFAULT '[]',
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS reports (
    id          TEXT PRIMARY KEY,
    project_id  TEXT,
    name        TEXT,
    created_at  REAL,
    format      TEXT,
    path        TEXT,
    summary     TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   REAL,
    level       TEXT,
    module      TEXT,
    message     TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key         TEXT PRIMARY KEY,
    value       TEXT,
    updated_at  REAL
);

CREATE TABLE IF NOT EXISTS plugins (
    id          TEXT PRIMARY KEY,
    name        TEXT,
    version     TEXT,
    enabled     INTEGER DEFAULT 1,
    path        TEXT,
    manifest    TEXT,
    installed_at REAL
);

CREATE INDEX IF NOT EXISTS idx_requests_host ON requests(host);
CREATE INDEX IF NOT EXISTS idx_requests_ts   ON requests(timestamp);
CREATE INDEX IF NOT EXISTS idx_logs_ts       ON logs(timestamp);
"""


class DatabaseManager:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._local = {}
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        import threading
        tid = threading.get_ident()
        if tid not in self._local:
            conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self._local[tid] = conn
        return self._local[tid]

    @contextmanager
    def _cursor(self):
        conn = self._get_conn()
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error("DB error: %s", e)
            raise

    def _init_db(self):
        conn = self._get_conn()
        conn.executescript(SCHEMA)
        conn.commit()
        logger.info("Database initialized at %s", self.db_path)

    # ── Projects ────────────────────────────────────────────────────────
    def create_project(self, project_id: str, name: str, description: str = "") -> bool:
        with self._cursor() as c:
            now = time.time()
            c.execute(
                "INSERT OR IGNORE INTO projects(id,name,description,created_at,updated_at) VALUES(?,?,?,?,?)",
                (project_id, name, description, now, now),
            )
        return True

    def get_projects(self) -> list[dict]:
        with self._cursor() as c:
            c.execute("SELECT * FROM projects ORDER BY updated_at DESC")
            return [dict(r) for r in c.fetchall()]

    def delete_project(self, project_id: str) -> bool:
        with self._cursor() as c:
            c.execute("DELETE FROM projects WHERE id=?", (project_id,))
        return True

    # ── Requests ────────────────────────────────────────────────────────
    def save_request(self, req_dict: dict, project_id: str = None, session_id: str = None):
        with self._cursor() as c:
            c.execute(
                """INSERT OR REPLACE INTO requests
                   (id,project_id,session_id,timestamp,method,url,host,port,path,
                    headers,body,is_https,status,duration_ms,notes,tags,response)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    req_dict.get("id"), project_id, session_id,
                    req_dict.get("timestamp"), req_dict.get("method"),
                    req_dict.get("url"), req_dict.get("host"), req_dict.get("port"),
                    req_dict.get("path"),
                    json.dumps(req_dict.get("headers", {})),
                    req_dict.get("body", ""),
                    int(req_dict.get("is_https", False)),
                    req_dict.get("status", ""),
                    req_dict.get("duration_ms", 0.0),
                    req_dict.get("notes", ""),
                    json.dumps(req_dict.get("tags", [])),
                    json.dumps(req_dict.get("response")) if req_dict.get("response") else None,
                ),
            )

    def get_requests(self, project_id: str = None, session_id: str = None,
                     limit: int = 5000, offset: int = 0) -> list[dict]:
        with self._cursor() as c:
            where, params = [], []
            if project_id:
                where.append("project_id=?"); params.append(project_id)
            if session_id:
                where.append("session_id=?"); params.append(session_id)
            clause = ("WHERE " + " AND ".join(where)) if where else ""
            c.execute(
                f"SELECT * FROM requests {clause} ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                params + [limit, offset],
            )
            rows = []
            for r in c.fetchall():
                d = dict(r)
                d["headers"] = json.loads(d["headers"] or "{}")
                d["tags"] = json.loads(d["tags"] or "[]")
                d["response"] = json.loads(d["response"]) if d["response"] else None
                rows.append(d)
            return rows

    def search_requests(self, query: str, project_id: str = None) -> list[dict]:
        with self._cursor() as c:
            where = ["(url LIKE ? OR host LIKE ? OR body LIKE ?)"]
            params = [f"%{query}%", f"%{query}%", f"%{query}%"]
            if project_id:
                where.append("project_id=?"); params.append(project_id)
            clause = "WHERE " + " AND ".join(where)
            c.execute(f"SELECT * FROM requests {clause} ORDER BY timestamp DESC LIMIT 500", params)
            return [dict(r) for r in c.fetchall()]

    def delete_request(self, req_id: str):
        with self._cursor() as c:
            c.execute("DELETE FROM requests WHERE id=?", (req_id,))

    def clear_requests(self, project_id: str = None):
        with self._cursor() as c:
            if project_id:
                c.execute("DELETE FROM requests WHERE project_id=?", (project_id,))
            else:
                c.execute("DELETE FROM requests")

    # ── Reports ─────────────────────────────────────────────────────────
    def save_report(self, report_id: str, project_id: str, name: str,
                    fmt: str, path: str, summary: str = ""):
        with self._cursor() as c:
            c.execute(
                "INSERT OR REPLACE INTO reports(id,project_id,name,created_at,format,path,summary) VALUES(?,?,?,?,?,?,?)",
                (report_id, project_id, name, time.time(), fmt, path, summary),
            )

    def get_reports(self, project_id: str = None) -> list[dict]:
        with self._cursor() as c:
            if project_id:
                c.execute("SELECT * FROM reports WHERE project_id=? ORDER BY created_at DESC", (project_id,))
            else:
                c.execute("SELECT * FROM reports ORDER BY created_at DESC")
            return [dict(r) for r in c.fetchall()]

    # ── Settings ────────────────────────────────────────────────────────
    def get_setting(self, key: str, default: Any = None) -> Any:
        with self._cursor() as c:
            c.execute("SELECT value FROM settings WHERE key=?", (key,))
            row = c.fetchone()
            if row:
                try:
                    return json.loads(row["value"])
                except Exception:
                    return row["value"]
            return default

    def set_setting(self, key: str, value: Any):
        with self._cursor() as c:
            c.execute(
                "INSERT OR REPLACE INTO settings(key,value,updated_at) VALUES(?,?,?)",
                (key, json.dumps(value), time.time()),
            )

    # ── Plugins ─────────────────────────────────────────────────────────
    def register_plugin(self, plugin_id: str, name: str, version: str,
                        path: str, manifest: dict):
        with self._cursor() as c:
            c.execute(
                """INSERT OR REPLACE INTO plugins(id,name,version,enabled,path,manifest,installed_at)
                   VALUES(?,?,?,1,?,?,?)""",
                (plugin_id, name, version, path, json.dumps(manifest), time.time()),
            )

    def get_plugins(self) -> list[dict]:
        with self._cursor() as c:
            c.execute("SELECT * FROM plugins ORDER BY name")
            rows = []
            for r in c.fetchall():
                d = dict(r)
                d["manifest"] = json.loads(d.get("manifest") or "{}")
                rows.append(d)
            return rows

    def set_plugin_enabled(self, plugin_id: str, enabled: bool):
        with self._cursor() as c:
            c.execute("UPDATE plugins SET enabled=? WHERE id=?", (int(enabled), plugin_id))

    # ── Logs ────────────────────────────────────────────────────────────
    def log(self, level: str, module: str, message: str):
        with self._cursor() as c:
            c.execute(
                "INSERT INTO logs(timestamp,level,module,message) VALUES(?,?,?,?)",
                (time.time(), level, module, message),
            )

    def get_logs(self, limit: int = 1000, level: str = None) -> list[dict]:
        with self._cursor() as c:
            if level:
                c.execute("SELECT * FROM logs WHERE level=? ORDER BY timestamp DESC LIMIT ?", (level, limit))
            else:
                c.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT ?", (limit,))
            return [dict(r) for r in c.fetchall()]

    def vacuum(self):
        conn = self._get_conn()
        conn.execute("VACUUM")
        conn.commit()

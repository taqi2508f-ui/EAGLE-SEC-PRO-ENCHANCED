import json
import time
import uuid
from pathlib import Path
from typing import Optional
from .logger import get_logger

logger = get_logger("session_manager")
SESSION_DIR = Path(__file__).resolve().parent.parent / "database" / "sessions"
SESSION_DIR.mkdir(parents=True, exist_ok=True)


class Session:
    def __init__(self, name: str = "Default Session", session_id: str = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.name = name
        self.created_at = time.time()
        self.updated_at = time.time()
        self.requests: list[dict] = []
        self.notes: str = ""
        self.tags: list[str] = []
        self.settings: dict = {}

    def add_request(self, req: dict):
        req["id"] = str(uuid.uuid4())
        req["timestamp"] = time.time()
        self.requests.append(req)
        self.updated_at = time.time()

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "requests": self.requests,
            "notes": self.notes,
            "tags": self.tags,
            "settings": self.settings,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        s = cls(name=data.get("name", "Session"), session_id=data.get("session_id"))
        s.created_at = data.get("created_at", time.time())
        s.updated_at = data.get("updated_at", time.time())
        s.requests = data.get("requests", [])
        s.notes = data.get("notes", "")
        s.tags = data.get("tags", [])
        s.settings = data.get("settings", {})
        return s


class SessionManager:
    def __init__(self):
        self.current: Optional[Session] = None
        self._sessions: dict[str, Session] = {}
        self._load_all()

    def new_session(self, name: str = "New Session") -> Session:
        s = Session(name=name)
        self._sessions[s.session_id] = s
        self.current = s
        logger.info("New session created: %s (%s)", s.name, s.session_id)
        return s

    def load_session(self, session_id: str) -> Optional[Session]:
        if session_id in self._sessions:
            self.current = self._sessions[session_id]
            return self.current
        path = SESSION_DIR / f"{session_id}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                s = Session.from_dict(data)
                self._sessions[s.session_id] = s
                self.current = s
                return s
            except Exception as e:
                logger.error("Failed to load session %s: %s", session_id, e)
        return None

    def save_session(self, session: Session = None):
        s = session or self.current
        if not s:
            return
        path = SESSION_DIR / f"{s.session_id}.json"
        try:
            path.write_text(json.dumps(s.to_dict(), indent=2), encoding="utf-8")
            logger.debug("Session saved: %s", s.session_id)
        except Exception as e:
            logger.error("Failed to save session: %s", e)

    def delete_session(self, session_id: str) -> bool:
        self._sessions.pop(session_id, None)
        path = SESSION_DIR / f"{session_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    def list_sessions(self) -> list[dict]:
        result = []
        for path in sorted(SESSION_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                result.append({
                    "session_id": data.get("session_id"),
                    "name": data.get("name", "Unnamed"),
                    "updated_at": data.get("updated_at", 0),
                    "request_count": len(data.get("requests", [])),
                })
            except Exception:
                pass
        return result

    def _load_all(self):
        for path in SESSION_DIR.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                s = Session.from_dict(data)
                self._sessions[s.session_id] = s
            except Exception:
                pass
        logger.info("Loaded %d sessions from disk", len(self._sessions))

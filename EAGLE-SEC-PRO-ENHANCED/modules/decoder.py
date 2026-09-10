import base64
import binascii
import hashlib
import json
import re
import urllib.parse
from typing import Optional

from core.logger import get_logger

logger = get_logger("decoder")


class DecoderEngine:
    """Handles all encode/decode/hash operations."""

    # ── Base64 ──────────────────────────────────────────────────────────
    @staticmethod
    def b64_decode(text: str) -> tuple[str, str]:
        try:
            padded = text + "=" * (-len(text) % 4)
            return base64.b64decode(padded).decode("utf-8", errors="replace"), "success"
        except Exception as e:
            return "", str(e)

    @staticmethod
    def b64_encode(text: str) -> tuple[str, str]:
        try:
            return base64.b64encode(text.encode("utf-8")).decode(), "success"
        except Exception as e:
            return "", str(e)

    @staticmethod
    def b64url_decode(text: str) -> tuple[str, str]:
        try:
            padded = text + "=" * (-len(text) % 4)
            return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace"), "success"
        except Exception as e:
            return "", str(e)

    @staticmethod
    def b64url_encode(text: str) -> tuple[str, str]:
        try:
            return base64.urlsafe_b64encode(text.encode()).decode().rstrip("="), "success"
        except Exception as e:
            return "", str(e)

    # ── URL ─────────────────────────────────────────────────────────────
    @staticmethod
    def url_decode(text: str) -> tuple[str, str]:
        try:
            return urllib.parse.unquote_plus(text), "success"
        except Exception as e:
            return "", str(e)

    @staticmethod
    def url_encode(text: str) -> tuple[str, str]:
        try:
            return urllib.parse.quote_plus(text), "success"
        except Exception as e:
            return "", str(e)

    @staticmethod
    def url_encode_all(text: str) -> tuple[str, str]:
        try:
            return urllib.parse.quote(text, safe=""), "success"
        except Exception as e:
            return "", str(e)

    # ── Hex ─────────────────────────────────────────────────────────────
    @staticmethod
    def hex_decode(text: str) -> tuple[str, str]:
        try:
            clean = text.replace(" ", "").replace("0x", "").replace("\\x", "")
            return bytes.fromhex(clean).decode("utf-8", errors="replace"), "success"
        except Exception as e:
            return "", str(e)

    @staticmethod
    def hex_encode(text: str) -> tuple[str, str]:
        try:
            return text.encode("utf-8").hex(), "success"
        except Exception as e:
            return "", str(e)

    @staticmethod
    def hex_encode_formatted(text: str) -> tuple[str, str]:
        try:
            h = text.encode("utf-8").hex()
            return " ".join(h[i:i+2] for i in range(0, len(h), 2)), "success"
        except Exception as e:
            return "", str(e)

    # ── JWT ─────────────────────────────────────────────────────────────
    @staticmethod
    def jwt_decode(token: str) -> tuple[dict, str]:
        try:
            parts = token.strip().split(".")
            if len(parts) != 3:
                return {}, "Invalid JWT: expected 3 parts"

            def _b64_dec(s: str) -> dict:
                padded = s + "=" * (-len(s) % 4)
                raw = base64.urlsafe_b64decode(padded)
                return json.loads(raw)

            header = _b64_dec(parts[0])
            payload = _b64_dec(parts[1])
            signature = parts[2]
            return {
                "header": header,
                "payload": payload,
                "signature": signature,
                "raw_parts": parts,
            }, "success"
        except Exception as e:
            return {}, str(e)

    @staticmethod
    def jwt_encode_unsigned(header: dict, payload: dict) -> tuple[str, str]:
        try:
            def _b64_enc(d: dict) -> str:
                return base64.urlsafe_b64encode(json.dumps(d, separators=(",", ":")).encode()).decode().rstrip("=")

            return f"{_b64_enc(header)}.{_b64_enc(payload)}.", "success"
        except Exception as e:
            return "", str(e)

    # ── JSON ────────────────────────────────────────────────────────────
    @staticmethod
    def json_format(text: str, indent: int = 2) -> tuple[str, str]:
        try:
            data = json.loads(text)
            return json.dumps(data, indent=indent, ensure_ascii=False), "success"
        except Exception as e:
            return "", str(e)

    @staticmethod
    def json_minify(text: str) -> tuple[str, str]:
        try:
            data = json.loads(text)
            return json.dumps(data, separators=(",", ":"), ensure_ascii=False), "success"
        except Exception as e:
            return "", str(e)

    # ── Hashes ──────────────────────────────────────────────────────────
    @staticmethod
    def hash_all(text: str) -> dict[str, str]:
        data = text.encode("utf-8")
        return {
            "md5":    hashlib.md5(data).hexdigest(),
            "sha1":   hashlib.sha1(data).hexdigest(),
            "sha256": hashlib.sha256(data).hexdigest(),
            "sha384": hashlib.sha384(data).hexdigest(),
            "sha512": hashlib.sha512(data).hexdigest(),
        }

    @staticmethod
    def hash_file(path: str) -> dict[str, str]:
        try:
            with open(path, "rb") as f:
                data = f.read()
            return {
                "md5":    hashlib.md5(data).hexdigest(),
                "sha1":   hashlib.sha1(data).hexdigest(),
                "sha256": hashlib.sha256(data).hexdigest(),
                "sha512": hashlib.sha512(data).hexdigest(),
            }
        except Exception as e:
            return {"error": str(e)}

    # ── HTML ────────────────────────────────────────────────────────────
    @staticmethod
    def html_encode(text: str) -> tuple[str, str]:
        import html
        try:
            return html.escape(text), "success"
        except Exception as e:
            return "", str(e)

    @staticmethod
    def html_decode(text: str) -> tuple[str, str]:
        import html
        try:
            return html.unescape(text), "success"
        except Exception as e:
            return "", str(e)

    # ── Auto-detect ─────────────────────────────────────────────────────
    @staticmethod
    def smart_decode(text: str) -> list[dict]:
        """Try multiple decode methods and return successful ones."""
        results = []
        engine = DecoderEngine()

        attempts = [
            ("Base64", engine.b64_decode),
            ("Base64 URL-safe", engine.b64url_decode),
            ("URL decode", engine.url_decode),
            ("Hex", engine.hex_decode),
            ("HTML", engine.html_decode),
        ]

        if text.count(".") == 2:
            jwt_result, jwt_status = engine.jwt_decode(text)
            if jwt_status == "success":
                results.append({"method": "JWT", "result": json.dumps(jwt_result, indent=2), "status": "success"})

        for name, fn in attempts:
            res, status = fn(text)
            if status == "success" and res and res != text:
                results.append({"method": name, "result": res, "status": "success"})

        return results

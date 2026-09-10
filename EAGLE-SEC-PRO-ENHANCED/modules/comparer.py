import difflib
import re
from dataclasses import dataclass
from typing import Optional

from core.logger import get_logger

logger = get_logger("comparer")


@dataclass
class DiffResult:
    similarity: float
    diff_lines: list[str]
    added: int
    removed: int
    unchanged: int
    unified_diff: str
    html_diff: str


class ComparerEngine:
    """Compares two HTTP requests/responses or arbitrary text."""

    @staticmethod
    def compare_text(a: str, b: str, context_lines: int = 3) -> DiffResult:
        a_lines = a.splitlines(keepends=True)
        b_lines = b.splitlines(keepends=True)

        matcher = difflib.SequenceMatcher(None, a_lines, b_lines)
        ratio = matcher.ratio()

        unified = list(difflib.unified_diff(
            a_lines, b_lines,
            fromfile="Original", tofile="Modified",
            n=context_lines,
        ))

        html = difflib.HtmlDiff(wrapcolumn=80).make_table(
            a_lines, b_lines, fromdesc="Original", todesc="Modified", context=True, numlines=context_lines
        )

        added = removed = unchanged = 0
        for op, i1, i2, j1, j2 in matcher.get_opcodes():
            if op == "insert":
                added += j2 - j1
            elif op == "delete":
                removed += i2 - i1
            elif op == "equal":
                unchanged += i2 - i1
            elif op == "replace":
                removed += i2 - i1
                added += j2 - j1

        return DiffResult(
            similarity=round(ratio * 100, 2),
            diff_lines=unified,
            added=added,
            removed=removed,
            unchanged=unchanged,
            unified_diff="".join(unified),
            html_diff=html,
        )

    @staticmethod
    def compare_headers(h1: dict, h2: dict) -> dict:
        all_keys = set(h1) | set(h2)
        result = {"added": {}, "removed": {}, "changed": {}, "unchanged": {}}
        for k in all_keys:
            if k in h1 and k not in h2:
                result["removed"][k] = h1[k]
            elif k not in h1 and k in h2:
                result["added"][k] = h2[k]
            elif h1[k] != h2[k]:
                result["changed"][k] = {"original": h1[k], "modified": h2[k]}
            else:
                result["unchanged"][k] = h1[k]
        return result

    @staticmethod
    def compare_requests(req1: dict, req2: dict) -> dict:
        return {
            "method": {"original": req1.get("method"), "modified": req2.get("method"),
                       "changed": req1.get("method") != req2.get("method")},
            "url":    {"original": req1.get("url"), "modified": req2.get("url"),
                       "changed": req1.get("url") != req2.get("url")},
            "headers": ComparerEngine.compare_headers(
                req1.get("headers", {}), req2.get("headers", {})
            ),
            "body": ComparerEngine.compare_text(
                req1.get("body", ""), req2.get("body", "")
            ),
        }

    @staticmethod
    def highlight_diff_line(line: str) -> str:
        if line.startswith("+"):
            return f'<span style="color:#00FF88">{line}</span>'
        elif line.startswith("-"):
            return f'<span style="color:#FF4444">{line}</span>'
        elif line.startswith("@@"):
            return f'<span style="color:#00D4FF">{line}</span>'
        return line

import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.logger import get_logger

logger = get_logger("reporter")

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
EXPORTS_DIR = Path(__file__).resolve().parent.parent / "exports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>EAGLE-SEC PRO Report - {title}</title>
<style>
  :root {{
    --bg: #0a0e1a;
    --surface: #111827;
    --border: #1e3a5f;
    --accent: #00D4FF;
    --accent2: #00FF88;
    --warn: #FFB800;
    --danger: #FF4444;
    --text: #e2e8f0;
    --muted: #64748b;
    --font: 'Consolas', 'Courier New', monospace;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: var(--font); font-size: 13px; }}
  header {{ background: linear-gradient(135deg, #0d1b2e 0%, #0a1628 100%);
    border-bottom: 2px solid var(--accent); padding: 24px 32px; }}
  header h1 {{ color: var(--accent); font-size: 26px; letter-spacing: 4px; text-transform: uppercase; }}
  header p {{ color: var(--muted); margin-top: 6px; }}
  .badge {{ display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:700; }}
  .badge-info {{ background:#0ea5e930; color:#38bdf8; border:1px solid #0ea5e9; }}
  .badge-warn {{ background:#f5930020; color:#fbbf24; border:1px solid #f59300; }}
  .badge-danger {{ background:#ef444420; color:#f87171; border:1px solid #ef4444; }}
  .badge-ok {{ background:#22c55e20; color:#4ade80; border:1px solid #22c55e; }}
  .container {{ max-width:1200px; margin:0 auto; padding:32px; }}
  .card {{ background:var(--surface); border:1px solid var(--border); border-radius:8px;
    padding:20px; margin-bottom:20px; }}
  .card h2 {{ color:var(--accent); font-size:14px; letter-spacing:2px; text-transform:uppercase;
    margin-bottom:16px; padding-bottom:8px; border-bottom:1px solid var(--border); }}
  .stats-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:16px; }}
  .stat {{ background:#0d1b2e; border:1px solid var(--border); border-radius:8px; padding:16px; text-align:center; }}
  .stat .val {{ font-size:28px; font-weight:700; color:var(--accent); }}
  .stat .lbl {{ color:var(--muted); font-size:11px; margin-top:4px; text-transform:uppercase; letter-spacing:1px; }}
  table {{ width:100%; border-collapse:collapse; font-size:12px; }}
  th {{ background:#0d1b2e; color:var(--accent); text-align:left; padding:10px 12px;
    text-transform:uppercase; letter-spacing:1px; font-size:11px; border-bottom:2px solid var(--border); }}
  td {{ padding:9px 12px; border-bottom:1px solid #1e2d3d; vertical-align:top; }}
  tr:hover td {{ background:#0d1b2e55; }}
  .method {{ font-weight:700; }}
  .GET {{ color:#38bdf8; }} .POST {{ color:#4ade80; }} .PUT {{ color:#fbbf24; }}
  .DELETE {{ color:#f87171; }} .PATCH {{ color:#a78bfa; }}
  .status-2xx {{ color:#4ade80; }} .status-3xx {{ color:#fbbf24; }}
  .status-4xx {{ color:#f87171; }} .status-5xx {{ color:#ff6b6b; }}
  pre {{ background:#0a0e1a; border:1px solid var(--border); border-radius:4px;
    padding:12px; overflow-x:auto; white-space:pre-wrap; word-break:break-all; }}
  .findings {{ }}
  .finding {{ border-left:3px solid var(--accent); padding:12px 16px; margin-bottom:12px;
    background:#0d1b2e; border-radius:0 4px 4px 0; }}
  footer {{ text-align:center; color:var(--muted); padding:32px; font-size:11px; border-top:1px solid var(--border); }}
  .glow {{ text-shadow: 0 0 10px var(--accent); }}
</style>
</head>
<body>
<header>
  <h1 class="glow">&#x26F5; EAGLE-SEC PRO</h1>
  <p>Security Audit Report &mdash; Generated {generated_at}</p>
  <p style="margin-top:8px">Project: <strong>{project}</strong> &nbsp;|&nbsp; Report ID: <code>{report_id}</code></p>
</header>
<div class="container">
  <div class="card">
    <h2>Summary</h2>
    <div class="stats-grid">
      <div class="stat"><div class="val">{total_requests}</div><div class="lbl">Total Requests</div></div>
      <div class="stat"><div class="val">{unique_hosts}</div><div class="lbl">Unique Hosts</div></div>
      <div class="stat"><div class="val">{unique_paths}</div><div class="lbl">Unique Paths</div></div>
      <div class="stat"><div class="val">{status_2xx}</div><div class="lbl">200 Responses</div></div>
      <div class="stat"><div class="val" style="color:#f87171">{status_4xx}</div><div class="lbl">4xx Errors</div></div>
      <div class="stat"><div class="val" style="color:#ff6b6b">{status_5xx}</div><div class="lbl">5xx Errors</div></div>
    </div>
  </div>

  {findings_section}

  <div class="card">
    <h2>Request Log ({total_requests} requests)</h2>
    <table>
      <thead>
        <tr>
          <th>#</th><th>Method</th><th>Host</th><th>Path</th>
          <th>Status</th><th>Duration</th><th>Time</th>
        </tr>
      </thead>
      <tbody>
        {request_rows}
      </tbody>
    </table>
  </div>
</div>
<footer>
  <p>EAGLE-SEC PRO v1.0.0 &mdash; Professional Security Testing Suite</p>
  <p style="margin-top:4px">Generated: {generated_at} &mdash; Report ID: {report_id}</p>
</footer>
</body>
</html>"""


class ReportGenerator:
    def __init__(self, reports_dir: Path = REPORTS_DIR, exports_dir: Path = EXPORTS_DIR):
        self.reports_dir = reports_dir
        self.exports_dir = exports_dir

    def generate_html(self, requests: list[dict], project: str = "Default",
                      findings: list[dict] = None, title: str = "Security Report") -> Path:
        report_id = str(uuid.uuid4())[:8].upper()
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        findings = findings or []

        hosts = set(r.get("host", "") for r in requests)
        paths = set(r.get("path", "") for r in requests)

        def status_class(code) -> str:
            if not code:
                return ""
            c = int(code)
            if 200 <= c < 300:
                return "status-2xx"
            if 300 <= c < 400:
                return "status-3xx"
            if 400 <= c < 500:
                return "status-4xx"
            if 500 <= c < 600:
                return "status-5xx"
            return ""

        rows = []
        for i, r in enumerate(requests[:5000], 1):
            resp = r.get("response") or {}
            code = resp.get("status_code", 0)
            ts = datetime.fromtimestamp(r.get("timestamp", 0)).strftime("%H:%M:%S")
            rows.append(
                f"<tr>"
                f"<td>{i}</td>"
                f"<td class='method {r.get('method','')}'>{r.get('method','')}</td>"
                f"<td>{r.get('host','')}</td>"
                f"<td style='max-width:300px;overflow:hidden;text-overflow:ellipsis'>{r.get('path','')}</td>"
                f"<td class='{status_class(code)}'>{code or '-'}</td>"
                f"<td>{r.get('duration_ms',0):.0f}ms</td>"
                f"<td>{ts}</td>"
                f"</tr>"
            )

        findings_html = ""
        if findings:
            items = "".join(
                f"<div class='finding'>"
                f"<strong>{f.get('title','Finding')}</strong> "
                f"<span class='badge badge-warn'>{f.get('severity','INFO')}</span>"
                f"<p style='margin-top:6px;color:#94a3b8'>{f.get('description','')}</p>"
                f"</div>"
                for f in findings
            )
            findings_html = f"<div class='card'><h2>Findings ({len(findings)})</h2>{items}</div>"

        html = HTML_TEMPLATE.format(
            title=title,
            project=project,
            report_id=report_id,
            generated_at=generated_at,
            total_requests=len(requests),
            unique_hosts=len(hosts),
            unique_paths=len(paths),
            status_2xx=sum(1 for r in requests if 200 <= (r.get("response") or {}).get("status_code", 0) < 300),
            status_4xx=sum(1 for r in requests if 400 <= (r.get("response") or {}).get("status_code", 0) < 500),
            status_5xx=sum(1 for r in requests if 500 <= (r.get("response") or {}).get("status_code", 0) < 600),
            request_rows="\n".join(rows),
            findings_section=findings_html,
        )

        out_path = self.reports_dir / f"eagle_report_{report_id}_{int(time.time())}.html"
        out_path.write_text(html, encoding="utf-8")
        logger.info("HTML report saved: %s", out_path)
        return out_path

    def generate_json(self, requests: list[dict], project: str = "Default",
                      findings: list[dict] = None) -> Path:
        report_id = str(uuid.uuid4())[:8].upper()
        data = {
            "report_id": report_id,
            "generated_at": datetime.now().isoformat(),
            "project": project,
            "summary": {
                "total_requests": len(requests),
                "unique_hosts": len(set(r.get("host", "") for r in requests)),
            },
            "findings": findings or [],
            "requests": requests,
        }
        out_path = self.exports_dir / f"eagle_report_{report_id}_{int(time.time())}.json"
        out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        logger.info("JSON report saved: %s", out_path)
        return out_path

    def generate_pdf(self, requests: list[dict], project: str = "Default",
                     findings: list[dict] = None) -> Optional[Path]:
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors
            from reportlab.lib.units import mm
            from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                            Table, TableStyle, HRFlowable)

            report_id = str(uuid.uuid4())[:8].upper()
            out_path = self.reports_dir / f"eagle_report_{report_id}_{int(time.time())}.pdf"

            doc = SimpleDocTemplate(str(out_path), pagesize=A4,
                                    leftMargin=20*mm, rightMargin=20*mm,
                                    topMargin=20*mm, bottomMargin=20*mm)

            BG = colors.HexColor("#0a0e1a")
            ACCENT = colors.HexColor("#00D4FF")
            TEXT = colors.HexColor("#e2e8f0")
            MUTED = colors.HexColor("#64748b")
            GREEN = colors.HexColor("#00FF88")
            RED = colors.HexColor("#FF4444")

            styles = getSampleStyleSheet()
            h1_style = ParagraphStyle("H1", fontName="Helvetica-Bold",
                                      fontSize=20, textColor=ACCENT, spaceAfter=6)
            h2_style = ParagraphStyle("H2", fontName="Helvetica-Bold",
                                      fontSize=13, textColor=ACCENT, spaceAfter=4, spaceBefore=12)
            body_style = ParagraphStyle("Body", fontName="Helvetica",
                                        fontSize=9, textColor=TEXT)
            code_style = ParagraphStyle("Code", fontName="Courier",
                                        fontSize=8, textColor=GREEN)

            story = []
            story.append(Paragraph("EAGLE-SEC PRO", h1_style))
            story.append(Paragraph(f"Security Audit Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                                   body_style))
            story.append(Paragraph(f"Project: {project}  |  Report ID: {report_id}", body_style))
            story.append(Spacer(1, 6*mm))
            story.append(HRFlowable(width="100%", color=ACCENT))
            story.append(Spacer(1, 4*mm))

            story.append(Paragraph("Summary", h2_style))
            hosts = set(r.get("host", "") for r in requests)
            summary_data = [
                ["Metric", "Value"],
                ["Total Requests", str(len(requests))],
                ["Unique Hosts", str(len(hosts))],
                ["Findings", str(len(findings or []))],
                ["Generated At", datetime.now().isoformat()],
            ]
            t = Table(summary_data, colWidths=[80*mm, 90*mm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#111827"), colors.HexColor("#0d1b2e")]),
                ("TEXTCOLOR", (0, 1), (-1, -1), TEXT),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#1e3a5f")),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(t)
            story.append(Spacer(1, 4*mm))

            story.append(Paragraph("Request Log", h2_style))
            req_data = [["#", "Method", "Host", "Path", "Status", "Duration"]]
            for i, r in enumerate(requests[:200], 1):
                resp = r.get("response") or {}
                req_data.append([
                    str(i), r.get("method", ""), r.get("host", ""),
                    (r.get("path", "") or "")[:50],
                    str(resp.get("status_code", "")),
                    f"{r.get('duration_ms', 0):.0f}ms",
                ])
            rt = Table(req_data, colWidths=[10*mm, 18*mm, 50*mm, 55*mm, 18*mm, 18*mm])
            rt.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#111827"), colors.HexColor("#0d1b2e")]),
                ("TEXTCOLOR", (0, 1), (-1, -1), TEXT),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#1e3a5f")),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(rt)

            doc.build(story)
            logger.info("PDF report saved: %s", out_path)
            return out_path
        except ImportError:
            logger.warning("reportlab not installed; skipping PDF")
            return None
        except Exception as e:
            logger.error("PDF generation failed: %s", e)
            return None

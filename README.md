# EAGLE-SEC PRO

**Professional Web Security Testing Suite** — a desktop intercepting proxy for web application security testing, built with Python 3.12 and PyQt6.

EAGLE-SEC PRO brings together the core toolkit a security researcher needs for manual web app testing in a single Windows desktop app: capture and modify HTTP/HTTPS traffic through a local intercepting proxy, replay and tweak requests, diff responses, decode/encode common data formats, and crawl targets to map their attack surface.

![Platform](https://img.shields.io/badge/platform-Windows%2010%2B-blue)
![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![UI](https://img.shields.io/badge/UI-PyQt6-green)
![License](https://img.shields.io/badge/license-UNLICENSED-lightgrey)

---

## ⚠️ Authorized Use Only

EAGLE-SEC PRO is an intercepting proxy intended **only** for testing systems you own or have explicit written authorization to test. Unauthorized interception, modification, or scanning of network traffic may violate the Computer Fraud and Abuse Act (or your local equivalent) and other laws. You are solely responsible for how you use this tool.

---

## Features

| Module | Description |
|---|---|
| 🔌 **Proxy** | HTTP/HTTPS intercepting proxy (default port `8080`) with CA certificate export for HTTPS interception |
| 🔁 **Repeater** | Resend and modify captured requests |
| 🆚 **Comparer** | Side-by-side diff of requests or responses |
| 🔐 **Decoder** | Base64, URL, Hex, JWT encode/decode, plus hashing utilities |
| 🗺️ **Site Map** | Automatic mapping of captured hosts and paths |
| 🕷️ **Crawler** | Recursive web spider with form extraction |
| 📊 **Reports** | Export findings as HTML, PDF, or JSON |
| 🧩 **Plugins** | Extend functionality with custom Python plugins |

---

## Requirements

- Windows 10 Pro or later
- Python 3.12+
- pip (included with Python)

---

## Installation

```bash
git clone https://github.com/your-username/EAGLE-SEC-PRO-ENCHANCED.git
cd eagle-sec-pro
install_requirements.bat
```

## Usage

```bash
launch.bat
```

### Proxy setup (browser)

1. Configure your browser's proxy to `127.0.0.1:8080`.
2. For HTTPS interception, install the CA certificate:
   **Menu → Proxy → Export CA Certificate** → install it in your browser or OS trust store.

### Keyboard shortcuts

| Shortcut | Action |
|---|---|
| `Alt+1..7` | Switch between tabs |
| `Ctrl+N` | New session |
| `Ctrl+O` | Open session |
| `Ctrl+S` | Save session |
| `Ctrl+L` | Clear proxy history |
| `Ctrl+,` | Open settings |

---

## Project Structure

```
main.py              Application entry point
assets/               Icons, images, QSS themes
config/               User settings (JSON)
core/                 Proxy engine, session manager, certificates, logger
database/             SQLite database + session files
exports/              Exported JSON reports
logs/                 Application log files
modules/              Decoder, comparer, site mapper, crawler, reporter
plugins/              Plugin system + example plugins
reports/              Generated HTML/PDF reports
ui/                   PyQt6 UI modules
```

---

## Plugins

Place plugin directories under `plugins/`. Each plugin needs:

- `plugin.json` — manifest (`id`, `name`, `version`, `entry`)
- `main.py` — a `Plugin` class implementing `on_load`, `on_request`, `on_response`

See `plugins/example_logger/` for a working example.

---

## Logs & Data

- Logs: `logs/eagle_sec.log`
- Database: `database/data/eagle_sec.db`

> **Before publishing this repo:** scrub `database/sessions/*.json`, `database/data/*`, and `database/certs/eagle_ca.key` from git history — these contain captured traffic and a private CA key and should never be committed. Add a `.gitignore` covering `database/`, `logs/`, `exports/`, and `reports/`.

---

## License

Add your license of choice here (e.g. MIT, GPLv3) before making this repository public.

---

Built with Python 3.12 + PyQt6.

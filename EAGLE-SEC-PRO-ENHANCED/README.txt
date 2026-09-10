
  ███████╗ █████╗  ██████╗ ██╗     ███████╗       ███████╗███████╗ ██████╗    ██████╗ ██████╗  ██████╗
  ██╔════╝██╔══██╗██╔════╝ ██║     ██╔════╝       ██╔════╝██╔════╝██╔════╝   ██╔══██╗██╔══██╗██╔═══██╗
  █████╗  ███████║██║  ███╗██║     █████╗         ███████╗█████╗  ██║        ██████╔╝██████╔╝██║   ██║
  ██╔══╝  ██╔══██║██║   ██║██║     ██╔══╝         ╚════██║██╔══╝  ██║        ██╔═══╝ ██╔══██╗██║   ██║
  ███████╗██║  ██║╚██████╔╝███████╗███████╗       ███████║███████╗╚██████╗   ██║     ██║  ██║╚██████╔╝
  ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚══════╝       ╚══════╝╚══════╝ ╚═════╝   ╚═╝     ╚═╝  ╚═╝ ╚═════╝

  EAGLE-SEC PRO v1.0.0  —  Professional Web Security Testing Suite
  =================================================================

QUICK START
-----------
1. Double-click install_requirements.bat   (first time only)
2. Double-click launch.bat

REQUIREMENTS
------------
  - Windows 10 Pro or later
  - Python 3.12+ (https://www.python.org/downloads/)
  - pip (included with Python)

FEATURES
--------
  [Proxy]       HTTP/HTTPS intercepting proxy (port 8080 by default)
  [Repeater]    Resend & modify captured requests
  [Comparer]    Side-by-side diff of requests or responses
  [Decoder]     Base64, URL, Hex, JWT decode/encode + hash utilities
  [Site Map]    Auto-map captured hosts and paths
  [Crawler]     Recursive web spider with form extraction
  [Reports]     HTML, PDF, and JSON report generation
  [Plugins]     Extend with custom Python plugins

PROXY SETUP (Browser)
---------------------
  Configure your browser to use:    127.0.0.1 : 8080

  For HTTPS interception, install the CA certificate:
    Menu → Proxy → Export CA Certificate → install in your browser/OS

PROJECT STRUCTURE
-----------------
  main.py              Application entry point
  assets/              Icons, images, QSS themes
  config/              User settings (JSON)
  core/                Proxy engine, session manager, certificates, logger
  database/            SQLite database + session files
  exports/             Exported JSON reports
  logs/                Application log files
  modules/             Decoder, comparer, site mapper, crawler, reporter
  plugins/             Plugin system + example plugins
  reports/             Generated HTML/PDF reports
  ui/                  PyQt6 UI modules

PLUGINS
-------
  Place plugin directories under plugins/ — each plugin needs:
    plugin.json   (manifest: id, name, version, entry)
    main.py       (Plugin class with on_load, on_request, on_response)

  See plugins/example_logger/ for a working example.

KEYBOARD SHORTCUTS
------------------
  Alt+1..7      Switch between tabs
  Ctrl+N        New session
  Ctrl+O        Open session
  Ctrl+S        Save session
  Ctrl+L        Clear proxy history
  Ctrl+,        Open settings

SUPPORT & LOGS
--------------
  Logs are written to: logs/eagle_sec.log
  Database:            database/data/eagle_sec.db

=================================================================
  EAGLE-SEC PRO — Built with Python 3.12 + PyQt6
=================================================================

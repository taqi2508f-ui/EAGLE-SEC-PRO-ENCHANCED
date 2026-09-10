@echo off
title EAGLE-SEC PRO - Dependency Installer
color 0B
echo.
echo  ================================================================
echo   EAGLE-SEC PRO v1.0.0 - Dependency Installer
echo  ================================================================
echo.

:: ── Check Python ─────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found in PATH.
    echo.
    echo  Please install Python 3.10 or newer from:
    echo    https://www.python.org/downloads/
    echo.
    echo  IMPORTANT: Check "Add Python to PATH" during installation!
    pause
    exit /b 1
)

echo  [OK] Python found:
python --version
echo.

:: ── Make sure pip actually exists ────────────────────────────────
echo  [*] Checking pip...
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo  [WARN] pip is missing from this Python environment - repairing...

    python -m ensurepip --upgrade >nul 2>&1
    python -m pip --version >nul 2>&1
    if errorlevel 1 (
        echo  [*] ensurepip did not work, downloading get-pip.py instead...
        powershell -NoProfile -Command "Invoke-WebRequest -Uri https://bootstrap.pypa.io/get-pip.py -OutFile '%TEMP%\get-pip.py'" >nul 2>&1
        if exist "%TEMP%\get-pip.py" (
            python "%TEMP%\get-pip.py" --quiet >nul 2>&1
            del "%TEMP%\get-pip.py" >nul 2>&1
        )
    )

    python -m pip --version >nul 2>&1
    if errorlevel 1 (
        echo  [ERROR] Could not install pip automatically.
        echo.
        echo  This usually means the venv at:
        echo    %~dp0
        echo  was created without pip, or "python" in your PATH points to a
        echo  broken/embeddable Python install rather than a normal one.
        echo.
        echo  Easiest fix: delete the venv folder and recreate it with:
        echo    python -m venv venv
        echo  ^(a fresh venv includes pip automatically^)
        pause
        exit /b 1
    )
    echo  [OK] pip repaired.
) else (
    echo  [OK] pip found.
)
echo.

:: ── Upgrade pip ──────────────────────────────────────────────────
echo  [*] Upgrading pip...
python -m pip install --upgrade pip --quiet
echo  [OK] pip upgraded.
echo.

:: ── Install core packages one by one ─────────────────────────────
echo  [*] Installing required packages...
echo      (some packages take a moment - please wait)
echo.

set FAILED=0

:: PyQt6 - required, must succeed
echo  [*] Installing PyQt6...
python -m pip install "PyQt6>=6.6.0" --quiet
if errorlevel 1 (
    echo  [ERROR] PyQt6 installation failed!
    echo  Try manually: pip install PyQt6
    set FAILED=1
) else (
    echo  [OK] PyQt6
)

:: cryptography - for HTTPS CA cert generation
echo  [*] Installing cryptography...
python -m pip install "cryptography>=41.0.0" --quiet
if errorlevel 1 (
    echo  [WARN] cryptography failed - HTTPS interception will be disabled
) else (
    echo  [OK] cryptography
)

:: requests - for web crawler
echo  [*] Installing requests...
python -m pip install "requests>=2.31.0" --quiet
if errorlevel 1 (
    echo  [WARN] requests failed - Crawler will be disabled
) else (
    echo  [OK] requests
)

:: beautifulsoup4 - for HTML parsing
echo  [*] Installing beautifulsoup4...
python -m pip install "beautifulsoup4>=4.12.0" --quiet
if errorlevel 1 (
    echo  [WARN] beautifulsoup4 failed - Crawler HTML parsing disabled
) else (
    echo  [OK] beautifulsoup4
)

:: lxml - fast HTML parser (optional, falls back to html.parser)
echo  [*] Installing lxml...
python -m pip install "lxml>=4.9.0" --quiet
if errorlevel 1 (
    echo  [WARN] lxml not installed - using built-in html.parser instead (this is fine)
) else (
    echo  [OK] lxml
)

:: reportlab - for PDF reports (optional)
echo  [*] Installing reportlab...
python -m pip install "reportlab>=4.0.0" --quiet
if errorlevel 1 (
    echo  [WARN] reportlab not installed - PDF reports will be unavailable
    echo         HTML and JSON reports will still work.
) else (
    echo  [OK] reportlab
)

echo.

:: ── Result ───────────────────────────────────────────────────────
if %FAILED%==1 (
    echo  ================================================================
    echo   [ERROR] PyQt6 is required but failed to install.
    echo   EAGLE-SEC PRO cannot run without it.
    echo.
    echo   Try running this command manually:
    echo     pip install PyQt6 --user
    echo  ================================================================
    echo.
    pause
    exit /b 1
)

echo  ================================================================
echo   [OK] Installation complete!
echo.
echo   Run launch.bat to start EAGLE-SEC PRO
echo  ================================================================
echo.
pause

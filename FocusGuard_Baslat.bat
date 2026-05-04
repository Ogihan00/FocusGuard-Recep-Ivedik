@echo off
cd /d "%~dp0"
if exist .venv (
    start "" ".venv\Scripts\pythonw.exe" focus_guard.py
) else (
    echo [.venv] klasoru bulunamadi! Lutfen once kurulumu yapin.
    pause
)
exit

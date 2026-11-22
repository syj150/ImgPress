@echo off
rem 若尚未安装依赖，先运行： python scripts\bootstrap.py --build
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\pythonw.exe" (
  start "" ".venv\Scripts\pythonw.exe" main.py
) else (
  start "" pythonw main.py
)

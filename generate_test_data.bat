@echo off
cd /d "%~dp0backend"
if not exist .venv\Scripts\python.exe (
  echo Сначала выполните run_backend_first_time.bat
  pause
  exit /b 1
)
.venv\Scripts\python.exe manage.py generate_test_data
pause

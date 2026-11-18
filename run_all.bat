@echo off
setlocal
cd /d "%~dp0"
title MATFLOW launcher

echo ========================================
echo   MATFLOW - запуск Django + Vue
echo ========================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ОШИБКА] Python не найден в PATH.
    echo Установи Python 3.12/3.13 и отметь Add Python to PATH.
    pause
    exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
    echo [ОШИБКА] npm не найден в PATH.
    echo Установи Node.js LTS.
    pause
    exit /b 1
)

if not exist "backend\.venv\Scripts\python.exe" (
    echo [1/5] Создаю виртуальное окружение...
    python -m venv "backend\.venv" || goto :fail
    echo [2/5] Устанавливаю Python-зависимости...
    "backend\.venv\Scripts\python.exe" -m pip install --upgrade pip || goto :fail
    "backend\.venv\Scripts\python.exe" -m pip install -r "backend\requirements.txt" || goto :fail
) else (
    echo [1/5] Python-окружение найдено.
)

if not exist "frontend\node_modules" (
    echo [3/5] Устанавливаю frontend-зависимости...
    pushd "frontend"
    call npm install || goto :fail_popd
    popd
) else (
    echo [3/5] node_modules найден.
)

echo [4/5] Применяю миграции...
"backend\.venv\Scripts\python.exe" "backend\manage.py" migrate || goto :fail
"backend\.venv\Scripts\python.exe" "backend\manage.py" ensure_demo_user || goto :fail

if not exist "backend\.matflow_iteration3_initialized" (
    echo [5/5] Создаю тестовые данные итерации 3...
    "backend\.venv\Scripts\python.exe" "backend\manage.py" generate_test_data || goto :fail
    echo initialized>"backend\.matflow_iteration3_initialized"
) else (
    echo [5/5] Тестовые данные уже инициализированы.
)

echo.
echo Запускаю backend и frontend в отдельных окнах...
start "MATFLOW Backend" cmd /k "cd /d ""%~dp0backend"" && .venv\Scripts\python.exe manage.py runserver"
start "MATFLOW Frontend" cmd /k "cd /d ""%~dp0frontend"" && npm run dev"

echo Ожидаю запуск серверов...
timeout /t 5 /nobreak >nul
start "" "http://127.0.0.1:5173"

echo.
echo Готово. Окно запуска можно закрыть.
echo Backend:  http://127.0.0.1:8000
echo Frontend: http://127.0.0.1:5173
echo Логин: admin / admin123
exit /b 0

:fail_popd
popd
:fail
echo.
echo [ОШИБКА] Установка или подготовка проекта завершилась с ошибкой.
pause
exit /b 1

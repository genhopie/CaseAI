@echo off
setlocal

echo ==========================================
echo Local Case AI - Install and Start
echo ==========================================

cd /d %~dp0

echo.
echo [1/4] Setting up Python environment...
cd services\local_api
if not exist .venv (
    py -m venv .venv
)
call .venv\Scripts\activate
pip install -r requirements.txt

echo.
echo [2/4] Starting API server...
start cmd /k "call .venv\Scripts\activate && py -m app.main"

cd ..\..\apps\desktop

echo.
echo [3/4] Installing Node dependencies...
if not exist node_modules (
    npm install
)

echo.
echo [4/4] Starting UI...
start cmd /k "npm run dev"

echo.
echo Application starting...
echo Open: http://localhost:5173
pause

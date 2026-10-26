@echo off
cd /d "%~dp0"
echo Creating Python virtual environment...
py -m venv .venv
if errorlevel 1 (
  echo Python launcher not found. Install Python 3.11+ and enable "Add Python to PATH".
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if not exist .env copy .env.example .env
echo.
echo Setup complete. Edit .env and add your API/email credentials.
pause

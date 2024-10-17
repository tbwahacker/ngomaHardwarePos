@echo off
setlocal enabledelayedexpansion

REM Define the base directory to search
set BASE_DIR=D:\POS\ngomaHardware\ngomahardware

REM Check if the base directory exists
if not exist %BASE_DIR% (
    echo The directory %BASE_DIR% does not exist.
    exit /b 1
)
echo %BASE_DIR% exists.
REM Change to the project directory
cd /d %BASE_DIR%

REM Run the Django development server
venv/Scripts/activate
python manage.py runserver

endlocal

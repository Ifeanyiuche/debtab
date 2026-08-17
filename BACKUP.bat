@echo off
setlocal enabledelayedexpansion
title DebTab - Backup Database
color 0B

REM ===============================================================
REM  Saves a complete copy of the live database to this computer.
REM
REM  Neon keeps your data safe, but a backup you physically own is
REM  the only kind nobody else can lose, expire, or delete. Run this
REM  after every tournament. It takes seconds.
REM ===============================================================

set "REPO=C:\Users\hp\debtab"
cd /d "%REPO%" 2>nul || (echo Could not find %REPO% & pause & exit /b 1)

cls
echo.
echo   ============================================================
echo                  DebTab  -  Database Backup
echo   ============================================================
echo.

if not exist ".env" (
    color 0E
    echo   SETUP NEEDED - one time only.
    echo.
    echo   To back up the live database, this computer needs to know
    echo   how to reach it.
    echo.
    echo     1. Open the file called  .env  in this folder with Notepad.
    echo        ^(If it does not exist, make a copy of .env.example
    echo         and rename the copy to  .env  ^)
    echo.
    echo     2. Add this line to the bottom, pasting your Neon
    echo        connection string after the equals sign:
    echo.
    echo          DATABASE_URL=postgresql://...your Neon string...
    echo.
    echo     3. Save the file and run this backup again.
    echo.
    echo   The .env file never leaves your computer - it is excluded
    echo   from GitHub automatically.
    echo.
    pause
    exit /b 1
)

findstr /b /c:"DATABASE_URL=" .env >nul 2>&1
if errorlevel 1 (
    color 0E
    echo   Your .env file exists but has no DATABASE_URL line.
    echo.
    echo   Open .env in Notepad and add:
    echo      DATABASE_URL=postgresql://...your Neon string...
    echo.
    pause
    exit /b 1
)

if not exist "backups" mkdir backups

for /f "tokens=2 delims==" %%i in ('wmic os get localdatetime /value 2^>nul') do set "DT=%%i"
set "STAMP=!DT:~0,4!-!DT:~4,2!-!DT:~6,2!_!DT:~8,2!!DT:~10,2!"
set "OUTFILE=backups\debtab-!STAMP!.json"

echo   Connecting to the live database...
echo   ^(it may take a few seconds to wake up^)
echo.

python manage.py dumpdata ^
    --natural-foreign --natural-primary ^
    --exclude contenttypes --exclude auth.permission ^
    --exclude sessions.session --exclude admin.logentry ^
    --indent 2 --output "!OUTFILE!"

if errorlevel 1 (
    color 0C
    echo.
    echo   BACKUP FAILED - nothing was saved.
    echo.
    echo   Most likely causes:
    echo     - DATABASE_URL in .env is wrong or out of date
    echo     - No internet connection
    echo     - Python packages missing. Run:  pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

color 0A
echo.
echo   ============================================================
echo                       BACKUP SAVED
echo   ============================================================
echo.
echo   File:  !OUTFILE!
for %%A in ("!OUTFILE!") do echo   Size:  %%~zA bytes
echo.
echo   Keep a copy somewhere off this computer too - OneDrive,
echo   Google Drive, or an external drive. A backup that lives only
echo   on the same machine is not really a backup.
echo.
echo   Opening the backups folder...
start "" "%REPO%\backups"
echo.
timeout /t 8 /nobreak >nul
exit /b 0

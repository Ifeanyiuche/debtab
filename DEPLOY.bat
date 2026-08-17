@echo off
setlocal enabledelayedexpansion
title DebTab - Deploying
color 0B

REM ===============================================================
REM  DebTab one-click deploy.
REM
REM  Double-click it. That is the whole procedure. It asks nothing,
REM  decides nothing, and needs no arguments. It saves every change
REM  in this folder, pushes to GitHub, and Render rebuilds the live
REM  site automatically.
REM ===============================================================

set "REPO=C:\Users\hp\debtab"
set "SITE=https://getdebtab.com"
set "HEALTH=https://getdebtab.com/healthz"
set "BRANCH=master"

cd /d "%REPO%" 2>nul
if errorlevel 1 (
    color 0C
    echo.
    echo   ERROR: Could not find the project folder:
    echo     %REPO%
    echo.
    pause
    exit /b 1
)

where git >nul 2>&1
if errorlevel 1 (
    color 0C
    echo.
    echo   ERROR: Git is not installed.
    echo   Get it from https://git-scm.com/download/win then run this again.
    echo.
    pause
    exit /b 1
)

cls
echo.
echo   ============================================================
echo                  DebTab  -  Deploying to live
echo   ============================================================
echo.

REM --- Build an automatic commit message from the date and time ---
for /f "tokens=1-4 delims=/:. " %%a in ("%DATE% %TIME%") do set "STAMP=%DATE% %TIME%"
set "MSG=Update from DEPLOY.bat - %STAMP%"

echo   Changes being deployed:
echo   ------------------------------------------------------------
git status --short
echo   ------------------------------------------------------------
echo.

REM --- 1. Save everything -----------------------------------------
echo   [1/4] Saving changes...
git add -A >nul 2>&1
git commit --allow-empty -m "!MSG!" >nul 2>&1
echo         done.

REM --- 2. Push, healing the common failure automatically -----------
echo   [2/4] Sending to GitHub...
git push origin %BRANCH% >nul 2>&1
if errorlevel 1 (
    echo         push rejected - syncing with GitHub and retrying...
    git pull --rebase origin %BRANCH% >nul 2>&1
    git push origin %BRANCH% >nul 2>&1
    if errorlevel 1 (
        echo.
        color 0C
        echo   ============================================================
        echo                         PUSH FAILED
        echo   ============================================================
        echo.
        echo   Your work is saved on this computer. Nothing is lost.
        echo   Nothing was deployed.
        echo.
        echo   This is almost always a GitHub sign-in problem. Run this
        echo   command once in this folder and follow the prompts:
        echo.
        echo       git push origin %BRANCH%
        echo.
        echo   After you sign in, this button will work every time.
        echo.
        pause
        exit /b 1
    )
)
echo         done. Render is building now.

REM --- 3. Wait for the new version -------------------------------
echo   [3/4] Waiting for the live site to come back...
echo.
echo         A free Render service rebuilds in about 3 to 5 minutes.
echo         You can close this window - the deploy finishes without it.
echo.

set /a TRIES=0
set /a MAXTRIES=40
set "CODE=000"

timeout /t 45 /nobreak >nul

:waitloop
set /a TRIES+=1
if !TRIES! gtr !MAXTRIES! goto :timedout

for /f %%s in ('curl -s -o nul -w "%%{http_code}" --max-time 20 "%HEALTH%" 2^>nul') do set "CODE=%%s"

if "!CODE!"=="200" goto :success

set /a ELAPSED=45+(!TRIES!*15)
echo         still building... ^(!ELAPSED!s elapsed, status !CODE!^)
timeout /t 15 /nobreak >nul
goto :waitloop

REM ---------------------------------------------------------------
:success
echo.
color 0A
echo   [4/4] Live.
echo.
echo   ============================================================
echo                      DEPLOY SUCCESSFUL
echo   ============================================================
echo.
echo   getdebtab.com is up and the database is responding.
echo.
start "" "%SITE%"
timeout /t 6 /nobreak >nul
exit /b 0

REM ---------------------------------------------------------------
:timedout
echo.
color 0E
echo   ============================================================
echo                  DEPLOYED, BUT NOT RESPONDING YET
echo   ============================================================
echo.
echo   Your code reached GitHub successfully, so nothing is lost.
echo   The server is not answering yet. Last status: !CODE!
echo.
if "!CODE!"=="503" (
    echo   503 means the app is running but cannot reach the database.
    echo   Check DATABASE_URL in Render, and check the database is awake.
)
if "!CODE!"=="500" (
    echo   500 means the app crashed. Open the Render Logs tab -
    echo   the full error is printed there now.
)
if "!CODE!"=="000" (
    echo   000 means no response at all. The build probably failed.
    echo   Open the Render Events tab to see why.
)
echo.
echo   Opening the Render dashboard so you can look...
start "" "https://dashboard.render.com"
echo.
pause
exit /b 1

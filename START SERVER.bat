@echo off
title DebTab Server
cd /d C:\Users\hp\debtab
echo.
echo  ==========================================
echo   DebTab - Debate Tabulation System
echo  ==========================================
echo.
echo  Starting server...
echo  Open your browser and go to:
echo  http://127.0.0.1:8000
echo.
echo  Press Ctrl+C to stop the server.
echo  DO NOT close this window while using DebTab.
echo.
python manage.py runserver
echo.
echo  Server stopped. Press any key to close.
pause

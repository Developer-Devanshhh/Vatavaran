@echo off
REM Script to push Vatavaran project to GitHub (Windows)

echo ==========================================
echo Pushing Vatavaran to GitHub
echo ==========================================
echo.

REM Check if git is initialized
if not exist ".git" (
    echo Initializing git repository...
    git init
    echo [OK] Git initialized
) else (
    echo [OK] Git already initialized
)

REM Add remote
echo.
echo Adding GitHub remote...
git remote remove origin 2>nul
git remote add origin https://github.com/Developer-Devanshhh/Vatavaran.git
echo [OK] Remote added

REM Add all files
echo.
echo Adding files to git...
git add .
echo [OK] Files added

REM Commit
echo.
echo Committing changes...
git commit -m "Initial commit: Vatavaran Climate Control System - Complete Django backend with LSTM inference - Weather API integration with caching - NLP command parser for voice control - CSV schedule generator - Raspberry Pi components (sensor, STT, IR blaster) - Comprehensive testing suite (76 unit tests) - Full documentation and deployment guides"
echo [OK] Changes committed

REM Push to GitHub
echo.
echo Pushing to GitHub...
echo Note: You may need to enter your GitHub credentials
git branch -M main
git push -u origin main

echo.
echo ==========================================
echo [OK] Successfully pushed to GitHub!
echo ==========================================
echo.
echo Repository: https://github.com/Developer-Devanshhh/Vatavaran
echo.
pause

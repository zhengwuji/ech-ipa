@echo off
chcp 65001 >nul
echo ========================================
echo   自动推送到GitHub - 无需确认
echo ========================================
echo.
python auto_commit_push.py
echo.
echo ========================================
pause


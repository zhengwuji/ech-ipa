@echo off
REM 设置自动推送的批处理脚本
REM 每次修改代码后运行此脚本会自动提交并推送到GitHub

echo 正在自动提交并推送到GitHub...
python auto_commit_push.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✓ 代码已成功推送到GitHub！
    echo GitHub Actions 将自动构建并发布新版本。
) else (
    echo.
    echo ✗ 推送失败，请检查错误信息。
)

pause


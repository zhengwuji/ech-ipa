@echo off
chcp 65001 >nul
echo ========================================
echo   清理Chrome驱动缓存工具
echo ========================================
echo.
echo 此工具将清除可能损坏的Chrome驱动缓存
echo 下次启动程序时会自动重新下载驱动
echo.

set CACHE_PATH=%USERPROFILE%\.wdm

if exist "%CACHE_PATH%" (
    echo 正在删除缓存文件夹: %CACHE_PATH%
    rd /s /q "%CACHE_PATH%"
    echo.
    echo ✓ 缓存已清除！
    echo.
    echo 下次运行程序时会自动重新下载驱动
) else (
    echo 未找到缓存文件夹，可能已经清理过了
)

echo.
pause


@echo off
chcp 65001 >nul
title 办公室点歌台

echo.
echo  ╔══════════════════════════════════════╗
echo  ║       🎵 办公室点歌台 🎵              ║
echo  ╠══════════════════════════════════════╣
echo  ║                                      ║
echo  ║  正在启动...                          ║
echo  ║                                      ║
echo  ╚══════════════════════════════════════╝
echo.

:: 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python！
    echo 请先安装 Python: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 提醒管理员密码
if "%WEBKARAOKE_ADMIN_PASSWORD%"=="" (
    echo [提示] 当前未设置 WEBKARAOKE_ADMIN_PASSWORD，将使用 config.py 中的默认密码。
    echo 建议在启动前执行:
    echo   set WEBKARAOKE_ADMIN_PASSWORD=你的强密码
    echo.
)

:: 检查 mpv
where mpv >nul 2>&1
if %errorlevel% neq 0 (
    echo [警告] 未找到 mpv 播放器！
    echo 安装方法: scoop bucket add extras ^&^& scoop install mpv
    echo 或从 https://mpv.io/installation/ 下载
    echo.
)

:: 安装依赖
echo [检查] 安装依赖...
python -m pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo [错误] 依赖安装失败，请检查网络或 Python 环境。
    pause
    exit /b 1
)

:: 检查 yt-dlp
python -m yt_dlp --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [警告] yt-dlp 检查失败，搜索下载功能可能不可用。
    echo.
)

:: 启动
echo [启动] 正在启动点歌台...
echo 浏览器地址: http://localhost:9800
echo.
python app.py

pause

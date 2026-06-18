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
pip install -r requirements.txt -q

:: 启动
echo [启动] 正在启动点歌台...
echo.
python app.py

pause

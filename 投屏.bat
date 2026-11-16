@echo off
chcp 65001 >nul
setlocal

:: scrcpy 由 winget 安装，路径里带版本号，这里自动找最新的
set "SCRCPY="
for /d %%D in ("%LOCALAPPDATA%\Microsoft\WinGet\Packages\Genymobile.scrcpy_*\scrcpy-win64-*") do (
    if exist "%%D\scrcpy.exe" set "SCRCPY=%%D\scrcpy.exe"
)
if not defined SCRCPY (
    where scrcpy >nul 2>nul && set "SCRCPY=scrcpy"
)
if not defined SCRCPY (
    echo 没找到 scrcpy，请先运行: winget install Genymobile.scrcpy
    pause
    exit /b 1
)

echo 使用: %SCRCPY%
echo.
echo 常用操作：
echo   鼠标左键 = 点击      按住拖动 = 滑动
echo   鼠标中键 / 右键 = 返回 / 回桌面
echo   Ctrl+Shift+O = 关手机屏幕（省电，投屏仍在）
echo   Ctrl+Shift+F = 全屏      Ctrl+Shift+V = 粘贴剪贴板
echo   关闭窗口即断开（不影响手机）
echo.

:: --max-size 1024 降分辨率减延迟；--stay-awake 投屏期间不休眠
"%SCRCPY%" --max-size 1024 --stay-awake --window-title "手机投屏"

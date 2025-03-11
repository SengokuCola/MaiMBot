@echo off
setlocal enabledelayedexpansion

:: 检查常见的MongoDB安装位置
set "MONGO_PATHS=C:\Program Files\MongoDB\Server"

:: 查找最新版本的MongoDB
set "latest_version="
set "mongo_bin_path="

if exist "%MONGO_PATHS%" (
    for /d %%i in ("%MONGO_PATHS%\*") do (
        set "current=%%~ni"
        if "!current!" GTR "!latest_version!" (
            set "latest_version=!current!"
            set "mongo_bin_path=%%i\bin"
        )
    )
)

:: 检查本地目录中的MongoDB
if exist "%~dp0..\mongodb\bin" (
    set "mongo_bin_path=%~dp0..\mongodb\bin"
)

if not defined mongo_bin_path (
    echo MongoDB未找到。
    exit /b 1
)

:: 获取当前用户的PATH环境变量
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "user_path=%%b"

:: 如果PATH不存在，创建一个新的
if not defined user_path set "user_path="

:: 检查PATH中是否已包含MongoDB路径
echo !user_path! | find /i "%mongo_bin_path%" > nul
if errorlevel 1 (
    :: 添加MongoDB bin目录到PATH
    if defined user_path (
        setx PATH "%mongo_bin_path%;%user_path%"
    ) else (
        setx PATH "%mongo_bin_path%"
    )
    echo MongoDB bin目录已添加到PATH环境变量：%mongo_bin_path%
) else (
    echo MongoDB bin目录已经在PATH环境变量中
)

echo 操作完成。
pause
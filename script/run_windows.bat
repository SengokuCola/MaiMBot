@echo off
setlocal enabledelayedexpansion
chcp 65001

REM 修正路径获取逻辑
cd /d "%~dp0" || (
    echo 错误：切换目录失败
    exit /b 1
)

if not exist "venv\" (
    echo 正在初始化虚拟环境...

    where python >nul 2>&1
    if %errorlevel% neq 0 (
        echo 未找到Python解释器
        exit /b 1
    )

    for /f "tokens=2" %%a in ('python --version 2^>^&1') do set version=%%a
    for /f "tokens=1,2 delims=." %%b in ("!version!") do (
        set major=%%b
        set minor=%%c
    )

    if !major! lss 3 (
        echo 需要Python大于等于3.0，当前版本 !version!
        exit /b 1
    )

    if !major! equ 3 if !minor! lss 9 (
        echo 需要Python大于等于3.9，当前版本 !version!
        exit /b 1
    )

    echo 正在安装virtualenv...
    python -m pip install virtualenv || (
        echo virtualenv安装失败
        exit /b 1
    )

    echo 正在创建虚拟环境...
    python -m virtualenv venv || (
        echo 虚拟环境创建失败
        exit /b 1
    )

    call venv\Scripts\activate.bat

) else (
    call venv\Scripts\activate.bat
)

echo 正在更新依赖...
pip install -r requirements.txt

echo 当前代理设置：
echo HTTP_PROXY=%HTTP_PROXY%
echo HTTPS_PROXY=%HTTPS_PROXY%

set HTTP_PROXY=
set HTTPS_PROXY=
echo 代理已取消。

set no_proxy=0.0.0.0/32

call nb run
pause
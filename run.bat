@echo off
chcp 65001 >nul

:: 检查 Python 是否安装
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo 错误：未安装 Python
    echo 请从 https://www.python.org/downloads/ 下载并安装 Python
    pause
    exit /b 1
)

:: 检查虚拟环境是否存在
if not exist venv (
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -i https://mirrors.aliyun.com/pypi/simple --upgrade -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

:: 运行 Python 脚本
python run.py

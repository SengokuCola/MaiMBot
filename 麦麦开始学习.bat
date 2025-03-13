@echo off
setlocal enabledelayedexpansion
chcp 65001
cd /d %~dp0

echo =====================================
echo 选择Python环境:
echo 1 - venv (推荐)
echo 2 - conda
echo =====================================
choice /c 12 /n /m "输入数字(1或2): "

if errorlevel 2 (
    echo =====================================
    set "CONDA_ENV="
    set /p CONDA_ENV="请输入要激活的 conda 环境名称: "
    
    :: 检查输入是否为空
    if "!CONDA_ENV!"=="" (
        echo 错误：环境名称不能为空
        pause
        exit /b 1
    )
    
    call conda activate !CONDA_ENV!
    if errorlevel 1 (
        echo 激活 conda 环境失败
        pause
        exit /b 1
    )
    
    echo Conda 环境 "!CONDA_ENV!" 激活成功
    python src/plugins/knowledge_library/knowledge_library.py
) else (
    if exist "venv\Scripts\python.exe" (
        venv\Scripts\python src/plugins/knowledge_library/knowledge_library.py
    ) else (
        echo =====================================
        echo 错误: venv环境不存在，请先创建虚拟环境
        pause
        exit /b 1
    )
)
endlocal
pause

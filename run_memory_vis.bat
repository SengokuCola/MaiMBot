@echo on
chcp 65001 > nul 
set /p CONDA_ENV="请输入要激活的 conda 环境名称: "
call conda activate %CONDA_ENV%
if errorlevel 1 (
    echo 激活 conda 环境失败
    pause
    exit /b 1
)
echo Conda 环境 "%CONDA_ENV%" 激活成功

set /p OPTION="请选择运行选项 (1: 运行全部绘制, 2: 运行简单绘制): "
if "%OPTION%"=="1" (
    python src/plugins/memory_system/memory_manual_build.py
) else if "%OPTION%"=="2" (
    python src/plugins/memory_system/draw_memory.py
) else (
    echo 无效的选项
    pause
    exit /b 1
)

if errorlevel 1 (
    echo 命令执行失败，错误代码 %errorlevel%
    pause
    exit /b 1
)
echo 脚本成功完成
pause
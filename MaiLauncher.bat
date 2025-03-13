@echo off
@REM setlocal enabledelayedexpansion
@chcp 65001

@REM 设置版本号
set "VERSION=0.3"

title 麦麦Bot控制台 v%VERSION%

@REM 设置Python和Git环境变量
set "_root=%~dp0"
set "_root=%_root:~0,-1%"
cd "%_root%"
echo "%_root%

if exist "%_root%\python" (
    set "PYTHON_HOME=%_root%\python"
) else if exist "%_root%\venv" (
    call "%_root%\venv\Scripts\activate.bat"
    set "PYTHON_HOME=%_root%\venv\Scripts"
) else if python -V >nul 2>&1 (
    for /f "delims=" %%a in ('where python') do (
        set "PYTHON_HOME=%%~dpa"
    )
) else if python3 -V >nul 2>&1 (
    for /f "delims=" %%a in ('where python3') do (
        set "PYTHON_HOME=%%~dpa"
    )
) else (
    echo Python环境未找到，请检查安装路径。
    exit /b
)

if exist "%_root%\tools\git\bin" (
    set "GIT_HOME=%_root%\tools\git\bin"
) else if git -v >nul 2>&1 (
    for /f "delims=" %%a in ('where git') do (
        set "GIT_HOME=%%~dpa"
    )
) else (
    echo Git环境未找到，请检查安装路径。
    exit /b
)


set "GIT_HOME=%_root%\tools\git\bin"
set "PATH=%PYTHON_HOME%;%GIT_HOME%;%PATH%"


@REM git获取当前分支名并保存在变量里
for /f "delims=" %%b in ('git symbolic-ref --short HEAD 2^>nul') do (
    set "BRANCH=%%b"
)

@REM 根据不同分支名给分支名字符串使用不同颜色
echo 分支名: %BRANCH%
if "%BRANCH%"=="main" (
    set "BRANCH_COLOR=[92m"
) else if "%BRANCH%"=="debug" (
    set "BRANCH_COLOR=[91m"
) else if "%BRANCH%"=="stable-dev" (
    set "BRANCH_COLOR=[96m"
) else (
    set "BRANCH_COLOR=[93m"
)

@REM endlocal & set "BRANCH_COLOR=%BRANCH_COLOR%"


:menu
@chcp 65001
cls
echo 麦麦Bot控制台 v%VERSION%  当前分支: %BRANCH_COLOR%%BRANCH%[0m
echo ======================
echo 1. 更新并启动麦麦Bot (默认)
echo 2. 直接启动麦麦Bot
echo 3. 麦麦配置菜单
echo 4. 麦麦神奇工具箱
echo 5. 退出
echo ======================

set /p choice="请输入选项数字 (1-5)并按下回车以选择: "

if "%choice%"=="" set choice=1

if "%choice%"=="1" goto update_and_start
if "%choice%"=="2" goto start_bot
if "%choice%"=="3" goto config_menu
if "%choice%"=="4" goto tools_menu
if "%choice%"=="5" exit /b

echo 无效的输入，请输入1-5之间的数字
timeout /t 2 >nul
goto menu

:config_menu
@chcp 65001
cls
echo 配置菜单
echo ======================
echo 1. 编辑配置文件 (config.toml)
echo 2. 编辑环境变量 (.env.prod)
echo 3. 打开安装目录
echo 4. 返回主菜单
echo ======================

set /p choice="请输入选项数字: "

if "%choice%"=="1" goto edit_config
if "%choice%"=="2" goto edit_env
if "%choice%"=="3" goto open_dir
if "%choice%"=="4" goto menu

echo 无效的输入，请输入1-4之间的数字
timeout /t 2 >nul
goto config_menu

:tools_menu
@chcp 65001
cls
echo 麦麦时尚工具箱  当前分支: %BRANCH_COLOR%%BRANCH%[0m
echo ======================
echo 1. 更新依赖
echo 2. 切换分支
echo 3. 更新配置文件
echo 4. 学习新的知识库
echo 5. 打开知识库文件夹
echo 6. 返回主菜单
echo ======================

set /p choice="请输入选项数字: "
if "%choice%"=="1" goto update_dependencies
if "%choice%"=="2" goto switch_branch
if "%choice%"=="3" goto update_config
if "%choice%"=="4" goto learn_new_knowledge
if "%choice%"=="5" goto open_knowledge_folder
if "%choice%"=="6" goto menu

echo 无效的输入，请输入1-6之间的数字
timeout /t 2 >nul
goto tools_menu

:update_dependencies
cls
echo 正在更新依赖...
python -m pip config set global.index-url https://mirrors.aliyun.com/pypi/simple
python.exe -m pip install -r requirements.txt

echo 依赖更新完成，按任意键返回工具箱菜单...
pause
goto tools_menu

:switch_branch
cls
echo 正在切换分支...
echo 当前分支: %BRANCH%
echo 可用分支: main, debug, stable-dev
echo 请输入要切换到的分支名 ([92mmain/[91mdebug/[96mstable-dev[0m):
set /p branch_name="分支名: "
if "%branch_name%"=="" set branch_name=main
if "%branch_name%"=="main" (
    set "BRANCH_COLOR=[92m"
) else if "%branch_name%"=="debug" (
    set "BRANCH_COLOR=[91m"
) else if "%branch_name%"=="stable-dev" (
    set "BRANCH_COLOR=[96m"
) else (
    echo 无效的分支名, 请重新输入
    timeout /t 2 >nul
    goto switch_branch
)

echo 正在切换到分支 %branch_name%...
git checkout %branch_name%
echo 分支切换完成，当前分支: %BRANCH_COLOR%%branch_name%[0m
set "BRANCH=%branch_name%"
echo 按任意键返回工具箱菜单...
pause >nul
goto tools_menu


:update_config
cls
echo 正在更新配置文件...
echo 请确保已备份重要数据，继续将修改当前配置文件。
echo 继续请按Y，取消请按任意键...
set /p confirm="继续？(Y/N): "
if /i "%confirm%"=="Y" (
    echo 正在更新配置文件...
    python\python.exe config\auto_update.py
    echo 配置文件更新完成，按任意键返回工具箱菜单...
) else (
    echo 取消更新配置文件，按任意键返回工具箱菜单...
)
pause >nul
goto tools_menu

:learn_new_knowledge
cls
echo 正在学习新的知识库...
echo 请确保已备份重要数据，继续将修改当前知识库。
echo 继续请按Y，取消请按任意键...
set /p confirm="继续？(Y/N): "
if /i "%confirm%"=="Y" (
    echo 正在学习新的知识库...
    python\python.exe src\plugins\zhishi\knowledge_library.py
    echo 学习完成，按任意键返回工具箱菜单...
) else (
    echo 取消学习新的知识库，按任意键返回工具箱菜单...
)
pause >nul
goto tools_menu

:open_knowledge_folder
cls
echo 正在打开知识库文件夹...
if exist data\raw_info (
    start explorer data\raw_info
) else (
    echo 知识库文件夹不存在！
    echo 正在创建文件夹...
    mkdir data\raw_info
    timeout /t 2 >nul
)
goto tools_menu


:update_and_start
cls
:retry_git_pull
tools\git\bin\git.exe pull > temp.log 2>&1
findstr /C:"detected dubious ownership" temp.log >nul
if %errorlevel% equ 0 (
    echo 检测到仓库权限问题，正在自动修复...
    tools\git\bin\git.exe config --global --add safe.directory "%cd%"
    echo 已添加例外，正在重试git pull...
    del temp.log
    goto retry_git_pull
)
del temp.log
echo 正在更新依赖...
python\python.exe -m pip config set global.index-url https://mirrors.aliyun.com/pypi/simple
python\python.exe -m pip install -r requirements.txt && cls

echo 当前代理设置:
echo HTTP_PROXY=%HTTP_PROXY%
echo HTTPS_PROXY=%HTTPS_PROXY%

echo Disable Proxy...
set HTTP_PROXY=
set HTTPS_PROXY=
set no_proxy=0.0.0.0/32

REM chcp 65001
python\python.exe bot.py
echo.
echo Bot已停止运行，按任意键返回主菜单...
pause >nul
goto menu

:start_bot
cls
echo 正在更新依赖...
python\python.exe -m pip config set global.index-url https://mirrors.aliyun.com/pypi/simple
python\python.exe -m pip install -r requirements.txt && cls

echo 当前代理设置:
echo HTTP_PROXY=%HTTP_PROXY%
echo HTTPS_PROXY=%HTTPS_PROXY%

echo Disable Proxy...
set HTTP_PROXY=
set HTTPS_PROXY=
set no_proxy=0.0.0.0/32

REM chcp 65001
python\python.exe bot.py
echo.
echo Bot已停止运行，按任意键返回主菜单...
pause >nul
goto menu

:edit_config
if exist config/bot_config.toml (
    start notepad config/bot_config.toml
) else (
    echo 配置文件 bot_config.toml 不存在！
    timeout /t 2 >nul
)
goto menu

:edit_env
if exist .env.prod (
    start notepad .env.prod
) else (
    echo 环境文件 .env.prod 不存在！
    timeout /t 2 >nul
)
goto menu

:open_dir
start explorer "%cd%"
goto menu

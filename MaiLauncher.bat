@echo off
@setlocal enabledelayedexpansion
@chcp 936

@REM 设置版本号
set "VERSION=1.0"

title 麦麦Bot控制台 v%VERSION%

@REM 设置Python和Git环境变量
set "_root=%~dp0"
set "_root=%_root:~0,-1%"
cd "%_root%"


:search_python
cls
if exist "%_root%\python" (
    set "PYTHON_HOME=%_root%\python"
) else if exist "%_root%\venv" (
    call "%_root%\venv\Scripts\activate.bat"
    set "PYTHON_HOME=%_root%\venv\Scripts"
) else (
    echo 正在自动查找Python解释器...

    where python >nul 2>&1
    if %errorlevel% equ 0 (
        for /f "delims=" %%i in ('where python') do (
            echo %%i | findstr /i /c:"!LocalAppData!\Microsoft\WindowsApps\python.exe" >nul
            if errorlevel 1 (
                echo 找到Python解释器：%%i
                set "py_path=%%i"
                goto :validate_python
            )
        )
    )
    set "search_paths=%ProgramFiles%\Git*;!LocalAppData!\Programs\Python\Python*"
    for /d %%d in (!search_paths!) do (
        if exist "%%d\python.exe" (
            set "py_path=%%d\python.exe"
            goto :validate_python
        )
    )
    echo 没有找到Python解释器,要安装吗?
    set /p pyinstall_confirm="继续？(Y/n): "
    if /i "!pyinstall_confirm!"=="Y" (
        cls
        echo 正在安装Python...
        winget install --id Python.Python.3.13 -e --accept-package-agreements --accept-source-agreements
        if %errorlevel% neq 0 (
            echo 安装失败，请手动安装Python
            start https://www.python.org/downloads/
            exit /b
        )
        echo 安装完成，正在验证Python...
        goto search_python

    ) else (
        echo 取消安装Python，按任意键退出...
        pause >nul
        exit /b
    )

    echo 错误：未找到可用的Python解释器！
    exit /b 1

    :validate_python
    "!py_path!" --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo 无效的Python解释器：%py_path%
        exit /b 1
    )

    :: 提取安装目录
    for %%i in ("%py_path%") do set "PYTHON_HOME=%%~dpi"
    set "PYTHON_HOME=%PYTHON_HOME:~0,-1%"
)
if not exist "%PYTHON_HOME%\python.exe" (
    echo Python路径验证失败：%PYTHON_HOME%
    echo 请检查Python安装路径中是否有python.exe文件
    exit /b 1
)
echo 成功设置Python路径：%PYTHON_HOME%



:search_git
cls
if exist "%_root%\tools\git\bin" (
    set "GIT_HOME=%_root%\tools\git\bin"
) else (
    echo 正在自动查找Git...

    where git >nul 2>&1
    if %errorlevel% equ 0 (
        for /f "delims=" %%i in ('where git') do (
            set "git_path=%%i"
            goto :validate_git
        )
    )
    echo 正在扫描常见安装路径...
    set "search_paths=!ProgramFiles!\Git\cmd"
    for /f "tokens=*" %%d in ("!search_paths!") do (
        if exist "%%d\git.exe" (
            set "git_path=%%d\git.exe"
            goto :validate_git
        )
    )
    echo 没有找到Git，要安装吗？
    set /p confirm="继续？(Y/N): "
    if /i "!confirm!"=="Y" (
        cls
        echo 正在安装Git...
        set "custom_url=https://ghfast.top/https://github.com/git-for-windows/git/releases/download/v2.48.1.windows.1/Git-2.48.1-64-bit.exe"

        set "download_path=%TEMP%\Git-Installer.exe"

        echo 正在下载Git安装包...
        curl -L -o "!download_path!" "!custom_url!"

        if exist "!download_path!" (
            echo 下载成功，开始安装Git...
            start /wait "" "!download_path!" /SILENT /NORESTART
        ) else (
            echo 下载失败，请手动安装Git
            start https://git-scm.com/download/win
            exit /b
        )

        del "!download_path!"
        echo 临时文件已清理。

        echo 安装完成，正在验证Git...
        where git >nul 2>&1
        if %errorlevel% equ 0 (
            for /f "delims=" %%i in ('where git') do (
                set "git_path=%%i"
                goto :validate_git
            )
            goto :search_git

        ) else (
            echo 安装完成，但未找到Git，请手动安装Git
            start https://git-scm.com/download/win
            exit /b
        )

    ) else (
        echo 取消安装Git，按任意键退出...
        pause >nul
        exit /b
    )

    echo 错误：未找到可用的Git！
    exit /b 1

    :validate_git
    "%git_path%" --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo 无效的Git：%git_path%
        exit /b 1
    )

    :: 提取安装目录
    for %%i in ("%git_path%") do set "GIT_HOME=%%~dpi"
    set "GIT_HOME=%GIT_HOME:~0,-1%"
)

:search_mongodb
cls
sc query | findstr /i "MongoDB" >nul
if !errorlevel! neq 0 (
    echo MongoDB服务未运行，正在尝试启动...
    powershell -Command "Start-Process -Verb RunAs cmd -ArgumentList '/c net start MongoDB'"
    echo 正在等待MongoDB服务启动...
    echo 按下任意键跳过等待...
    timeout /t 30 >nul
    sc query | findstr /i "MongoDB" >nul
    if !errorlevel! neq 0 (
        echo MongoDB服务启动失败，可能是没有安装，要安装吗？
        set /p confirm="继续？(Y/N): "
        if /i "!confirm!"=="Y" (
            echo 正在安装MongoDB...
            winget install --id MongoDB.Server -e --accept-package-agreements --accept-source-agreements
            echo 安装完成，正在启动MongoDB服务...
            net start MongoDB
            if %errorlevel% neq 0 (
                echo 启动MongoDB服务失败，请手动启动
                exit /b
            )
            echo MongoDB服务已启动
        ) else (
            echo 取消安装MongoDB，按任意键退出...
            pause >nul
            exit /b
        )
    )
) else (
    echo MongoDB服务已运行
)

@REM set "GIT_HOME=%_root%\tools\git\bin"
set "PATH=%PYTHON_HOME%;%GIT_HOME%;%PATH%"

:install_maim
if not exist "!_root!\bot.py" (
    cls
    echo 你似乎没有安装麦麦Bot，要安装在当前目录吗？
    set /p confirm="继续？(Y/N): "
    if /i "!confirm!"=="Y" (
        echo 要使用Git代理下载吗？
        set /p proxy_confirm="继续？(Y/N): "
        if /i "!proxy_confirm!"=="Y" (
            echo 正在安装麦麦Bot...
            git clone https://ghfast.top/https://github.com/SengokuCola/MaiMBot
        ) else (
            echo 正在安装麦麦Bot...
            git clone https://github.com/SengokuCola/MaiMBot
        )
        xcopy /E /H /I MaiMBot . >nul 2>&1
        rmdir /s /q MaiMBot
        git checkout main-fix

        echo 安装完成，正在安装依赖...
        python -m pip config set global.index-url https://mirrors.aliyun.com/pypi/simple
        python -m pip install virtualenv
        python -m virtualenv venv
        call venv\Scripts\activate.bat
        python -m pip install -r requirements.txt

        echo 安装完成，要编辑配置文件吗？
        set /p edit_confirm="继续？(Y/N): "
        if /i "!edit_confirm!"=="Y" (
            goto config_menu
        ) else (
            echo 取消编辑配置文件，按任意键返回主菜单...
        )
    )
)


@REM git获取当前分支名并保存在变量里
for /f "delims=" %%b in ('git symbolic-ref --short HEAD 2^>nul') do (
    set "BRANCH=%%b"
)

@REM 根据不同分支名给分支名字符串使用不同颜色
echo 分支名: %BRANCH%
if "!BRANCH!"=="main" (
    set "BRANCH_COLOR=[92m"
) else if "!BRANCH!"=="main-fix" (
    set "BRANCH_COLOR=[91m"
@REM ) else if "%BRANCH%"=="stable-dev" (
@REM     set "BRANCH_COLOR=[96m"
) else (
    set "BRANCH_COLOR=[93m"
)

@REM endlocal & set "BRANCH_COLOR=%BRANCH_COLOR%"

:check_is_venv
echo 正在检查是否在虚拟环境中...
if exist "%_root%\config\no_venv" (
    echo 检测到no_venv,跳过虚拟环境检查
    goto menu
)
if not defined VIRTUAL_ENV (
    echo 当前使用的Python环境为：
    echo !PYTHON_HOME!
    echo 似乎没有使用虚拟环境，是否要创建一个新的虚拟环境？
    set /p confirm="继续？(Y/N): "
    if /i "!confirm!"=="Y" (
        echo 正在创建虚拟环境...
        python -m virtualenv venv
        call venv\Scripts\activate.bat
        echo 要安装依赖吗？
        set /p install_confirm="继续？(Y/N): "
        if /i "%install_confirm%"=="Y" (
            echo 正在安装依赖...
            python -m pip config set global.index-url https://mirrors.aliyun.com/pypi/simple
            python -m pip install -r requirements.txt
        )
        echo 虚拟环境创建完成，按任意键返回...
    ) else (
        echo 要永久跳过虚拟环境检查吗？
        set /p no_venv_confirm="继续？(Y/N): "
        if /i "!no_venv_confirm!"=="Y" (
            echo 正在创建no_venv文件...
            echo 1 > "%_root%\config\no_venv"
            echo 已创建no_venv文件，按任意键返回...
        ) else (
            echo 取消跳过虚拟环境检查，按任意键返回...
        )
    )
    pause >nul
)
goto menu

:menu
@chcp 936
cls
echo 麦麦Bot控制台 v%VERSION%  当前分支: %BRANCH_COLOR%%BRANCH%[0m
echo 当前Python环境: [96m!PYTHON_HOME![0m
echo ======================
echo 1. 更新并启动麦麦Bot (默认)
echo 2. 直接启动麦麦Bot
echo 3. 启动麦麦配置界面
echo 4. 打开麦麦神奇工具箱
echo 5. 退出
echo ======================

set /p choice="请输入选项数字 (1-5)并按下回车以选择: "

if "!choice!"=="" set choice=1

if "!choice!"=="1" goto update_and_start
if "!choice!"=="2" goto start_bot
if "!choice!"=="3" goto config_menu
if "!choice!"=="4" goto tools_menu
if "!choice!"=="5" exit /b

echo 无效的输入，请输入1-5之间的数字
timeout /t 2 >nul
goto menu

:config_menu
@chcp 936
cls
if not exist config/bot_config.toml (
    copy /Y "template\bot_config_template.toml" "config\bot_config.toml"

)
if not exist .env.prod (
    copy /Y "template.env" ".env.prod"
)

start python webui.py

goto menu


:tools_menu
@chcp 936
cls
echo 麦麦时尚工具箱  当前分支: %BRANCH_COLOR%%BRANCH%[0m
echo ======================
echo 1. 更新依赖
echo 2. 切换分支
echo 3. 重置当前分支
echo 4. 更新配置文件
echo 5. 学习新的知识库
echo 6. 打开知识库文件夹
echo 7. 返回主菜单
echo ======================

set /p choice="请输入选项数字: "
if "!choice!"=="1" goto update_dependencies
if "!choice!"=="2" goto switch_branch
if "!choice!"=="3" goto reset_branch
if "!choice!"=="4" goto update_config
if "!choice!"=="5" goto learn_new_knowledge
if "!choice!"=="6" goto open_knowledge_folder
if "!choice!"=="7" goto menu

echo 无效的输入，请输入1-7之间的数字
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
@REM echo 可用分支: main, debug, stable-dev
echo 1. 切换到[92mmain[0m
echo 2. 切换到[91mmain-fix[0m
echo 请输入要切换到的分支:
set /p branch_name="分支名: "
if "%branch_name%"=="" set branch_name=main
if "%branch_name%"=="main" (
    set "BRANCH_COLOR=[92m"
) else if "%branch_name%"=="main-fix" (
    set "BRANCH_COLOR=[91m"
@REM ) else if "%branch_name%"=="stable-dev" (
@REM     set "BRANCH_COLOR=[96m"
) else if "%branch_name%"=="1" (
    set "BRANCH_COLOR=[92m"
    set "branch_name=main"
) else if "%branch_name%"=="2" (
    set "BRANCH_COLOR=[91m"
    set "branch_name=main-fix"
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


:reset_branch
cls
echo 正在重置当前分支...
echo 当前分支: !BRANCH!
echo 确认要重置当前分支吗？
set /p confirm="继续？(Y/N): "
if /i "!confirm!"=="Y" (
    echo 正在重置当前分支...
    git reset --hard !BRANCH!
    echo 分支重置完成，按任意键返回工具箱菜单...
) else (
    echo 取消重置当前分支，按任意键返回工具箱菜单...
)
pause >nul
goto tools_menu


:update_config
cls
echo 正在更新配置文件...
echo 请确保已备份重要数据，继续将修改当前配置文件。
echo 继续请按Y，取消请按任意键...
set /p confirm="继续？(Y/N): "
if /i "!confirm!"=="Y" (
    echo 正在更新配置文件...
    python.exe config\auto_update.py
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
if /i "!confirm!"=="Y" (
    echo 正在学习新的知识库...
    python.exe src\plugins\zhishi\knowledge_library.py
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
git pull > temp.log 2>&1
findstr /C:"detected dubious ownership" temp.log >nul
if %errorlevel% equ 0 (
    echo 检测到仓库权限问题，正在自动修复...
    git config --global --add safe.directory "%cd%"
    echo 已添加例外，正在重试git pull...
    del temp.log
    goto retry_git_pull
)
del temp.log
echo 正在更新依赖...
python -m pip config set global.index-url https://mirrors.aliyun.com/pypi/simple
python -m pip install -r requirements.txt && cls

echo 当前代理设置:
echo HTTP_PROXY=%HTTP_PROXY%
echo HTTPS_PROXY=%HTTPS_PROXY%

echo Disable Proxy...
set HTTP_PROXY=
set HTTPS_PROXY=
set no_proxy=0.0.0.0/32

REM chcp 65001
python bot.py
echo.
echo Bot已停止运行，按任意键返回主菜单...
pause >nul
goto menu

:start_bot
cls
echo 正在更新依赖...
python -m pip config set global.index-url https://mirrors.aliyun.com/pypi/simple
python -m pip install -r requirements.txt && cls

echo 当前代理设置:
echo HTTP_PROXY=%HTTP_PROXY%
echo HTTPS_PROXY=%HTTPS_PROXY%

echo Disable Proxy...
set HTTP_PROXY=
set HTTPS_PROXY=
set no_proxy=0.0.0.0/32

REM chcp 65001
python bot.py
echo.
echo Bot已停止运行，按任意键返回主菜单...
pause >nul
goto menu


:open_dir
start explorer "%cd%"
goto menu

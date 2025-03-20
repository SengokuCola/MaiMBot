@echo off
@setlocal enabledelayedexpansion
@chcp 936

@REM ÉèÖÃ°æ±¾ºÅ
set "VERSION=1.0"

title ÂóÂóBot¿ØÖÆÌ¨ v%VERSION%

@REM ÉèÖÃPythonºÍGit»·¾³±äÁ¿
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
    echo ÕýÔÚ×Ô¶¯²éÕÒPython½âÊÍÆ÷...

    where python >nul 2>&1
    if %errorlevel% equ 0 (
        for /f "delims=" %%i in ('where python') do (
            echo %%i | findstr /i /c:"!LocalAppData!\Microsoft\WindowsApps\python.exe" >nul
            if errorlevel 1 (
                echo ÕÒµ½Python½âÊÍÆ÷£º%%i
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
    echo Ã»ÓÐÕÒµ½Python½âÊÍÆ÷,Òª°²×°Âð?
    set /p pyinstall_confirm="¼ÌÐø£¿(Y/n): "
    if /i "!pyinstall_confirm!"=="Y" (
        cls
        echo ÕýÔÚ°²×°Python...
        winget install --id Python.Python.3.13 -e --accept-package-agreements --accept-source-agreements
        if %errorlevel% neq 0 (
            echo °²×°Ê§°Ü£¬ÇëÊÖ¶¯°²×°Python
            start https://www.python.org/downloads/
            exit /b
        )
        echo °²×°Íê³É£¬ÕýÔÚÑéÖ¤Python...
        goto search_python

    ) else (
        echo È¡Ïû°²×°Python£¬°´ÈÎÒâ¼üÍË³ö...
        pause >nul
        exit /b
    )

    echo ´íÎó£ºÎ´ÕÒµ½¿ÉÓÃµÄPython½âÊÍÆ÷£¡
    exit /b 1

    :validate_python
    "!py_path!" --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo ÎÞÐ§µÄPython½âÊÍÆ÷£º%py_path%
        exit /b 1
    )

    :: ÌáÈ¡°²×°Ä¿Â¼
    for %%i in ("%py_path%") do set "PYTHON_HOME=%%~dpi"
    set "PYTHON_HOME=%PYTHON_HOME:~0,-1%"
)
if not exist "%PYTHON_HOME%\python.exe" (
    echo PythonÂ·¾¶ÑéÖ¤Ê§°Ü£º%PYTHON_HOME%
    echo Çë¼ì²éPython°²×°Â·¾¶ÖÐÊÇ·ñÓÐpython.exeÎÄ¼þ
    exit /b 1
)
echo ³É¹¦ÉèÖÃPythonÂ·¾¶£º%PYTHON_HOME%



:search_git
cls
if exist "%_root%\tools\git\bin" (
    set "GIT_HOME=%_root%\tools\git\bin"
) else (
    echo ÕýÔÚ×Ô¶¯²éÕÒGit...

    where git >nul 2>&1
    if %errorlevel% equ 0 (
        for /f "delims=" %%i in ('where git') do (
            set "git_path=%%i"
            goto :validate_git
        )
    )
    echo ÕýÔÚÉ¨Ãè³£¼û°²×°Â·¾¶...
    set "search_paths=!ProgramFiles!\Git\cmd"
    for /f "tokens=*" %%d in ("!search_paths!") do (
        if exist "%%d\git.exe" (
            set "git_path=%%d\git.exe"
            goto :validate_git
        )
    )
    echo Ã»ÓÐÕÒµ½Git£¬Òª°²×°Âð£¿
    set /p confirm="¼ÌÐø£¿(Y/N): "
    if /i "!confirm!"=="Y" (
        cls
        echo ÕýÔÚ°²×°Git...
        set "custom_url=https://ghfast.top/https://github.com/git-for-windows/git/releases/download/v2.48.1.windows.1/Git-2.48.1-64-bit.exe"

        set "download_path=%TEMP%\Git-Installer.exe"

        echo ÕýÔÚÏÂÔØGit°²×°°ü...
        curl -L -o "!download_path!" "!custom_url!"

        if exist "!download_path!" (
            echo ÏÂÔØ³É¹¦£¬¿ªÊ¼°²×°Git...
            start /wait "" "!download_path!" /SILENT /NORESTART
        ) else (
            echo ÏÂÔØÊ§°Ü£¬ÇëÊÖ¶¯°²×°Git
            start https://git-scm.com/download/win
            exit /b
        )

        del "!download_path!"
        echo ÁÙÊ±ÎÄ¼þÒÑÇåÀí¡£

        echo °²×°Íê³É£¬ÕýÔÚÑéÖ¤Git...
        where git >nul 2>&1
        if %errorlevel% equ 0 (
            for /f "delims=" %%i in ('where git') do (
                set "git_path=%%i"
                goto :validate_git
            )
            goto :search_git

        ) else (
            echo °²×°Íê³É£¬µ«Î´ÕÒµ½Git£¬ÇëÊÖ¶¯°²×°Git
            start https://git-scm.com/download/win
            exit /b
        )

    ) else (
        echo È¡Ïû°²×°Git£¬°´ÈÎÒâ¼üÍË³ö...
        pause >nul
        exit /b
    )

    echo ´íÎó£ºÎ´ÕÒµ½¿ÉÓÃµÄGit£¡
    exit /b 1

    :validate_git
    "%git_path%" --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo ÎÞÐ§µÄGit£º%git_path%
        exit /b 1
    )

    :: ÌáÈ¡°²×°Ä¿Â¼
    for %%i in ("%git_path%") do set "GIT_HOME=%%~dpi"
    set "GIT_HOME=%GIT_HOME:~0,-1%"
)

:search_mongodb
cls
sc query | findstr /i "MongoDB" >nul
if !errorlevel! neq 0 (
    echo MongoDB·þÎñÎ´ÔËÐÐ£¬ÊÇ·ñ³¢ÊÔÔËÐÐ·þÎñ£¿
    set /p confirm="ÊÇ·ñÆô¶¯£¿(Y/N): "
    if /i "!confirm!"=="Y" (
        echo ÕýÔÚ³¢ÊÔÆô¶¯MongoDB·þÎñ...
        powershell -Command "Start-Process -Verb RunAs cmd -ArgumentList '/c net start MongoDB'"
        echo ÕýÔÚµÈ´ýMongoDB·þÎñÆô¶¯...
		echo °´ÏÂÈÎÒâ¼üÌø¹ýµÈ´ý...
		timeout /t 30 >nul
        sc query | findstr /i "MongoDB" >nul
        if !errorlevel! neq 0 (
            echo MongoDB·þÎñÆô¶¯Ê§°Ü£¬¿ÉÄÜÊÇÃ»ÓÐ°²×°£¬Òª°²×°Âð£¿
            set /p install_confirm="¼ÌÐø°²×°£¿(Y/N): "
            if /i "!install_confirm!"=="Y" (
                echo ÕýÔÚ°²×°MongoDB...
                winget install --id MongoDB.Server -e --accept-package-agreements --accept-source-agreements
                echo °²×°Íê³É£¬ÕýÔÚÆô¶¯MongoDB·þÎñ...
                net start MongoDB
                if !errorlevel! neq 0 (
                    echo Æô¶¯MongoDB·þÎñÊ§°Ü£¬ÇëÊÖ¶¯Æô¶¯
                    exit /b
                ) else (
                    echo MongoDB·þÎñÒÑ³É¹¦Æô¶¯
                )
            ) else (
                echo È¡Ïû°²×°MongoDB£¬°´ÈÎÒâ¼üÍË³ö...
                pause >nul
				exit /b
            )
        )
    ) else (
        echo "¾¯¸æ£ºMongoDB·þÎñÎ´ÔËÐÐ£¬½«µ¼ÖÂMaiMBotÎÞ·¨·ÃÎÊÊý¾Ý¿â£¡"
    )
) else (
    echo MongoDB·þÎñÒÑÔËÐÐ
)

@REM set "GIT_HOME=%_root%\tools\git\bin"
set "PATH=%PYTHON_HOME%;%GIT_HOME%;%PATH%"

:install_maim
if not exist "!_root!\bot.py" (
    cls
    echo ÄãËÆºõÃ»ÓÐ°²×°ÂóÂóBot£¬Òª°²×°ÔÚµ±Ç°Ä¿Â¼Âð£¿
    set /p confirm="¼ÌÐø£¿(Y/N): "
    if /i "!confirm!"=="Y" (
        echo ÒªÊ¹ÓÃGit´úÀíÏÂÔØÂð£¿
        set /p proxy_confirm="¼ÌÐø£¿(Y/N): "
        if /i "!proxy_confirm!"=="Y" (
            echo ÕýÔÚ°²×°ÂóÂóBot...
            git clone https://ghfast.top/https://github.com/SengokuCola/MaiMBot
        ) else (
            echo ÕýÔÚ°²×°ÂóÂóBot...
            git clone https://github.com/SengokuCola/MaiMBot
        )
        xcopy /E /H /I MaiMBot . >nul 2>&1
        rmdir /s /q MaiMBot
        git checkout main-fix

        echo °²×°Íê³É£¬ÕýÔÚ°²×°ÒÀÀµ...
        python -m pip config set global.index-url https://mirrors.aliyun.com/pypi/simple
        python -m pip install virtualenv
        python -m virtualenv venv
        call venv\Scripts\activate.bat
        python -m pip install -r requirements.txt

        echo °²×°Íê³É£¬Òª±à¼­ÅäÖÃÎÄ¼þÂð£¿
        set /p edit_confirm="¼ÌÐø£¿(Y/N): "
        if /i "!edit_confirm!"=="Y" (
            goto config_menu
        ) else (
            echo È¡Ïû±à¼­ÅäÖÃÎÄ¼þ£¬°´ÈÎÒâ¼ü·µ»ØÖ÷²Ëµ¥...
        )
    )
)


@REM git»ñÈ¡µ±Ç°·ÖÖ§Ãû²¢±£´æÔÚ±äÁ¿Àï
for /f "delims=" %%b in ('git symbolic-ref --short HEAD 2^>nul') do (
    set "BRANCH=%%b"
)

@REM ¸ù¾Ý²»Í¬·ÖÖ§Ãû¸ø·ÖÖ§Ãû×Ö·û´®Ê¹ÓÃ²»Í¬ÑÕÉ«
echo ·ÖÖ§Ãû: %BRANCH%
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
echo ÕýÔÚ¼ì²éÐéÄâ»·¾³×´Ì¬...
if exist "%_root%\config\no_venv" (
    echo ¼ì²âµ½no_venv,Ìø¹ýÐéÄâ»·¾³¼ì²é
    goto menu
)

:: »·¾³¼ì²â
if defined VIRTUAL_ENV (
    goto menu
)
if exist "%_root%\config\conda_env" (
    set /p CONDA_ENV=<"%_root%\config\conda_env"
    call conda activate !CONDA_ENV! || (
    echo ¼¤»îÊ§°Ü£¬¿ÉÄÜÔ­Òò£º
    echo 1. »·¾³²»´æÔÚ
    echo 2. condaÅäÖÃÒì³£
    pause
    goto conda_menu
	)
	echo ³É¹¦¼¤»îconda»·¾³£º!CONDA_ENV!
	goto menu
)

echo =====================================
echo ÐéÄâ»·¾³¼ì²â¾¯¸æ£º
echo µ±Ç°Ê¹ÓÃÏµÍ³PythonÂ·¾¶£º!PYTHON_HOME!
echo Î´¼ì²âµ½¼¤»îµÄÐéÄâ»·¾³£¡

:env_interaction
echo =====================================
echo ÇëÑ¡Ôñ²Ù×÷£º
echo 1 - ´´½¨²¢¼¤»îVenvÐéÄâ»·¾³£¨ÍÆ¼ö£©
echo 2 - ´´½¨/¼¤»îCondaÐéÄâ»·¾³
echo 3 - ÁÙÊ±Ìø¹ý±¾´Î¼ì²é
echo 4 - ÓÀ¾ÃÌø¹ýÐéÄâ»·¾³¼ì²é
set /p choice="ÇëÊäÈëÑ¡Ïî(1-4): "

if "!choice!"=="4" (
	echo ÒªÓÀ¾ÃÌø¹ýÐéÄâ»·¾³¼ì²éÂð£¿
    set /p no_venv_confirm="¼ÌÐø£¿(Y/N): ....."
    if /i "!no_venv_confirm!"=="Y" (
		echo 1 > "%_root%\config\no_venv"
		echo ÒÑ´´½¨no_venvÎÄ¼þ
		pause >nul
		goto menu
	) else (
        echo È¡ÏûÌø¹ýÐéÄâ»·¾³¼ì²é£¬°´ÈÎÒâ¼ü·µ»Ø...
        pause >nul
        goto env_interaction
    )
)

if "!choice!"=="3" (
    echo ¾¯¸æ£ºÊ¹ÓÃÏµÍ³»·¾³¿ÉÄÜµ¼ÖÂÒÀÀµ³åÍ»£¡
    timeout /t 2 >nul
    goto menu
)

if "!choice!"=="2" goto handle_conda
if "!choice!"=="1" goto handle_venv

echo ÎÞÐ§µÄÊäÈë£¬ÇëÊäÈë1-4Ö®¼äµÄÊý×Ö
timeout /t 2 >nul
goto env_interaction

:handle_venv
python -m pip config set global.index-url https://mirrors.aliyun.com/pypi/simple
echo ÕýÔÚ³õÊ¼»¯Venv»·¾³...
python -m pip install virtualenv || (
    echo °²×°»·¾³Ê§°Ü£¬´íÎóÂë£º!errorlevel!
    pause
    goto env_interaction
)
echo ´´½¨ÐéÄâ»·¾³µ½£ºvenv
    python -m virtualenv venv || (
    echo »·¾³´´½¨Ê§°Ü£¬´íÎóÂë£º!errorlevel!
    pause
    goto env_interaction
)

call venv\Scripts\activate.bat
echo ÒÑ¼¤»îVenv»·¾³
echo Òª°²×°ÒÀÀµÂð£¿
set /p install_confirm="¼ÌÐø£¿(Y/N): "
if /i "!install_confirm!"=="Y" (
    goto update_dependencies
)
goto menu

:handle_conda
where conda >nul 2>&1 || (
    echo Î´¼ì²âµ½conda£¬¿ÉÄÜÔ­Òò£º
    echo 1. Î´°²×°Miniconda
    echo 2. condaÅäÖÃÒì³£
    timeout /t 10 >nul
    goto env_interaction
)

:conda_menu
echo ÇëÑ¡ÔñConda²Ù×÷£º
echo 1 - ´´½¨ÐÂ»·¾³
echo 2 - ¼¤»îÒÑÓÐ»·¾³
echo 3 - ·µ»ØÉÏ¼¶²Ëµ¥
set /p choice="ÇëÊäÈëÑ¡Ïî(1-3): "

if "!choice!"=="3" goto env_interaction
if "!choice!"=="2" goto activate_conda
if "!choice!"=="1" goto create_conda

echo ÎÞÐ§µÄÊäÈë£¬ÇëÊäÈë1-3Ö®¼äµÄÊý×Ö
timeout /t 2 >nul
goto conda_menu

:create_conda
set /p "CONDA_ENV=ÇëÊäÈëÐÂ»·¾³Ãû³Æ£º"
if "!CONDA_ENV!"=="" (
    echo »·¾³Ãû³Æ²»ÄÜÎª¿Õ£¡
    goto create_conda
)
conda create -n !CONDA_ENV! python=3.13 -y || (
    echo »·¾³´´½¨Ê§°Ü£¬´íÎóÂë£º!errorlevel!
    timeout /t 10 >nul
    goto conda_menu
)
goto activate_conda

:activate_conda
set /p "CONDA_ENV=ÇëÊäÈëÒª¼¤»îµÄ»·¾³Ãû³Æ£º"
call conda activate !CONDA_ENV! || (
    echo ¼¤»îÊ§°Ü£¬¿ÉÄÜÔ­Òò£º
    echo 1. »·¾³²»´æÔÚ
    echo 2. condaÅäÖÃÒì³£
    pause
    goto conda_menu
)
echo ³É¹¦¼¤»îconda»·¾³£º!CONDA_ENV!
echo !CONDA_ENV! > "%_root%\config\conda_env"
echo Òª°²×°ÒÀÀµÂð£¿
set /p install_confirm="¼ÌÐø£¿(Y/N): "
if /i "!install_confirm!"=="Y" (
    goto update_dependencies
)
:menu
@chcp 936
cls
echo ÂóÂóBot¿ØÖÆÌ¨ v%VERSION%  µ±Ç°·ÖÖ§: %BRANCH_COLOR%%BRANCH%[0m
echo µ±Ç°Python»·¾³: [96m!PYTHON_HOME![0m
echo ======================
echo 1. ¸üÐÂ²¢Æô¶¯ÂóÂóBot (Ä¬ÈÏ)
echo 2. Ö±½ÓÆô¶¯ÂóÂóBot
echo 3. Æô¶¯ÂóÂóÅäÖÃ½çÃæ
echo 4. ´ò¿ªÂóÂóÉñÆæ¹¤¾ßÏä
echo 5. ÍË³ö
echo ======================

set /p choice="ÇëÊäÈëÑ¡ÏîÊý×Ö (1-5)²¢°´ÏÂ»Ø³µÒÔÑ¡Ôñ: "

if "!choice!"=="" set choice=1

if "!choice!"=="1" goto update_and_start
if "!choice!"=="2" goto start_bot
if "!choice!"=="3" goto config_menu
if "!choice!"=="4" goto tools_menu
if "!choice!"=="5" exit /b

echo ÎÞÐ§µÄÊäÈë£¬ÇëÊäÈë1-5Ö®¼äµÄÊý×Ö
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
echo ÂóÂóÊ±ÉÐ¹¤¾ßÏä  µ±Ç°·ÖÖ§: %BRANCH_COLOR%%BRANCH%[0m
echo ======================
echo 1. ¸üÐÂÒÀÀµ
echo 2. ÇÐ»»·ÖÖ§
echo 3. ÖØÖÃµ±Ç°·ÖÖ§
echo 4. ¸üÐÂÅäÖÃÎÄ¼þ
echo 5. Ñ§Ï°ÐÂµÄÖªÊ¶¿â
echo 6. ´ò¿ªÖªÊ¶¿âÎÄ¼þ¼Ð
echo 7. ·µ»ØÖ÷²Ëµ¥
echo ======================

set /p choice="ÇëÊäÈëÑ¡ÏîÊý×Ö: "
if "!choice!"=="1" goto update_dependencies
if "!choice!"=="2" goto switch_branch
if "!choice!"=="3" goto reset_branch
if "!choice!"=="4" goto update_config
if "!choice!"=="5" goto learn_new_knowledge
if "!choice!"=="6" goto open_knowledge_folder
if "!choice!"=="7" goto menu

echo ÎÞÐ§µÄÊäÈë£¬ÇëÊäÈë1-6Ö®¼äµÄÊý×Ö
timeout /t 2 >nul
goto tools_menu

:update_dependencies
cls
echo ÕýÔÚ¸üÐÂÒÀÀµ...
python -m pip config set global.index-url https://mirrors.aliyun.com/pypi/simple
python.exe -m pip install -r requirements.txt

echo ÒÀÀµ¸üÐÂÍê³É£¬°´ÈÎÒâ¼ü·µ»Ø¹¤¾ßÏä²Ëµ¥...
pause
goto tools_menu

:switch_branch
cls
echo ÕýÔÚÇÐ»»·ÖÖ§...
echo µ±Ç°·ÖÖ§: %BRANCH%
@REM echo ¿ÉÓÃ·ÖÖ§: main, debug, stable-dev
echo 1. ÇÐ»»µ½[92mmain[0m
echo 2. ÇÐ»»µ½[91mmain-fix[0m
echo ÇëÊäÈëÒªÇÐ»»µ½µÄ·ÖÖ§:
set /p branch_name="·ÖÖ§Ãû: "
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
    echo ÎÞÐ§µÄ·ÖÖ§Ãû, ÇëÖØÐÂÊäÈë
    timeout /t 2 >nul
    goto switch_branch
)

echo ÕýÔÚÇÐ»»µ½·ÖÖ§ %branch_name%...
git checkout %branch_name%
echo ·ÖÖ§ÇÐ»»Íê³É£¬µ±Ç°·ÖÖ§: %BRANCH_COLOR%%branch_name%[0m
set "BRANCH=%branch_name%"
echo °´ÈÎÒâ¼ü·µ»Ø¹¤¾ßÏä²Ëµ¥...
pause >nul
goto tools_menu


:reset_branch
cls
echo ÕýÔÚÖØÖÃµ±Ç°·ÖÖ§...
echo µ±Ç°·ÖÖ§: !BRANCH!
echo È·ÈÏÒªÖØÖÃµ±Ç°·ÖÖ§Âð£¿
set /p confirm="¼ÌÐø£¿(Y/N): "
if /i "!confirm!"=="Y" (
    echo ÕýÔÚÖØÖÃµ±Ç°·ÖÖ§...
    git reset --hard !BRANCH!
    echo ·ÖÖ§ÖØÖÃÍê³É£¬°´ÈÎÒâ¼ü·µ»Ø¹¤¾ßÏä²Ëµ¥...
) else (
    echo È¡ÏûÖØÖÃµ±Ç°·ÖÖ§£¬°´ÈÎÒâ¼ü·µ»Ø¹¤¾ßÏä²Ëµ¥...
)
pause >nul
goto tools_menu


:update_config
cls
echo ÕýÔÚ¸üÐÂÅäÖÃÎÄ¼þ...
echo ÇëÈ·±£ÒÑ±¸·ÝÖØÒªÊý¾Ý£¬¼ÌÐø½«ÐÞ¸Äµ±Ç°ÅäÖÃÎÄ¼þ¡£
echo ¼ÌÐøÇë°´Y£¬È¡ÏûÇë°´ÈÎÒâ¼ü...
set /p confirm="¼ÌÐø£¿(Y/N): "
if /i "!confirm!"=="Y" (
    echo ÕýÔÚ¸üÐÂÅäÖÃÎÄ¼þ...
    python.exe config\auto_update.py
    echo ÅäÖÃÎÄ¼þ¸üÐÂÍê³É£¬°´ÈÎÒâ¼ü·µ»Ø¹¤¾ßÏä²Ëµ¥...
) else (
    echo È¡Ïû¸üÐÂÅäÖÃÎÄ¼þ£¬°´ÈÎÒâ¼ü·µ»Ø¹¤¾ßÏä²Ëµ¥...
)
pause >nul
goto tools_menu

:learn_new_knowledge
cls
echo ÕýÔÚÑ§Ï°ÐÂµÄÖªÊ¶¿â...
echo ÇëÈ·±£ÒÑ±¸·ÝÖØÒªÊý¾Ý£¬¼ÌÐø½«ÐÞ¸Äµ±Ç°ÖªÊ¶¿â¡£
echo ¼ÌÐøÇë°´Y£¬È¡ÏûÇë°´ÈÎÒâ¼ü...
set /p confirm="¼ÌÐø£¿(Y/N): "
if /i "!confirm!"=="Y" (
    echo ÕýÔÚÑ§Ï°ÐÂµÄÖªÊ¶¿â...
    python.exe src\plugins\zhishi\knowledge_library.py
    echo Ñ§Ï°Íê³É£¬°´ÈÎÒâ¼ü·µ»Ø¹¤¾ßÏä²Ëµ¥...
) else (
    echo È¡ÏûÑ§Ï°ÐÂµÄÖªÊ¶¿â£¬°´ÈÎÒâ¼ü·µ»Ø¹¤¾ßÏä²Ëµ¥...
)
pause >nul
goto tools_menu

:open_knowledge_folder
cls
echo ÕýÔÚ´ò¿ªÖªÊ¶¿âÎÄ¼þ¼Ð...
if exist data\raw_info (
    start explorer data\raw_info
) else (
    echo ÖªÊ¶¿âÎÄ¼þ¼Ð²»´æÔÚ£¡
    echo ÕýÔÚ´´½¨ÎÄ¼þ¼Ð...
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
    echo ¼ì²âµ½²Ö¿âÈ¨ÏÞÎÊÌâ£¬ÕýÔÚ×Ô¶¯ÐÞ¸´...
    git config --global --add safe.directory "%cd%"
    echo ÒÑÌí¼ÓÀýÍâ£¬ÕýÔÚÖØÊÔgit pull...
    del temp.log
    goto retry_git_pull
)
del temp.log
echo ÕýÔÚ¸üÐÂÒÀÀµ...
python -m pip config set global.index-url https://mirrors.aliyun.com/pypi/simple
python -m pip install -r requirements.txt && cls

echo µ±Ç°´úÀíÉèÖÃ:
echo HTTP_PROXY=%HTTP_PROXY%
echo HTTPS_PROXY=%HTTPS_PROXY%

echo Disable Proxy...
set HTTP_PROXY=
set HTTPS_PROXY=
set no_proxy=0.0.0.0/32

REM chcp 65001
python bot.py
echo.
echo BotÒÑÍ£Ö¹ÔËÐÐ£¬°´ÈÎÒâ¼ü·µ»ØÖ÷²Ëµ¥...
pause >nul
goto menu

:start_bot
cls
echo ÕýÔÚ¸üÐÂÒÀÀµ...
python -m pip config set global.index-url https://mirrors.aliyun.com/pypi/simple
python -m pip install -r requirements.txt && cls

echo µ±Ç°´úÀíÉèÖÃ:
echo HTTP_PROXY=%HTTP_PROXY%
echo HTTPS_PROXY=%HTTPS_PROXY%

echo Disable Proxy...
set HTTP_PROXY=
set HTTPS_PROXY=
set no_proxy=0.0.0.0/32

REM chcp 65001
python bot.py
echo.
echo BotÒÑÍ£Ö¹ÔËÐÐ£¬°´ÈÎÒâ¼ü·µ»ØÖ÷²Ëµ¥...
pause >nul
goto menu


:open_dir
start explorer "%cd%"
goto menu

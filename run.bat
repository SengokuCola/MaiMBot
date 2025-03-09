@ECHO OFF
chcp 65001
python -m venv venv
call venv\Scripts\activate.bat
pip install -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple --upgrade -r requirements.txt
python run.py
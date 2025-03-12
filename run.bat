@ECHO OFF
chcp 65001
if not exist "venv" (
  python -m venv venv
  call venv\Scripts\activate.bat
  pip install -i https://mirrors.aliyun.com/pypi/simple --upgrade -r requirements.txt
  ) else (
  call venv\Scripts\activate.bat
)
python run.py
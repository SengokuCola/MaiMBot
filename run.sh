#!/bin/bash

# 设置 UTF-8 编码
export LANG=C.UTF-8

# 检查是否安装了 pip
if ! command -v pip3 &> /dev/null; then
    echo "错误：未安装 python3-pip 软件包"
    echo "请执行以下命令之一进行安装："
    # 针对不同发行版提供安装命令
    echo "Ubuntu/Debian ：sudo apt update && sudo apt install -y python3-pip"
    echo "CentOS/RHEL ：sudo yum update -y && sudo yum install -y python3-pip"
    echo "Fedora ：sudo dnf update -y && sudo dnf install -y python3-pip"
    echo "Arch Linux ：sudo pacman -Sy python-pip"
    exit 1
fi

# 检查是否安装了 venv
if ! python3 -c "import venv" &> /dev/null; then
    echo "错误：未安装 python3-venv 软件包"
    echo "请执行以下命令之一进行安装："
    # 针对不同发行版提供安装命令
    echo "Ubuntu/Debian ：sudo apt update && sudo apt install -y python3-venv"
    echo "CentOS/RHEL ：sudo yum update -y && sudo yum install -y python3-venv"
    echo "Fedora ：sudo dnf update -y && sudo dnf install -y python3-venv"
    echo "Arch Linux ：sudo pacman -Sy python-venv"
    exit 1
fi

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    python3 -m venv venv
    source venv/bin/activate
    pip install -i https://mirrors.aliyun.com/pypi/simple --upgrade -r requirements.txt
else
    source venv/bin/activate
fi

# 运行 Python 脚本
python run.py
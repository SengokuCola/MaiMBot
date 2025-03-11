#!/bin/bash

# 设置UTF-8编码
export LANG=en_US.UTF-8

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR" || {
    echo "错误：切换目录失败"
    exit 1
}

# 检查Python版本
if ! command -v python3 &> /dev/null; then
    echo "未找到Python解释器"
    exit 1
fi

version=$(python3 --version 2>&1 | cut -d' ' -f2)
major=$(echo "$version" | cut -d'.' -f1)
minor=$(echo "$version" | cut -d'.' -f2)

if [ "$major" -lt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -lt 9 ]; }; then
    echo "需要Python大于等于3.9，当前版本 $version"
    exit 1
fi

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo "正在初始化虚拟环境..."
    
    # 检查并安装virtualenv
    echo "正在安装virtualenv..."
    python3 -m pip install virtualenv || {
        echo "virtualenv安装失败"
        exit 1
    }
    
    echo "正在创建虚拟环境..."
    python3 -m virtualenv venv || {
        echo "虚拟环境创建失败"
        exit 1
    }
fi

# 激活虚拟环境
source venv/bin/activate || {
    echo "虚拟环境激活失败"
    exit 1
}

# 更新依赖
echo "正在更新依赖..."
pip install -r requirements.txt

# 显示并取消代理设置
echo "当前代理设置："
echo "HTTP_PROXY=$HTTP_PROXY"
echo "HTTPS_PROXY=$HTTPS_PROXY"

unset HTTP_PROXY
unset HTTPS_PROXY
echo "代理已取消。"

export no_proxy=0.0.0.0/32

# 运行主程序
nb run
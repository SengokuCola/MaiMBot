# 📦 Linux系统如何手动部署MaiMbot麦麦？

## 准备工作
- 一台联网的Linux设备（本教程以Ubuntu/Debian系为例）
- QQ小号（QQ框架的使用可能导致qq被风控，严重（小概率）可能会导致账号封禁，强烈不推荐使用大号）
- 可用的大模型API
- 一个AI助手，网上随便搜一家打开来用都行，可以帮你解决一些不懂的问题
- 以下内容假设你对Linux系统有一定的了解，如果觉得难以理解，请直接用Windows系统部署[Windows系统部署指南](./manual_deploy_windows.md)

## 你需要知道什么？

- 如何正确向AI助手提问，来学习新知识

- Python是什么

- Python的虚拟环境是什么？如何创建虚拟环境

- 命令行是什么

- 数据库是什么？如何安装并启动MongoDB

- 如何运行一个QQ机器人，以及NapCat框架是什么
---

## 环境配置

### 1️⃣ **确认Python版本**

需确保Python版本为3.9及以上

```bash
python --version
# 或
python3 --version
```
如果版本低于3.9，请更新Python版本。
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.9
# 如执行了这一步，建议在执行时将python3指向python3.9
# 更新替代方案，设置 python3.9 为默认的 python3 版本:
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 1
sudo update-alternatives --config python3
```

### 2️⃣ **创建虚拟环境**
```bash
# 方法1：使用venv(推荐)
python3 -m venv maimbot
source maimbot/bin/activate  # 激活环境

# 方法2：使用conda（需先安装Miniconda）
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
conda create -n maimbot python=3.9
conda activate maimbot

# 通过以上方法创建并进入虚拟环境后，再执行以下命令

# 安装依赖（任选一种环境）
pip install -r requirements.txt
```

---

## 数据库配置
### 3️⃣ **安装并启动MongoDB**
- 安装与启动: Debian参考[官方文档](https://docs.mongodb.com/manual/tutorial/install-mongodb-on-debian/)，Ubuntu参考[官方文档](https://docs.mongodb.com/manual/tutorial/install-mongodb-on-ubuntu/)

- 默认连接本地27017端口
---

## NapCat配置
### 4️⃣ **安装NapCat框架**

- 参考[NapCat官方文档](https://www.napcat.wiki/guide/boot/Shell#napcat-installer-linux%E4%B8%80%E9%94%AE%E4%BD%BF%E7%94%A8%E8%84%9A%E6%9C%AC-%E6%94%AF%E6%8C%81ubuntu-20-debian-10-centos9)安装

-  使用QQ小号登录，添加反向WS地址: `ws://127.0.0.1:8080/onebot/v11/ws`

---

## 配置文件设置
### 5️⃣ **配置文件设置，让麦麦Bot正常工作**
- 修改环境配置文件: `.env.prod`
- 修改机器人配置文件: `bot_config.toml`


---

## 启动机器人
### 6️⃣ **启动麦麦机器人**
```bash
# 在项目目录下操作
nb run
# 或
python3 bot.py
```

---

## **其他组件(可选)**
- 直接运行 knowledge.py生成知识库


---

## 常见问题
🔧 权限问题: 在命令前加 `sudo`  
🔌 端口占用: 使用 `sudo lsof -i :8080` 查看端口占用  
🛡️ 防火墙: 确保8080/27017端口开放  
```bash
sudo ufw allow 8080/tcp
sudo ufw allow 27017/tcp
```
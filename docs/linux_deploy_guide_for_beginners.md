# 面向纯新手的Linux服务器麦麦部署指南

## 你得先有一个服务器

为了能使麦麦在你的电脑关机之后还能运行，你需要一台不间断开机的主机，也就是我们常说的服务器。

华为云、阿里云、腾讯云等等都是在国内可以选择的选择。

你可以去租一台最低配置的就足敷需要了，按月租大概十几块钱就能租到了。

我们假设你已经租好了一台Linux架构的云服务器。我用的是阿里云ubuntu24.04，其他的原理相似。

## 0.我们就从零开始吧

### 网络问题

为访问github相关界面，推荐去下一款加速器，新手可以试试watttoolkit。

### 安装包下载

#### MongoDB

对于ubuntu24.04 x86来说是这个：

https://repo.mongodb.org/apt/ubuntu/dists/noble/mongodb-org/8.0/multiverse/binary-amd64/mongodb-org-server_8.0.5_amd64.deb

如果不是就在这里自行选择对应版本

https://www.mongodb.com/try/download/community-kubernetes-operator

#### Napcat

在这里选择对应版本。

https://github.com/NapNeko/NapCatQQ/releases/tag/v4.6.7

对于ubuntu24.04 x86来说是这个：

https://dldir1.qq.com/qqfile/qq/QQNT/ee4bd910/linuxqq_3.2.16-32793_amd64.deb

#### 麦麦

https://github.com/SengokuCola/MaiMBot/archive/refs/tags/0.5.8-alpha.zip

下载这个官方压缩包。

### 路径

我把麦麦相关文件放在了/moi/mai里面，你可以凭喜好更改，记得适当调整下面涉及到的部分即可。

文件结构：

```
moi
└─ mai
   ├─ linuxqq_3.2.16-32793_amd64.deb
   ├─ mongodb-org-server_8.0.5_amd64.deb
   └─ bot
      └─ MaiMBot-0.5.8-alpha.zip
```

### 网络

你可以在你的服务器控制台网页更改防火墙规则，允许6099，8080，27017这几个端口的出入。

## 1.正式开始！

远程连接你的服务器，你会看到一个黑框框闪着白方格，这就是我们要进行设置的场所——终端了。以下的bash命令都是在这里输入。

## 2. Python的安装

- 导入 Python 的稳定版 PPA：

```bash
sudo add-apt-repository ppa:deadsnakes/ppa
```

- 导入 PPA 后，更新 APT 缓存：

```bash
sudo apt update
```

- 在「终端」中执行以下命令来安装 Python 3.12：

```bash
sudo apt install python3.12
```

- 验证安装是否成功：

```bash
python3.12 --version
```

- 在「终端」中，执行以下命令安装 pip：

```bash
sudo apt install python3-pip
```

- 检查Pip是否安装成功：

```bash
pip --version
```

- 安装必要组件

``` bash
sudo apt install python-is-python3
```

## 3.MongoDB的安装

``` bash
cd /moi/mai
```

``` bash
dpkg -i mongodb-org-server_8.0.5_amd64.deb
```

``` bash
mkdir -p /root/data/mongodb/{data,log}
```

## 4.MongoDB的运行

```bash
service mongod start
```

```bash
systemctl status mongod #通过这条指令检查运行状态
```

有需要的话可以把这个服务注册成开机自启

```bash
sudo systemctl enable mongod
```

## 5.napcat的安装

``` bash
curl -o napcat.sh https://nclatest.znin.net/NapNeko/NapCat-Installer/main/script/install.sh && sudo bash napcat.sh
```

上面的不行试试下面的

``` bash
dpkg -i linuxqq_3.2.16-32793_amd64.deb
apt-get install -f
dpkg -i linuxqq_3.2.16-32793_amd64.deb
```

成功的标志是输入``` napcat ```出来炫酷的彩虹色界面

## 6.napcat的运行

此时你就可以根据提示在```napcat```里面登录你的QQ号了。

```bash
napcat start <你的QQ号>
napcat status #检查运行状态
```

然后你就可以登录napcat的webui进行设置了：

```http://<你服务器的公网IP>:6099/webui?token=napcat```

第一次是这个，后续改了密码之后token就会对应修改。你也可以使用```napcat log <你的QQ号>```来查看webui地址。把里面的```127.0.0.1```改成<你服务器的公网IP>即可。

登录上之后在网络配置界面添加websocket客户端，名称随便输一个，url改成`ws://127.0.0.1:8080/onebot/v11/ws`保存之后点启用，就大功告成了。

## 7.麦麦的安装

### step 1 安装解压软件

```
sudo apt-get install unzip
```

### step 2 解压文件

```bash
cd /moi/mai/bot # 注意：要切换到压缩包的目录中去
unzip MaiMBot-0.5.8-alpha.zip
```

### step 3 进入虚拟环境安装库

```bash
cd /moi/mai/bot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### step 4 试运行

```bash
cd /moi/mai/bot
python -m venv venv
source venv/bin/activate
python bot.py
```

肯定运行不成功，不过你会发现结束之后多了一些文件

```
bot
├─ .env.prod
└─ config
   └─ bot_config.toml
```

你要会vim直接在终端里修改也行，不过也可以把它们下到本地改好再传上去：

### step 5 文件配置

本项目需要配置两个主要文件：

1. `.env.prod` - 配置API服务和系统环境
2. `bot_config.toml` - 配置机器人行为和模型

#### API

你可以注册一个硅基流动的账号，通过邀请码注册有14块钱的免费额度：https://cloud.siliconflow.cn/i/7Yld7cfg。

#### 在.env.prod中定义API凭证：

```
# API凭证配置
SILICONFLOW_KEY=your_key        # 硅基流动API密钥
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1/  # 硅基流动API地址

DEEP_SEEK_KEY=your_key          # DeepSeek API密钥
DEEP_SEEK_BASE_URL=https://api.deepseek.com/v1  # DeepSeek API地址

CHAT_ANY_WHERE_KEY=your_key     # ChatAnyWhere API密钥
CHAT_ANY_WHERE_BASE_URL=https://api.chatanywhere.tech/v1  # ChatAnyWhere API地址
```

#### 在bot_config.toml中引用API凭证：

```
[model.llm_reasoning]
name = "Pro/deepseek-ai/DeepSeek-R1"
base_url = "SILICONFLOW_BASE_URL"  # 引用.env.prod中定义的地址
key = "SILICONFLOW_KEY"            # 引用.env.prod中定义的密钥
```

如需切换到其他API服务，只需修改引用：

```
[model.llm_reasoning]
name = "Pro/deepseek-ai/DeepSeek-R1"
base_url = "DEEP_SEEK_BASE_URL"  # 切换为DeepSeek服务
key = "DEEP_SEEK_KEY"            # 使用DeepSeek密钥
```

#### 配置文件详解

##### 环境配置文件 (.env.prod)

```
# API配置
SILICONFLOW_KEY=your_key
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1/
DEEP_SEEK_KEY=your_key
DEEP_SEEK_BASE_URL=https://api.deepseek.com/v1
CHAT_ANY_WHERE_KEY=your_key
CHAT_ANY_WHERE_BASE_URL=https://api.chatanywhere.tech/v1

# 服务配置
HOST=127.0.0.1  # 如果使用Docker部署，需要改成0.0.0.0，否则QQ消息无法传入
PORT=8080

# 数据库配置
MONGODB_HOST=127.0.0.1  # 如果使用Docker部署，需要改成数据库容器的名字，默认是mongodb
MONGODB_PORT=27017
DATABASE_NAME=MegBot
MONGODB_USERNAME = ""  # 数据库用户名
MONGODB_PASSWORD = ""  # 数据库密码
MONGODB_AUTH_SOURCE = ""  # 认证数据库

# 插件配置
PLUGINS=["src2.plugins.chat"]
```

##### 机器人配置文件 (bot_config.toml)

```
[bot]
qq = "机器人QQ号"  # 必填
nickname = "麦麦"  # 机器人昵称（你希望机器人怎么称呼它自己）

[personality]
prompt_personality = [
    "曾经是一个学习地质的女大学生，现在学习心理学和脑科学，你会刷贴吧",
    "是一个女大学生，你有黑色头发，你会刷小红书"
]
prompt_schedule = "一个曾经学习地质,现在学习心理学和脑科学的女大学生，喜欢刷qq，贴吧，知乎和小红书"

[message]
min_text_length = 2  # 最小回复长度
max_context_size = 15  # 上下文记忆条数
emoji_chance = 0.2  # 表情使用概率
ban_words = []  # 禁用词列表

[emoji]
auto_save = true  # 自动保存表情
enable_check = false  # 启用表情审核
check_prompt = "符合公序良俗"

[groups]
talk_allowed = []      # 允许对话的群号
talk_frequency_down = []   # 降低回复频率的群号
ban_user_id = []      # 禁止回复的用户QQ号

[others]
enable_advance_output = true  # 启用详细日志
enable_kuuki_read = true  # 启用场景理解

# 模型配置
[model.llm_reasoning]  # 推理模型
name = "Pro/deepseek-ai/DeepSeek-R1"
base_url = "SILICONFLOW_BASE_URL"
key = "SILICONFLOW_KEY"

[model.llm_reasoning_minor]  # 轻量推理模型
name = "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"
base_url = "SILICONFLOW_BASE_URL"
key = "SILICONFLOW_KEY"

[model.llm_normal]  # 对话模型
name = "Pro/deepseek-ai/DeepSeek-V3"
base_url = "SILICONFLOW_BASE_URL"
key = "SILICONFLOW_KEY"

[model.llm_normal_minor]  # 备用对话模型
name = "deepseek-ai/DeepSeek-V2.5"
base_url = "SILICONFLOW_BASE_URL"
key = "SILICONFLOW_KEY"

[model.vlm]  # 图像识别模型
name = "deepseek-ai/deepseek-vl2"
base_url = "SILICONFLOW_BASE_URL"
key = "SILICONFLOW_KEY"

[model.embedding]  # 文本向量模型
name = "BAAI/bge-m3"
base_url = "SILICONFLOW_BASE_URL"
key = "SILICONFLOW_KEY"


[topic.llm_topic]
name = "Pro/deepseek-ai/DeepSeek-V3"
base_url = "SILICONFLOW_BASE_URL"
key = "SILICONFLOW_KEY"
```

**step # 6** 运行

现在再运行

```bash
cd /moi/mai/bot
python -m venv venv
source venv/bin/activate
python bot.py
```

应该就能运行成功了。

## 8.事后配置

可是现在还有个问题：只要你一关闭终端，bot.py就会停止运行。那该怎么办呢？我们可以把bot.py注册成服务。

重启服务器，打开MongoDB和napcat服务。

新建一个文件，名为`bot.service`，内容如下

```
[Unit]
Description=maimai bot

[Service]
WorkingDirectory=/moi/mai/bot
ExecStart=/moi/mai/bot/venv/bin/python /moi/mai/bot/bot.py
Restart=on-failure
User=root

[Install]
WantedBy=multi-user.target
```

里面的路径视自己的情况更改。

把它放到`/etc/systemd/system`里面。

重新加载 `systemd` 配置：

```bash
sudo systemctl daemon-reload
```

启动服务：

```bash
sudo systemctl start bot.service # 启动服务
sudo systemctl restart bot.service # 或者重启服务
```

检查服务状态：

```bash
sudo systemctl status bot.service
```

现在再关闭终端，检查麦麦能不能正常回复QQ信息。如果可以的话就大功告成了！

## 9.命令速查

```bash
service mongod start # 启动mongod服务
napcat start <你的QQ号> # 登录napcat
cd /moi/mai/bot # 切换路径
python -m venv venv # 创建虚拟环境
source venv/bin/activate # 激活虚拟环境

sudo systemctl daemon-reload # 重新加载systemd配置
sudo systemctl start bot.service # 启动bot服务
sudo systemctl enable bot.service # 启动bot服务

sudo systemctl status bot.service # 检查bot服务状态
```

```
python bot.py
```


# 🔧 配置指南

## 简介

本项目需要配置两个主要文件：

1. `.env.prod` - 配置API服务和系统环境
2. `bot_config.toml` - 配置机器人行为和模型

## API配置说明

`.env.prod` 和 `bot_config.toml` 中的API配置关系如下：

### 在.env.prod中定义API凭证

```ini
# API凭证配置
SILICONFLOW_KEY=your_key        # 硅基流动API密钥
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1/  # 硅基流动API地址

DEEP_SEEK_KEY=your_key          # DeepSeek API密钥
DEEP_SEEK_BASE_URL=https://api.deepseek.com/v1  # DeepSeek API地址

CHAT_ANY_WHERE_KEY=your_key     # ChatAnyWhere API密钥
CHAT_ANY_WHERE_BASE_URL=https://api.chatanywhere.tech/v1  # ChatAnyWhere API地址
```

### 在bot_config.toml中引用API凭证

```toml
[model.llm_reasoning]
name = "Pro/deepseek-ai/DeepSeek-R1"
provider = "SILICONFLOW"         # 引用.env.prod中定义的宏
```

如需切换到其他API服务，只需修改引用：

```toml
[model.llm_reasoning]
name = "deepseek-reasoner"       # 改成对应的模型名称，这里为DeepseekR1
provider = "DEEP_SEEK"           # 使用DeepSeek密钥
```

## 配置文件详解

### 环境配置文件 (.env.prod)

```ini
# API配置
SILICONFLOW_KEY=your_key
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1/
DEEP_SEEK_KEY=your_key
DEEP_SEEK_BASE_URL=https://api.deepseek.com/v1
CHAT_ANY_WHERE_KEY=your_key
CHAT_ANY_WHERE_BASE_URL=https://api.chatanywhere.tech/v1

# 服务配置

HOST=127.0.0.1  # 如果使用Docker部署，需要改成0.0.0.0，否则QQ消息无法传入
PORT=8080       # 与反向端口相同

# 数据库配置
MONGODB_HOST=127.0.0.1  # 如果使用Docker部署，需要改成数据库容器的名字，默认是mongodb
MONGODB_PORT=27017      # MongoDB端口

DATABASE_NAME=MegBot
# 数据库认证信息，如果需要认证就取消注释并填写下面三行
# MONGODB_USERNAME = ""
# MONGODB_PASSWORD = ""
# MONGODB_AUTH_SOURCE = ""

# 也可以使用URI连接数据库，取消注释填写在下面这行（URI的优先级比上面的高）
# MONGODB_URI=mongodb://127.0.0.1:27017/MegBot

# 插件配置
PLUGINS=["src2.plugins.chat"]
```

### 机器人配置文件 (bot_config.toml)

```toml
[bot]
qq = "机器人QQ号"  # 机器人的QQ号，必填
nickname = "麦麦"  # 机器人昵称
# alias_names: 配置机器人可使用的别名。当机器人在群聊或对话中被调用时，别名可以作为直接命令或提及机器人的关键字使用。
# 该配置项为字符串数组。例如: ["小麦", "阿麦"]
alias_names = ["小麦", "阿麦"]  # 机器人别名

[personality]
prompt_personality = [
    "曾经是一个学习地质的女大学生，现在学习心理学和脑科学，你会刷贴吧",
    "是一个女大学生，你有黑色头发，你会刷小红书"
] # 人格提示词
prompt_schedule = "一个曾经学习地质,现在学习心理学和脑科学的女大学生，喜欢刷qq，贴吧，知乎和小红书" # 日程生成提示词

[message]
min_text_length = 2  # 最小回复长度
max_context_size = 15  # 上下文记忆条数
emoji_chance = 0.2  # 表情使用概率
thinking_timeout = 120 # 机器人思考时间，时间越长能思考的时间越多，但是不要太长

response_willing_amplifier = 1 # 机器人回复意愿放大系数，增大会更愿意聊天
response_interested_rate_amplifier = 1 # 机器人回复兴趣度放大系数，听到记忆里的内容时意愿的放大系数
down_frequency_rate = 3.5 # 降低回复频率的群组回复意愿降低系数
ban_words = []  # 禁用词列表

[emoji]
auto_save = true  # 自动保存表情
enable_check = false  # 启用表情审核
check_prompt = "符合公序良俗"

[groups]
talk_allowed = {} # 允许对话的群号与对应的回复权重
ban_user_id = []      # 禁止回复的用户QQ号

[others]
enable_advance_output = true # 是否启用高级输出
enable_kuuki_read = true # 是否启用读空气功能
enable_debug_output = false # 是否启用调试输出
enable_friend_chat = false # 是否启用好友聊天

# 模型配置
[model.llm_reasoning]  # 推理模型
name = "Pro/deepseek-ai/DeepSeek-R1"
provider = "SILICONFLOW"

[model.llm_reasoning_minor]  # 轻量推理模型
name = "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"
provider = "SILICONFLOW"

[model.llm_normal]  # 对话模型
name = "Pro/deepseek-ai/DeepSeek-V3"
provider = "SILICONFLOW"

[model.llm_normal_minor]  # 备用对话模型
name = "deepseek-ai/DeepSeek-V2.5"
provider = "SILICONFLOW"

[model.vlm]  # 图像识别模型
name = "deepseek-ai/deepseek-vl2"
provider = "SILICONFLOW"

[model.embedding]  # 文本向量模型
name = "BAAI/bge-m3"
provider = "SILICONFLOW"


[topic.llm_topic]
name = "Pro/deepseek-ai/DeepSeek-V3"
provider = "SILICONFLOW"
```

## 注意事项

1. API密钥安全：
   - 妥善保管API密钥
   - 不要将含有密钥的配置文件上传至公开仓库

2. 配置修改：
   - 修改配置后需重启服务
   - 使用默认服务(硅基流动)时无需修改模型配置
   - QQ号和群号使用数字格式(机器人QQ号除外)

3. 其他说明：
   - 项目处于测试阶段，可能存在未知问题
   - 建议初次使用保持默认配置

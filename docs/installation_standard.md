# 🔧 配置指南

## 简介

本项目需要配置两个主要文件：
1. `.env.prod` - 配置API服务和系统环境
2. `bot_config.toml` - 配置机器人行为和模型

## API配置说明

`.env.prod` 和 `bot_config.toml` 中的API配置关系如下：

### 在.env.prod中定义API凭证：
```ini
# API凭证配置
SILICONFLOW_KEY=your_key        # 硅基流动API密钥
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1/  # 硅基流动API地址

DEEP_SEEK_KEY=your_key          # DeepSeek API密钥
DEEP_SEEK_BASE_URL=https://api.deepseek.com/v1  # DeepSeek API地址

CHAT_ANY_WHERE_KEY=your_key     # ChatAnyWhere API密钥
CHAT_ANY_WHERE_BASE_URL=https://api.chatanywhere.tech/v1  # ChatAnyWhere API地址
```

### 在bot_config.toml中引用API凭证：
```toml
[model.llm_reasoning]
name = "Pro/deepseek-ai/DeepSeek-R1"
base_url = "SILICONFLOW_BASE_URL"  # 引用.env.prod中定义的地址
key = "SILICONFLOW_KEY"            # 引用.env.prod中定义的密钥
```

如需切换到其他API服务，只需修改引用：
```toml
[model.llm_reasoning]
name = "deepseek-reasoner"       # 改成对应的模型名称，这里为DeepseekR1
base_url = "DEEP_SEEK_BASE_URL"  # 切换为DeepSeek服务
key = "DEEP_SEEK_KEY"            # 使用DeepSeek密钥
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
MONGODB_USERNAME = ""  # 数据库用户名
MONGODB_PASSWORD = ""  # 数据库密码
MONGODB_AUTH_SOURCE = ""  # 认证数据库

# 插件配置
PLUGINS=["src2.plugins.chat"]
```

### 机器人配置文件 (bot_config.toml)
```toml
[bot]
qq = "机器人QQ号"  # 必填
nickname = "麦麦"  # 机器人昵称
# alias_names: 配置机器人可使用的别名。当机器人在群聊或对话中被调用时，别名可以作为直接命令或提及机器人的关键字使用。
# 该配置项为字符串数组。例如: ["小麦", "阿麦"]
alias_names = ["小麦", "阿麦"]  # 机器人别名

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
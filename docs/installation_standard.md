# 🔧 配置指南

## 简介

本项目需要配置两个主要文件：

1. `.env.prod` - 配置API服务和系统环境，放置于程序目录
2. `bot_config.toml` - 配置机器人行为和模型，放置于程序目录下的config文件夹

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
[model.llm_reasoning] #回复模型1 主要回复模型
name = "Pro/deepseek-ai/DeepSeek-R1"
provider = "SILICONFLOW"#.env.prod中KEY和BASE_URL前的名称
pri_in = 0 #模型的输入价格（非必填，可以记录消耗）
pri_out = 0 #模型的输出价格（非必填，可以记录消耗）
```

如需切换到其他API服务，只需修改引用：

```toml
[model.llm_reasoning]
name = "deepseek-reasoner"# 改成对应的模型名称，这里为DeepseekR1
provider = "DEEP_SEEK"#.env.prod中KEY和BASE_URL前的名称，切换为DeepSeek官方服务
```

## 配置文件详解

### 环境配置文件 (config/.env.prod)

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
qq = "机器人QQ号"  # 必填
nickname = "麦麦"  # 机器人昵称
# alias_names: 配置机器人可使用的别名。当机器人在群聊或对话中被调用时，别名可以作为直接命令或提及机器人的关键字使用。
# 该配置项为字符串数组。例如: ["小麦", "阿麦"]
alias_names = ["小麦", "阿麦"]  # 机器人别名

[personality]
prompt_personality = [
"曾经是一个学习地质的女大学生，现在学习心理学和脑科学，你会刷贴吧",
"是一个女大学生，你有黑色头发，你会刷小红书",
"是一个女大学生，你有黑色头发，你会刷B站"
]
personality_1_probability = 0.6 # 第一种人格出现概率
personality_2_probability = 0.3 # 第二种人格出现概率
personality_3_probability = 0.1 # 第三种人格出现概率，请确保三个概率相加等于1
prompt_schedule = "一个曾经学习地质,现在学习心理学和脑科学的女大学生，喜欢刷qq，贴吧，知乎和小红书"

[message]
min_text_length = 2  # 最小回复长度
max_context_size = 15  # 上下文记忆条数
emoji_chance = 0.2  # 表情使用概率
thinking_timeout = 120 # 麦麦思考时间

response_willing_amplifier = 1 # 麦麦回复意愿放大系数，一般为1
response_interested_rate_amplifier = 1 # 麦麦回复兴趣度放大系数,听到记忆里的内容时放大系数
down_frequency_rate = 3.5 # 降低回复频率的群组回复意愿降低系数
ban_words = []  # 禁用词列表

ban_msgs_regex = [
    # 需要过滤的消息（原始消息）匹配的正则表达式，匹配到的消息将被过滤（支持CQ码），若不了解正则表达式请勿修改
    #"https?://[^\\s]+", # 匹配https链接
    #"\\d{4}-\\d{2}-\\d{2}", # 匹配日期
    # "\\[CQ:at,qq=\\d+\\]" # 匹配@
]

[emoji]
check_interval = 120 # 检查表情包的时间间隔
register_interval = 10 # 注册表情包的时间间隔
auto_save = true  # 自动偷表情包
enable_check = false  # 是否启用表情包过滤
check_prompt = "符合公序良俗" # 表情包过滤要求

[cq_code]
enable_pic_translate = false

[response]
model_r1_probability = 0.8 # 麦麦回答时选择主要回复模型1 模型的概率
model_v3_probability = 0.1 # 麦麦回答时选择次要回复模型2 模型的概率
model_r1_distill_probability = 0.1 # 麦麦回答时选择次要回复模型3 模型的概率
max_response_length = 1024 # 麦麦回答的最大token数

[memory]
build_memory_interval = 600 # 记忆构建间隔 单位秒   间隔越低，麦麦学习越多，但是冗余信息也会增多
memory_compress_rate = 0.1 # 记忆压缩率 控制记忆精简程度 建议保持默认,调高可以获得更多信息，但是冗余信息也会增多

forget_memory_interval = 600 # 记忆遗忘间隔 单位秒   间隔越低，麦麦遗忘越频繁，记忆更精简，但更难学习
memory_forget_time = 24 #多长时间后的记忆会被遗忘 单位小时 
memory_forget_percentage = 0.01 # 记忆遗忘比例 控制记忆遗忘程度 越大遗忘越多 建议保持默认


memory_ban_words = [ #不希望记忆的词
    # "403","张三"
]

[mood]
mood_update_interval = 1.0 # 情绪更新间隔 单位秒
mood_decay_rate = 0.95 # 情绪衰减率
mood_intensity_factor = 1.0 # 情绪强度因子

[keywords_reaction] # 针对某个关键词作出反应
enable = true  # 关键词反应功能的总开关

[[keywords_reaction.rules]] # 如果想要新增多个关键词，直接复制本条，修改keywords和reaction即可
enable = true # 是否启用此条（为了人类在未来AI战争能更好地识别AI（bushi），默认开启）
keywords = ["人机", "bot", "机器", "入机", "robot", "机器人"] # 会触发反应的关键词
reaction = "有人说你是人机或者机器人，否定这一事实，攻击或反问他。注意，只有认为你是机器人才回复，否则不要否认" # 触发之后添加的提示词

[[keywords_reaction.rules]] # 就像这样复制
enable = false # 仅作示例，不会触发
keywords = ["测试关键词回复","test",""]
reaction = "回答“测试成功”"

[chinese_typo]
enable = true # 是否启用中文错别字生成器
error_rate=0.006 # 单字替换概率
min_freq=7 # 最小字频阈值
tone_error_rate=0.2 # 声调错误概率
word_replace_rate=0.006 # 整词替换概率

[others]
enable_advance_output = true # 是否启用高级输出
enable_kuuki_read = true # 是否启用读空气功能
enable_debug_output = false # 是否启用调试输出
enable_friend_chat = false # 是否启用好友聊天

[groups]
talk_allowed = []      # 允许对话的群号
talk_frequency_down = []   # 降低回复频率的群号
ban_user_id = []      # 禁止回复的用户QQ号


#V3
#name = "deepseek-chat"
#base_url = "DEEP_SEEK_BASE_URL"
#key = "DEEP_SEEK_KEY"

#R1
#name = "deepseek-reasoner"
#base_url = "DEEP_SEEK_BASE_URL"
#key = "DEEP_SEEK_KEY"

#下面的模型若使用硅基流动则不需要更改，使用ds官方则改成.env.prod自定义的宏，使用自定义模型则选择定位相似的模型自己填写

#推理模型：

[model.llm_reasoning] #回复模型1 主要回复模型
name = "Pro/deepseek-ai/DeepSeek-R1"
provider = "SILICONFLOW"
pri_in = 0 #模型的输入价格（非必填，可以记录消耗）
pri_out = 0 #模型的输出价格（非必填，可以记录消耗）


[model.llm_reasoning_minor] #回复模型3 次要回复模型
name = "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"
provider = "SILICONFLOW"

#非推理模型

[model.llm_normal] #V3 回复模型2 次要回复模型
name = "Pro/deepseek-ai/DeepSeek-V3"
provider = "SILICONFLOW"

[model.llm_normal_minor] #V2.5
name = "deepseek-ai/DeepSeek-V2.5"
provider = "SILICONFLOW"

[model.llm_emotion_judge] #主题判断 0.7/m
name = "Qwen/Qwen2.5-14B-Instruct"
provider = "SILICONFLOW"

[model.llm_topic_judge] #主题判断：建议使用qwen2.5 7b
name = "Pro/Qwen/Qwen2.5-7B-Instruct"
provider = "SILICONFLOW"

[model.llm_summary_by_topic] #建议使用qwen2.5 32b 及以上
name = "Qwen/Qwen2.5-32B-Instruct"
provider = "SILICONFLOW"
pri_in = 0
pri_out = 0

[model.moderation] #内容审核 未启用
name = ""
provider = "SILICONFLOW"
pri_in = 0
pri_out = 0

# 识图模型

[model.vlm] #图像识别 0.35/m
name = "deepseek-ai/deepseek-vl2"
provider = "SILICONFLOW"



#嵌入模型

[model.embedding] #嵌入
name = "BAAI/bge-m3"
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

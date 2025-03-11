# 🔧 配置指南 喵~

## 👋 你好呀

让咱来告诉你我们要做什么喵：

1. 我们要一起设置一个可爱的AI机器人
2. 这个机器人可以在QQ上陪你聊天玩耍哦
3. 需要设置两个文件才能让机器人工作呢

## 📝 需要设置的文件喵

要设置这两个文件才能让机器人跑起来哦：

1. `.env.prod` - 这个文件告诉机器人要用哪些AI服务呢
2. `bot_config.toml` - 这个文件教机器人怎么和你聊天喵

## 🔑 密钥和域名的对应关系

想象一下，你要进入一个游乐园，需要：

1. 知道游乐园的地址（这就是域名 base_url）
2. 有入场的门票（这就是密钥 key）

在 `.env.prod` 文件里，我们定义了三个游乐园的地址和门票喵：

```ini
# 硅基流动游乐园
SILICONFLOW_KEY=your_key        # 硅基流动的门票
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1/  # 硅基流动的地址

# DeepSeek游乐园
DEEP_SEEK_KEY=your_key          # DeepSeek的门票
DEEP_SEEK_BASE_URL=https://api.deepseek.com/v1  # DeepSeek的地址

# ChatAnyWhere游乐园
CHAT_ANY_WHERE_KEY=your_key     # ChatAnyWhere的门票
CHAT_ANY_WHERE_BASE_URL=https://api.chatanywhere.tech/v1  # ChatAnyWhere的地址
```

然后在 `bot_config.toml` 里，机器人会用这些门票和地址去游乐园玩耍：

```toml
[model.llm_reasoning]
name = "Pro/deepseek-ai/DeepSeek-R1"
base_url = "SILICONFLOW_BASE_URL"  # 告诉机器人：去硅基流动游乐园玩
key = "SILICONFLOW_KEY"            # 用硅基流动的门票进去

[model.llm_normal]
name = "Pro/deepseek-ai/DeepSeek-V3"
base_url = "SILICONFLOW_BASE_URL"  # 还是去硅基流动游乐园
key = "SILICONFLOW_KEY"            # 用同一张门票就可以啦
```

### 🎪 举个例子喵

如果你想用DeepSeek官方的服务，就要这样改：

```toml
[model.llm_reasoning]
name = "deepseek-reasoner"       # 改成对应的模型名称，这里为DeepseekR1
base_url = "DEEP_SEEK_BASE_URL"  # 改成去DeepSeek游乐园
key = "DEEP_SEEK_KEY"            # 用DeepSeek的门票

[model.llm_normal]
name = "deepseek-chat"           # 改成对应的模型名称，这里为DeepseekV3
base_url = "DEEP_SEEK_BASE_URL"  # 也去DeepSeek游乐园
key = "DEEP_SEEK_KEY"            # 用同一张DeepSeek门票
```

### 🎯 简单来说

- `.env.prod` 文件就像是你的票夹，存放着各个游乐园的门票和地址
- `bot_config.toml` 就是告诉机器人：用哪张票去哪个游乐园玩
- 所有模型都可以用同一个游乐园的票，也可以去不同的游乐园玩耍
- 如果用硅基流动的服务，就保持默认配置不用改呢~

记住：门票（key）要保管好，不能给别人看哦，不然别人就可以用你的票去玩了喵！

## ---让我们开始吧---

### 第一个文件：环境配置 (.env.prod)

这个文件就像是机器人的"身份证"呢，告诉它要用哪些AI服务喵~

```ini
# 这些是AI服务的密钥，就像是魔法钥匙一样呢
# 要把 your_key 换成真正的密钥才行喵
# 比如说：SILICONFLOW_KEY=sk-123456789abcdef
SILICONFLOW_KEY=your_key
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1/
DEEP_SEEK_KEY=your_key
DEEP_SEEK_BASE_URL=https://api.deepseek.com/v1
CHAT_ANY_WHERE_KEY=your_key
CHAT_ANY_WHERE_BASE_URL=https://api.chatanywhere.tech/v1

# 如果你不知道这是什么，那么下面这些不用改，保持原样就好啦
# 如果使用Docker部署，需要改成0.0.0.0喵，不然听不见群友讲话了喵
HOST=127.0.0.1
PORT=8080

# 这些是数据库设置，一般也不用改呢
# 如果使用Docker部署，需要把MONGODB_HOST改成数据库容器的名字喵，默认是mongodb喵
MONGODB_HOST=127.0.0.1
MONGODB_PORT=27017
DATABASE_NAME=MegBot
# 数据库认证信息，如果需要认证就取消注释并填写下面三行喵
# MONGODB_USERNAME = ""
# MONGODB_PASSWORD = ""
# MONGODB_AUTH_SOURCE = ""

# 也可以使用URI连接数据库，取消注释填写在下面这行喵（URI的优先级比上面的高）
# MONGODB_URI=mongodb://127.0.0.1:27017/MegBot

# 这里是机器人的插件列表呢
PLUGINS=["src2.plugins.chat"]
```

### 第二个文件：机器人配置 (bot_config.toml)

这个文件就像是教机器人"如何说话"的魔法书呢！

```toml
[bot]
qq = "把这里改成你的机器人QQ号喵"  # 填写你的机器人QQ号
nickname = "麦麦"  # 机器人的名字，你可以改成你喜欢的任何名字哦，建议和机器人QQ名称/群昵称一样哦
alias_names = ["小麦", "阿麦"] # 也可以用这个招呼机器人，可以不设置呢

[personality]
# 这里可以设置机器人的性格呢，让它更有趣一些喵
prompt_personality = [
    "曾经是一个学习地质的女大学生，现在学习心理学和脑科学，你会刷贴吧",    # 贴吧风格的性格
    "是一个女大学生，你有黑色头发，你会刷小红书"    # 小红书风格的性格
]
prompt_schedule = "一个曾经学习地质,现在学习心理学和脑科学的女大学生，喜欢刷qq，贴吧，知乎和小红书"

[message]
min_text_length = 2  # 机器人每次至少要说几个字呢
max_context_size = 15  # 机器人能记住多少条消息喵
emoji_chance = 0.2  # 机器人使用表情的概率哦（0.2就是20%的机会呢）
ban_words = ["脏话", "不文明用语"]  # 在这里填写不让机器人说的词

[emoji]
auto_save = true  # 是否自动保存看到的表情包呢
enable_check = false  # 是否要检查表情包是不是合适的喵
check_prompt = "符合公序良俗"  # 检查表情包的标准呢

[groups]
talk_allowed = [123456, 789012]      # 比如：让机器人在群123456和789012里说话
talk_frequency_down = [345678]   # 比如：在群345678里少说点话
ban_user_id = [111222]      # 比如：不回复QQ号为111222的人的消息

[others]
enable_advance_output = true  # 是否要显示更多的运行信息呢
enable_kuuki_read = true  # 让机器人能够"察言观色"喵

# 模型配置部分的详细说明喵~


#下面的模型若使用硅基流动则不需要更改，使用ds官方则改成在.env.prod自己指定的密钥和域名，使用自定义模型则选择定位相似的模型自己填写

[model.llm_reasoning] #推理模型R1，用来理解和思考的喵
name = "Pro/deepseek-ai/DeepSeek-R1"  # 模型名字
# name = "Qwen/QwQ-32B"  # 如果想用千问模型，可以把上面那行注释掉，用这个呢
base_url = "SILICONFLOW_BASE_URL"  # 使用在.env.prod里设置的服务地址
key = "SILICONFLOW_KEY"  # 使用在.env.prod里设置的密钥

[model.llm_reasoning_minor] #R1蒸馏模型，是个轻量版的推理模型喵
name = "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"
base_url = "SILICONFLOW_BASE_URL"
key = "SILICONFLOW_KEY"

[model.llm_normal] #V3模型，用来日常聊天的喵
name = "Pro/deepseek-ai/DeepSeek-V3"
base_url = "SILICONFLOW_BASE_URL"
key = "SILICONFLOW_KEY"

[model.llm_normal_minor] #V2.5模型，是V3的前代版本呢
name = "deepseek-ai/DeepSeek-V2.5"
base_url = "SILICONFLOW_BASE_URL"
key = "SILICONFLOW_KEY"

[model.vlm] #图像识别模型，让机器人能看懂图片喵
name = "deepseek-ai/deepseek-vl2"
base_url = "SILICONFLOW_BASE_URL"
key = "SILICONFLOW_KEY"

[model.embedding] #嵌入模型，帮助机器人理解文本的相似度呢
name = "BAAI/bge-m3"
base_url = "SILICONFLOW_BASE_URL"
key = "SILICONFLOW_KEY"

# 如果选择了llm方式提取主题，就用这个模型配置喵
[topic.llm_topic]
name = "Pro/deepseek-ai/DeepSeek-V3"
base_url = "SILICONFLOW_BASE_URL"
key = "SILICONFLOW_KEY"
```

## 💡 模型配置说明喵

1. **关于模型服务**：
   - 如果你用硅基流动的服务，这些配置都不用改呢
   - 如果用DeepSeek官方API，要把base_url和key改成你在.env.prod里设置的值喵
   - 如果要用自定义模型，选择一个相似功能的模型配置来改呢

2. **主要模型功能**：
   - `llm_reasoning`: 负责思考和推理的大脑喵
   - `llm_normal`: 负责日常聊天的嘴巴呢
   - `vlm`: 负责看图片的眼睛哦
   - `embedding`: 负责理解文字含义的理解力喵
   - `topic`: 负责理解对话主题的能力呢

## 🌟 小提示

- 如果你刚开始使用，建议保持默认配置呢
- 不同的模型有不同的特长，可以根据需要调整它们的使用比例哦

## 🌟 小贴士喵

- 记得要好好保管密钥（key）哦，不要告诉别人呢
- 配置文件要小心修改，改错了机器人可能就不能和你玩了喵
- 如果想让机器人更聪明，可以调整 personality 里的设置呢
- 不想让机器人说某些话，就把那些词放在 ban_words 里面喵
- QQ群号和QQ号都要用数字填写，不要加引号哦（除了机器人自己的QQ号）

## ⚠️ 注意事项

- 这个机器人还在测试中呢，可能会有一些小问题喵
- 如果不知道怎么改某个设置，就保持原样不要动它哦~
- 记得要先有AI服务的密钥，不然机器人就不能和你说话了呢
- 修改完配置后要重启机器人才能生效喵~

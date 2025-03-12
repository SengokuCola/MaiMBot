import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import tomli
from loguru import logger
from packaging import version
from packaging.version import Version, InvalidVersion
from packaging.specifiers import SpecifierSet, InvalidSpecifier


@dataclass
class BotConfig:
    """机器人配置类"""

    INNER_VERSION: Version = None

    BOT_QQ: Optional[int] = 1
    BOT_NICKNAME: Optional[str] = None
    BOT_ALIAS_NAMES: List[str] = field(default_factory=list)  # 别名，可以通过这个叫它

    # 消息处理相关配置
    MIN_TEXT_LENGTH: int = 2  # 最小处理文本长度
    MAX_CONTEXT_SIZE: int = 15  # 上下文最大消息数
    emoji_chance: float = 0.2  # 发送表情包的基础概率

    ENABLE_PIC_TRANSLATE: bool = True  # 是否启用图片翻译

    talk_allowed_groups = set()
    talk_frequency_down_groups = set()
    thinking_timeout: int = 100  # 思考时间

    response_willing_amplifier: float = 1.0  # 回复意愿放大系数
    response_interested_rate_amplifier: float = 1.0  # 回复兴趣度放大系数
    down_frequency_rate: float = 3.5  # 降低回复频率的群组回复意愿降低系数

    ban_user_id = set()

    
    EMOJI_CHECK_INTERVAL: int = 120  # 表情包检查间隔（分钟）
    EMOJI_REGISTER_INTERVAL: int = 10  # 表情包注册间隔（分钟）
    EMOJI_SAVE: bool = True  # 偷表情包
    EMOJI_CHECK: bool = False  # 是否开启过滤
    EMOJI_CHECK_PROMPT: str = "符合公序良俗"  # 表情包过滤要求

    ban_words = set()
    ban_msgs_regex = set()

    max_response_length: int = 1024  # 最大回复长度

    # 模型配置
    llm_reasoning: Dict[str, str] = field(default_factory=lambda: {})
    llm_reasoning_minor: Dict[str, str] = field(default_factory=lambda: {})
    llm_normal: Dict[str, str] = field(default_factory=lambda: {})
    llm_normal_minor: Dict[str, str] = field(default_factory=lambda: {})
    llm_topic_judge: Dict[str, str] = field(default_factory=lambda: {})
    llm_summary_by_topic: Dict[str, str] = field(default_factory=lambda: {})
    llm_emotion_judge: Dict[str, str] = field(default_factory=lambda: {})
    embedding: Dict[str, str] = field(default_factory=lambda: {})
    vlm: Dict[str, str] = field(default_factory=lambda: {})
    moderation: Dict[str, str] = field(default_factory=lambda: {})

    MODEL_R1_PROBABILITY: float = 0.8  # R1模型概率
    MODEL_V3_PROBABILITY: float = 0.1  # V3模型概率
    MODEL_R1_DISTILL_PROBABILITY: float = 0.1  # R1蒸馏模型概率

    enable_advance_output: bool = False  # 是否启用高级输出
    enable_kuuki_read: bool = True  # 是否启用读空气功能
    enable_debug_output: bool = False  # 是否启用调试输出
    enable_friend_chat: bool = False  # 是否启用好友聊天

    mood_update_interval: float = 1.0  # 情绪更新间隔 单位秒
    mood_decay_rate: float = 0.95  # 情绪衰减率
    mood_intensity_factor: float = 0.7  # 情绪强度因子

    keywords_reaction_rules = []  # 关键词回复规则

    chinese_typo_enable = True  # 是否启用中文错别字生成器
    chinese_typo_error_rate = 0.03  # 单字替换概率
    chinese_typo_min_freq = 7  # 最小字频阈值
    chinese_typo_tone_error_rate = 0.2  # 声调错误概率
    chinese_typo_word_replace_rate = 0.02  # 整词替换概率

    # 默认人设
    PROMPT_PERSONALITY = [
        "曾经是一个学习地质的女大学生，现在学习心理学和脑科学，你会刷贴吧",
        "是一个女大学生，你有黑色头发，你会刷小红书",
        "是一个女大学生，你会刷b站，对ACG文化感兴趣",
    ]

    PROMPT_SCHEDULE_GEN = "一个曾经学习地质,现在学习心理学和脑科学的女大学生，喜欢刷qq，贴吧，知乎和小红书"

    PERSONALITY_1: float = 0.6  # 第一种人格概率
    PERSONALITY_2: float = 0.3  # 第二种人格概率
    PERSONALITY_3: float = 0.1  # 第三种人格概率
    
    build_memory_interval: int = 600  # 记忆构建间隔（秒）
    
    forget_memory_interval: int = 600  # 记忆遗忘间隔（秒）
    memory_forget_time: int = 24  # 记忆遗忘时间（小时）
    memory_forget_percentage: float = 0.01  # 记忆遗忘比例
    memory_compress_rate: float = 0.1  # 记忆压缩率
    memory_ban_words: list = field(
        default_factory=lambda: ["表情包", "图片", "回复", "聊天记录"]
    )  # 添加新的配置项默认值

    @staticmethod
    def get_config_dir() -> str:
        """获取配置文件目录"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
        config_dir = os.path.join(root_dir, "config")
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        return config_dir

    @classmethod
    def convert_to_specifierset(cls, value: str) -> SpecifierSet:
        """将 字符串 版本表达式转换成 SpecifierSet
        Args:
            value[str]: 版本表达式(字符串)
        Returns:
            SpecifierSet
        """

        try:
            converted = SpecifierSet(value)
        except InvalidSpecifier:
            logger.error(f"{value} 分类使用了错误的版本约束表达式\n", "请阅读 https://semver.org/lang/zh-CN/ 修改代码")
            exit(1)

        return converted

    @classmethod
    def get_config_version(cls, toml: dict) -> Version:
        """提取配置文件的 SpecifierSet 版本数据
        Args:
            toml[dict]: 输入的配置文件字典
        Returns:
            Version
        """

        if "inner" in toml:
            try:
                config_version: str = toml["inner"]["version"]
            except KeyError as e:
                logger.error("配置文件中 inner 段 不存在, 这是错误的配置文件")
                raise KeyError(f"配置文件中 inner 段 不存在 {e}, 这是错误的配置文件") from e
        else:
            toml["inner"] = {"version": "0.0.0"}
            config_version = toml["inner"]["version"]

        try:
            ver = version.parse(config_version)
        except InvalidVersion as e:
            logger.error(
                "配置文件中 inner段 的 version 键是错误的版本描述\n"
                "请阅读 https://semver.org/lang/zh-CN/ 修改配置，并参考本项目指定的模板进行修改\n"
                "本项目在不同的版本下有不同的模板，请注意识别"
            )
            raise InvalidVersion("配置文件中 inner段 的 version 键是错误的版本描述\n") from e

        return ver

    @classmethod
    def load_config(cls, config_path: str = None) -> "BotConfig":
        """从TOML配置文件加载配置"""
        config = cls()

        def personality(parent: dict):
            personality_config = parent["personality"]
            personality = personality_config.get("prompt_personality")
            if len(personality) >= 2:
                logger.debug(f"载入自定义人格:{personality}")
                config.PROMPT_PERSONALITY = personality_config.get("prompt_personality", config.PROMPT_PERSONALITY)
            logger.info(f"载入自定义日程prompt:{personality_config.get('prompt_schedule', config.PROMPT_SCHEDULE_GEN)}")
            config.PROMPT_SCHEDULE_GEN = personality_config.get("prompt_schedule", config.PROMPT_SCHEDULE_GEN)

            if config.INNER_VERSION in SpecifierSet(">=0.0.2"):
                config.PERSONALITY_1 = personality_config.get("personality_1_probability", config.PERSONALITY_1)
                config.PERSONALITY_2 = personality_config.get("personality_2_probability", config.PERSONALITY_2)
                config.PERSONALITY_3 = personality_config.get("personality_3_probability", config.PERSONALITY_3)

        def emoji(parent: dict):
            emoji_config = parent["emoji"]
            config.EMOJI_CHECK_INTERVAL = emoji_config.get("check_interval", config.EMOJI_CHECK_INTERVAL)
            config.EMOJI_REGISTER_INTERVAL = emoji_config.get("register_interval", config.EMOJI_REGISTER_INTERVAL)
            config.EMOJI_CHECK_PROMPT = emoji_config.get("check_prompt", config.EMOJI_CHECK_PROMPT)
            config.EMOJI_SAVE = emoji_config.get("auto_save", config.EMOJI_SAVE)
            config.EMOJI_CHECK = emoji_config.get("enable_check", config.EMOJI_CHECK)

        def cq_code(parent: dict):
            cq_code_config = parent["cq_code"]
            config.ENABLE_PIC_TRANSLATE = cq_code_config.get("enable_pic_translate", config.ENABLE_PIC_TRANSLATE)

        def bot(parent: dict):
            # 机器人基础配置
            bot_config = parent["bot"]
            bot_qq = bot_config.get("qq")
            config.BOT_QQ = int(bot_qq)
            config.BOT_NICKNAME = bot_config.get("nickname", config.BOT_NICKNAME)

            if config.INNER_VERSION in SpecifierSet(">=0.0.5"):
                config.BOT_ALIAS_NAMES = bot_config.get("alias_names", config.BOT_ALIAS_NAMES)

        def response(parent: dict):
            response_config = parent["response"]
            config.MODEL_R1_PROBABILITY = response_config.get("model_r1_probability", config.MODEL_R1_PROBABILITY)
            config.MODEL_V3_PROBABILITY = response_config.get("model_v3_probability", config.MODEL_V3_PROBABILITY)
            config.MODEL_R1_DISTILL_PROBABILITY = response_config.get(
                "model_r1_distill_probability", config.MODEL_R1_DISTILL_PROBABILITY
            )
            config.max_response_length = response_config.get("max_response_length", config.max_response_length)

        def model(parent: dict):
            # 加载模型配置
            model_config: dict = parent["model"]

            config_list = [
                "llm_reasoning",
                "llm_reasoning_minor",
                "llm_normal",
                "llm_normal_minor",
                "llm_topic_judge",
                "llm_summary_by_topic",
                "llm_emotion_judge",
                "vlm",
                "embedding",
                "moderation",
            ]

            for item in config_list:
                if item in model_config:
                    cfg_item: dict = model_config[item]

                    # base_url 的例子： SILICONFLOW_BASE_URL
                    # key 的例子： SILICONFLOW_KEY
                    cfg_target = {"name": "", "base_url": "", "key": "", "pri_in": 0, "pri_out": 0}

                    if config.INNER_VERSION in SpecifierSet("<=0.0.0"):
                        cfg_target = cfg_item

                    elif config.INNER_VERSION in SpecifierSet(">=0.0.1"):
                        stable_item = ["name", "pri_in", "pri_out"]
                        pricing_item = ["pri_in", "pri_out"]
                        # 从配置中原始拷贝稳定字段
                        for i in stable_item:
                            # 如果 字段 属于计费项 且获取不到，那默认值是 0
                            if i in pricing_item and i not in cfg_item:
                                cfg_target[i] = 0
                            else:
                                # 没有特殊情况则原样复制
                                try:
                                    cfg_target[i] = cfg_item[i]
                                except KeyError as e:
                                    logger.error(f"{item} 中的必要字段不存在，请检查")
                                    raise KeyError(f"{item} 中的必要字段 {e} 不存在，请检查") from e

                        provider = cfg_item.get("provider")
                        if provider is None:
                            logger.error(f"provider 字段在模型配置 {item} 中不存在，请检查")
                            raise KeyError(f"provider 字段在模型配置 {item} 中不存在，请检查")

                        cfg_target["base_url"] = f"{provider}_BASE_URL"
                        cfg_target["key"] = f"{provider}_KEY"

                    # 如果 列表中的项目在 model_config 中，利用反射来设置对应项目
                    setattr(config, item, cfg_target)
                else:
                    logger.error(f"模型 {item} 在config中不存在，请检查")
                    raise KeyError(f"模型 {item} 在config中不存在，请检查")

        def message(parent: dict):
            msg_config = parent["message"]
            config.MIN_TEXT_LENGTH = msg_config.get("min_text_length", config.MIN_TEXT_LENGTH)
            config.MAX_CONTEXT_SIZE = msg_config.get("max_context_size", config.MAX_CONTEXT_SIZE)
            config.emoji_chance = msg_config.get("emoji_chance", config.emoji_chance)
            config.ban_words = msg_config.get("ban_words", config.ban_words)

            if config.INNER_VERSION in SpecifierSet(">=0.0.2"):
                config.thinking_timeout = msg_config.get("thinking_timeout", config.thinking_timeout)
                config.response_willing_amplifier = msg_config.get(
                    "response_willing_amplifier", config.response_willing_amplifier
                )
                config.response_interested_rate_amplifier = msg_config.get(
                    "response_interested_rate_amplifier", config.response_interested_rate_amplifier
                )
                config.down_frequency_rate = msg_config.get("down_frequency_rate", config.down_frequency_rate)
            
            if config.INNER_VERSION in SpecifierSet(">=0.0.6"):
                config.ban_msgs_regex = msg_config.get("ban_msgs_regex", config.ban_msgs_regex)

        def memory(parent: dict):
            memory_config = parent["memory"]
            config.build_memory_interval = memory_config.get("build_memory_interval", config.build_memory_interval)
            config.forget_memory_interval = memory_config.get("forget_memory_interval", config.forget_memory_interval)

            # 在版本 >= 0.0.4 时才处理新增的配置项
            if config.INNER_VERSION in SpecifierSet(">=0.0.4"):
                config.memory_ban_words = set(memory_config.get("memory_ban_words", []))
                
            if config.INNER_VERSION in SpecifierSet(">=0.0.7"):
                config.memory_forget_time = memory_config.get("memory_forget_time", config.memory_forget_time)
                config.memory_forget_percentage = memory_config.get("memory_forget_percentage", config.memory_forget_percentage)
                config.memory_compress_rate = memory_config.get("memory_compress_rate", config.memory_compress_rate)

        def mood(parent: dict):
            mood_config = parent["mood"]
            config.mood_update_interval = mood_config.get("mood_update_interval", config.mood_update_interval)
            config.mood_decay_rate = mood_config.get("mood_decay_rate", config.mood_decay_rate)
            config.mood_intensity_factor = mood_config.get("mood_intensity_factor", config.mood_intensity_factor)

        def keywords_reaction(parent: dict):
            keywords_reaction_config = parent["keywords_reaction"]
            if keywords_reaction_config.get("enable", False):
                config.keywords_reaction_rules = keywords_reaction_config.get("rules", config.keywords_reaction_rules)

        def chinese_typo(parent: dict):
            chinese_typo_config = parent["chinese_typo"]
            config.chinese_typo_enable = chinese_typo_config.get("enable", config.chinese_typo_enable)
            config.chinese_typo_error_rate = chinese_typo_config.get("error_rate", config.chinese_typo_error_rate)
            config.chinese_typo_min_freq = chinese_typo_config.get("min_freq", config.chinese_typo_min_freq)
            config.chinese_typo_tone_error_rate = chinese_typo_config.get(
                "tone_error_rate", config.chinese_typo_tone_error_rate
            )
            config.chinese_typo_word_replace_rate = chinese_typo_config.get(
                "word_replace_rate", config.chinese_typo_word_replace_rate
            )

        def groups(parent: dict):
            groups_config = parent["groups"]
            config.talk_allowed_groups = set(groups_config.get("talk_allowed", []))
            config.talk_frequency_down_groups = set(groups_config.get("talk_frequency_down", []))
            config.ban_user_id = set(groups_config.get("ban_user_id", []))

        def others(parent: dict):
            others_config = parent["others"]
            config.enable_advance_output = others_config.get("enable_advance_output", config.enable_advance_output)
            config.enable_kuuki_read = others_config.get("enable_kuuki_read", config.enable_kuuki_read)
            if config.INNER_VERSION in SpecifierSet(">=0.0.7"):
                config.enable_debug_output = others_config.get("enable_debug_output", config.enable_debug_output)
                config.enable_friend_chat = others_config.get("enable_friend_chat", config.enable_friend_chat)

        # 版本表达式：>=1.0.0,<2.0.0
        # 允许字段：func: method, support: str, notice: str, necessary: bool
        # 如果使用 notice 字段，在该组配置加载时，会展示该字段对用户的警示
        # 例如："notice": "personality 将在 1.3.2 后被移除"，那么在有效版本中的用户就会虽然可以
        # 正常执行程序，但是会看到这条自定义提示
        include_configs = {
            "personality": {"func": personality, "support": ">=0.0.0"},
            "emoji": {"func": emoji, "support": ">=0.0.0"},
            "cq_code": {"func": cq_code, "support": ">=0.0.0"},
            "bot": {"func": bot, "support": ">=0.0.0"},
            "response": {"func": response, "support": ">=0.0.0"},
            "model": {"func": model, "support": ">=0.0.0"},
            "message": {"func": message, "support": ">=0.0.0"},
            "memory": {"func": memory, "support": ">=0.0.0", "necessary": False},
            "mood": {"func": mood, "support": ">=0.0.0"},
            "keywords_reaction": {"func": keywords_reaction, "support": ">=0.0.2", "necessary": False},
            "chinese_typo": {"func": chinese_typo, "support": ">=0.0.3", "necessary": False},
            "groups": {"func": groups, "support": ">=0.0.0"},
            "others": {"func": others, "support": ">=0.0.0"},
        }

        # 原地修改，将 字符串版本表达式 转换成 版本对象
        for key in include_configs:
            item_support = include_configs[key]["support"]
            include_configs[key]["support"] = cls.convert_to_specifierset(item_support)

        if os.path.exists(config_path):
            with open(config_path, "rb") as f:
                try:
                    toml_dict = tomli.load(f)
                except tomli.TOMLDecodeError as e:
                    logger.critical(f"配置文件bot_config.toml填写有误，请检查第{e.lineno}行第{e.colno}处：{e.msg}")
                    exit(1)

                # 获取配置文件版本
                config.INNER_VERSION = cls.get_config_version(toml_dict)

                # 如果在配置中找到了需要的项，调用对应项的闭包函数处理
                for key in include_configs:
                    if key in toml_dict:
                        group_specifierset: SpecifierSet = include_configs[key]["support"]

                        # 检查配置文件版本是否在支持范围内
                        if config.INNER_VERSION in group_specifierset:
                            # 如果版本在支持范围内，检查是否存在通知
                            if "notice" in include_configs[key]:
                                logger.warning(include_configs[key]["notice"])

                            include_configs[key]["func"](toml_dict)

                        else:
                            # 如果版本不在支持范围内，崩溃并提示用户
                            logger.error(
                                f"配置文件中的 '{key}' 字段的版本 ({config.INNER_VERSION}) 不在支持范围内。\n"
                                f"当前程序仅支持以下版本范围: {group_specifierset}"
                            )
                            raise InvalidVersion(f"当前程序仅支持以下版本范围: {group_specifierset}")

                    # 如果 necessary 项目存在，而且显式声明是 False，进入特殊处理
                    elif "necessary" in include_configs[key] and include_configs[key].get("necessary") is False:
                        # 通过 pass 处理的项虽然直接忽略也是可以的，但是为了不增加理解困难，依然需要在这里显式处理
                        if key == "keywords_reaction":
                            pass

                    else:
                        # 如果用户根本没有需要的配置项，提示缺少配置
                        logger.error(f"配置文件中缺少必需的字段: '{key}'")
                        raise KeyError(f"配置文件中缺少必需的字段: '{key}'")

                logger.success(f"成功加载配置文件: {config_path}")

        return config


# 获取配置文件路径
bot_config_floder_path = BotConfig.get_config_dir()
logger.debug(f"正在品鉴配置文件目录: {bot_config_floder_path}")

bot_config_path = os.path.join(bot_config_floder_path, "bot_config.toml")

if os.path.exists(bot_config_path):
    # 如果开发环境配置文件不存在，则使用默认配置文件
    logger.debug(f"异常的新鲜，异常的美味: {bot_config_path}")
    logger.info("使用bot配置文件")
else:
    # 配置文件不存在
    logger.error("配置文件不存在，请检查路径: {bot_config_path}")
    raise FileNotFoundError(f"配置文件不存在: {bot_config_path}")

global_config = BotConfig.load_config(config_path=bot_config_path)

if not global_config.enable_advance_output:
    logger.remove()
    
# 调试输出功能
if global_config.enable_debug_output:
    logger.remove()
    logger.add(sys.stdout, level="DEBUG")

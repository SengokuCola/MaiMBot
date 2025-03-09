import os
import shutil
import nonebot
import time
from dotenv import load_dotenv
from loguru import logger
from nonebot.adapters.onebot.v11 import Adapter
import platform

# 获取没有加载env时的环境变量
env_mask = {key: os.getenv(key) for key in os.environ}

def easter_egg():
    # 彩蛋
    from colorama import init, Fore

    init()
    text = "多年以后，面对AI行刑队，张三将会回想起他2023年在会议上讨论人工智能的那个下午"
    rainbow_colors = [Fore.RED, Fore.YELLOW, Fore.GREEN, Fore.CYAN, Fore.BLUE, Fore.MAGENTA]
    rainbow_text = ""
    for i, char in enumerate(text):
        rainbow_text += rainbow_colors[i % len(rainbow_colors)] + char
    print(rainbow_text)

def init_config():
    # 初次启动检测
    if not os.path.exists("config/bot_config.toml"):
        logger.warning("检测到bot_config.toml不存在，正在从模板复制")
        
        # 检查config目录是否存在
        if not os.path.exists("config"):
            os.makedirs("config")
            logger.info("创建config目录")

        shutil.copy("template/bot_config_template.toml", "config/bot_config.toml")
        logger.info("复制完成，请修改config/bot_config.toml和.env.prod中的配置后重新启动")

def init_env():
    # 初始化.env 默认ENVIRONMENT=prod
    if not os.path.exists(".env"):
        with open(".env", "w") as f:
            f.write("ENVIRONMENT=prod")

        # 检测.env.prod文件是否存在
        if not os.path.exists(".env.prod"):
            logger.error("检测到.env.prod文件不存在")
            shutil.copy("template.env", "./.env.prod")

    # 首先加载基础环境变量.env
    if os.path.exists(".env"):
        load_dotenv(".env")
        logger.success("成功加载基础环境变量配置")

def load_env():
    # 使用闭包实现对加载器的横向扩展，避免大量重复判断
    def prod():
        logger.success("加载生产环境变量配置")
        load_dotenv(".env.prod", override=True)  # override=True 允许覆盖已存在的环境变量

    def dev():
        logger.success("加载开发环境变量配置")
        load_dotenv(".env.dev", override=True)  # override=True 允许覆盖已存在的环境变量

    fn_map = {
        "prod": prod,
        "dev": dev
    }

    env = os.getenv("ENVIRONMENT")
    logger.info(f"[load_env] 当前的 ENVIRONMENT 变量值：{env}")

    if env in fn_map:
        fn_map[env]() # 根据映射执行闭包函数

    elif os.path.exists(f".env.{env}"):
        logger.success(f"加载{env}环境变量配置")
        load_dotenv(f".env.{env}", override=True)  # override=True 允许覆盖已存在的环境变量

    else:
        logger.error(f"ENVIRONMENT 配置错误，请检查 .env 文件中的 ENVIRONMENT 变量及对应 .env.{env} 是否存在")
        RuntimeError(f"ENVIRONMENT 配置错误，请检查 .env 文件中的 ENVIRONMENT 变量及对应 .env.{env} 是否存在")



def scan_provider(env_config: dict):
    provider = {}

    # 利用未初始化 env 时获取的 env_mask 来对新的环境变量集去重
    # 避免 GPG_KEY 这样的变量干扰检查
    env_config = dict(filter(lambda item: item[0] not in env_mask, env_config.items()))

    # 遍历 env_config 的所有键
    for key in env_config:
        # 检查键是否符合 {provider}_BASE_URL 或 {provider}_KEY 的格式
        if key.endswith("_BASE_URL") or key.endswith("_KEY"):
            # 提取 provider 名称
            provider_name = key.split("_", 1)[0]  # 从左分割一次，取第一部分

            # 初始化 provider 的字典（如果尚未初始化）
            if provider_name not in provider:
                provider[provider_name] = {"url": None, "key": None}

            # 根据键的类型填充 url 或 key
            if key.endswith("_BASE_URL"):
                provider[provider_name]["url"] = env_config[key]
            elif key.endswith("_KEY"):
                provider[provider_name]["key"] = env_config[key]

    # 检查每个 provider 是否同时存在 url 和 key
    for provider_name, config in provider.items():
        if config["url"] is None or config["key"] is None:
            logger.error(
                f"provider 内容：{config}\n"
                f"env_config 内容：{env_config}"
            )
            raise ValueError(f"请检查 '{provider_name}' 提供商配置是否丢失 BASE_URL 或 KEY 环境变量")

if __name__ == "__main__":
    # 利用 TZ 环境变量设定程序工作的时区
    # 仅保证行为一致，不依赖 localtime()，实际对生产环境几乎没有作用
    if platform.system().lower() != 'windows':
        time.tzset()

    easter_egg()
    init_config()
    init_env()
    load_env()

    env_config = {key: os.getenv(key) for key in os.environ}
    scan_provider(env_config)

    # 设置基础配置
    base_config = {
        "websocket_port": int(env_config.get("PORT", 8080)),
        "host": env_config.get("HOST", "127.0.0.1"),
        "log_level": "INFO",
    }

    # 合并配置
    nonebot.init(**base_config, **env_config)

    # 注册适配器
    driver = nonebot.get_driver()
    driver.register_adapter(Adapter)

    # 加载插件
    nonebot.load_plugins("src/plugins")

    nonebot.run()

import asyncio
import time
import os

from loguru import logger
from nonebot import get_driver, on_message, require
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message, MessageSegment,MessageEvent
from nonebot.typing import T_State

from ...common.database import Database
from ..moods.moods import MoodManager  # 导入情绪管理器
# from ..schedule.schedule_generator import bot_schedule
from ..utils.statistic import LLMStatistics
from .bot import chat_bot
from .config import global_config
from .emoji_manager import emoji_manager
from .relationship_manager import relationship_manager
from .willing_manager import willing_manager
from .chat_stream import chat_manager
from ..memory_system.memory import hippocampus, memory_graph
from .bot import ChatBot
from .message_sender import message_manager, message_sender


# 创建LLM统计实例
llm_stats = LLMStatistics("llm_statistics.txt")

# 添加标志变量
_message_manager_started = False

# 获取驱动器
driver = get_driver()
config = driver.config

Database.initialize(
    uri=os.getenv("MONGODB_URI"),
    host=os.getenv("MONGODB_HOST", "127.0.0.1"),
    port=int(os.getenv("MONGODB_PORT", "27017")),
    db_name=os.getenv("DATABASE_NAME", "MegBot"),
    username=os.getenv("MONGODB_USERNAME"),
    password=os.getenv("MONGODB_PASSWORD"),
    auth_source=os.getenv("MONGODB_AUTH_SOURCE"),
)
logger.success("初始化数据库成功")


# 初始化表情管理器
emoji_manager.initialize()

logger.debug(f"正在唤醒{global_config.BOT_NICKNAME}......")
# 创建机器人实例
chat_bot = ChatBot()
# 注册消息处理器
msg_in = on_message(priority=5)
# 创建定时任务
scheduler = require("nonebot_plugin_apscheduler").scheduler


@driver.on_startup
async def start_background_tasks():
    """启动后台任务"""
    # 启动LLM统计
    llm_stats.start()
    logger.success("LLM统计功能启动成功")

    # 初始化并启动情绪管理器
    mood_manager = MoodManager.get_instance()
    mood_manager.start_mood_update(update_interval=global_config.mood_update_interval)
    logger.success("情绪管理器启动成功")

    # 只启动表情包管理任务
    asyncio.create_task(emoji_manager.start_periodic_check(interval_MINS=global_config.EMOJI_CHECK_INTERVAL))
#    await bot_schedule.initialize()
#    bot_schedule.print_schedule()


@driver.on_startup
async def init_relationships():
    """在 NoneBot2 启动时初始化关系管理器"""
    logger.debug("正在加载用户关系数据...")
    await relationship_manager.load_all_relationships()
    asyncio.create_task(relationship_manager._start_relationship_manager())


@driver.on_bot_connect
async def _(bot: Bot):
    """Bot连接成功时的处理"""
    global _message_manager_started
    logger.debug(f"-----------{global_config.BOT_NICKNAME}成功连接！-----------")
    await willing_manager.ensure_started()

    message_sender.set_bot(bot)
    logger.success("-----------消息发送器已启动！-----------")

    if not _message_manager_started:
        asyncio.create_task(message_manager.start_processor())
        _message_manager_started = True
        logger.success("-----------消息处理器已启动！-----------")

    asyncio.create_task(emoji_manager._periodic_scan(interval_MINS=global_config.EMOJI_REGISTER_INTERVAL))
    logger.success("-----------开始偷表情包！-----------")
    asyncio.create_task(chat_manager._initialize())
    asyncio.create_task(chat_manager._auto_save_task())


@msg_in.handle()
async def _(bot: Bot, event: MessageEvent, state: T_State):
    await chat_bot.handle_message(event, bot)


# 添加build_memory定时任务
@scheduler.scheduled_job("interval", seconds=global_config.build_memory_interval, id="build_memory")
async def build_memory_task():
    """每build_memory_interval秒执行一次记忆构建"""
    logger.debug(
        "[记忆构建]"
        "------------------------------------开始构建记忆--------------------------------------")
    start_time = time.time()
    await hippocampus.operation_build_memory(chat_size=20)
    end_time = time.time()
    logger.success(
        f"[记忆构建]--------------------------记忆构建完成：耗时: {end_time - start_time:.2f} "
        "秒-------------------------------------------")


@scheduler.scheduled_job("interval", seconds=global_config.forget_memory_interval, id="forget_memory")
async def forget_memory_task():
    """每30秒执行一次记忆构建"""
    print("\033[1;32m[记忆遗忘]\033[0m 开始遗忘记忆...")
    await hippocampus.operation_forget_topic(percentage=global_config.memory_forget_percentage)
    print("\033[1;32m[记忆遗忘]\033[0m 记忆遗忘完成")


@scheduler.scheduled_job("interval", seconds=global_config.build_memory_interval + 10, id="merge_memory")
async def merge_memory_task():
    """每30秒执行一次记忆构建"""
    # print("\033[1;32m[记忆整合]\033[0m 开始整合")
    # await hippocampus.operation_merge_memory(percentage=0.1)
    # print("\033[1;32m[记忆整合]\033[0m 记忆整合完成")


@scheduler.scheduled_job("interval", seconds=30, id="print_mood")
async def print_mood_task():
    """每30秒打印一次情绪状态"""
    mood_manager = MoodManager.get_instance()
    mood_manager.print_mood_status()

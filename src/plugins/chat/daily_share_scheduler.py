import asyncio
import random
import datetime
from typing import Optional, Dict
from loguru import logger

from nonebot import get_driver
from .config import global_config
from .willing_manager import willing_manager
from .llm_generator import DailyMessageGenerate
from .message import Message, MessageSending, MessageSet
from .message_sender import message_manager
from .message_base import UserInfo, GroupInfo, Seg
from .chat_stream import chat_manager
from .message_cq import (
    MessageRecvCQ,
)

class DailyShareScheduler:
    def __init__(self):
        self.daily_generator = DailyMessageGenerate()
        self._tasks: Dict[str, asyncio.Task] = {}  # 存储每个群的任务
        self._started = False
        
    async def _group_share_task(self, group_id: str):
        """单个群组的分享任务"""
        # 为每个群组设置随机的初始等待时间，避免同时执行
        initial_wait = random.uniform(0, 30)
        daily_share_interval = global_config.daily_share_interval + initial_wait
        await asyncio.sleep(daily_share_interval)
        
        while True:
            try:
                current_time = datetime.datetime.now()
                
                # 检查是否在允许的时间范围内
                if global_config.daily_share_time_start <= current_time.hour < global_config.daily_share_time_end:
                    try:
                        # 创建用户信息
                        bot_user_info = UserInfo(
                            user_id=global_config.BOT_QQ,
                            user_nickname=global_config.BOT_NICKNAME,
                            platform="qq"
                        )
                        
                        # 创建群组信息
                        group_info = GroupInfo(
                            group_id=group_id,
                            group_name=None,
                            platform="qq"
                        )
                        
                        # 创建聊天流
                        chat_stream = await chat_manager.get_or_create_stream(
                            platform="qq",
                            user_info=bot_user_info,
                            group_info=group_info
                        )
                        
                        # 检查分享意愿
                        share_willing = await willing_manager.check_daily_share_wiling(chat_stream)
                        
                        # 生成随机数并与意愿比较
                        if random.random() < share_willing:
                            try:
                                # 创建消息对象
                                message = Message(
                                    message_id=f"daily_{int(datetime.datetime.now().timestamp())}",
                                    time=int(datetime.datetime.now().timestamp()),
                                    chat_stream=chat_stream,
                                    user_info=bot_user_info,
                                    message_segment=None,
                                    reply=None,
                                    detailed_plain_text="",
                                    processed_plain_text=""
                                )
                                
                                # 生成日常分享内容
                                content = await self.daily_generator.gen_response(message)

                                if content:
                                    # 创建消息段
                                    message_segment = Seg(type="text", data=content)
                                    
                                    message_set = MessageSet(
                                        chat_stream=chat_stream,
                                        message_id=message.message_info.message_id
                                    )
                                    
                                    # 创建发送消息对象
                                    bot_message = MessageSending(
                                        message_id=message.message_info.message_id,
                                        chat_stream=chat_stream,
                                        bot_user_info=bot_user_info,
                                        sender_info=bot_user_info,
                                        message_segment=message_segment,
                                        reply=None,
                                        is_head=True,
                                        is_emoji=False
                                    )                                      
                                    await bot_message.process()
                                    message_set.add_message(bot_message)
                                    message_manager.add_message(message_set)
                                    logger.info(f"群[{group_id}]分享意愿[{share_willing:.2f}]，已生成日常分享并加入发送队列")
                                
                                # 重置该群的分享意愿
                                await willing_manager.reset_daily_share_wiling(chat_stream)
                            except Exception as e:
                                logger.error(f"生成或发送消息时出错: {str(e)}")
                        else:
                            logger.debug(f"群[{group_id}]分享意愿[{share_willing:.2f}]不足，跳过分享")
                    except Exception as e:
                        logger.error(f"处理群[{group_id}]时出错: {str(e)}")
                
                # 等待2小时，加上随机偏移，避免同时执行
                wait_time = 30 + random.uniform(-5, 5)  # 测试时使用30秒，加上随机偏移
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"群[{group_id}]的日常分享任务出错: {str(e)}")
                await asyncio.sleep(60)  # 出错后等待1分钟再试
                
    async def start(self):
        """启动定时任务"""
        if not self._started:
            self._started = True
            # 为每个群创建独立的任务
            for group_id in global_config.shares_allow_groups:
                logger.info(f"启动群[{group_id}]的日常分享任务")
                # 使用 create_task 创建独立的任务
                task = asyncio.create_task(self._group_share_task(group_id))
                self._tasks[group_id] = task
            logger.info("日常分享定时任务已启动")

# 创建全局实例
daily_share_scheduler = DailyShareScheduler()

# 在驱动器启动时启动定时任务
driver = get_driver()

@driver.on_startup
async def _():
    await daily_share_scheduler.start() 
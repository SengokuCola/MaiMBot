import asyncio
import time
from typing import Dict, List, Optional, Union

from loguru import logger
from nonebot.adapters.onebot.v11 import Bot

from .cq_code import cq_code_tool
from .message import Message, Message_Sending, Message_Thinking, MessageSet
from .storage import MessageStorage
from .utils import calculate_typing_time
from .config import global_config


class Message_Sender:
    """发送器"""

    def __init__(self):
        self.message_interval = (0.5, 1)  # 消息间隔时间范围(秒)
        self.last_send_time = 0
        self._current_bot = None

    def set_bot(self, bot: Bot):
        """设置当前bot实例"""
        self._current_bot = bot

    async def send_group_message(
            self,
            group_id: int,
            send_text: str,
            auto_escape: bool = False,
            reply_message_id: int = None,
            at_user_id: int = None
    ) -> None:

        if not self._current_bot:
            raise RuntimeError("Bot未设置，请先调用set_bot方法设置bot实例")

        message = send_text

        # 如果需要回复
        if reply_message_id:
            reply_cq = cq_code_tool.create_reply_cq(reply_message_id)
            message = reply_cq + message

        # 如果需要at
        # if at_user_id:
        #     at_cq = cq_code_tool.create_at_cq(at_user_id)
        #     message = at_cq + " " + message

        typing_time = calculate_typing_time(message)
        if typing_time > 10:
            typing_time = 10
        await asyncio.sleep(typing_time)

        # 发送消息
        try:
            await self._current_bot.send_group_msg(
                group_id=group_id,
                message=message,
                auto_escape=auto_escape
            )
            logger.debug(f"发送消息{message}成功")
        except Exception:
            logger.exception(f"发送消息{message}失败")


class MessageContainer:
    """单个群的发送/思考消息容器"""

    def __init__(self, group_id: int, max_size: int = 100):
        self.group_id = group_id
        self.max_size = max_size
        self.messages = []
        self.last_send_time = 0
        self.thinking_timeout = 20  # 思考超时时间（秒）

    def get_timeout_messages(self) -> List[Message_Sending]:
        """获取所有超时的Message_Sending对象（思考时间超过30秒），按thinking_start_time排序"""
        current_time = time.time()
        timeout_messages = []

        for msg in self.messages:
            if isinstance(msg, Message_Sending):
                if current_time - msg.thinking_start_time > self.thinking_timeout:
                    timeout_messages.append(msg)

        # 按thinking_start_time排序，时间早的在前面
        timeout_messages.sort(key=lambda x: x.thinking_start_time)

        return timeout_messages

    def get_earliest_message(self) -> Optional[Union[Message_Thinking, Message_Sending]]:
        """获取thinking_start_time最早的消息对象"""
        if not self.messages:
            return None
        earliest_time = float('inf')
        earliest_message = None
        for msg in self.messages:
            msg_time = msg.thinking_start_time
            if msg_time < earliest_time:
                earliest_time = msg_time
                earliest_message = msg
        return earliest_message

    def add_message(self, message: Union[Message_Thinking, Message_Sending]) -> None:
        """添加消息到队列"""
        # print(f"\033[1;32m[添加消息]\033[0m 添加消息到对应群")
        if isinstance(message, MessageSet):
            for single_message in message.messages:
                self.messages.append(single_message)
        else:
            self.messages.append(message)

    def remove_message(self, message: Union[Message_Thinking, Message_Sending]) -> bool:
        """移除消息，如果消息存在则返回True，否则返回False"""
        try:
            if message in self.messages:
                self.messages.remove(message)
                return True
            return False
        except Exception:
            logger.exception("移除消息时发生错误")
            return False

    def has_messages(self) -> bool:
        """检查是否有待发送的消息"""
        return bool(self.messages)

    def get_all_messages(self) -> List[Union[Message, Message_Thinking]]:
        """获取所有消息"""
        return list(self.messages)


class MessageManager:
    """管理所有群的消息容器"""

    def __init__(self):
        self.containers: Dict[int, MessageContainer] = {}
        self.storage = MessageStorage()
        self._running = True

    def get_container(self, group_id: int) -> MessageContainer:
        """获取或创建群的消息容器"""
        if group_id not in self.containers:
            self.containers[group_id] = MessageContainer(group_id)
        return self.containers[group_id]

    def add_message(self, message: Union[Message_Thinking, Message_Sending, MessageSet]) -> None:
        container = self.get_container(message.group_id)
        container.add_message(message)

    async def process_group_messages(self, group_id: int):
        """处理群消息"""
        # if int(time.time() / 3) == time.time() / 3:
        # print(f"\033[1;34m[调试]\033[0m 开始处理群{group_id}的消息")
        container = self.get_container(group_id)
        if container.has_messages():
            # 最早的对象，可能是思考消息，也可能是发送消息
            message_earliest = container.get_earliest_message()  # 一个message_thinking or message_sending

            # 如果是思考消息
            if isinstance(message_earliest, Message_Thinking):
                # 优先等待这条消息
                message_earliest.update_thinking_time()
                thinking_time = message_earliest.thinking_time
                print(f"消息正在思考中，已思考{int(thinking_time)}秒\r", end='', flush=True)

                # 检查是否超时
                if thinking_time > global_config.thinking_timeout:
                    logger.warning(f"消息思考超时({thinking_time}秒)，移除该消息")
                    container.remove_message(message_earliest)
            else:  # 如果不是message_thinking就只能是message_sending
                logger.debug(f"消息'{message_earliest.processed_plain_text}'正在发送中")
                # 直接发，等什么呢
                if message_earliest.is_head and message_earliest.update_thinking_time() > 30:
                    await message_sender.send_group_message(group_id, message_earliest.processed_plain_text,
                                                            auto_escape=False,
                                                            reply_message_id=message_earliest.reply_message_id)
                else:
                    await message_sender.send_group_message(group_id, message_earliest.processed_plain_text,
                                                            auto_escape=False)
                # 移除消息
                if message_earliest.is_emoji:
                    message_earliest.processed_plain_text = "[表情包]"
                await self.storage.store_message(message_earliest, None)

                container.remove_message(message_earliest)

            # 获取并处理超时消息
            message_timeout = container.get_timeout_messages()  # 也许是一堆message_sending
            if message_timeout:
                logger.warning(f"发现{len(message_timeout)}条超时消息")
                for msg in message_timeout:
                    if msg == message_earliest:
                        continue  # 跳过已经处理过的消息

                    try:
                        # 发送
                        if msg.is_head and msg.update_thinking_time() > 30:
                            await message_sender.send_group_message(group_id, msg.processed_plain_text,
                                                                    auto_escape=False,
                                                                    reply_message_id=msg.reply_message_id)
                        else:
                            await message_sender.send_group_message(group_id, msg.processed_plain_text,
                                                                    auto_escape=False)

                        # 如果是表情包，则替换为"[表情包]"
                        if msg.is_emoji:
                            msg.processed_plain_text = "[表情包]"
                        await self.storage.store_message(msg, None)

                        # 安全地移除消息
                        if not container.remove_message(msg):
                            logger.warning("尝试删除不存在的消息")
                    except Exception:
                        logger.exception("处理超时消息时发生错误")
                        continue

    async def start_processor(self):
        """启动消息处理器"""
        while self._running:
            await asyncio.sleep(1)
            tasks = []
            for group_id in self.containers.keys():
                tasks.append(self.process_group_messages(group_id))

            await asyncio.gather(*tasks)


# 创建全局消息管理器实例
message_manager = MessageManager()
# 创建全局发送器实例
message_sender = Message_Sender()

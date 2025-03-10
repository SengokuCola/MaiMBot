import time
from random import random
import asyncio

from loguru import logger
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from ..memory_system.memory import hippocampus
from ..moods.moods import MoodManager  # 导入情绪管理器
from .config import global_config
from .cq_code import CQCode  # 导入CQCode模块
from .emoji_manager import emoji_manager  # 导入表情包管理器
from .llm_generator import ResponseGenerator
from .message import (
    Message,
    Message_Sending,
    Message_Thinking,  # 导入 Message_Thinking 类
    MessageSet,
)
from .message_sender import message_manager  # 导入新的消息管理器
from .relationship_manager import relationship_manager
from .storage import MessageStorage
from .utils import calculate_typing_time, is_mentioned_bot_in_txt
from .willing_manager import willing_manager  # 导入意愿管理器


class ChatBot:
    def __init__(self):
        self.storage = MessageStorage()
        self.gpt = ResponseGenerator()
        self.bot = None  # bot 实例引用
        self._started = False
        self.mood_manager = MoodManager.get_instance()  # 获取情绪管理器单例
        self.mood_manager.start_mood_update()  # 启动情绪更新

        self.emoji_chance = 0.2  # 发送表情包的基础概率
        # self.message_streams = MessageStreamContainer()

    async def _ensure_started(self):
        """确保所有任务已启动"""
        if not self._started:
            self._started = True

    async def handle_message(self, event: GroupMessageEvent, bot: Bot) -> None:
        """处理收到的群消息"""

        if event.group_id not in global_config.talk_allowed_groups:
            return
        self.bot = bot  # 更新 bot 实例

        if event.user_id in global_config.ban_user_id:
            return

        group_info = await bot.get_group_info(group_id=event.group_id)
        sender_info = await bot.get_group_member_info(group_id=event.group_id, user_id=event.user_id, no_cache=True)

        await relationship_manager.update_relationship(user_id=event.user_id, data=sender_info)
        await relationship_manager.update_relationship_value(user_id=event.user_id, relationship_value=0.5)

        message = Message(
            group_id=event.group_id,
            user_id=event.user_id,
            message_id=event.message_id,
            user_cardname=sender_info['card'],
            raw_message=str(event.original_message),
            plain_text=event.get_plaintext(),
            reply_message=event.reply,
        )
        await message.initialize()

        # 过滤词
        for word in global_config.ban_words:
            if word in message.detailed_plain_text:
                logger.info(
                    f"[{message.group_name}]{message.user_nickname}:{message.processed_plain_text}")
                logger.info(f"[过滤词识别]消息中含有{word}，filtered")
                return

        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(message.time))

        # topic=await topic_identifier.identify_topic_llm(message.processed_plain_text)
        topic = ''
        interested_rate = 0
        interested_rate = await hippocampus.memory_activate_value(message.processed_plain_text) / 100
        logger.debug(f"对{message.processed_plain_text}"
                     f"的激活度:{interested_rate}")
        # logger.info(f"\033[1;32m[主题识别]\033[0m 使用{global_config.topic_extract}主题: {topic}")

        await self.storage.store_message(message, topic[0] if topic else None)

        is_mentioned = is_mentioned_bot_in_txt(message.processed_plain_text)

        if is_mentioned:
            #如果被@等待下文10秒
            await asyncio.sleep(10)
            logger.info(f"被@，等待下文")

        reply_probability = willing_manager.change_reply_willing_received(
            event.group_id,
            topic[0] if topic else None,
            is_mentioned,
            global_config,
            event.user_id,
            message.is_emoji,
            interested_rate
        )
        current_willing = willing_manager.get_willing(event.group_id)

        logger.info(
            f"[{current_time}][{message.group_name}]{message.user_nickname}:"
            f"{message.processed_plain_text}[回复意愿:{current_willing:.2f}][概率:{reply_probability * 100:.1f}%]")

        response = ""

        if random() < reply_probability:
            tinking_time_point = round(time.time(), 2)
            think_id = 'mt' + str(tinking_time_point)
            thinking_message = Message_Thinking(message=message, message_id=think_id)

            message_manager.add_message(thinking_message)

            willing_manager.change_reply_willing_sent(thinking_message.group_id)

            response, raw_content = await self.gpt.generate_response(message)

        if response:
            container = message_manager.get_container(event.group_id)
            thinking_message = None
            # 找到message,删除
            for msg in container.messages:
                if isinstance(msg, Message_Thinking) and msg.message_id == think_id:
                    thinking_message = msg
                    container.messages.remove(msg)
                    # print(f"\033[1;32m[思考消息删除]\033[0m 已找到思考消息对象，开始删除")
                    break

            # 如果找不到思考消息，直接返回
            if not thinking_message:
                logger.warning(f"未找到对应的思考消息，可能已超时被移除")
                return

            # 记录开始思考的时间，避免从思考到回复的时间太久
            thinking_start_time = thinking_message.thinking_start_time
            message_set = MessageSet(event.group_id, global_config.BOT_QQ,
                                     think_id)  # 发送消息的id和产生发送消息的message_thinking是一致的
            # 计算打字时间，1是为了模拟打字，2是避免多条回复乱序
            accu_typing_time = 0

            # print(f"\033[1;32m[开始回复]\033[0m 开始将回复1载入发送容器")
            mark_head = False
            for msg in response:
                # print(f"\033[1;32m[回复内容]\033[0m {msg}")
                # 通过时间改变时间戳
                typing_time = calculate_typing_time(msg)
                accu_typing_time += typing_time
                timepoint = tinking_time_point + accu_typing_time

                bot_message = Message_Sending(
                    group_id=event.group_id,
                    user_id=global_config.BOT_QQ,
                    message_id=think_id,
                    raw_message=msg,
                    plain_text=msg,
                    processed_plain_text=msg,
                    user_nickname=global_config.BOT_NICKNAME,
                    group_name=message.group_name,
                    time=timepoint,  # 记录了回复生成的时间
                    thinking_start_time=thinking_start_time,  # 记录了思考开始的时间
                    reply_message_id=message.message_id
                )
                await bot_message.initialize()
                if not mark_head:
                    bot_message.is_head = True
                    mark_head = True
                message_set.add_message(bot_message)

            # message_set 可以直接加入 message_manager
            # print(f"\033[1;32m[回复]\033[0m 将回复载入发送容器")
            message_manager.add_message(message_set)

            bot_response_time = tinking_time_point

            if random() < global_config.emoji_chance:
                emoji_raw = await emoji_manager.get_emoji_for_text(response)

                # 检查是否 <没有找到> emoji
                if emoji_raw != None:
                    emoji_path, discription = emoji_raw

                    emoji_cq = CQCode.create_emoji_cq(emoji_path)

                    if random() < 0.5:
                        bot_response_time = tinking_time_point - 1
                    else:
                        bot_response_time = bot_response_time + 1

                    bot_message = Message_Sending(
                        group_id=event.group_id,
                        user_id=global_config.BOT_QQ,
                        message_id=0,
                        raw_message=emoji_cq,
                        plain_text=emoji_cq,
                        processed_plain_text=emoji_cq,
                        detailed_plain_text=discription,
                        user_nickname=global_config.BOT_NICKNAME,
                        group_name=message.group_name,
                        time=bot_response_time,
                        is_emoji=True,
                        translate_cq=False,
                        thinking_start_time=thinking_start_time,
                        # reply_message_id=message.message_id
                    )
                    await bot_message.initialize()
                    message_manager.add_message(bot_message)
            emotion = await self.gpt._get_emotion_tags(raw_content)
            logger.debug(f"为 '{response}' 获取到的情感标签为：{emotion}")
            valuedict = {
                'happy': 0.5,
                'angry': -1,
                'sad': -0.5,
                'surprised': 0.2,
                'disgusted': -1.5,
                'fearful': -0.7,
                'neutral': 0.1
            }
            await relationship_manager.update_relationship_value(message.user_id,
                                                                 relationship_value=valuedict[emotion[0]])
            # 使用情绪管理器更新情绪
            self.mood_manager.update_mood_from_emotion(emotion[0], global_config.mood_intensity_factor)

        # willing_manager.change_reply_willing_after_sent(event.group_id)


# 创建全局ChatBot实例
chat_bot = ChatBot()

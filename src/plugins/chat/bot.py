import re
import time
from random import random

import asyncio

from loguru import logger
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    MessageEvent,
    PrivateMessageEvent,
)

from ..memory_system.memory import hippocampus
from ..moods.moods import MoodManager  # 导入情绪管理器
from .config import global_config
from .emoji_manager import emoji_manager  # 导入表情包管理器
from .llm_generator import ResponseGenerator
from .message import MessageSending, MessageRecv, MessageThinking, MessageSet
from .message_cq import (
    MessageRecvCQ,
)
from .chat_stream import chat_manager

from .message_sender import message_manager  # 导入新的消息管理器
from .relationship_manager import relationship_manager
from .storage import MessageStorage
from .utils import calculate_typing_time, is_mentioned_bot_in_message
from .utils_image import image_path_to_base64
from .willing_manager import willing_manager  # 导入意愿管理器
from .message_base import UserInfo, GroupInfo, Seg


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

    async def handle_message(self, event: MessageEvent, bot: Bot) -> None:
        """处理收到的消息"""

        self.bot = bot  # 更新 bot 实例

        # 用户屏蔽,不区分私聊/群聊
        if event.user_id in global_config.ban_user_id:
            return

        # 处理私聊消息
        if isinstance(event, PrivateMessageEvent):
            if not global_config.enable_friend_chat:  # 私聊过滤
                return
            else:
                try:
                    user_info = UserInfo(
                        user_id=event.user_id,
                        user_nickname=(await bot.get_stranger_info(user_id=event.user_id, no_cache=True))["nickname"],
                        user_cardname=None,
                        platform="qq",
                    )
                except Exception as e:
                    logger.error(f"获取陌生人信息失败: {e}")
                    return
                logger.debug(user_info)

                # group_info = GroupInfo(group_id=0, group_name="私聊", platform="qq")
                group_info = None

        # 处理群聊消息
        else:
            # 白名单设定由nontbot侧完成
            if event.group_id:
                if event.group_id not in global_config.talk_allowed_groups:
                    return

            user_info = UserInfo(
                user_id=event.user_id,
                user_nickname=event.sender.nickname,
                user_cardname=event.sender.card or None,
                platform="qq",
            )

            group_info = GroupInfo(group_id=event.group_id, group_name=None, platform="qq")

        # group_info = await bot.get_group_info(group_id=event.group_id)
        # sender_info = await bot.get_group_member_info(group_id=event.group_id, user_id=event.user_id, no_cache=True)

        message_cq = MessageRecvCQ(
            message_id=event.message_id,
            user_info=user_info,
            raw_message=str(event.original_message),
            group_info=group_info,
            reply_message=event.reply,
            platform="qq",
        )
        message_json = message_cq.to_dict()

        # 进入maimbot
        message = MessageRecv(message_json)
        groupinfo = message.message_info.group_info
        userinfo = message.message_info.user_info
        messageinfo = message.message_info

        # 消息过滤，涉及到config有待更新

        chat = await chat_manager.get_or_create_stream(
            platform=messageinfo.platform, user_info=userinfo, group_info=groupinfo
        )
        message.update_chat_stream(chat)
        await relationship_manager.update_relationship(
            chat_stream=chat,
        )
        await relationship_manager.update_relationship_value(chat_stream=chat, relationship_value=0.5)

        await message.process()
        # 过滤词
        for word in global_config.ban_words:
            if word in message.processed_plain_text:
                logger.info(
                    f"[{chat.group_info.group_name if chat.group_info.group_id else '私聊'}]{userinfo.user_nickname}:{message.processed_plain_text}"
                )
                logger.info(f"[过滤词识别]消息中含有{word}，filtered")
                return

        # 正则表达式过滤
        for pattern in global_config.ban_msgs_regex:
            if re.search(pattern, message.raw_message):
                logger.info(
                    f"[{chat.group_info.group_name if chat.group_info.group_id else '私聊'}]{message.user_nickname}:{message.raw_message}"
                )
                logger.info(f"[正则表达式过滤]消息匹配到{pattern}，filtered")
                return

        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(messageinfo.time))

        # topic=await topic_identifier.identify_topic_llm(message.processed_plain_text)
        
        topic = ""
        interested_rate = await hippocampus.memory_activate_value(message.processed_plain_text) / 100
        logger.debug(f"对{message.processed_plain_text}的激活度:{interested_rate}")
        # logger.info(f"\033[1;32m[主题识别]\033[0m 使用{global_config.topic_extract}主题: {topic}")


        await self.storage.store_message(message, chat, topic[0] if topic else None)

        is_mentioned = is_mentioned_bot_in_message(message)
    
        if is_mentioned:
            #如果被@等待下文10秒
            await asyncio.sleep(10)
            logger.info(f"被@，等待下文")
            
        reply_probability = await willing_manager.change_reply_willing_received(
            chat_stream=chat,
            topic=topic[0] if topic else None,
            is_mentioned_bot=is_mentioned,
            config=global_config,
            is_emoji=message.is_emoji,
            interested_rate=interested_rate,


        )
        current_willing = willing_manager.get_willing(chat_stream=chat)

        logger.info(
            f"[{current_time}][{chat.group_info.group_name if chat.group_info.group_id else '私聊'}]{chat.user_info.user_nickname}:"
            f"{message.processed_plain_text}[回复意愿:{current_willing:.2f}][概率:{reply_probability * 100:.1f}%]"
        )

        response = None

        if random() < reply_probability:
            bot_user_info = UserInfo(
                user_id=global_config.BOT_QQ,
                user_nickname=global_config.BOT_NICKNAME,
                platform=messageinfo.platform,
            )
            thinking_time_point = round(time.time(), 2)
            think_id = "mt" + str(thinking_time_point)
            thinking_message = MessageThinking(
                message_id=think_id,
                chat_stream=chat,
                bot_user_info=bot_user_info,
                reply=message,
            )

            message_manager.add_message(thinking_message)

            willing_manager.change_reply_willing_sent(chat)

            response, raw_content = await self.gpt.generate_response(message)

        # print(f"response: {response}")
        if response:
            # print(f"有response: {response}")
            container = message_manager.get_container(chat.stream_id)
            thinking_message = None
            # 找到message,删除
            # print(f"开始找思考消息")
            for msg in container.messages:
                if isinstance(msg, MessageThinking) and msg.message_info.message_id == think_id:
                    # print(f"找到思考消息: {msg}")
                    thinking_message = msg
                    container.messages.remove(msg)
                    break

            # 如果找不到思考消息，直接返回
            if not thinking_message:
                logger.warning("未找到对应的思考消息，可能已超时被移除")
                return

            # 记录开始思考的时间，避免从思考到回复的时间太久
            thinking_start_time = thinking_message.thinking_start_time
            message_set = MessageSet(chat, think_id)
            # 计算打字时间，1是为了模拟打字，2是避免多条回复乱序
            accu_typing_time = 0

            mark_head = False
            for msg in response:
                # print(f"\033[1;32m[回复内容]\033[0m {msg}")
                # 通过时间改变时间戳
                typing_time = calculate_typing_time(msg)
                logger.debug(f"typing_time: {typing_time}")
                accu_typing_time += typing_time
                timepoint = thinking_time_point + accu_typing_time
                message_segment = Seg(type="text", data=msg)
                # logger.debug(f"message_segment: {message_segment}")
                bot_message = MessageSending(
                    message_id=think_id,
                    chat_stream=chat,
                    bot_user_info=bot_user_info,
                    sender_info=userinfo,
                    message_segment=message_segment,
                    reply=message,
                    is_head=not mark_head,
                    is_emoji=False,
                )
                print(f"bot_message: {bot_message}")
                if not mark_head:
                    mark_head = True
                print(f"添加消息到message_set: {bot_message}")
                message_set.add_message(bot_message)

            # message_set 可以直接加入 message_manager
            # print(f"\033[1;32m[回复]\033[0m 将回复载入发送容器")

            logger.debug("添加message_set到message_manager")

            message_manager.add_message(message_set)

            bot_response_time = thinking_time_point

            if random() < global_config.emoji_chance:
                emoji_raw = await emoji_manager.get_emoji_for_text(response)

                # 检查是否 <没有找到> emoji
                if emoji_raw != None:
                    emoji_path, description = emoji_raw

                    emoji_cq = image_path_to_base64(emoji_path)

                    if random() < 0.5:
                        bot_response_time = thinking_time_point - 1
                    else:
                        bot_response_time = bot_response_time + 1

                    message_segment = Seg(type="emoji", data=emoji_cq)
                    bot_message = MessageSending(
                        message_id=think_id,
                        chat_stream=chat,
                        bot_user_info=bot_user_info,
                        sender_info=userinfo,
                        message_segment=message_segment,
                        reply=message,
                        is_head=False,
                        is_emoji=True,
                    )
                    message_manager.add_message(bot_message)

            emotion = await self.gpt._get_emotion_tags(raw_content)
            logger.debug(f"为 '{response}' 获取到的情感标签为：{emotion}")
            valuedict = {
                "happy": 0.5,
                "angry": -1,
                "sad": -0.5,
                "surprised": 0.2,
                "disgusted": -1.5,
                "fearful": -0.7,
                "neutral": 0.1,
            }
            await relationship_manager.update_relationship_value(
                chat_stream=chat, relationship_value=valuedict[emotion[0]]
            )
            # 使用情绪管理器更新情绪
            self.mood_manager.update_mood_from_emotion(emotion[0], global_config.mood_intensity_factor)

            # willing_manager.change_reply_willing_after_sent(
            #     chat_stream=chat
            # )


# 创建全局ChatBot实例
chat_bot = ChatBot()

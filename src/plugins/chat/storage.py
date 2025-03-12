from typing import Optional, Union

from ...common.database import Database
from .message import MessageSending, MessageRecv
from .chat_stream import ChatStream
from loguru import logger


class MessageStorage:
    def __init__(self):
        self.db = Database.get_instance()
        
    async def store_message(self, message: Union[MessageSending, MessageRecv],chat_stream:ChatStream, topic: Optional[str] = None) -> None:
        """存储消息到数据库"""
        try:
            message_data = {
                    "message_id": message.message_info.message_id,
                    "time": message.message_info.time,
                    "chat_id":chat_stream.stream_id,
                    "chat_info": chat_stream.to_dict(),
                    "user_info": message.message_info.user_info.to_dict(),
                    "processed_plain_text": message.processed_plain_text,
                    "detailed_plain_text": message.detailed_plain_text,
                    "topic": topic,
                }
            self.db.db.messages.insert_one(message_data)
        except Exception:
            logger.exception("存储消息失败")

# 如果需要其他存储相关的函数，可以在这里添加

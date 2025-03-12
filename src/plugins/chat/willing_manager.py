import asyncio
from typing import Dict


from .config import global_config
from .chat_stream import ChatStream

from loguru import logger


class WillingManager:
    def __init__(self):
        self.chat_reply_willing: Dict[str, float] = {}  # 存储每个聊天流的回复意愿
        self.chat_reply_willing: Dict[str, float] = {}  # 存储每个聊天流的回复意愿
        self._decay_task = None
        self._started = False
        
    async def _decay_reply_willing(self):
        """定期衰减回复意愿"""
        while True:
            await asyncio.sleep(5)
            for chat_id in self.chat_reply_willing:
                self.chat_reply_willing[chat_id] = max(0, self.chat_reply_willing[chat_id] * 0.6)
            for chat_id in self.chat_reply_willing:
                self.chat_reply_willing[chat_id] = max(0, self.chat_reply_willing[chat_id] * 0.6)
                
    def get_willing(self,chat_stream:ChatStream) -> float:
        """获取指定聊天流的回复意愿"""
        stream = chat_stream
        if stream:
            return self.chat_reply_willing.get(stream.stream_id, 0)
        return 0
    
    def set_willing(self, chat_id: str, willing: float):
        """设置指定聊天流的回复意愿"""
        self.chat_reply_willing[chat_id] = willing
    def set_willing(self, chat_id: str, willing: float):
        """设置指定聊天流的回复意愿"""
        self.chat_reply_willing[chat_id] = willing
        
    async def change_reply_willing_received(self, 
                                          chat_stream:ChatStream,
                                          topic: str = None,
                                          is_mentioned_bot: bool = False,
                                          config = None,
                                          is_emoji: bool = False,
                                          interested_rate: float = 0) -> float:
        """改变指定聊天流的回复意愿并返回回复概率"""
        # 获取或创建聊天流
        stream = chat_stream
        chat_id = stream.stream_id
        
        current_willing = self.chat_reply_willing.get(chat_id, 0)
        
        # print(f"初始意愿: {current_willing}")
        if is_mentioned_bot and current_willing < 1.0:
            current_willing += 0.9
            print(f"被提及, 当前意愿: {current_willing}")
        elif is_mentioned_bot:
            current_willing += 0.05
            print(f"被重复提及, 当前意愿: {current_willing}")
        
        if is_emoji:
            current_willing *= 0.1
            print(f"表情包, 当前意愿: {current_willing}")
        
        print(f"放大系数_interested_rate: {global_config.response_interested_rate_amplifier}")
        interested_rate *= global_config.response_interested_rate_amplifier #放大回复兴趣度
        if interested_rate > 0.4:
            # print(f"兴趣度: {interested_rate}, 当前意愿: {current_willing}")
            current_willing += interested_rate-0.4
        
        current_willing *= global_config.response_willing_amplifier #放大回复意愿
        # print(f"放大系数_willing: {global_config.response_willing_amplifier}, 当前意愿: {current_willing}")
        
        reply_probability = max((current_willing - 0.45) * 2, 0)

        # 回复意愿增强器
        if global_config.reply_possibility_enhance_enable:
            logger.debug("回复意愿增强器激活")
            # 群聊
            if chat_stream.group_info and chat_stream.group_info.group_id:
                reply_probability += global_config.group_reply_possibility_enhance
                reply_probability = min(reply_probability, global_config.max_group_reply_possibility)
                reply_probability = max(reply_probability, global_config.min_group_reply_possibility)
                logger.debug(f"群聊回复意愿增强: {reply_probability}")
                
            # 私聊
            else:
                reply_probability += global_config.friend_reply_possibility_enhance
                reply_probability = min(reply_probability, global_config.max_friend_reply_possibility)
                reply_probability = max(reply_probability, global_config.min_friend_reply_possibility)
                logger.debug(f"私聊回复意愿增强: {reply_probability}")
                

        # 检查群组权限（如果是群聊）
        if chat_stream.group_info:                
            if chat_stream.group_info.group_id in config.talk_frequency_down_groups:
                reply_probability = reply_probability / global_config.down_frequency_rate

        reply_probability = min(reply_probability, 1)
        if reply_probability < 0:
            reply_probability = 0
            
        self.chat_reply_willing[chat_id] = min(current_willing, 3.0)
        return reply_probability
    
    def change_reply_willing_sent(self, chat_stream:ChatStream):
        """开始思考后降低聊天流的回复意愿"""
        stream = chat_stream
        if stream:
            current_willing = self.chat_reply_willing.get(stream.stream_id, 0)
            self.chat_reply_willing[stream.stream_id] = max(0, current_willing - 2)
        
    def change_reply_willing_after_sent(self,chat_stream:ChatStream):
        """发送消息后提高聊天流的回复意愿"""
        stream = chat_stream
        if stream:
            current_willing = self.chat_reply_willing.get(stream.stream_id, 0)
            if current_willing < 1:
                self.chat_reply_willing[stream.stream_id] = min(1, current_willing + 0.2)
        
    async def ensure_started(self):
        """确保衰减任务已启动"""
        if not self._started:
            if self._decay_task is None:
                self._decay_task = asyncio.create_task(self._decay_reply_willing())
            self._started = True

# 创建全局实例
willing_manager = WillingManager() 
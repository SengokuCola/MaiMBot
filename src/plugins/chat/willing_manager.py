import asyncio
from typing import Dict
import datetime


from .config import global_config
from .chat_stream import ChatStream

from loguru import logger


class WillingManager:
    def __init__(self):
        self.chat_reply_willing: Dict[str, float] = {}  # 存储每个聊天流的回复意愿
        self._decay_task = None
        self._started = False
        self.default_willing: float = global_config.response_willing_amplifier  # 默认回复意愿
        
        # 根据当前UTC时间和time_periods初始化默认回复意愿状态
        self._init_willing_based_on_utc_time()

    def _init_willing_based_on_utc_time(self):
        """根据当前UTC时间初始化回复意愿状态"""
        if not global_config.enable_utc_time_control:
            return
            
        current_utc_hour = datetime.datetime.utcnow().hour
        logger.debug(f"机器人启动时UTC时间为{current_utc_hour}点，开始基于时间段配置初始化回复意愿")
        
        # 查找当前时间所在的时间段
        current_period = None
        for period in global_config.time_periods:
            start_hour = period["start_hour"]
            end_hour = period["end_hour"]
            
            # 检查当前时间是否在这个时间段内
            if start_hour <= current_utc_hour < end_hour:
                current_period = period
                break
        
        # 如果找到当前时间所在的时间段，计算初始回复意愿
        if current_period:
            start_hour = current_period["start_hour"]
            end_hour = current_period["end_hour"]
            mode = current_period["mode"]
            
            # 计算在时间段内的位置（0-1之间）
            time_range = end_hour - start_hour
            if time_range <= 0:  # 处理跨夜的情况
                time_range += 24
            position = (current_utc_hour - start_hour) / time_range
            
            if mode == "decrease":
                # 逐渐降低意愿至0，根据位置计算当前应有的意愿
                willing_factor = max(0, 1 - position)
                # 设置全局默认回复意愿
                default_willing = global_config.response_willing_amplifier * willing_factor
                logger.info(f"启动时UTC时间{current_utc_hour}在降低时间段{start_hour}-{end_hour}内，位置{position:.2f}，意愿因子{willing_factor:.2f}，初始意愿设为: {default_willing:.2f}")
            
            elif mode == "increase":
                # 从0逐渐恢复到配置值，根据位置计算当前应有的意愿
                willing_factor = min(1, position)
                # 设置全局默认回复意愿
                default_willing = global_config.response_willing_amplifier * willing_factor
                logger.info(f"启动时UTC时间{current_utc_hour}在提高时间段{start_hour}-{end_hour}内，位置{position:.2f}，意愿因子{willing_factor:.2f}，初始意愿设为: {default_willing:.2f}")
        else:
            # 未找到当前时间的配置，需要确定延续哪个时间点的值
            
            # 找到最接近当前时间的时间段结束点
            closest_period_end = None
            min_hours_diff = 24
            
            for period in global_config.time_periods:
                end_hour = period["end_hour"]
                # 计算结束时间与当前时间的差距（考虑跨天）
                hours_diff = (current_utc_hour - end_hour) % 24
                
                if hours_diff < min_hours_diff:
                    min_hours_diff = hours_diff
                    closest_period_end = period
            
            if closest_period_end:
                mode = closest_period_end["mode"]
                # 如果最近的时间段是降低模式，那么当前回复意愿应为0
                if mode == "decrease":
                    default_willing = 0
                    logger.info(f"启动时UTC时间{current_utc_hour}不在任何配置时间段内，延续最近的降低时间段结束值，初始意愿设为0")
                # 如果最近的时间段是提高模式，设为最大值
                else:
                    default_willing = global_config.response_willing_amplifier
                    logger.info(f"启动时UTC时间{current_utc_hour}不在任何配置时间段内，延续最近的提高时间段结束值，初始意愿设为{default_willing:.2f}")
            else:
                # 没有任何时间段配置，使用默认值
                default_willing = global_config.response_willing_amplifier
                logger.info(f"没有找到任何有效的时间段配置，初始意愿设为默认值{default_willing:.2f}")

        # 保存计算出的默认回复意愿
        self.default_willing = default_willing

    async def _decay_reply_willing(self):
        """定期衰减回复意愿"""
        while True:
            await asyncio.sleep(5)
            for chat_id in self.chat_reply_willing:
                self.chat_reply_willing[chat_id] = max(0, self.chat_reply_willing[chat_id] * 0.6)

    def get_willing(self, chat_stream: ChatStream) -> float:
        """获取指定聊天流的回复意愿"""
        stream = chat_stream
        if stream:
            # 如果该聊天流没有回复意愿记录，使用默认回复意愿
            return self.chat_reply_willing.get(stream.stream_id, self.default_willing)
        return 0

    def set_willing(self, chat_id: str, willing: float):
        """设置指定聊天流的回复意愿"""
        self.chat_reply_willing[chat_id] = willing

    async def change_reply_willing_received(
        self,
        chat_stream: ChatStream,
        topic: str = None,
        is_mentioned_bot: bool = False,
        config=None,
        is_emoji: bool = False,
        interested_rate: float = 0,
    ) -> float:
        """改变指定聊天流的回复意愿并返回回复概率"""
        # 获取或创建聊天流
        stream = chat_stream
        chat_id = stream.stream_id

        # 获取当前聊天流的回复意愿，如果不存在则使用默认回复意愿
        current_willing = self.chat_reply_willing.get(chat_id, self.default_willing)

        if is_mentioned_bot and current_willing < 1.0:
            current_willing += 0.9
            logger.debug(f"被提及, 当前意愿: {current_willing}")
        elif is_mentioned_bot:
            current_willing += 0.05
            logger.debug(f"被重复提及, 当前意愿: {current_willing}")

        if is_emoji:
            current_willing *= 0.1
            logger.debug(f"表情包, 当前意愿: {current_willing}")

        logger.debug(f"放大系数_interested_rate: {global_config.response_interested_rate_amplifier}")
        interested_rate *= global_config.response_interested_rate_amplifier  # 放大回复兴趣度
        if interested_rate > 0.4:
            # print(f"兴趣度: {interested_rate}, 当前意愿: {current_willing}")
            current_willing += interested_rate - 0.4

        current_willing *= global_config.response_willing_amplifier  # 放大回复意愿
        # print(f"放大系数_willing: {global_config.response_willing_amplifier}, 当前意愿: {current_willing}")

        # 基于UTC时间调整回复意愿
        if global_config.enable_utc_time_control:
            current_utc_hour = datetime.datetime.utcnow().hour
            
            # 查找当前时间所在的时间段
            current_period = None
            for period in global_config.time_periods:
                start_hour = period["start_hour"]
                end_hour = period["end_hour"]
                
                # 检查当前时间是否在这个时间段内
                if start_hour <= current_utc_hour < end_hour:
                    current_period = period
                    break
            
            # 如果找到当前时间所在的时间段，应用相应的回复意愿调整
            if current_period:
                start_hour = current_period["start_hour"]
                end_hour = current_period["end_hour"]
                mode = current_period["mode"]
                
                # 计算在时间段内的位置（0-1之间）
                time_range = end_hour - start_hour
                if time_range <= 0:  # 处理跨夜的情况
                    time_range += 24
                position = (current_utc_hour - start_hour) / time_range
                
                if mode == "decrease":
                    # 逐渐降低意愿至0
                    willing_factor = max(0, 1 - position)
                    original_willing = current_willing
                    current_willing *= willing_factor
                    logger.debug(f"UTC时间{current_utc_hour}在降低时间段{start_hour}-{end_hour}内，位置{position:.2f}，意愿因子{willing_factor:.2f}，调整前意愿: {original_willing:.2f}，调整后意愿: {current_willing:.2f}")
                
                elif mode == "increase":
                    # 从0逐渐恢复到配置值
                    willing_factor = min(1, position)
                    original_willing = current_willing
                    # 这里可能需要根据上一个时间段的终点调整起始值
                    # 如果上一个时间段结束于0，则从0开始提高
                    current_willing *= willing_factor
                    logger.debug(f"UTC时间{current_utc_hour}在提高时间段{start_hour}-{end_hour}内，位置{position:.2f}，意愿因子{willing_factor:.2f}，调整前意愿: {original_willing:.2f}，调整后意愿: {current_willing:.2f}")
            else:
                # 未找到当前时间的配置，需要确定延续哪个时间点的值
                
                # 找到最接近当前时间的时间段结束点
                closest_period_end = None
                min_hours_diff = 24
                
                for period in global_config.time_periods:
                    end_hour = period["end_hour"]
                    # 计算结束时间与当前时间的差距（考虑跨天）
                    hours_diff = (current_utc_hour - end_hour) % 24
                    
                    if hours_diff < min_hours_diff:
                        min_hours_diff = hours_diff
                        closest_period_end = period
                
                if closest_period_end:
                    mode = closest_period_end["mode"]
                    # 如果最近的时间段是降低模式，那么当前回复意愿应为0
                    if mode == "decrease":
                        current_willing = 0
                        logger.debug(f"UTC时间{current_utc_hour}不在任何配置时间段内，延续最近的降低时间段结束值，意愿设为0")
                    # 如果最近的时间段是提高模式，保持原值不变（已经是global_config.response_willing_amplifier的值）
                    else:
                        logger.debug(f"UTC时间{current_utc_hour}不在任何配置时间段内，延续最近的提高时间段结束值，保持原意愿{current_willing:.2f}")

        reply_probability = max((current_willing - 0.45) * 2, 0)

        # 检查群组权限（如果是群聊）
        if chat_stream.group_info:
            if chat_stream.group_info.group_id in config.talk_frequency_down_groups:
                reply_probability = reply_probability / global_config.down_frequency_rate

        reply_probability = min(reply_probability, 1)
        if reply_probability < 0:
            reply_probability = 0

        self.chat_reply_willing[chat_id] = min(current_willing, 3.0)
        return reply_probability

    def change_reply_willing_sent(self, chat_stream: ChatStream):
        """开始思考后降低聊天流的回复意愿"""
        stream = chat_stream
        if stream:
            current_willing = self.chat_reply_willing.get(stream.stream_id, 0)
            self.chat_reply_willing[stream.stream_id] = max(0, current_willing - 2)

    def change_reply_willing_after_sent(self, chat_stream: ChatStream):
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

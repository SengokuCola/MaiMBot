import asyncio
import random
import time
from loguru import logger
from .config import global_config


class WillingManager:
    def __init__(self):
        self.group_reply_willing = {}  # 存储每个群的回复意愿
        self.group_high_willing_until = {}  # 存储每个群高回复意愿的截止时间
        self.group_next_high_willing_time = {}  # 存储每个群下一次高回复意愿的开始时间
        self.group_message_counter = {}  # 存储每个群的消息计数
        self._decay_task = None
        self._started = False
        self.min_reply_willing = 0.02
        self.max_reply_willing = 3.0
        self.attenuation_coefficient = 0.9
        
        # 高频率回复周期配置
        self.high_willing_min_minutes = 3  # 高回复意愿持续时间最短3分钟
        self.high_willing_max_minutes = 4  # 高回复意愿持续时间最长4分钟
        
        # 低频率回复周期配置
        self.cycle_min_minutes = 10  # 两次高回复意愿之间的时间间隔最短10分钟
        self.cycle_max_minutes = 30  # 两次高回复意愿之间的时间间隔最长30分钟
        
        # 回复意愿变化配置
        self.high_willing_increase = 0.1  # 高回复期内未回复时的意愿增加
        self.low_willing_increase = 0.01  # 低回复期内未回复时的意愿增加
        self.reply_willing_decrease = 0.35  # 回复后的意愿降低
        self.mentioned_willing_increase = 0.2  # 被@时的意愿增加
        self.mentioned_msg_count = 6  # 被@时的消息计数增加值
        
        # 消息计数器相关配置
        self.high_period_msg_threshold = 4  # 高回复期内，至少累积几条消息才考虑回复
        self.low_period_msg_threshold = 12  # 低回复期内，至少累积几条消息才考虑回复
        
        # 高回复意愿期的回复意愿基础值
        self.high_willing_base = 1.0
        
        # 回复概率上限
        self.high_period_max_probability = 0.65  # 高回复期内最大回复概率
        self.low_period_max_probability = 0.5  # 低回复期内最大回复概率
        self.mentioned_max_probability = 0.5  # 被@时的最大回复概率
        
        # 低频群组配置
        self.low_freq_high_period_min_probability = 0.15  # 低频群组在高回复期的最低回复概率
        self.low_freq_msg_threshold_reduction = 2  # 低频群组在高回复期的消息阈值降低值

    def _generate_high_willing_period(self) -> int:
        """生成高回复意愿的随机持续时间（秒）"""
        minutes = random.uniform(self.high_willing_min_minutes, self.high_willing_max_minutes)
        return int(minutes * 60)
        
    def _generate_next_cycle_time(self) -> int:
        """生成下一个高回复意愿周期的等待时间（秒）"""
        minutes = random.uniform(self.cycle_min_minutes, self.cycle_max_minutes)
        return int(minutes * 60)

    async def _decay_reply_willing(self):
        """定期衰减回复意愿并管理周期"""
        while True:
            await asyncio.sleep(5)  # 每5秒检查一次
            current_time = time.time()
            
            for group_id in list(self.group_reply_willing.keys()):
                # 检查是否处于高回复意愿期
                if group_id in self.group_high_willing_until:
                    # 如果当前时间超过高回复意愿期，大幅度降低回复意愿
                    if current_time > self.group_high_willing_until[group_id]:
                        self.group_reply_willing[group_id] = self.min_reply_willing
                        # 移除过期的时间记录
                        self.group_high_willing_until.pop(group_id)
                        # 重置消息计数器
                        self.group_message_counter[group_id] = 0
                        
                        # 设置下一次高回复意愿期的开始时间
                        next_cycle_time = self._generate_next_cycle_time()
                        self.group_next_high_willing_time[group_id] = current_time + next_cycle_time
                        logger.debug(f"群组 {group_id} 高回复意愿期结束，回复意愿重置为 {self.min_reply_willing}，"
                                    f"将在 {next_cycle_time/60:.1f} 分钟后进入下一个高回复意愿期")
                    else:
                        # 在高回复意愿期内，轻微衰减
                        self.group_reply_willing[group_id] = max(
                            0.5,  # 高回复意愿期的最低值
                            self.group_reply_willing[group_id] * 0.95  # 轻微衰减
                        )
                # 检查是否需要进入高回复意愿期
                elif group_id in self.group_next_high_willing_time:
                    if current_time > self.group_next_high_willing_time[group_id]:
                        # 是时候进入新的高回复意愿期了
                        high_period = self._generate_high_willing_period()
                        self.group_high_willing_until[group_id] = current_time + high_period
                        self.group_reply_willing[group_id] = self.high_willing_base
                        # 重置消息计数器
                        self.group_message_counter[group_id] = 0
                        # 移除下次高意愿时间记录
                        self.group_next_high_willing_time.pop(group_id)
                        logger.debug(f"群组 {group_id} 进入新的高回复意愿期，持续 {high_period/60:.1f} 分钟")
                    else:
                        # 正常衰减
                        self.group_reply_willing[group_id] = max(
                            self.min_reply_willing,
                            self.group_reply_willing[group_id] * self.attenuation_coefficient
                        )
                else:
                    # 正常衰减
                    self.group_reply_willing[group_id] = max(
                        self.min_reply_willing,
                        self.group_reply_willing[group_id] * self.attenuation_coefficient
                    )
                    
                    # 初始化下一次高回复意愿期
                    if group_id not in self.group_next_high_willing_time:
                        next_cycle_time = self._generate_next_cycle_time()
                        self.group_next_high_willing_time[group_id] = current_time + next_cycle_time
                        logger.debug(f"群组 {group_id} 将在 {next_cycle_time/60:.1f} 分钟后进入高回复意愿期")

    def get_willing(self, group_id: int) -> float:
        """获取指定群组的回复意愿"""
        return self.group_reply_willing.get(group_id, 0)

    def set_willing(self, group_id: int, willing: float):
        """设置指定群组的回复意愿"""
        self.group_reply_willing[group_id] = willing
        
        # 如果设置了较高的意愿值，可能需要立即进入高回复意愿期
        if willing > 1.0 and group_id not in self.group_high_willing_until:
            high_period = self._generate_high_willing_period()
            self.group_high_willing_until[group_id] = time.time() + high_period
            # 重置消息计数器
            self.group_message_counter[group_id] = 0
            # 清除下次高意愿时间安排
            if group_id in self.group_next_high_willing_time:
                self.group_next_high_willing_time.pop(group_id)
            logger.debug(f"群组 {group_id} 立即进入高回复意愿期，持续 {high_period/60:.1f} 分钟")

    def change_reply_willing_received(self, group_id: int, topic: str, is_mentioned_bot: bool, config,
                                      user_id: int = None, is_emoji: bool = False, interested_rate: float = 0) -> float:

        # 若非目标回复群组，则直接return
        if group_id not in config.talk_allowed_groups:
            reply_probability = 0
            return reply_probability

        # 初始化消息计数器(如果不存在)
        if group_id not in self.group_message_counter:
            self.group_message_counter[group_id] = 0
            
        # 增加消息计数
        self.group_message_counter[group_id] += 1
        
        # 初始化群组意愿值(如果不存在)
        if group_id not in self.group_reply_willing:
            self.group_reply_willing[group_id] = self.min_reply_willing
            # 为新群组初始化下一次高回复意愿期
            next_cycle_time = self._generate_next_cycle_time()
            self.group_next_high_willing_time[group_id] = time.time() + next_cycle_time
            logger.debug(f"新群组 {group_id} 将在 {next_cycle_time/60:.1f} 分钟后进入高回复意愿期")
        else:
            # 根据当前处于高/低回复期来决定意愿增加量
            current_willing = self.group_reply_willing.get(group_id, 0)
            
            # 判断是否在高回复意愿期
            in_high_period = group_id in self.group_high_willing_until and time.time() < self.group_high_willing_until[group_id]
            
            # 根据不同周期选择不同的意愿增加量
            willing_increase = self.high_willing_increase if in_high_period else self.low_willing_increase
            
            self.group_reply_willing[group_id] = min(
                self.max_reply_willing,
                current_willing + willing_increase
            )
            
            period_type = "高" if in_high_period else "低"
            logger.debug(f"[{group_id}]处于{period_type}回复期，增加意愿: +{willing_increase}，当前: {self.group_reply_willing[group_id]}")

        current_willing = self.group_reply_willing.get(group_id, 0)
        logger.debug(f"[{group_id}]的初始回复意愿: {current_willing}")

        # 根据消息类型（被cue/表情包）调控
        if is_mentioned_bot:
            # 被@时增加一定意愿值，但不会太高
            current_willing = min(
                self.max_reply_willing,
                current_willing + self.mentioned_willing_increase
            )
            # 被提及时增加一定消息计数，但不会直接确保回复
            self.group_message_counter[group_id] = min(
                self.group_message_counter[group_id] + self.mentioned_msg_count,
                self.low_period_msg_threshold  # 最多增加到低周期阈值
            )
            logger.debug(f"被提及, 当前意愿: {current_willing}, 消息计数增加到: {self.group_message_counter[group_id]}")

        if is_emoji:
            current_willing *= 0.5
            logger.debug(f"表情包, 当前意愿: {current_willing}")

        # 兴趣放大系数，若兴趣 > 0.4则增加回复概率
        interested_rate_amplifier = global_config.response_interested_rate_amplifier
        logger.debug(f"放大系数_interested_rate: {interested_rate_amplifier}")
        interested_rate *= interested_rate_amplifier

        current_willing += max(
            0.0,
            interested_rate - 0.4
        )

        # 回复意愿系数调控，独立乘区
        willing_amplifier = max(
            global_config.response_willing_amplifier,
            self.min_reply_willing
        )
        current_willing *= willing_amplifier
        logger.debug(f"放大系数_willing: {global_config.response_willing_amplifier}, 当前意愿: {current_willing}")

        # 回复概率迭代，保底0.01回复概率
        reply_probability = max(
            (current_willing - 0.5) * 2.5,
            self.min_reply_willing
        )

        # 检查是否在高回复意愿期内
        if group_id in self.group_high_willing_until and time.time() < self.group_high_willing_until[group_id]:
            # 在高回复意愿期内
            is_low_freq_group = group_id in config.talk_frequency_down_groups
            
            # 低频群组在高回复期使用较低的消息阈值
            actual_threshold = self.high_period_msg_threshold
            if is_low_freq_group:
                actual_threshold = max(2, self.high_period_msg_threshold - self.low_freq_msg_threshold_reduction)
            
            # 检查消息数量是否达到阈值
            if self.group_message_counter[group_id] >= actual_threshold:
                # 提高回复概率，但有上限
                base_probability = reply_probability * 1.2
                
                if is_low_freq_group:
                    # 低频群组在高回复期保持一定的回复概率
                    reply_probability = max(
                        min(base_probability, self.high_period_max_probability * 0.6),  # 最高概率降低到正常的60%
                        self.low_freq_high_period_min_probability  # 保证最低概率
                    )
                    logger.debug(f"低频群组在高回复意愿期内，消息数:{self.group_message_counter[group_id]}，设置回复概率为: {reply_probability}")
                else:
                    # 普通群组正常处理
                    reply_probability = min(base_probability, self.high_period_max_probability)
                    logger.debug(f"群组在高回复意愿期内，消息数:{self.group_message_counter[group_id]}，提高回复概率至: {reply_probability}")
            else:
                # 消息数量不足，但在高回复期仍保持一定概率
                if is_low_freq_group:
                    # 低频群组在高回复期即使消息不足也保持最低概率
                    reply_probability = max(reply_probability * 0.5, self.low_freq_high_period_min_probability)
                    logger.debug(f"低频群组在高回复意愿期内，消息数不足({self.group_message_counter[group_id]}/{actual_threshold})，保持最低概率: {reply_probability}")
                else:
                    # 普通群组正常降低概率
                    reply_probability *= 0.5
                    logger.debug(f"群组在高回复意愿期内，但消息数不足({self.group_message_counter[group_id]}/{actual_threshold})，降低回复概率至: {reply_probability}")
        else:
            # 在低回复意愿期内，需要大量消息累积才可能回复
            if self.group_message_counter[group_id] >= self.low_period_msg_threshold:
                # 达到了阈值，但概率仍然很低
                reply_probability = min(reply_probability * 0.8, self.low_period_max_probability)
                logger.debug(f"群组在低回复意愿期内，消息数达标({self.group_message_counter[group_id]}/{self.low_period_msg_threshold})，回复概率设为: {reply_probability}")
            else:
                # 消息数不足，几乎不回复
                reply_probability *= 0.05
                logger.debug(f"群组在低回复意愿期内，消息数不足({self.group_message_counter[group_id]}/{self.low_period_msg_threshold})，回复概率极低: {reply_probability}")

        # 如果是被@，限制最终概率不超过mentioned_max_probability
        if is_mentioned_bot:
            reply_probability = min(reply_probability, self.mentioned_max_probability)
            logger.debug(f"被@消息，限制最终回复概率为: {reply_probability}")

        # 最终回复概率限制
        reply_probability = min(reply_probability, 1)

        self.group_reply_willing[group_id] = min(current_willing, self.max_reply_willing)
        logger.debug(f"当前群组{group_id}回复概率：{reply_probability}")
        return reply_probability

    def change_reply_willing_sent(self, group_id: int):
        """开始思考后降低群组的回复意愿"""
        current_willing = self.group_reply_willing.get(group_id, 0)
        self.group_reply_willing[group_id] = max(0, current_willing - self.reply_willing_decrease)
        # 回复后重置消息计数器
        self.group_message_counter[group_id] = 0
        logger.debug(f"[{group_id}]回复后，降低意愿: -{self.reply_willing_decrease}，当前: {self.group_reply_willing[group_id]}，消息计数重置为0")

    def change_reply_willing_after_sent(self, group_id: int):
        """发送消息后修改群组的回复意愿"""
        # 保持降低的意愿，不再额外增加
        pass

    async def ensure_started(self):
        """确保衰减任务已启动"""
        if not self._started:
            if self._decay_task is None:
                self._decay_task = asyncio.create_task(self._decay_reply_willing())
            self._started = True


# 创建全局实例
willing_manager = WillingManager()

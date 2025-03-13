import asyncio
import random
import time
from typing import Dict
from loguru import logger


from .config import global_config
from .chat_stream import ChatStream


class WillingManager:
    def __init__(self):
        self.chat_reply_willing: Dict[str, float] = {}  # 存储每个聊天流的回复意愿
        self.chat_high_willing_mode: Dict[str, bool] = {}  # 存储每个聊天流是否处于高回复意愿期
        self.chat_msg_count: Dict[str, int] = {}  # 存储每个聊天流接收到的消息数量
        self.chat_last_mode_change: Dict[str, float] = {}  # 存储每个聊天流上次模式切换的时间
        self.chat_high_willing_duration: Dict[str, int] = {}  # 高意愿期持续时间(秒)
        self.chat_low_willing_duration: Dict[str, int] = {}  # 低意愿期持续时间(秒)
        self.chat_last_reply_time: Dict[str, float] = {}  # 存储每个聊天流上次回复的时间
        self.chat_last_sender_id: Dict[str, str] = {}  # 存储每个聊天流上次回复的用户ID
        self.chat_conversation_context: Dict[str, bool] = {}  # 标记是否处于对话上下文中
        self.chat_consecutive_replies: Dict[str, int] = {}  # 存储每个聊天流的连续回复次数

        # 冷群检测相关属性
        self.group_activity: Dict[str, Dict] = {}  # 存储群组活跃度信息
        self.group_is_cold: Dict[str, bool] = {}  # 标记群组是否为冷群
        self.cold_group_check_interval = 1800  # 冷群检测时间间隔(秒)，默认30分钟

        self._decay_task = None
        self._mode_switch_task = None
        self._cleanup_task = None  # 新增清理任务
        self._cold_group_check_task = None  # 冷群检测任务
        self._started = False

    async def _decay_reply_willing(self):
        """定期衰减回复意愿"""
        while True:
            await asyncio.sleep(5)
            for chat_id in list(self.chat_reply_willing.keys()):
                is_high_mode = self.chat_high_willing_mode.get(chat_id, False)
                if is_high_mode:
                    # 高回复意愿期内轻微衰减
                    self.chat_reply_willing[chat_id] = max(0.5, self.chat_reply_willing[chat_id] * 0.95)
                else:
                    # 低回复意愿期内正常衰减
                    self.chat_reply_willing[chat_id] = max(0, self.chat_reply_willing[chat_id] * 0.8)

    async def _mode_switch_check(self):
        """定期检查是否需要切换回复意愿模式"""
        while True:
            current_time = time.time()
            await asyncio.sleep(10)  # 每10秒检查一次

            for chat_id in list(self.chat_high_willing_mode.keys()):
                last_change_time = self.chat_last_mode_change.get(chat_id, 0)
                is_high_mode = self.chat_high_willing_mode.get(chat_id, False)

                # 获取当前模式的持续时间
                duration = 0
                if is_high_mode:
                    duration = self.chat_high_willing_duration.get(chat_id, 180)  # 使用已存储的持续时间或默认3分钟
                else:
                    duration = self.chat_low_willing_duration.get(chat_id, 300)  # 使用已存储的持续时间或默认5分钟

                # 检查是否需要切换模式
                if current_time - last_change_time > duration:
                    self._switch_willing_mode(chat_id)
                elif not is_high_mode and random.random() < 0.05:  # 降低随机切换概率到5%
                    # 低回复意愿期有小概率随机切换到高回复期
                    self._switch_willing_mode(chat_id)

                # 检查对话上下文状态是否需要重置
                last_reply_time = self.chat_last_reply_time.get(chat_id, 0)
                if current_time - last_reply_time > 300:  # 5分钟无交互，重置对话上下文
                    self.chat_conversation_context[chat_id] = False
                    # 重置连续回复计数
                    self.chat_consecutive_replies[chat_id] = 0

    def _switch_willing_mode(self, chat_id: str):
        """切换聊天流的回复意愿模式"""
        is_high_mode = self.chat_high_willing_mode.get(chat_id, False)

        if is_high_mode:
            # 从高回复期切换到低回复期
            self.chat_high_willing_mode[chat_id] = False
            self.chat_reply_willing[chat_id] = 0.1  # 设置为最低回复意愿
            self.chat_low_willing_duration[chat_id] = random.randint(600, 1200)  # 10-20分钟
            logger.debug(f"聊天流 {chat_id} 切换到低回复意愿期，持续 {self.chat_low_willing_duration[chat_id]} 秒")
        else:
            # 从低回复期切换到高回复期
            self.chat_high_willing_mode[chat_id] = True
            self.chat_reply_willing[chat_id] = 1.0  # 设置为较高回复意愿
            self.chat_high_willing_duration[chat_id] = random.randint(180, 240)  # 3-4分钟
            logger.debug(f"聊天流 {chat_id} 切换到高回复意愿期，持续 {self.chat_high_willing_duration[chat_id]} 秒")

        self.chat_last_mode_change[chat_id] = time.time()
        self.chat_msg_count[chat_id] = 0  # 重置消息计数

    def get_willing(self, chat_stream: ChatStream) -> float:
        """获取指定聊天流的回复意愿"""
        stream = chat_stream
        if stream:
            return self.chat_reply_willing.get(stream.stream_id, 0)
        return 0

    def set_willing(self, chat_id: str, willing: float):
        """设置指定聊天流的回复意愿"""
        self.chat_reply_willing[chat_id] = willing

    def _ensure_chat_initialized(self, chat_id: str):
        """确保聊天流的所有数据已初始化"""
        current_time = time.time()

        if chat_id not in self.chat_reply_willing:
            self.chat_reply_willing[chat_id] = 0.1

        if chat_id not in self.chat_high_willing_mode:
            self.chat_high_willing_mode[chat_id] = False
            self.chat_last_mode_change[chat_id] = current_time
            self.chat_low_willing_duration[chat_id] = random.randint(300, 1200)  # 5-20分钟

        if chat_id not in self.chat_msg_count:
            self.chat_msg_count[chat_id] = 0

        if chat_id not in self.chat_conversation_context:
            self.chat_conversation_context[chat_id] = False

        if chat_id not in self.chat_consecutive_replies:
            self.chat_consecutive_replies[chat_id] = 0

        # 确保所有其他字典键也被初始化
        if chat_id not in self.chat_last_reply_time:
            self.chat_last_reply_time[chat_id] = 0

        if chat_id not in self.chat_last_sender_id:
            self.chat_last_sender_id[chat_id] = ""

        if chat_id not in self.chat_high_willing_duration:
            self.chat_high_willing_duration[chat_id] = random.randint(180, 240)  # 3-4分钟

    async def change_reply_willing_received(
        self,
        chat_stream: ChatStream,
        topic: str = None,
        is_mentioned_bot: bool = False,
        config=None,
        is_emoji: bool = False,
        interested_rate: float = 0,
        sender_id: str = None,
    ) -> float:
        """改变指定聊天流的回复意愿并返回回复概率"""
        # 获取或创建聊天流
        stream = chat_stream
        chat_id = stream.stream_id
        current_time = time.time()

        self._ensure_chat_initialized(chat_id)

        # 更新群组活跃度信息
        if chat_stream.group_info and sender_id:
            self._update_group_activity(chat_stream, sender_id)

        # 检查连续回复计数重置
        last_reply_time = self.chat_last_reply_time.get(chat_id, 0)
        if current_time - last_reply_time > 30:  # 30秒内没有新回复，重置连续回复计数
            self.chat_consecutive_replies[chat_id] = 0
            logger.debug(f"重置连续回复计数 - 聊天流 {chat_id}")

        # 增加消息计数
        self.chat_msg_count[chat_id] = self.chat_msg_count.get(chat_id, 0) + 1

        current_willing = self.chat_reply_willing.get(chat_id, 0)
        is_high_mode = self.chat_high_willing_mode.get(chat_id, False)
        msg_count = self.chat_msg_count.get(chat_id, 0)
        in_conversation_context = self.chat_conversation_context.get(chat_id, False)
        consecutive_replies = self.chat_consecutive_replies.get(chat_id, 0)

        # 检查是否是对话上下文中的追问
        last_sender = self.chat_last_sender_id.get(chat_id, "")
        is_follow_up_question = False

        # 改进的追问检测逻辑
        time_window = 180  # 扩大到3分钟
        max_msgs = 8  # 增加消息数量阈值

        # 1. 同一用户短时间内发送多条消息
        if (
            sender_id
            and sender_id == last_sender
            and current_time - last_reply_time < time_window
            and msg_count <= max_msgs
        ):
            is_follow_up_question = True
            in_conversation_context = True
            self.chat_conversation_context[chat_id] = True

            # 根据消息间隔动态调整回复意愿提升
            time_since_last = current_time - last_reply_time
            if time_since_last < 60:  # 1分钟内
                current_willing += 0.4  # 快速跟进，提高更多
            else:
                current_willing += 0.2  # 较慢跟进，提高较少

            logger.debug(f"检测到追问 (同一用户), 提高回复意愿, 时间间隔: {time_since_last:.1f}秒")

        # 2. 即使不是同一用户，如果处于活跃对话中，也有可能是追问
        elif in_conversation_context and current_time - last_reply_time < time_window:
            # 处于活跃对话中，但不是同一用户，视为对话延续
            in_conversation_context = True
            logger.debug("检测到对话延续 (不同用户), 保持对话上下文")

        # 特殊情况处理
        if is_mentioned_bot:
            current_willing += 0.9
            in_conversation_context = True
            self.chat_conversation_context[chat_id] = True
            # 被提及时重置连续回复计数，允许新的对话开始
            self.chat_consecutive_replies[chat_id] = 0
            logger.debug(f"被提及, 当前意愿: {current_willing}, 重置连续回复计数")

        # 降低图片回复率到20%
        if is_emoji:
            current_willing *= 0.2
            # 确保图片消息的回复意愿不会太低
            current_willing = max(current_willing, 0.05)
            logger.debug(f"图片消息, 当前意愿: {current_willing}")

        # 根据话题兴趣度适当调整
        if interested_rate > 0.5:
            current_willing += (interested_rate - 0.5) * 0.5

        # 确保意愿值有一个合理的下限
        current_willing = max(current_willing, 0.05)

        # 根据当前模式计算回复概率
        base_probability = 0.0

        if in_conversation_context:
            # 在对话上下文中，降低基础回复概率
            base_probability = 0.5 if is_high_mode else 0.25
            logger.debug(f"处于对话上下文中，基础回复概率: {base_probability}")
        elif is_high_mode:
            # 高回复周期：1-3句话有80%的概率会回复一次
            base_probability = 0.80 if 1 <= msg_count <= 3 else 0.2
        else:
            # 低回复周期：需要最少15句才有50%的概率会回一句
            base_probability = 0.50 if msg_count >= 15 else 0.03 * min(msg_count, 10)

        # 确保基础概率不会太低
        base_probability = max(base_probability, 0.01)

        # 考虑回复意愿的影响
        reply_probability = base_probability * current_willing

        # 根据连续回复次数调整概率
        if consecutive_replies >= 4:
            reply_probability *= 0.01  # 连续回复4次或以上，降低到1%
            logger.debug("连续回复次数 >= 3, 降低回复概率到1%")
        elif consecutive_replies >= 3:
            reply_probability *= 0.1  # 连续回复3次，降低到10%
            logger.debug("连续回复次数 = 2, 降低回复概率到10%")

        # 检查是否为冷群，提高冷群的回复概率
        if chat_stream.group_info:
            group_id = self._get_group_id_from_chat_id(chat_id)
            is_cold_group = self.group_is_cold.get(group_id, False)

            if is_cold_group:
                # 冷群中提高回复概率为三倍
                reply_probability = min(reply_probability * 3.0)
                logger.debug(f"检测到冷群 {group_id}，提高回复概率到: {reply_probability:.2f}")

        # 检查群组权限（如果是群聊）
        if chat_stream.group_info and config:
            if chat_stream.group_info.group_id in config.talk_frequency_down_groups:
                reply_probability = reply_probability / global_config.down_frequency_rate

        # 限制最大回复概率
        reply_probability = min(reply_probability, 0.80)  # 设置最大回复概率为80%

        # 确保回复概率在合理范围内
        reply_probability = max(reply_probability, 0.001)  # 确保概率最低不低于0.1%

        # 对于追问和被提及，保持最低回复概率
        if (in_conversation_context and is_follow_up_question) or is_mentioned_bot:
            reply_probability = max(reply_probability, 0.3)  # 最低30%回复概率

        # 记录当前发送者ID以便后续追踪
        if sender_id:
            self.chat_last_sender_id[chat_id] = sender_id

        # 最终限制回复意愿范围
        self.chat_reply_willing[chat_id] = min(max(current_willing, 0.05), 3.0)

        return reply_probability

    def change_reply_willing_sent(self, chat_stream: ChatStream):
        """开始思考后降低聊天流的回复意愿"""
        stream = chat_stream
        if stream:
            chat_id = stream.stream_id
            self._ensure_chat_initialized(chat_id)
            is_high_mode = self.chat_high_willing_mode.get(chat_id, False)
            current_willing = self.chat_reply_willing.get(chat_id, 0)

            # 增加连续回复计数
            self.chat_consecutive_replies[chat_id] = self.chat_consecutive_replies.get(chat_id, 0) + 1
            logger.debug(f"增加连续回复计数到 {self.chat_consecutive_replies[chat_id]} - 聊天流 {chat_id}")

            # 回复后减少回复意愿
            self.chat_reply_willing[chat_id] = max(0, current_willing - 0.3)

            # 标记为对话上下文中
            self.chat_conversation_context[chat_id] = True

            # 记录最后回复时间
            self.chat_last_reply_time[chat_id] = time.time()

            # 重置消息计数
            self.chat_msg_count[chat_id] = 0

    def change_reply_willing_not_sent(self, chat_stream: ChatStream):
        """决定不回复后提高聊天流的回复意愿"""
        stream = chat_stream
        if stream:
            chat_id = stream.stream_id
            self._ensure_chat_initialized(chat_id)
            is_high_mode = self.chat_high_willing_mode.get(chat_id, False)
            current_willing = self.chat_reply_willing.get(chat_id, 0)
            in_conversation_context = self.chat_conversation_context.get(chat_id, False)

            # 根据当前模式调整不回复后的意愿增加
            if is_high_mode:
                willing_increase = 0.1
            elif in_conversation_context:
                # 在对话上下文中但决定不回复，小幅增加回复意愿
                willing_increase = 0.15
            else:
                willing_increase = random.uniform(0.05, 0.1)

            self.chat_reply_willing[chat_id] = min(2.0, current_willing + willing_increase)

    def change_reply_willing_after_sent(self, chat_stream: ChatStream):
        """发送消息后提高聊天流的回复意愿"""
        # 由于已经在sent中处理，这个方法保留但不再需要额外调整
        pass

    async def _cleanup_inactive_chats(self):
        """定期清理长时间不活跃的聊天流数据"""
        while True:
            await asyncio.sleep(3600)  # 每小时执行一次清理
            current_time = time.time()
            inactive_threshold = 86400  # 24小时不活跃的聊天流将被清理

            # 收集需要清理的聊天流ID
            to_clean = []

            for chat_id in list(self.chat_last_reply_time.keys()):
                last_active = self.chat_last_reply_time.get(chat_id, 0)
                if current_time - last_active > inactive_threshold:
                    to_clean.append(chat_id)

            # 从所有字典中移除不活跃的聊天流
            for chat_id in to_clean:
                self._remove_chat_data(chat_id)

            if to_clean:
                logger.debug(f"已清理 {len(to_clean)} 个不活跃的聊天流数据")

    def _remove_chat_data(self, chat_id: str):
        """从所有字典中移除指定聊天流的数据"""
        dictionaries = [
            self.chat_reply_willing,
            self.chat_high_willing_mode,
            self.chat_msg_count,
            self.chat_last_mode_change,
            self.chat_high_willing_duration,
            self.chat_low_willing_duration,
            self.chat_last_reply_time,
            self.chat_last_sender_id,
            self.chat_conversation_context,
            self.chat_consecutive_replies,
        ]

        for dictionary in dictionaries:
            if chat_id in dictionary:
                dictionary.pop(chat_id, None)

        # 尝试清理相关的群组数据
        try:
            group_id = self._get_group_id_from_chat_id(chat_id)
            if group_id in self.group_activity and len(self.group_activity[group_id]["active_users"]) <= 1:
                # 如果只有一个活跃用户，可能就是这个被清理的聊天，整个清理群组数据
                self.group_activity.pop(group_id, None)
                self.group_is_cold.pop(group_id, None)
        except Exception as e:
            logger.error(f"尝试清理群组数据时出错: {e}")

        logger.debug(f"已移除聊天流 {chat_id} 的所有数据")

    async def stop(self):
        """停止所有异步任务"""
        if self._decay_task and not self._decay_task.done():
            self._decay_task.cancel()
            try:
                await self._decay_task
            except asyncio.CancelledError:
                pass

        if self._mode_switch_task and not self._mode_switch_task.done():
            self._mode_switch_task.cancel()
            try:
                await self._mode_switch_task
            except asyncio.CancelledError:
                pass

        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        if self._cold_group_check_task and not self._cold_group_check_task.done():
            self._cold_group_check_task.cancel()
            try:
                await self._cold_group_check_task
            except asyncio.CancelledError:
                pass

        self._started = False
        logger.debug("已停止所有WillingManager任务")

    async def ensure_started(self):
        """确保所有任务已启动"""
        if not self._started:
            if self._decay_task is None:
                self._decay_task = asyncio.create_task(self._decay_reply_willing())
            if self._mode_switch_task is None:
                self._mode_switch_task = asyncio.create_task(self._mode_switch_check())
            if self._cleanup_task is None:
                self._cleanup_task = asyncio.create_task(self._cleanup_inactive_chats())
            if self._cold_group_check_task is None:
                self._cold_group_check_task = asyncio.create_task(self._cold_group_check())
            self._started = True
            logger.debug("WillingManager所有任务已启动")

    def _get_group_id_from_chat_id(self, chat_id: str) -> str:
        """从聊天流ID提取群组ID，如果失败则返回原ID"""
        # 通常聊天流ID中会包含群组ID信息
        # 根据实际格式进行提取，这里假设格式为 platform:group_id:user_id
        try:
            parts = chat_id.split(":")
            if len(parts) >= 2:
                return f"{parts[0]}:{parts[1]}"  # platform:group_id作为群组标识
            return chat_id
        except Exception:
            return chat_id

    def _update_group_activity(self, chat_stream: ChatStream, sender_id: str = None):
        """更新群组活跃度信息"""
        if not chat_stream.group_info:
            return  # 非群聊不需处理

        current_time = time.time()
        group_id = self._get_group_id_from_chat_id(chat_stream.stream_id)

        # 确保群组活跃度记录存在
        if group_id not in self.group_activity:
            self.group_activity[group_id] = {
                "message_count": 0,  # 消息总数
                "active_users": set(),  # 活跃用户集合
                "first_message_time": current_time,  # 第一条消息时间
                "last_message_time": current_time,  # 最后一条消息时间
                "check_start_time": current_time,  # 本次检测开始时间
            }

        # 更新活跃度信息
        activity = self.group_activity[group_id]
        activity["message_count"] += 1
        activity["last_message_time"] = current_time

        if sender_id:
            activity["active_users"].add(sender_id)

        # 检查是否需要重置统计
        time_since_start = current_time - activity["check_start_time"]
        if time_since_start > self.cold_group_check_interval:
            # 计算活跃度指标并判断是否为冷群
            self._check_cold_group(group_id)

            # 重置统计
            activity["message_count"] = 1
            activity["active_users"] = set([sender_id]) if sender_id else set()
            activity["check_start_time"] = current_time

    def _check_cold_group(self, group_id: str):
        """检查群组是否为冷群，并更新状态"""
        if group_id not in self.group_activity:
            return

        activity = self.group_activity[group_id]
        message_count = activity["message_count"]
        active_users_count = len(activity["active_users"])
        interval = activity["last_message_time"] - activity["check_start_time"]

        # 如果时间间隔太短，不进行判断
        if interval < 600:  # 至少需要10分钟的数据
            return

        # 计算活跃度指标
        # 冷群判定标准：半小时内发言人数少于5人，且发言次数少于20次
        scaled_interval = interval / self.cold_group_check_interval  # 将时间标准化到检测间隔
        scaled_message_count = message_count / scaled_interval
        scaled_active_users = active_users_count / scaled_interval

        # 判断是否为冷群
        is_cold = scaled_active_users < 5.0 and scaled_message_count < 20.0

        # 更新冷群状态
        self.group_is_cold[group_id] = is_cold
        logger.debug(
            f"群 {group_id} 活跃度检查: 消息数={message_count}, 活跃用户数={active_users_count}, 时间间隔={interval:.1f}秒, 判定为{'冷群' if is_cold else '活跃群'}"
        )

    async def _cold_group_check(self):
        """定期检查所有群组的冷热状态"""
        while True:
            await asyncio.sleep(self.cold_group_check_interval / 2)  # 检测间隔的一半时间运行一次
            current_time = time.time()

            for group_id in list(self.group_activity.keys()):
                activity = self.group_activity[group_id]
                # 如果距离上次检测已经超过了检测间隔，执行一次检测
                if current_time - activity["check_start_time"] > self.cold_group_check_interval:
                    self._check_cold_group(group_id)
                    # 重置检测起始时间
                    activity["check_start_time"] = current_time

            # 清理太久没活动的群组记录
            self._cleanup_inactive_groups(current_time)

    def _cleanup_inactive_groups(self, current_time: float):
        """清理长时间不活跃的群组记录"""
        inactive_threshold = 86400 * 3  # 3天不活跃则清理
        inactive_groups = []

        for group_id, activity in list(self.group_activity.items()):
            if current_time - activity["last_message_time"] > inactive_threshold:
                inactive_groups.append(group_id)

        for group_id in inactive_groups:
            if group_id in self.group_activity:
                self.group_activity.pop(group_id)
            if group_id in self.group_is_cold:
                self.group_is_cold.pop(group_id)

        if inactive_groups:
            logger.debug(f"已清理 {len(inactive_groups)} 个不活跃的群组记录")


# 创建全局实例
willing_manager = WillingManager()

import os
import datetime
import json
from typing import Dict, Union

from loguru import logger
from nonebot import get_driver

from src.plugins.chat.config import global_config

from ...common.database import Database  # 使用正确的导入语法
from ..models.utils_model import LLM_request

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

class ScheduleGenerator:
    def __init__(self):
        # 根据global_config.llm_normal这一字典配置指定模型
        # self.llm_scheduler = LLMModel(model = global_config.llm_normal,temperature=0.9)
        self.llm_scheduler = LLM_request(model=global_config.llm_normal, temperature=0.9)
        self.db = Database.get_instance()
        self.today_schedule_text = ""
        self.today_schedule = {}
        self.tomorrow_schedule_text = ""
        self.tomorrow_schedule = {}
        self.yesterday_schedule_text = ""
        self.yesterday_schedule = {}

    async def initialize(self):
        today = datetime.datetime.now()
        tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)

        self.today_schedule_text, self.today_schedule = await self.generate_daily_schedule(target_date=today)
        self.tomorrow_schedule_text, self.tomorrow_schedule = await self.generate_daily_schedule(target_date=tomorrow,
                                                                                                 read_only=True)
        self.yesterday_schedule_text, self.yesterday_schedule = await self.generate_daily_schedule(
            target_date=yesterday, read_only=True)

    async def generate_daily_schedule(self, target_date: datetime.datetime = None, read_only: bool = False) -> Dict[
        str, str]:
        return  '忘了', None
        date_str = target_date.strftime("%Y-%m-%d")
        weekday = target_date.strftime("%A")

        schedule_text = str

        existing_schedule = self.db.db.schedule.find_one({"date": date_str})
        if existing_schedule:
            logger.debug(f"{date_str}的日程已存在:")
            schedule_text = existing_schedule["schedule"]
            # print(self.schedule_text)

        elif not read_only:
            logger.debug(f"{date_str}的日程不存在，准备生成新的日程。")
            prompt = f"""我是{global_config.BOT_NICKNAME}，{global_config.PROMPT_SCHEDULE_GEN}，请为我生成{date_str}（{weekday}）的日程安排，包括：""" + \
                     """
            1. 早上的学习和工作安排
            2. 下午的活动和任务
            3. 晚上的计划和休息时间
            请按照时间顺序列出具体时间点和对应的活动，用一个时间点而不是时间段来表示时间，用JSON格式返回日程表，仅返回内容，不要返回注释，不要添加任何markdown或代码块样式，时间采用24小时制，格式为{"时间": "活动","时间": "活动",...}。"""

            try:
                schedule_text, _ = await self.llm_scheduler.generate_response(prompt)
                self.db.db.schedule.insert_one({"date": date_str, "schedule": schedule_text})
            except Exception as e:
                logger.error(f"生成日程失败: {str(e)}")
                schedule_text = "生成日程时出错了"
            # print(self.schedule_text)
        else:
            logger.debug(f"{date_str}的日程不存在。")
            schedule_text = "忘了"

            return schedule_text, None

        schedule_form = self._parse_schedule(schedule_text)
        return schedule_text, schedule_form

    def _parse_schedule(self, schedule_text: str) -> Union[bool, Dict[str, str]]:
        """解析日程文本，转换为时间和活动的字典"""
        try:
            schedule_dict = json.loads(schedule_text)
            return schedule_dict
        except json.JSONDecodeError:
            logger.exception("解析日程失败: {}".format(schedule_text))
            return False

    def _parse_time(self, time_str: str) -> str:
        """解析时间字符串，转换为时间"""
        return datetime.datetime.strptime(time_str, "%H:%M")

    def get_current_task(self) -> str:
        """获取当前时间应该进行的任务"""
        current_time = datetime.datetime.now().strftime("%H:%M")

        # 找到最接近当前时间的任务
        closest_time = None
        min_diff = float('inf')

        # 检查今天的日程
        if not self.today_schedule:
            return "摸鱼"
        for time_str in self.today_schedule.keys():
            diff = abs(self._time_diff(current_time, time_str))
            if closest_time is None or diff < min_diff:
                closest_time = time_str
                min_diff = diff

        # 检查昨天的日程中的晚间任务
        if self.yesterday_schedule:
            for time_str in self.yesterday_schedule.keys():
                if time_str >= "20:00":  # 只考虑晚上8点之后的任务
                    # 计算与昨天这个时间点的差异（需要加24小时）
                    diff = abs(self._time_diff(current_time, time_str))
                    if diff < min_diff:
                        closest_time = time_str
                        min_diff = diff
                        return closest_time, self.yesterday_schedule[closest_time]

        if closest_time:
            return closest_time, self.today_schedule[closest_time]
        return "摸鱼"

    def _time_diff(self, time1: str, time2: str) -> int:
        """计算两个时间字符串之间的分钟差"""
        if time1 == "24:00":
            time1 = "23:59"
        if time2 == "24:00":
            time2 = "23:59"
        t1 = datetime.datetime.strptime(time1, "%H:%M")
        t2 = datetime.datetime.strptime(time2, "%H:%M")
        diff = int((t2 - t1).total_seconds() / 60)
        # 考虑时间的循环性
        if diff < -720:
            diff += 1440  # 加一天的分钟
        elif diff > 720:
            diff -= 1440  # 减一天的分钟
        # print(f"时间1[{time1}]: 时间2[{time2}]，差值[{diff}]分钟")
        return diff

    def print_schedule(self):
        """打印完整的日程安排"""
        if not self._parse_schedule(self.today_schedule_text):
            logger.warning("今日日程有误，将在下次运行时重新生成")
            self.db.db.schedule.delete_one({"date": datetime.datetime.now().strftime("%Y-%m-%d")})
        else:
            logger.info("=== 今日日程安排 ===")
            for time_str, activity in self.today_schedule.items():
                logger.info(f"时间[{time_str}]: 活动[{activity}]")
            logger.info("==================")


# def main():
#     # 使用示例
#     scheduler = ScheduleGenerator()
#     # new_schedule = scheduler.generate_daily_schedule()
#     scheduler.print_schedule()
#     print("\n当前任务：")
#     print(scheduler.get_current_task())

#     print("昨天日程：")
#     print(scheduler.yesterday_schedule)
#     print("今天日程：")
#     print(scheduler.today_schedule)
#     print("明天日程：")
#     print(scheduler.tomorrow_schedule)

# if __name__ == "__main__":
#     main()

bot_schedule = ScheduleGenerator()

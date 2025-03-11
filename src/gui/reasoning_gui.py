import os
import queue
import sys
import threading
import time
from datetime import datetime
from typing import Dict, List
from loguru import logger
from typing import Optional
from pymongo import MongoClient

import customtkinter as ctk
from dotenv import load_dotenv

# 获取当前文件的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录
root_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))

# 加载环境变量
if os.path.exists(os.path.join(root_dir, '.env.dev')):
    load_dotenv(os.path.join(root_dir, '.env.dev'))
    logger.info("成功加载开发环境配置")
elif os.path.exists(os.path.join(root_dir, '.env.prod')):
    load_dotenv(os.path.join(root_dir, '.env.prod'))
    logger.info("成功加载生产环境配置")
else:
    logger.error("未找到环境配置文件")
    sys.exit(1)


class Database:
    _instance: Optional["Database"] = None

    def __init__(self, host: str, port: int, db_name: str, username: str = None, password: str = None,
                 auth_source: str = None):
        if username and password:
            self.client = MongoClient(
                host=host,
                port=port,
                username=username,
                password=password,
                authSource=auth_source or 'admin'
            )
        else:
            self.client = MongoClient(host, port)
        self.db = self.client[db_name]

    @classmethod
    def initialize(cls, host: str, port: int, db_name: str, username: str = None, password: str = None,
                   auth_source: str = None) -> "Database":
        if cls._instance is None:
            cls._instance = cls(host, port, db_name, username, password, auth_source)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "Database":
        if cls._instance is None:
            raise RuntimeError("Database not initialized")
        return cls._instance


class ReasoningGUI:
    def __init__(self):
        # 记录启动时间戳，转换为Unix时间戳
        self.start_timestamp = datetime.now().timestamp()
        logger.info(f"程序启动时间戳: {self.start_timestamp}")

        # 设置主题
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # 创建主窗口
        self.root = ctk.CTk()
        self.root.title('麦麦推理')
        self.root.geometry('800x600')
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        # 初始化数据库连接
        try:
            self.db = Database.get_instance().db
            logger.success("数据库连接成功")
        except RuntimeError:
            logger.warning("数据库未初始化，正在尝试初始化...")
            try:
                Database.initialize("127.0.0.1", 27017, "maimai_bot")
                self.db = Database.get_instance().db
                logger.success("数据库初始化成功")
            except Exception:
                logger.exception("数据库初始化失败")
                sys.exit(1)

        # 存储群组数据
        self.group_data: Dict[str, List[dict]] = {}

        # 创建更新队列
        self.update_queue = queue.Queue()

        # 创建主框架
        self.frame = ctk.CTkFrame(self.root)
        self.frame.pack(pady=20, padx=20, fill="both", expand=True)

        # 添加标题
        self.title = ctk.CTkLabel(self.frame, text="麦麦的脑内所想", font=("Arial", 24))
        self.title.pack(pady=10, padx=10)

        # 创建左右分栏
        self.paned = ctk.CTkFrame(self.frame)
        self.paned.pack(fill="both", expand=True, padx=10, pady=10)

        # 左侧群组列表
        self.left_frame = ctk.CTkFrame(self.paned, width=200)
        self.left_frame.pack(side="left", fill="y", padx=5, pady=5)

        self.group_label = ctk.CTkLabel(self.left_frame, text="群组列表", font=("Arial", 16))
        self.group_label.pack(pady=5)

        # 创建可滚动框架来容纳群组按钮
        self.group_scroll_frame = ctk.CTkScrollableFrame(self.left_frame, width=180, height=400)
        self.group_scroll_frame.pack(pady=5, padx=5, fill="both", expand=True)

        # 存储群组按钮的字典
        self.group_buttons: Dict[str, ctk.CTkButton] = {}
        # 当前选中的群组ID
        self.selected_group_id: Optional[str] = None

        # 右侧内容显示
        self.right_frame = ctk.CTkFrame(self.paned)
        self.right_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        self.content_label = ctk.CTkLabel(self.right_frame, text="推理内容", font=("Arial", 16))
        self.content_label.pack(pady=5)

        # 创建富文本显示框
        self.content_text = ctk.CTkTextbox(self.right_frame, width=500, height=400)
        self.content_text.pack(pady=5, padx=5, fill="both", expand=True)

        # 配置文本标签 - 只使用颜色
        self.content_text.tag_config("timestamp", foreground="#888888")  # 时间戳使用灰色
        self.content_text.tag_config("user", foreground="#4CAF50")  # 用户名使用绿色
        self.content_text.tag_config("message", foreground="#2196F3")  # 消息使用蓝色
        self.content_text.tag_config("model", foreground="#9C27B0")  # 模型名称使用紫色
        self.content_text.tag_config("prompt", foreground="#FF9800")  # prompt内容使用橙色
        self.content_text.tag_config("reasoning", foreground="#FF9800")  # 推理过程使用橙色
        self.content_text.tag_config("response", foreground="#E91E63")  # 回复使用粉色
        self.content_text.tag_config("separator", foreground="#666666")  # 分隔符使用深灰色

        # 底部控制栏
        self.control_frame = ctk.CTkFrame(self.frame)
        self.control_frame.pack(fill="x", padx=10, pady=5)

        self.clear_button = ctk.CTkButton(
            self.control_frame,
            text="清除显示",
            command=self.clear_display,
            width=120
        )
        self.clear_button.pack(side="left", padx=5)

        # 启动自动更新线程
        self.update_thread = threading.Thread(target=self._auto_update, daemon=True)
        self.update_thread.start()

        # 启动GUI更新检查
        self.root.after(100, self._process_queue)

    def _on_closing(self):
        """处理窗口关闭事件"""
        self.root.quit()
        sys.exit(0)

    def _process_queue(self):
        """处理更新队列中的任务"""
        try:
            while True:
                task = self.update_queue.get_nowait()
                if task['type'] == 'update_group_list':
                    self._update_group_list_gui()
                elif task['type'] == 'update_display':
                    self._update_display_gui(task['group_id'])
        except queue.Empty:
            pass
        finally:
            # 继续检查队列
            self.root.after(100, self._process_queue)

    def _update_group_list_gui(self):
        """在主线程中更新群组列表"""
        # 清除现有按钮
        for button in self.group_buttons.values():
            button.destroy()
        self.group_buttons.clear()

        # 创建新的群组按钮
        for group_id in self.group_data.keys():
            button = ctk.CTkButton(
                self.group_scroll_frame,
                text=f"群号: {group_id}",
                width=160,
                height=30,
                corner_radius=8,
                command=lambda gid=group_id: self._on_group_select(gid)
            )
            button.pack(pady=2, padx=5)
            self.group_buttons[group_id] = button

        # 如果有选中的群组，保持其高亮状态
        if self.selected_group_id and self.selected_group_id in self.group_buttons:
            self._highlight_selected_group(self.selected_group_id)

    def _on_group_select(self, group_id: str):
        """处理群组选择事件"""
        self._highlight_selected_group(group_id)
        self._update_display_gui(group_id)

    def _highlight_selected_group(self, group_id: str):
        """高亮显示选中的群组按钮"""
        # 重置所有按钮的颜色
        for gid, button in self.group_buttons.items():
            if gid == group_id:
                # 设置选中按钮的颜色
                button.configure(fg_color="#1E88E5", hover_color="#1976D2")
            else:
                # 恢复其他按钮的默认颜色
                button.configure(fg_color="#2B2B2B", hover_color="#404040")

        self.selected_group_id = group_id

    def _update_display_gui(self, group_id: str):
        """在主线程中更新显示内容"""
        if group_id in self.group_data:
            self.content_text.delete("1.0", "end")
            for item in self.group_data[group_id]:
                # 时间戳
                time_str = item['time'].strftime("%Y-%m-%d %H:%M:%S")
                self.content_text.insert("end", f"[{time_str}]\n", "timestamp")

                # 用户信息
                self.content_text.insert("end", "用户: ", "timestamp")
                self.content_text.insert("end", f"{item.get('user', '未知')}\n", "user")

                # 消息内容
                self.content_text.insert("end", "消息: ", "timestamp")
                self.content_text.insert("end", f"{item.get('message', '')}\n", "message")

                # 模型信息
                self.content_text.insert("end", "模型: ", "timestamp")
                self.content_text.insert("end", f"{item.get('model', '')}\n", "model")

                # Prompt内容
                self.content_text.insert("end", "Prompt内容:\n", "timestamp")
                prompt_text = item.get('prompt', '')
                if prompt_text and prompt_text.lower() != 'none':
                    lines = prompt_text.split('\n')
                    for line in lines:
                        if line.strip():
                            self.content_text.insert("end", "    " + line + "\n", "prompt")
                else:
                    self.content_text.insert("end", "    无Prompt内容\n", "prompt")

                # 推理过程
                self.content_text.insert("end", "推理过程:\n", "timestamp")
                reasoning_text = item.get('reasoning', '')
                if reasoning_text and reasoning_text.lower() != 'none':
                    lines = reasoning_text.split('\n')
                    for line in lines:
                        if line.strip():
                            self.content_text.insert("end", "    " + line + "\n", "reasoning")
                else:
                    self.content_text.insert("end", "    无推理过程\n", "reasoning")

                # 回复内容
                self.content_text.insert("end", "回复: ", "timestamp")
                self.content_text.insert("end", f"{item.get('response', '')}\n", "response")

                # 分隔符
                self.content_text.insert("end", f"\n{'=' * 50}\n\n", "separator")

            # 滚动到顶部
            self.content_text.see("1.0")

    def _auto_update(self):
        """自动更新函数"""
        while True:
            try:
                # 从数据库获取最新数据，只获取启动时间之后的记录
                query = {"time": {"$gt": self.start_timestamp}}
                logger.debug(f"查询条件: {query}")

                # 先获取一条记录检查时间格式
                sample = self.db.reasoning_logs.find_one()
                if sample:
                    logger.debug(f"样本记录时间格式: {type(sample['time'])} 值: {sample['time']}")

                cursor = self.db.reasoning_logs.find(query).sort("time", -1)
                new_data = {}
                total_count = 0

                for item in cursor:
                    # 调试输出
                    if total_count == 0:
                        logger.debug(f"记录时间: {item['time']}, 类型: {type(item['time'])}")

                    total_count += 1
                    group_id = str(item.get('group_id', 'unknown'))
                    if group_id not in new_data:
                        new_data[group_id] = []

                    # 转换时间戳为datetime对象
                    if isinstance(item['time'], (int, float)):
                        time_obj = datetime.fromtimestamp(item['time'])
                    elif isinstance(item['time'], datetime):
                        time_obj = item['time']
                    else:
                        logger.warning(f"未知的时间格式: {type(item['time'])}")
                        time_obj = datetime.now()  # 使用当前时间作为后备

                    new_data[group_id].append({
                        'time': time_obj,
                        'user': item.get('user', '未知'),
                        'message': item.get('message', ''),
                        'model': item.get('model', '未知'),
                        'reasoning': item.get('reasoning', ''),
                        'response': item.get('response', ''),
                        'prompt': item.get('prompt', '')  # 添加prompt字段
                    })

                logger.info(f"从数据库加载了 {total_count} 条记录，分布在 {len(new_data)} 个群组中")

                # 更新数据
                if new_data != self.group_data:
                    self.group_data = new_data
                    logger.info("数据已更新，正在刷新显示...")
                    # 将更新任务添加到队列
                    self.update_queue.put({'type': 'update_group_list'})
                    if self.group_data:
                        # 如果没有选中的群组，选择最新的群组
                        if not self.selected_group_id or self.selected_group_id not in self.group_data:
                            self.selected_group_id = next(iter(self.group_data))
                        self.update_queue.put({
                            'type': 'update_display',
                            'group_id': self.selected_group_id
                        })
            except Exception:
                logger.exception("自动更新出错")

            # 每5秒更新一次
            time.sleep(5)

    def clear_display(self):
        """清除显示内容"""
        self.content_text.delete("1.0", "end")

    def run(self):
        """运行GUI"""
        self.root.mainloop()


def main():
    """主函数"""
    Database.initialize(
        host=os.getenv("MONGODB_HOST"),
        port=int(os.getenv("MONGODB_PORT")),
        db_name=os.getenv("DATABASE_NAME"),
        username=os.getenv("MONGODB_USERNAME"),
        password=os.getenv("MONGODB_PASSWORD"),
        auth_source=os.getenv("MONGODB_AUTH_SOURCE")
    )

    app = ReasoningGUI()
    app.run()


if __name__ == "__main__":
    main()

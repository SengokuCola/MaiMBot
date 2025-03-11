import sys
import threading
import time
import json
import asyncio
import websockets
from io import StringIO
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Callable
from loguru import logger
import os


class OutputCapture:
    """捕获标准输出和错误输出的类"""

    def __init__(self, original_stream):
        self.original_stream = original_stream
        self.buffer = StringIO()
        self.listeners: List[Callable[[str], None]] = []

    def write(self, data):
        # 写入原始流
        self.original_stream.write(data)
        # 写入缓冲区
        self.buffer.write(data)
        # 通知所有监听器
        for listener in self.listeners:
            listener(data)

    def flush(self):
        self.original_stream.flush()
        self.buffer.flush()

    def add_listener(self, listener: Callable[[str], None]):
        """添加输出监听器"""
        self.listeners.append(listener)

    def remove_listener(self, listener: Callable[[str], None]):
        """移除输出监听器"""
        if listener in self.listeners:
            self.listeners.remove(listener)


class WebSocketServer:
    """WebSocket服务器，用于将捕获的输出发送到前端"""

    def __init__(self, host: str = None, port: int = None):
        # 从环境变量或配置获取主机和端口
        self.host = host or os.getenv("WEBSOCKET_HOST", "localhost")
        self.port = port or int(os.getenv("WEBSOCKET_PORT", "8765"))
        self.server = None
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.running = False
        self.loop = None

    async def handler(self, websocket, path):
        """处理WebSocket连接"""
        self.clients.add(websocket)
        try:
            await websocket.send(
                json.dumps(
                    {
                        "type": "connection",
                        "message": "已连接到MaiMBot输出管理器",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            )

            # 发送历史记录
            history = output_manager.get_message_history()
            await websocket.send(
                json.dumps(
                    {
                        "type": "history",
                        "messages": history,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            )

            # 保持连接直到客户端断开
            while True:
                await websocket.recv()
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        """广播消息到所有连接的客户端"""
        if not self.clients:
            return

        message_json = json.dumps(message)
        tasks = [client.send(message_json) for client in self.clients]
        if tasks:
            await asyncio.gather(*tasks)

    def start(self):
        """启动WebSocket服务器"""
        if self.running:
            return

        self.running = True

        # 在新线程中运行事件循环
        def run_server():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            start_server = websockets.serve(self.handler, self.host, self.port)

            self.server = self.loop.run_until_complete(start_server)
            logger.info(f"WebSocket服务器已启动，运行在 ws://{self.host}:{self.port}")

            try:
                self.loop.run_forever()
            except KeyboardInterrupt:
                pass
            finally:
                self.server.close()
                self.loop.run_until_complete(self.server.wait_closed())
                self.loop.close()
                self.running = False

        threading.Thread(target=run_server, daemon=True).start()

    def stop(self):
        """停止WebSocket服务器"""
        if not self.running or not self.loop:
            return

        self.loop.call_soon_threadsafe(self.loop.stop)
        self.running = False
        logger.info("WebSocket服务器已停止")


# 使用threading.Lock进行初始化保护
_output_manager_lock = threading.Lock()
_output_manager_initialized = False


class OutputManager:
    """单例模式的输出管理器"""

    def __init__(self):
        global _output_manager_initialized
        with _output_manager_lock:
            if not _output_manager_initialized:
                # 初始化属性
                self.stdout_capture = None
                self.stderr_capture = None
                self.websocket_server = WebSocketServer()
                self.message_history: List[Dict[str, Any]] = []
                self.max_history_size = 1000  # 最大历史记录数量
                _output_manager_initialized = True

    def start_capture(self):
        """开始捕获标准输出和错误输出"""
        if self.stdout_capture is None:
            self.stdout_capture = OutputCapture(sys.stdout)
            sys.stdout = self.stdout_capture
            self.stdout_capture.add_listener(
                lambda data: self._process_output("stdout", data)
            )

        if self.stderr_capture is None:
            self.stderr_capture = OutputCapture(sys.stderr)
            sys.stderr = self.stderr_capture
            self.stderr_capture.add_listener(
                lambda data: self._process_output("stderr", data)
            )

        # 启动WebSocket服务器
        self.websocket_server.start()

        logger.info("输出捕获已启动")

    def stop_capture(self):
        """停止捕获标准输出和错误输出"""
        if self.stdout_capture is not None:
            sys.stdout = self.stdout_capture.original_stream
            self.stdout_capture = None

        if self.stderr_capture is not None:
            sys.stderr = self.stderr_capture.original_stream
            self.stderr_capture = None

        # 停止WebSocket服务器
        self.websocket_server.stop()

        logger.info("输出捕获已停止")

    def _process_output(self, source: str, data: str):
        """处理捕获的输出"""
        if not data.strip():
            return

        message = {
            "type": "output",
            "source": source,
            "content": data,
            "timestamp": datetime.now().isoformat(),
        }

        # 添加到历史记录
        self.message_history.append(message)

        # 限制历史记录大小
        if len(self.message_history) > self.max_history_size:
            self.message_history = self.message_history[-self.max_history_size :]

        # 通过WebSocket发送
        if self.websocket_server.running and self.websocket_server.loop:
            asyncio.run_coroutine_threadsafe(
                self.websocket_server.broadcast(message), self.websocket_server.loop
            )

    def get_message_history(self) -> List[Dict[str, Any]]:
        """获取消息历史记录"""
        return self.message_history

    def send_custom_message(
        self, message_type: str, content: Any, source: str = "custom"
    ):
        """发送自定义消息"""
        message = {
            "type": message_type,
            "source": source,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }

        # 添加到历史记录
        self.message_history.append(message)

        # 限制历史记录大小
        if len(self.message_history) > self.max_history_size:
            self.message_history = self.message_history[-self.max_history_size :]

        # 通过WebSocket发送
        if self.websocket_server.running and self.websocket_server.loop:
            asyncio.run_coroutine_threadsafe(
                self.websocket_server.broadcast(message), self.websocket_server.loop
            )


# 创建全局单例实例
output_manager = OutputManager()


# 示例用法
if __name__ == "__main__":
    # 启动输出管理器
    output_manager = OutputManager()
    output_manager.start_capture()

    # 模拟程序输出
    print("这是一条标准输出信息")
    print("这是另一条标准输出信息")

    # 模拟错误输出
    sys.stderr.write("这是一条错误信息\n")

    # 发送自定义消息
    output_manager.send_custom_message(
        "status", {"progress": 50, "status": "processing"}, "task_manager"
    )

    # 保持程序运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        output_manager.stop_capture()
        print("程序已退出")

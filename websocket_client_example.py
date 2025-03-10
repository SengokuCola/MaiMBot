import asyncio
import websockets
import json
from datetime import datetime


async def connect_to_output_manager():
    """连接到OutputManager的WebSocket服务器并接收消息"""

    uri = "ws://localhost:8765"
    print(f"正在连接到 {uri}...")

    try:
        async with websockets.connect(uri) as websocket:
            print("已连接到服务器")

            while True:
                # 接收消息
                message = await websocket.recv()
                data = json.loads(message)

                # 格式化时间戳
                timestamp = datetime.fromisoformat(data["timestamp"]).strftime(
                    "%H:%M:%S"
                )

                # 根据消息类型和来源显示不同颜色
                if data["type"] == "output":
                    if data["source"] == "stdout":
                        # 标准输出 - 白色
                        print(f"\033[37m[{timestamp}] {data['content']}\033[0m", end="")
                    elif data["source"] == "stderr":
                        # 错误输出 - 红色
                        print(f"\033[31m[{timestamp}] {data['content']}\033[0m", end="")
                elif data["type"] == "connection":
                    # 连接消息 - 绿色
                    print(f"\033[32m[{timestamp}] {data['message']}\033[0m")
                elif data["type"] == "history":
                    # 历史记录 - 蓝色
                    print(
                        f"\033[34m[{timestamp}] 收到历史记录: {len(data['messages'])} 条消息\033[0m"
                    )
                else:
                    # 其他消息 - 黄色
                    content = data.get("content", "")
                    if isinstance(content, dict):
                        content = json.dumps(content, ensure_ascii=False)
                    print(f"\033[33m[{timestamp}] [{data['type']}] {content}\033[0m")

    except websockets.exceptions.ConnectionClosed:
        print("与服务器的连接已断开")
    except Exception as e:
        print(f"发生错误: {e}")


if __name__ == "__main__":
    # 运行客户端
    asyncio.run(connect_to_output_manager())

import time
import sys
from src.common.output_manager import OutputManager


def main():
    # 初始化输出管理器
    output_manager = OutputManager()

    # 启动输出捕获
    output_manager.start_capture()
    print("输出管理器已启动，WebSocket服务器运行在 ws://localhost:8765")
    print("您可以使用任何WebSocket客户端连接到此地址来接收输出")

    # 发送一些测试消息
    print("这是一条标准输出消息")
    sys.stderr.write("这是一条错误输出消息\n")

    # 发送自定义消息
    output_manager.send_custom_message(
        "status", {"progress": 50, "status": "processing"}, "task_manager"
    )

    # 每隔1秒发送一条消息
    try:
        count = 0
        while True:
            count += 1
            print(f"测试消息 #{count}")
            if count % 5 == 0:
                sys.stderr.write(f"错误消息 #{count}\n")

            # 每10条消息发送一次自定义消息
            if count % 10 == 0:
                output_manager.send_custom_message(
                    "progress", {"count": count, "percentage": count % 100}, "counter"
                )

            time.sleep(1)
    except KeyboardInterrupt:
        # 停止输出捕获
        output_manager.stop_capture()
        print("程序已退出")


if __name__ == "__main__":
    main()

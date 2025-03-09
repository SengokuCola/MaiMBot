import os
import subprocess
import zipfile
import sys
import requests
from tqdm import tqdm


def extract_files(zip_path, target_dir):
    """
    解压

    Args:
    zip_path: 源ZIP压缩包路径（需确保是有效压缩包）
    target_dir: 目标文件夹路径（会自动创建不存在的目录）
    """
    # 打开ZIP压缩包（上下文管理器自动处理关闭）
    with zipfile.ZipFile(zip_path) as zip_ref:
        # 通过第一个文件路径推断顶层目录名（格式如：top_dir/）
        top_dir = zip_ref.namelist()[0].split("/")[0] + "/"

        # 遍历压缩包内所有文件条目
        for file in zip_ref.namelist():
            # 跳过目录条目，仅处理文件
            if file.startswith(top_dir) and not file.endswith("/"):
                # 截取顶层目录后的相对路径（如：sub_dir/file.txt）
                rel_path = file[len(top_dir) :]

                # 创建目标目录结构（含多级目录）
                os.makedirs(
                    os.path.dirname(f"{target_dir}/{rel_path}"),
                    exist_ok=True,  # 忽略已存在目录的错误
                )

                # 读取压缩包内文件内容并写入目标路径
                with open(f"{target_dir}/{rel_path}", "wb") as f:
                    f.write(zip_ref.read(file))


def run_cmd(command: str, open_new_window: bool = False):
    """
    运行 cmd 命令

    Args:
        command (str): 指定要运行的命令
        open_new_window (bool): 指定是否新建一个 cmd 窗口运行
    """
    creationflags = 0
    if open_new_window:
        creationflags = subprocess.CREATE_NEW_CONSOLE
    subprocess.Popen(
        [
            "cmd.exe",
            "/c",
            command,
        ],
        creationflags=creationflags,
    )


def run_maimbot():
    run_cmd(r"napcat\NapCatWinBootMain.exe 10001", False)
    run_cmd(
        r"mongodb\bin\mongod.exe --dbpath=" + os.getcwd() + r"\mongodb\db --port 27017",
        True,
    )
    run_cmd("nb run", True)


def install_mongodb():
    """
    安装 MongoDB
    """
    print("下载 MongoDB")
    resp = requests.get(
        "https://fastdl.mongodb.org/windows/mongodb-windows-x86_64-latest.zip",
        stream=True,
    )
    total = int(resp.headers.get("content-length", 0))  # 计算文件大小
    with open("mongodb.zip", "w+b") as file, tqdm(  # 展示下载进度条，并解压文件
        desc="mongodb.zip",
        total=total,
        unit="iB",
        unit_scale=True,
        unit_divisor=1024,
    ) as bar:
        for data in resp.iter_content(chunk_size=1024):
            size = file.write(data)
            bar.update(size)
        extract_files("mongodb.zip", "mongodb")
        print("MongoDB 下载完成")
        os.remove("mongodb.zip")


def install_napcat():
    run_cmd("start https://github.com/NapNeko/NapCatQQ/releases", True)
    print("请检查弹出的浏览器窗口，点击**第一个**蓝色的“Win64无头” 下载 napcat")
    napcat_filename = input(
        "下载完成后请把文件复制到此文件夹，并将**不包含后缀的文件名**输入至此窗口，如 NapCat.32793.Shell："
    )
    extract_files(napcat_filename + ".zip", "napcat")
    print("NapCat 安装完成")
    os.remove(napcat_filename + ".zip")


if __name__ == "__main__":
    os.system("cls")
    if sys.version_info < (3, 9):
        print("当前 Python 版本过低，最低版本为 3.9，请更新 Python 版本")
        print("按任意键退出")
        input()
        exit(1)
    choice = input(
        "请输入要进行的操作：\n"
        "1.首次安装\n"
        "2.运行麦麦\n"
        "3.运行麦麦并启动可视化推理界面\n"
    )
    os.system("cls")
    if choice == "1":
        install_napcat()
        install_mongodb()
    elif choice == "2":
        run_maimbot()
    elif choice == "3":
        run_maimbot()
        run_cmd("python src/gui/reasoning_gui.py", True)

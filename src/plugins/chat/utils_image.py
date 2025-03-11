import base64
import io
import os
import time
import zlib  # 用于 CRC32

from loguru import logger
from nonebot import get_driver
from PIL import Image

from ...common.database import Database
from ..chat.config import global_config

driver = get_driver()
config = driver.config



def storage_compress_image(base64_data: str, max_size: int = 200) -> str:
    """
    压缩base64格式的图片到指定大小（单位：KB）并在数据库中记录图片信息
    Args:
        base64_data: base64编码的图片数据
        max_size: 最大文件大小（KB）
    Returns:
        str: 压缩后的base64图片数据
    """
    try:
        # 将base64转换为字节数据
        image_data = base64.b64decode(base64_data)
        
        # 使用 CRC32 计算哈希值
        hash_value = format(zlib.crc32(image_data) & 0xFFFFFFFF, 'x')
        
        # 确保图片目录存在
        images_dir = "data/images"
        os.makedirs(images_dir, exist_ok=True)
        
        # 连接数据库
        db = Database.get_instance()
        
        # 检查是否已存在相同哈希值的图片
        collection = db.db['images']
        existing_image = collection.find_one({'hash': hash_value})
        
        if existing_image:
            print(f"\033[1;33m[提示]\033[0m 发现重复图片，使用已存在的文件: {existing_image['path']}")
            return base64_data

        # 将字节数据转换为图片对象
        img = Image.open(io.BytesIO(image_data))
        
        # 如果是动图，直接返回原图
        if getattr(img, 'is_animated', False):
            return base64_data
            
        # 计算当前大小（KB）
        current_size = len(image_data) / 1024
        
        # 如果已经小于目标大小，直接使用原图
        if current_size <= max_size:
            compressed_data = image_data
        else:
            # 压缩逻辑
            # 先缩放到50%
            new_width = int(img.width * 0.5)
            new_height = int(img.height * 0.5)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 如果缩放后的最大边长仍然大于400，继续缩放
            max_dimension = 400
            max_current = max(new_width, new_height)
            if max_current > max_dimension:
                ratio = max_dimension / max_current
                new_width = int(new_width * ratio)
                new_height = int(new_height * ratio)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 转换为RGB模式（去除透明通道）
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # 使用固定质量参数压缩
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=85, optimize=True)
            compressed_data = output.getvalue()
        
        # 生成文件名（使用时间戳和哈希值确保唯一性）
        timestamp = int(time.time())
        filename = f"{timestamp}_{hash_value}.jpg"
        image_path = os.path.join(images_dir, filename)
        
        # 保存文件
        with open(image_path, "wb") as f:
            f.write(compressed_data)
            
        print(f"\033[1;32m[成功]\033[0m 保存图片到: {image_path}")
        
        try:
            # 准备数据库记录
            image_record = {
                'filename': filename,
                'path': image_path,
                'size': len(compressed_data) / 1024,
                'timestamp': timestamp,
                'width': img.width,
                'height': img.height,
                'description': '',
                'tags': [],
                'type': 'image',
                'hash': hash_value
            }
            
            # 保存记录
            collection.insert_one(image_record)
            print("\033[1;32m[成功]\033[0m 保存图片记录到数据库")
            
        except Exception as db_error:
            print(f"\033[1;31m[错误]\033[0m 数据库操作失败: {str(db_error)}")
        
        # 将压缩后的数据转换为base64
        compressed_base64 = base64.b64encode(compressed_data).decode('utf-8')
        return compressed_base64
        
    except Exception as e:
        print(f"\033[1;31m[错误]\033[0m 压缩图片失败: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return base64_data

def storage_emoji(image_data: bytes) -> bytes:
    """
    存储表情包到本地文件夹
    Args:
        image_data: 图片字节数据
        group_id: 群组ID（仅用于日志）
        user_id: 用户ID（仅用于日志）
    Returns:
        bytes: 原始图片数据
    """
    if not global_config.EMOJI_SAVE:
        return image_data
    try:
        # 使用 CRC32 计算哈希值
        hash_value = format(zlib.crc32(image_data) & 0xFFFFFFFF, 'x')
        
        # 确保表情包目录存在
        emoji_dir = "data/emoji"
        os.makedirs(emoji_dir, exist_ok=True)
        
        # 检查是否已存在相同哈希值的文件
        for filename in os.listdir(emoji_dir):
            if hash_value in filename:
                # print(f"\033[1;33m[提示]\033[0m 发现重复表情包: {filename}")
                return image_data
        
        # 生成文件名
        timestamp = int(time.time())
        filename = f"{timestamp}_{hash_value}.jpg"
        emoji_path = os.path.join(emoji_dir, filename)
        
        # 直接保存原始文件
        with open(emoji_path, "wb") as f:
            f.write(image_data)
            
        print(f"\033[1;32m[成功]\033[0m 保存表情包到: {emoji_path}")
        return image_data
        
    except Exception as e:
        print(f"\033[1;31m[错误]\033[0m 保存表情包失败: {str(e)}")
        return image_data 
    

def storage_image(image_data: bytes) -> bytes:
    """
    存储图片到本地文件夹
    Args:
        image_data: 图片字节数据
        group_id: 群组ID（仅用于日志）
        user_id: 用户ID（仅用于日志）
    Returns:
        bytes: 原始图片数据
    """
    try:
        # 使用 CRC32 计算哈希值
        hash_value = format(zlib.crc32(image_data) & 0xFFFFFFFF, 'x')
        
        # 确保表情包目录存在
        image_dir = "data/image"
        os.makedirs(image_dir, exist_ok=True)
        
        # 检查是否已存在相同哈希值的文件
        for filename in os.listdir(image_dir):
            if hash_value in filename:
                # print(f"\033[1;33m[提示]\033[0m 发现重复表情包: {filename}")
                return image_data
        
        # 生成文件名
        timestamp = int(time.time())
        filename = f"{timestamp}_{hash_value}.jpg"
        image_path = os.path.join(image_dir, filename)
        
        # 直接保存原始文件
        with open(image_path, "wb") as f:
            f.write(image_data)
            
        print(f"\033[1;32m[成功]\033[0m 保存图片到: {image_path}")
        return image_data
        
    except Exception as e:
        print(f"\033[1;31m[错误]\033[0m 保存图片失败: {str(e)}")
        return image_data 

def compress_base64_image_by_scale(base64_data: str, target_size: int = 0.8 * 1024 * 1024) -> str:
    """压缩base64格式的图片到指定大小
    Args:
        base64_data: base64编码的图片数据
        target_size: 目标文件大小（字节），默认0.8MB
    Returns:
        str: 压缩后的base64图片数据
    """
    try:
        # 将base64转换为字节数据
        image_data = base64.b64decode(base64_data)
        
        # 如果已经小于目标大小，直接返回原图
        if len(image_data) <= 2*1024*1024:
            return base64_data
            
        # 将字节数据转换为图片对象
        img = Image.open(io.BytesIO(image_data))
        
        # 获取原始尺寸
        original_width, original_height = img.size
        
        # 计算缩放比例
        scale = min(1.0, (target_size / len(image_data)) ** 0.5)
        
        # 计算新的尺寸
        new_width = int(original_width * scale)
        new_height = int(original_height * scale)
        
        # 创建内存缓冲区
        output_buffer = io.BytesIO()
        
        # 如果是GIF，处理所有帧
        if getattr(img, "is_animated", False):
            frames = []
            for frame_idx in range(img.n_frames):
                img.seek(frame_idx)
                new_frame = img.copy()
                new_frame = new_frame.resize((new_width//2, new_height//2), Image.Resampling.LANCZOS) # 动图折上折
                frames.append(new_frame)
            
            # 保存到缓冲区
            frames[0].save(
                output_buffer,
                format='GIF',
                save_all=True,
                append_images=frames[1:],
                optimize=True,
                duration=img.info.get('duration', 100),
                loop=img.info.get('loop', 0)
            )
        else:
            # 处理静态图片
            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 保存到缓冲区，保持原始格式
            if img.format == 'PNG' and img.mode in ('RGBA', 'LA'):
                resized_img.save(output_buffer, format='PNG', optimize=True)
            else:
                resized_img.save(output_buffer, format='JPEG', quality=95, optimize=True)
        
        # 获取压缩后的数据并转换为base64
        compressed_data = output_buffer.getvalue()
        logger.success(f"压缩图片: {original_width}x{original_height} -> {new_width}x{new_height}")
        logger.info(f"压缩前大小: {len(image_data)/1024:.1f}KB, 压缩后大小: {len(compressed_data)/1024:.1f}KB")
        
        return base64.b64encode(compressed_data).decode('utf-8')
        
    except Exception as e:
        logger.error(f"压缩图片失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return base64_data 

def image_path_to_base64(image_path: str) -> str:
    """将图片路径转换为base64编码
    Args:
        image_path: 图片文件路径
    Returns:
        str: base64编码的图片数据
    """
    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()
            return base64.b64encode(image_data).decode('utf-8')
    except Exception as e:
        logger.error(f"读取图片失败: {image_path}, 错误: {str(e)}")
        return None 
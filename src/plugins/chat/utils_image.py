import base64
import os
import time
import aiohttp
import hashlib
from typing import Optional, Union

from loguru import logger
from nonebot import get_driver

from ...common.database import Database
from ..chat.config import global_config
from ..models.utils_model import LLM_request
driver = get_driver()
config = driver.config

class ImageManager:
    _instance = None
    IMAGE_DIR = "data"  # 图像存储根目录
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.db = None
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.db = Database.get_instance()
            self._ensure_image_collection()
            self._ensure_description_collection()
            self._ensure_image_dir()
            self._initialized = True
            self._llm = LLM_request(model=global_config.vlm, temperature=0.4, max_tokens=300)
            
    def _ensure_image_dir(self):
        """确保图像存储目录存在"""
        os.makedirs(self.IMAGE_DIR, exist_ok=True)
        
    def _ensure_image_collection(self):
        """确保images集合存在并创建索引"""
        if 'images' not in self.db.db.list_collection_names():
            self.db.db.create_collection('images')
            # 创建索引
            self.db.db.images.create_index([('hash', 1)], unique=True)
            self.db.db.images.create_index([('url', 1)])
            self.db.db.images.create_index([('path', 1)])

    def _ensure_description_collection(self):
        """确保image_descriptions集合存在并创建索引"""
        if 'image_descriptions' not in self.db.db.list_collection_names():
            self.db.db.create_collection('image_descriptions')
            # 创建索引
            self.db.db.image_descriptions.create_index([('hash', 1)], unique=True)
            self.db.db.image_descriptions.create_index([('type', 1)])

    def _get_description_from_db(self, image_hash: str, description_type: str) -> Optional[str]:
        """从数据库获取图片描述
        
        Args:
            image_hash: 图片哈希值
            description_type: 描述类型 ('emoji' 或 'image')
            
        Returns:
            Optional[str]: 描述文本，如果不存在则返回None
        """
        result= self.db.db.image_descriptions.find_one({
            'hash': image_hash,
            'type': description_type
        })
        return result['description'] if result else None

    def _save_description_to_db(self, image_hash: str, description: str, description_type: str) -> None:
        """保存图片描述到数据库
        
        Args:
            image_hash: 图片哈希值
            description: 描述文本
            description_type: 描述类型 ('emoji' 或 'image')
        """
        self.db.db.image_descriptions.update_one(
            {'hash': image_hash, 'type': description_type},
            {
                '$set': {
                    'description': description,
                    'timestamp': int(time.time())
                }
            },
            upsert=True
        )

    async def save_image(self, 
                        image_data: Union[str, bytes], 
                        url: str = None, 
                        description: str = None, 
                        is_base64: bool = False) -> Optional[str]:
        """保存图像
        Args:
            image_data: 图像数据(base64字符串或字节)
            url: 图像URL
            description: 图像描述
            is_base64: image_data是否为base64格式
        Returns:
            str: 保存后的文件路径,失败返回None
        """
        try:
            # 转换为字节格式
            if is_base64:
                if isinstance(image_data, str):
                    image_bytes = base64.b64decode(image_data)
                else:
                    return None
            else:
                if isinstance(image_data, bytes):
                    image_bytes = image_data
                else:
                    return None
                    
            # 计算哈希值
            image_hash = hashlib.md5(image_bytes).hexdigest()
            
            # 查重
            existing = self.db.db.images.find_one({'hash': image_hash})
            if existing:
                return existing['path']
                
            # 生成文件名和路径
            timestamp = int(time.time())
            filename = f"{timestamp}_{image_hash[:8]}.jpg"
            file_path = os.path.join(self.IMAGE_DIR, filename)
            
            # 保存文件
            with open(file_path, "wb") as f:
                f.write(image_bytes)
                
            # 保存到数据库
            image_doc = {
                'hash': image_hash,
                'path': file_path,
                'url': url,
                'description': description,
                'timestamp': timestamp
            }
            self.db.db.images.insert_one(image_doc)
            
            return file_path
            
        except Exception as e:
            logger.error(f"保存图像失败: {str(e)}")
            return None
            
    async def get_image_by_url(self, url: str) -> Optional[str]:
        """根据URL获取图像路径(带查重)
        Args:
            url: 图像URL
        Returns:
            str: 本地文件路径,不存在返回None
        """
        try:
            # 先查找是否已存在
            existing = self.db.db.images.find_one({'url': url})
            if existing:
                return existing['path']
                
            # 下载图像
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        image_bytes = await resp.read()
                        return await self.save_image(image_bytes, url=url)
            return None
            
        except Exception as e:
            logger.error(f"获取图像失败: {str(e)}")
            return None
            
    async def get_base64_by_url(self, url: str) -> Optional[str]:
        """根据URL获取base64(带查重)
        Args:
            url: 图像URL
        Returns:
            str: base64字符串,失败返回None
        """
        try:
            image_path = await self.get_image_by_url(url)
            if not image_path:
                return None
                
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
                return base64.b64encode(image_bytes).decode('utf-8')
                
        except Exception as e:
            logger.error(f"获取base64失败: {str(e)}")
            return None
            
        
    def check_url_exists(self, url: str) -> bool:
        """检查URL是否已存在
        Args:
            url: 图像URL
        Returns:
            bool: 是否存在
        """
        return self.db.db.images.find_one({'url': url}) is not None
        
    def check_hash_exists(self, image_data: Union[str, bytes], is_base64: bool = False) -> bool:
        """检查图像是否已存在
        Args:
            image_data: 图像数据(base64或字节)
            is_base64: 是否为base64格式
        Returns:
            bool: 是否存在
        """
        try:
            if is_base64:
                if isinstance(image_data, str):
                    image_bytes = base64.b64decode(image_data)
                else:
                    return False
            else:
                if isinstance(image_data, bytes):
                    image_bytes = image_data
                else:
                    return False
                    
            image_hash = hashlib.md5(image_bytes).hexdigest()
            return self.db.db.images.find_one({'hash': image_hash}) is not None
            
        except Exception as e:
            logger.error(f"检查哈希失败: {str(e)}")
            return False
        
    async def get_emoji_description(self, image_base64: str) -> str:
        """获取表情包描述，带查重和保存功能"""
        try:
            # 计算图片哈希
            image_bytes = base64.b64decode(image_base64)
            image_hash = hashlib.md5(image_bytes).hexdigest()
            
            # 查询缓存的描述
            cached_description = self._get_description_from_db(image_hash, 'emoji')
            if cached_description:
                logger.info(f"缓存表情包描述: {cached_description}")
                return f"[表情包：{cached_description}]"

            # 调用AI获取描述
            prompt = "这是一个表情包，使用中文简洁的描述一下表情包的内容和表情包所表达的情感，可以使用二次元词汇。如果有文字，请把文字描述出来。"
            description, _ = await self._llm.generate_response_for_image(prompt, image_base64)
            
            # 根据配置决定是否保存图片
            if global_config.EMOJI_SAVE:
                # 生成文件名和路径
                timestamp = int(time.time())
                filename = f"{timestamp}_{image_hash[:8]}.jpg"
                file_path = os.path.join(self.IMAGE_DIR, 'emoji',filename)
                
                try:
                    # 保存文件
                    with open(file_path, "wb") as f:
                        f.write(image_bytes)
                    
                    # 保存到数据库
                    image_doc = {
                        'hash': image_hash,
                        'path': file_path,
                        'type': 'emoji',
                        'description': description,
                        'timestamp': timestamp
                    }
                    self.db.db.images.update_one(
                        {'hash': image_hash},
                        {'$set': image_doc},
                        upsert=True
                    )
                    logger.success(f"保存表情包: {file_path}")
                except Exception as e:
                    logger.error(f"保存表情包文件失败: {str(e)}")
            
            # 保存描述到数据库
            self._save_description_to_db(image_hash, description, 'emoji')
            
            return f"[表情包：{description}]"
        except Exception as e:
            logger.error(f"获取表情包描述失败: {str(e)}")
            return "[表情包]"

    async def get_image_description(self, image_base64: str) -> str:
        """获取普通图片描述，带查重和保存功能"""
        try:
            # 计算图片哈希
            image_bytes = base64.b64decode(image_base64)
            image_hash = hashlib.md5(image_bytes).hexdigest()

            # 查询缓存的描述
            cached_description = self._get_description_from_db(image_hash, 'image')
            if cached_description:
                return f"[图片：{cached_description}]"

            # 调用AI获取描述
            prompt = "请用中文描述这张图片的内容。如果有文字，请把文字都描述出来。并尝试猜测这个图片的含义。最多200个字，可以使用二次元词汇，如果有二次元人物，请详细描述其动作神态和发色、衣着。"
            description, _ = await self._llm.generate_response_for_image(prompt, image_base64)

            if description is None:
                logger.warning("AI未能生成图片描述")
                return "[图片]"
            
            # 根据配置决定是否保存图片
            if global_config.EMOJI_SAVE:
                # 生成文件名和路径
                timestamp = int(time.time())
                filename = f"{timestamp}_{image_hash[:8]}.jpg"
                file_path = os.path.join(self.IMAGE_DIR,'image', filename)
                
                try:
                    # 保存文件
                    with open(file_path, "wb") as f:
                        f.write(image_bytes)
                    
                    # 保存到数据库
                    image_doc = {
                        'hash': image_hash,
                        'path': file_path,
                        'type': 'image',
                        'description': description,
                        'timestamp': timestamp
                    }
                    self.db.db.images.update_one(
                        {'hash': image_hash},
                        {'$set': image_doc},
                        upsert=True
                    )
                    logger.success(f"保存图片: {file_path}")
                except Exception as e:
                    logger.error(f"保存图片文件失败: {str(e)}")
            
            # 保存描述到数据库
            self._save_description_to_db(image_hash, description, 'image')
            
            return f"[图片：{description}]"
        except Exception as e:
            logger.error(f"获取图片描述失败: {str(e)}")
            return "[图片]"



# 创建全局单例
image_manager = ImageManager()


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
import aiohttp
import asyncio
import requests
import time
from typing import Tuple, Union
from nonebot import get_driver
from loguru import logger
from ..chat.config import global_config

driver = get_driver()
config = driver.config

class LLM_request:
    def __init__(self, model, **kwargs):
        # 将大写的配置键转换为小写并从config中获取实际值
        try:
            self.api_key = getattr(config, model["key"])
            self.base_url = getattr(config, model["base_url"])
        except AttributeError as e:
            logger.error(f"配置错误：找不到对应的配置项 - {str(e)}")
            raise ValueError(f"配置错误：找不到对应的配置项 - {str(e)}") from e
        self.model_name = model["name"]
        self.params = kwargs

    async def generate_response(self, prompt: str) -> Tuple[str, str]:
        """根据输入的提示生成模型的异步响应"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 构建请求体
        data = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            **self.params
        }
        
        # 发送请求到完整的chat/completions端点
        api_url = f"{self.base_url.rstrip('/')}/chat/completions"
        logger.info(f"发送请求到URL: {api_url}")  # 记录请求的URL
        
        max_retries = 3
        base_wait_time = 15
        
        for retry in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(api_url, headers=headers, json=data) as response:
                        if response.status == 429:
                            wait_time = base_wait_time * (2 ** retry)  # 指数退避
                            logger.warning(f"遇到请求限制(429)，等待{wait_time}秒后重试...")
                            await asyncio.sleep(wait_time)
                            continue
                            
                        response.raise_for_status()  # 检查其他响应状态
                        
                        result = await response.json()
                        if "choices" in result and len(result["choices"]) > 0:
                            content = result["choices"][0]["message"]["content"]
                            reasoning_content = result["choices"][0]["message"].get("reasoning_content", "")
                            return content, reasoning_content
                        return "没有返回结果", ""
                
            except Exception as e:
                if retry < max_retries - 1:  # 如果还有重试机会
                    wait_time = base_wait_time * (2 ** retry)
                    logger.error(f"[回复]请求失败，等待{wait_time}秒后重试... 错误: {str(e)}", exc_info=True)
                    await asyncio.sleep(wait_time)
                else:
                    logger.critical(f"请求失败: {str(e)}", exc_info=True)
                    return f"请求失败: {str(e)}", ""
        
        logger.error("达到最大重试次数，请求仍然失败")
        return "达到最大重试次数，请求仍然失败", ""

    async def generate_response_for_image(self, prompt: str, image_base64: str) -> Tuple[str, str]:
        """根据输入的提示和图片生成模型的异步响应"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 构建请求体
        data = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            **self.params
        }
        
        # 发送请求到完整的chat/completions端点
        api_url = f"{self.base_url.rstrip('/')}/chat/completions"
        logger.info(f"发送请求到URL: {api_url}")  # 记录请求的URL
        
        max_retries = 3
        base_wait_time = 15
        
        for retry in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(api_url, headers=headers, json=data) as response:
                        if response.status == 429:
                            wait_time = base_wait_time * (2 ** retry)  # 指数退避
                            logger.warning(f"遇到请求限制(429)，等待{wait_time}秒后重试...")
                            await asyncio.sleep(wait_time)
                            continue
                            
                        response.raise_for_status()  # 检查其他响应状态
                        
                        result = await response.json()
                        if "choices" in result and len(result["choices"]) > 0:
                            content = result["choices"][0]["message"]["content"]
                            reasoning_content = result["choices"][0]["message"].get("reasoning_content", "")
                            return content, reasoning_content
                        return "没有返回结果", ""
                
            except Exception as e:
                if retry < max_retries - 1:  # 如果还有重试机会
                    wait_time = base_wait_time * (2 ** retry)
                    logger.error(f"[image回复]请求失败，等待{wait_time}秒后重试... 错误: {str(e)}", exc_info=True)
                    await asyncio.sleep(wait_time)
                else:
                    logger.critical(f"请求失败: {str(e)}", exc_info=True)
                    return f"请求失败: {str(e)}", ""
        
        logger.error("达到最大重试次数，请求仍然失败")
        return "达到最大重试次数，请求仍然失败", ""

    def generate_response_for_image_sync(self, prompt: str, image_base64: str) -> Tuple[str, str]:
        """同步方法：根据输入的提示和图片生成模型的响应"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 构建请求体
        data = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            **self.params
        }
        
        # 发送请求到完整的chat/completions端点
        api_url = f"{self.base_url.rstrip('/')}/chat/completions"
        logger.info(f"发送请求到URL: {api_url}")  # 记录请求的URL
        
        max_retries = 2
        base_wait_time = 6
        
        for retry in range(max_retries):
            try:
                response = requests.post(api_url, headers=headers, json=data, timeout=30)
                
                if response.status_code == 429:
                    wait_time = base_wait_time * (2 ** retry)
                    logger.warning(f"遇到请求限制(429)，等待{wait_time}秒后重试...")
                    time.sleep(wait_time)
                    continue
                    
                response.raise_for_status()  # 检查其他响应状态
                
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]
                    reasoning_content = result["choices"][0]["message"].get("reasoning_content", "")
                    return content, reasoning_content
                return "没有返回结果", ""
                
            except Exception as e:
                if retry < max_retries - 1:  # 如果还有重试机会
                    wait_time = base_wait_time * (2 ** retry)
                    logger.error(f"[image_sync回复]请求失败，等待{wait_time}秒后重试... 错误: {str(e)}", exc_info=True)
                    time.sleep(wait_time)
                else:
                    logger.critical(f"请求失败: {str(e)}", exc_info=True)
                    return f"请求失败: {str(e)}", ""
        
        logger.error("达到最大重试次数，请求仍然失败")
        return "达到最大重试次数，请求仍然失败", ""

    def get_embedding_sync(self, text: str, model: str = "BAAI/bge-m3") -> Union[list, None]:
        """同步方法：获取文本的embedding向量
        
        Args:
            text: 需要获取embedding的文本
            model: 使用的模型名称，默认为"BAAI/bge-m3"
            
        Returns:
            list: embedding向量，如果失败则返回None
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model,
            "input": text,
            "encoding_format": "float"
        }
        
        api_url = f"{self.base_url.rstrip('/')}/embeddings"
        logger.info(f"发送请求到URL: {api_url}")  # 记录请求的URL
        
        max_retries = 2
        base_wait_time = 6
        
        for retry in range(max_retries):
            try:
                response = requests.post(api_url, headers=headers, json=data, timeout=30)
                
                if response.status_code == 429:
                    wait_time = base_wait_time * (2 ** retry)
                    logger.warning(f"遇到请求限制(429)，等待{wait_time}秒后重试...")
                    time.sleep(wait_time)
                    continue
                    
                response.raise_for_status()
                
                result = response.json()
                if 'data' in result and len(result['data']) > 0:
                    return result['data'][0]['embedding']
                return None
                
            except Exception as e:
                if retry < max_retries - 1:
                    wait_time = base_wait_time * (2 ** retry)
                    logger.error(f"[embedding_sync]请求失败，等待{wait_time}秒后重试... 错误: {str(e)}", exc_info=True)
                    time.sleep(wait_time)
                else:
                    logger.critical(f"embedding请求失败: {str(e)}", exc_info=True)
                    return None
        
        logger.error("达到最大重试次数，embedding请求仍然失败")
        return None

    async def get_embedding(self, text: str, model: str = "BAAI/bge-m3") -> Union[list, None]:
        """异步方法：获取文本的embedding向量
        
        Args:
            text: 需要获取embedding的文本
            model: 使用的模型名称，默认为"BAAI/bge-m3"
            
        Returns:
            list: embedding向量，如果失败则返回None
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model,
            "input": text,
            "encoding_format": "float"
        }
        
        api_url = f"{self.base_url.rstrip('/')}/embeddings"
        logger.info(f"发送请求到URL: {api_url}")  # 记录请求的URL
        
        max_retries = 3
        base_wait_time = 15
        
        for retry in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(api_url, headers=headers, json=data) as response:
                        if response.status == 429:
                            wait_time = base_wait_time * (2 ** retry)
                            logger.warning(f"遇到请求限制(429)，等待{wait_time}秒后重试...")
                            await asyncio.sleep(wait_time)
                            continue
                            
                        response.raise_for_status()
                        
                        result = await response.json()
                        if 'data' in result and len(result['data']) > 0:
                            return result['data'][0]['embedding']
                        return None
                
            except Exception as e:
                if retry < max_retries - 1:
                    wait_time = base_wait_time * (2 ** retry)
                    logger.error(f"[embedding]请求失败，等待{wait_time}秒后重试... 错误: {str(e)}", exc_info=True)
                    await asyncio.sleep(wait_time)
                else:
                    logger.critical(f"embedding请求失败: {str(e)}", exc_info=True)
                    return None
        
        logger.error("达到最大重试次数，embedding请求仍然失败")
        return None
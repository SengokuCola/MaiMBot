import base64
import html
import os
import time
from dataclasses import dataclass
from typing import Dict, Optional

import requests

# 解析各种CQ码
# 包含CQ码类
import urllib3
from nonebot import get_driver
from urllib3.util import create_urllib3_context

from ..models.utils_model import LLM_request
from .config import global_config
from .mapper import emojimapper
from .utils_image import storage_emoji, storage_image
from .utils_user import get_user_nickname

driver = get_driver()
config = driver.config

# TLS1.3特殊处理 https://github.com/psf/requests/issues/6616
ctx = create_urllib3_context()
ctx.load_default_certs()
ctx.set_ciphers("AES128-GCM-SHA256")


class TencentSSLAdapter(requests.adapters.HTTPAdapter):
    def __init__(self, ssl_context=None, **kwargs):
        self.ssl_context = ssl_context
        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = urllib3.poolmanager.PoolManager(
            num_pools=connections, maxsize=maxsize,
            block=block, ssl_context=self.ssl_context)


@dataclass
class CQCode:
    """
    CQ码数据类，用于存储和处理CQ码
    
    属性:
        type: CQ码类型（如'image', 'at', 'face'等）
        params: CQ码的参数字典
        raw_code: 原始CQ码字符串
        translated_plain_text: 经过处理（如AI翻译）后的文本表示
    """
    type: str
    params: Dict[str, str]
    # raw_code: str
    group_id: int
    user_id: int
    group_name: str = ""
    user_nickname: str = ""
    translated_plain_text: Optional[str] = None
    reply_message: Dict = None  # 存储回复消息
    image_base64: Optional[str] = None
    _llm: Optional[LLM_request] = None

    def __post_init__(self):
        """初始化LLM实例"""
        self._llm = LLM_request(model=global_config.vlm, temperature=0.4, max_tokens=300)

    async def translate(self):
        """根据CQ码类型进行相应的翻译处理"""
        if self.type == 'text':
            self.translated_plain_text = self.params.get('text', '')
        elif self.type == 'image':
            if self.params.get('sub_type') == '0':
                self.translated_plain_text = await self.translate_image()
            else:
                self.translated_plain_text = await self.translate_emoji()
        elif self.type == 'at':
            user_nickname = get_user_nickname(self.params.get('qq', ''))
            if user_nickname:
                self.translated_plain_text = f"[@{user_nickname}]"
            else:
                self.translated_plain_text = "@某人"
        elif self.type == 'reply':
            self.translated_plain_text = await self.translate_reply()
        elif self.type == 'face':
            face_id = self.params.get('id', '')
            # self.translated_plain_text = f"[表情{face_id}]"
            self.translated_plain_text = f"[{emojimapper.get(int(face_id), '表情')}]"
        elif self.type == 'forward':
            self.translated_plain_text = await self.translate_forward()
        else:
            self.translated_plain_text = f"[{self.type}]"

    def get_img(self):
        '''
        headers = {
            'User-Agent': 'QQ/8.9.68.11565 CFNetwork/1220.1 Darwin/20.3.0',
            'Accept': 'image/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
        '''
        # 腾讯专用请求头配置
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.87 Safari/537.36',
            'Accept': 'text/html, application/xhtml xml, */*',
            'Accept-Encoding': 'gbk, GB2312',
            'Accept-Language': 'zh-cn',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Cache-Control': 'no-cache'
        }
        url = html.unescape(self.params['url'])

        # 暂时性修复multimedia 网站的SSL问题 Todo:修复ssl问题
        url.replace("https://multimedia.nt.qq.com.cn", "http://multimedia.nt.qq.com.cn")

        if not url.startswith(('http://', 'https://')):
            return None

        # 创建专用会话
        session = requests.session()
        session.adapters.pop("https://", None)
        session.mount("https://", TencentSSLAdapter(ctx))

        max_retries = 3
        for retry in range(max_retries):
            try:
                response = session.get(
                    url,
                    headers=headers,
                    timeout=15,
                    allow_redirects=True,
                    stream=True  # 流式传输避免大内存问题
                )

                # 腾讯服务器特殊状态码处理
                if response.status_code == 400 and 'multimedia.nt.qq.com.cn' in url:
                    return None

                if response.status_code != 200:
                    raise requests.exceptions.HTTPError(f"HTTP {response.status_code}")

                # 验证内容类型
                content_type = response.headers.get('Content-Type', '')
                if not content_type.startswith('image/'):
                    raise ValueError(f"非图片内容类型: {content_type}")

                # 转换为Base64
                image_base64 = base64.b64encode(response.content).decode('utf-8')
                self.image_base64 = image_base64
                return image_base64

            except (requests.exceptions.SSLError, requests.exceptions.HTTPError) as e:
                if retry == max_retries - 1:
                    print(f"\033[1;31m[致命错误]\033[0m 最终请求失败: {str(e)}")
                time.sleep(1.5 ** retry)  # 指数退避

            except Exception as e:
                print(f"\033[1;33m[未知错误]\033[0m {str(e)}")
                return None

        return None

    async def translate_emoji(self) -> str:
        """处理表情包类型的CQ码"""
        if 'url' not in self.params:
            return '[表情包]'
        base64_str = self.get_img()
        if base64_str:
            # 将 base64 字符串转换为字节类型
            image_bytes = base64.b64decode(base64_str)
            storage_emoji(image_bytes)
            return await self.get_emoji_description(base64_str)
        else:
            return '[表情包]'

    async def translate_image(self) -> str:
        """处理图片类型的CQ码，区分普通图片和表情包"""
        # 没有url，直接返回默认文本
        if 'url' not in self.params:
            return '[图片]'
        base64_str = self.get_img()
        if base64_str:
            image_bytes = base64.b64decode(base64_str)
            storage_image(image_bytes)
            return await self.get_image_description(base64_str)
        else:
            return '[图片]'

    async def get_emoji_description(self, image_base64: str) -> str:
        """调用AI接口获取表情包描述"""
        try:
            prompt = "这是一个表情包，请用简短的中文描述这个表情包传达的情感和含义。最多20个字。"
            # description, _ = self._llm.generate_response_for_image_sync(prompt, image_base64)
            description, _ = await self._llm.generate_response_for_image(prompt, image_base64)
            return f"[表情包：{description}]"
        except Exception as e:
            print(f"\033[1;31m[错误]\033[0m AI接口调用失败: {str(e)}")
            return "[表情包]"

    async def get_image_description(self, image_base64: str) -> str:
        """调用AI接口获取普通图片描述"""
        try:
            prompt = "请用中文描述这张图片的内容。如果有文字，请把文字都描述出来。并尝试猜测这个图片的含义。最多200个字。"
            # description, _ = self._llm.generate_response_for_image_sync(prompt, image_base64)
            description, _ = await self._llm.generate_response_for_image(prompt, image_base64)
            return f"[图片：{description}]"
        except Exception as e:
            print(f"\033[1;31m[错误]\033[0m AI接口调用失败: {str(e)}")
            return "[图片]"

    async def translate_forward(self) -> str:
        """处理转发消息"""
        try:
            if 'content' not in self.params:
                return '[转发消息]'

            # 解析content内容（需要先反转义）
            content = self.unescape(self.params['content'])
            # print(f"\033[1;34m[调试信息]\033[0m 转发消息内容: {content}")
            # 将字符串形式的列表转换为Python对象
            import ast
            try:
                messages = ast.literal_eval(content)
            except ValueError as e:
                print(f"\033[1;31m[错误]\033[0m 解析转发消息内容失败: {str(e)}")
                return '[转发消息]'

            # 处理每条消息
            formatted_messages = []
            for msg in messages:
                sender = msg.get('sender', {})
                nickname = sender.get('card') or sender.get('nickname', '未知用户')

                # 获取消息内容并使用Message类处理
                raw_message = msg.get('raw_message', '')
                message_array = msg.get('message', [])

                if message_array and isinstance(message_array, list):
                    # 检查是否包含嵌套的转发消息
                    for message_part in message_array:
                        if message_part.get('type') == 'forward':
                            content = '[转发消息]'
                            break
                    else:
                        # 处理普通消息
                        if raw_message:
                            from .message import Message
                            message_obj = Message(
                                user_id=msg.get('user_id', 0),
                                message_id=msg.get('message_id', 0),
                                raw_message=raw_message,
                                plain_text=raw_message,
                                group_id=msg.get('group_id', 0)
                            )
                            await message_obj.initialize()
                            content = message_obj.processed_plain_text
                        else:
                            content = '[空消息]'
                else:
                    # 处理普通消息
                    if raw_message:
                        from .message import Message
                        message_obj = Message(
                            user_id=msg.get('user_id', 0),
                            message_id=msg.get('message_id', 0),
                            raw_message=raw_message,
                            plain_text=raw_message,
                            group_id=msg.get('group_id', 0)
                        )
                        await message_obj.initialize()
                        content = message_obj.processed_plain_text
                    else:
                        content = '[空消息]'

                formatted_msg = f"{nickname}: {content}"
                formatted_messages.append(formatted_msg)

            # 合并所有消息
            combined_messages = '\n'.join(formatted_messages)
            print(f"\033[1;34m[调试信息]\033[0m 合并后的转发消息: {combined_messages}")
            return f"[转发消息:\n{combined_messages}]"

        except Exception as e:
            print(f"\033[1;31m[错误]\033[0m 处理转发消息失败: {str(e)}")
            return '[转发消息]'

    async def translate_reply(self) -> str:
        """处理回复类型的CQ码"""

        # 创建Message对象
        from .message import Message
        if self.reply_message == None:
            # print(f"\033[1;31m[错误]\033[0m 回复消息为空")
            return '[回复某人消息]'

        if self.reply_message.sender.user_id:
            message_obj = Message(
                user_id=self.reply_message.sender.user_id,
                message_id=self.reply_message.message_id,
                raw_message=str(self.reply_message.message),
                group_id=self.group_id
            )
            await message_obj.initialize()
            if message_obj.user_id == global_config.BOT_QQ:
                return f"[回复 {global_config.BOT_NICKNAME} 的消息: {message_obj.processed_plain_text}]"
            else:
                return f"[回复 {self.reply_message.sender.nickname} 的消息: {message_obj.processed_plain_text}]"

        else:
            print("\033[1;31m[错误]\033[0m 回复消息的sender.user_id为空")
            return '[回复某人消息]'

    @staticmethod
    def unescape(text: str) -> str:
        """反转义CQ码中的特殊字符"""
        return text.replace('&#44;', ',') \
            .replace('&#91;', '[') \
            .replace('&#93;', ']') \
            .replace('&amp;', '&')

    @staticmethod
    def create_emoji_cq(file_path: str) -> str:
        """
        创建表情包CQ码
        Args:
            file_path: 本地表情包文件路径
        Returns:
            表情包CQ码字符串
        """
        # 确保使用绝对路径
        abs_path = os.path.abspath(file_path)
        # 转义特殊字符
        escaped_path = abs_path.replace('&', '&amp;') \
            .replace('[', '&#91;') \
            .replace(']', '&#93;') \
            .replace(',', '&#44;')
        # 生成CQ码，设置sub_type=1表示这是表情包
        return f"[CQ:image,file=file:///{escaped_path},sub_type=1]"


class CQCode_tool:
    @staticmethod
    async def cq_from_dict_to_class(cq_code: Dict, reply: Optional[Dict] = None) -> CQCode:
        """
        将CQ码字典转换为CQCode对象
        
        Args:
            cq_code: CQ码字典
            reply: 回复消息的字典（可选）
            
        Returns:
            CQCode对象
        """
        # 处理字典形式的CQ码
        # 从cq_code字典中获取type字段的值,如果不存在则默认为'text'
        cq_type = cq_code.get('type', 'text')
        params = {}
        if cq_type == 'text':
            params['text'] = cq_code.get('data', {}).get('text', '')
        else:
            params = cq_code.get('data', {})

        instance = CQCode(
            type=cq_type,
            params=params,
            group_id=0,
            user_id=0,
            reply_message=reply
        )

        # 进行翻译处理
        await instance.translate()
        return instance

    @staticmethod
    def create_reply_cq(message_id: int) -> str:
        """
        创建回复CQ码
        Args:
            message_id: 回复的消息ID
        Returns:
            回复CQ码字符串
        """
        return f"[CQ:reply,id={message_id}]"


cq_code_tool = CQCode_tool()

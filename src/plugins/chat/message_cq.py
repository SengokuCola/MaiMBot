import time
from dataclasses import dataclass
from typing import Dict, Optional

import urllib3

from .cq_code import cq_code_tool
from .utils_cq import parse_cq_code
from .utils_user import get_groupname
from .message_base import Seg, GroupInfo, UserInfo, BaseMessageInfo, MessageBase
# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#这个类是消息数据类，用于存储和管理消息数据。
#它定义了消息的属性，包括群组ID、用户ID、消息ID、原始消息内容、纯文本内容和时间戳。
#它还定义了两个辅助属性：keywords用于提取消息的关键词，is_plain_text用于判断消息是否为纯文本。

@dataclass
class MessageCQ(MessageBase):
    """QQ消息基类，继承自MessageBase
    
    最小必要参数:
    - message_id: 消息ID
    - user_id: 发送者/接收者ID
    - platform: 平台标识（默认为"qq"）
    """
    def __init__(
        self,
        message_id: int,
        user_info: UserInfo,
        group_info: Optional[GroupInfo] = None,
        platform: str = "qq"
    ):
        # 构造基础消息信息
        message_info = BaseMessageInfo(
            platform=platform,
            message_id=message_id,
            time=int(time.time()),
            group_info=group_info,
            user_info=user_info
        )
        # 调用父类初始化，message_segment 由子类设置
        super().__init__(
            message_info=message_info,
            message_segment=None,
            raw_message=None
        )

@dataclass
class MessageRecvCQ(MessageCQ):
    """QQ接收消息类，用于解析raw_message到Seg对象"""
    
    def __init__(
        self,
        message_id: int,
        user_info: UserInfo,
        raw_message: str,
        group_info: Optional[GroupInfo] = None,
        platform: str = "qq",
        reply_message: Optional[Dict] = None,
    ):
        # 调用父类初始化
        super().__init__(message_id, user_info, group_info, platform)
        
        # 私聊消息不携带group_info
        if group_info is None:
            pass

        elif group_info.group_name is None:
            group_info.group_name = get_groupname(group_info.group_id)
        
        # 解析消息段
        self.message_segment = self._parse_message(raw_message, reply_message)
        self.raw_message = raw_message

    def _parse_message(self, message: str, reply_message: Optional[Dict] = None) -> Seg:
        """解析消息内容为Seg对象"""
        cq_code_dict_list = []
        segments = []
        
        start = 0
        while True:
            cq_start = message.find('[CQ:', start)
            if cq_start == -1:
                if start < len(message):
                    text = message[start:].strip()
                    if text:
                        cq_code_dict_list.append(parse_cq_code(text))
                break

            if cq_start > start:
                text = message[start:cq_start].strip()
                if text:
                    cq_code_dict_list.append(parse_cq_code(text))

            cq_end = message.find(']', cq_start)
            if cq_end == -1:
                text = message[cq_start:].strip()
                if text:
                    cq_code_dict_list.append(parse_cq_code(text))
                break

            cq_code = message[cq_start:cq_end + 1]
            cq_code_dict_list.append(parse_cq_code(cq_code))
            start = cq_end + 1

        # 转换CQ码为Seg对象
        for code_item in cq_code_dict_list:
            message_obj = cq_code_tool.cq_from_dict_to_class(code_item,msg=self,reply=reply_message)
            if message_obj.translated_segments:
                segments.append(message_obj.translated_segments)

        # 如果只有一个segment，直接返回
        if len(segments) == 1:
            return segments[0]
        
        # 否则返回seglist类型的Seg
        return Seg(type='seglist', data=segments)

    def to_dict(self) -> Dict:
        """转换为字典格式，包含所有必要信息"""
        base_dict = super().to_dict()
        return base_dict

@dataclass
class MessageSendCQ(MessageCQ):
    """QQ发送消息类，用于将Seg对象转换为raw_message"""
    
    def __init__(
        self,
        data: Dict
    ):
        # 调用父类初始化
        message_info = BaseMessageInfo.from_dict(data.get('message_info', {}))
        message_segment = Seg.from_dict(data.get('message_segment', {}))
        super().__init__(
            message_info.message_id, 
            message_info.user_info, 
            message_info.group_info if message_info.group_info else None, 
            message_info.platform
            )
        
        self.message_segment = message_segment
        self.raw_message = self._generate_raw_message()

    def _generate_raw_message(self, ) -> str:
        """将Seg对象转换为raw_message"""
        segments = []

        # 处理消息段
        if self.message_segment.type == 'seglist':
            for seg in self.message_segment.data:
                segments.append(self._seg_to_cq_code(seg))
        else:
            segments.append(self._seg_to_cq_code(self.message_segment))

        return ''.join(segments)

    def _seg_to_cq_code(self, seg: Seg) -> str:
        """将单个Seg对象转换为CQ码字符串"""
        if seg.type == 'text':
            return str(seg.data)
        elif seg.type == 'image':
            return cq_code_tool.create_image_cq_base64(seg.data)
        elif seg.type == 'emoji':
            return cq_code_tool.create_emoji_cq_base64(seg.data)
        elif seg.type == 'at':
            return f"[CQ:at,qq={seg.data}]"
        elif seg.type == 'reply':
            return cq_code_tool.create_reply_cq(int(seg.data))
        else:
            return f"[{seg.data}]"


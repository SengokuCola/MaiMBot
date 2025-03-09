import random
import time
from typing import List, Optional, Tuple, Union

from nonebot import get_driver

from ...common.database import Database
from ..models.utils_model import LLM_request
from .config import global_config
from .message import Message
from .prompt_builder import prompt_builder
from .relationship_manager import relationship_manager
from .utils import process_llm_response

driver = get_driver()
config = driver.config


class ResponseGenerator:
    def __init__(self):
        self.model_r1 = LLM_request(model=global_config.llm_reasoning, temperature=0.7,max_tokens=1000,stream=True)
        self.model_v3 = LLM_request(model=global_config.llm_normal, temperature=0.7,max_tokens=1000)
        self.model_r1_distill = LLM_request(model=global_config.llm_reasoning_minor, temperature=0.7,max_tokens=1000)
        self.model_v25 = LLM_request(model=global_config.llm_normal_minor, temperature=0.7,max_tokens=1000)
        self.db = Database.get_instance()
        self.current_model_type = 'r1'  # 默认使用 R1

    async def generate_response(self, message: Message) -> Optional[Union[str, List[str]]]:
        """根据当前模型类型选择对应的生成函数"""
        # 从global_config中获取模型概率值并选择模型
        rand = random.random()
        if rand < global_config.MODEL_R1_PROBABILITY:
            self.current_model_type = 'r1'
            current_model = self.model_r1
        elif rand < global_config.MODEL_R1_PROBABILITY + global_config.MODEL_V3_PROBABILITY:
            self.current_model_type = 'v3'
            current_model = self.model_v3
        else:
            self.current_model_type = 'r1_distill'
            current_model = self.model_r1_distill

        print(f"+++++++++++++++++{global_config.BOT_NICKNAME}{self.current_model_type}思考中+++++++++++++++++")
        
        model_response = await self._generate_response_with_model(message, current_model)
        raw_content=model_response
        
        if model_response:
            print(f'{global_config.BOT_NICKNAME}的回复是：{model_response}')
            model_response = await self._process_response(model_response)
            if model_response:

                return model_response ,raw_content
        return None,raw_content

    async def _generate_response_with_model(self, message: Message, model: LLM_request) -> Optional[str]:
        """使用指定的模型生成回复"""
        sender_name = message.user_nickname or f"用户{message.user_id}"
        if message.user_cardname:
            sender_name=f"[({message.user_id}){message.user_nickname}]{message.user_cardname}"
        
        # 获取关系值
        relationship_value = relationship_manager.get_relationship(message.user_id).relationship_value if relationship_manager.get_relationship(message.user_id) else 0.0
        if relationship_value != 0.0:
            # print(f"\033[1;32m[关系管理]\033[0m 回复中_当前关系值: {relationship_value}")
            pass
        
        # 构建prompt
        prompt, prompt_check = await prompt_builder._build_prompt(
            message_txt=message.processed_plain_text,
            sender_name=sender_name,
            relationship_value=relationship_value,
            group_id=message.group_id
        )

        # 读空气模块 简化逻辑，先停用
        # if global_config.enable_kuuki_read:
        #     content_check, reasoning_content_check = await self.model_v3.generate_response(prompt_check)
        #     print(f"\033[1;32m[读空气]\033[0m 读空气结果为{content_check}")
        #     if 'yes' not in content_check.lower() and random.random() < 0.3:
        #         self._save_to_db(
        #             message=message,
        #             sender_name=sender_name,
        #             prompt=prompt,
        #             prompt_check=prompt_check,
        #             content="",
        #             content_check=content_check,
        #             reasoning_content="",
        #             reasoning_content_check=reasoning_content_check
        #         )
        #         return None

        # 生成回复
        try:
            content, reasoning_content = await model.generate_response(prompt)
        except Exception as e:
            print(f"生成回复时出错: {e}")
            return None
        
        # 保存到数据库
        self._save_to_db(
            message=message,
            sender_name=sender_name,
            prompt=prompt,
            prompt_check=prompt_check,
            content=content,
            # content_check=content_check if global_config.enable_kuuki_read else "",
            reasoning_content=reasoning_content,
            # reasoning_content_check=reasoning_content_check if global_config.enable_kuuki_read else ""
        )
        
        return content

    # def _save_to_db(self, message: Message, sender_name: str, prompt: str, prompt_check: str,
    #                 content: str, content_check: str, reasoning_content: str, reasoning_content_check: str):
    def _save_to_db(self, message: Message, sender_name: str, prompt: str, prompt_check: str,
                content: str, reasoning_content: str,):
        """保存对话记录到数据库"""
        self.db.db.reasoning_logs.insert_one({
            'time': time.time(),
            'group_id': message.group_id,
            'user': sender_name,
            'message': message.processed_plain_text,
            'model': self.current_model_type,
            # 'reasoning_check': reasoning_content_check,
            # 'response_check': content_check,
            'reasoning': reasoning_content,
            'response': content,
            'prompt': prompt,
            'prompt_check': prompt_check
        })

    async def _get_emotion_tags(self, content: str) -> List[str]:
        """提取情感标签"""
        try:
            prompt = f'''请根据他的发言，从"happy,angry,sad,surprised,disgusted,fearful,neutral"中选出最匹配的1个情感标签并输出
            只输出标签就好，不要输出其他内容:
            性格：{global_config.PROMPT_PERSONALITY[0]}
            发言：{content}
            输出：
            '''
            content, _ = await self.model_v25.generate_response(prompt)
            content=content.strip()
            if content in ['happy','angry','sad','surprised','disgusted','fearful','neutral']:
                return [content]
            else:
                return ["neutral"]
            
        except Exception as e:
            print(f"获取情感标签时出错: {e}")
            return ["neutral"]
    
    async def _process_response(self, content: str) -> Tuple[List[str], List[str]]:
        """处理响应内容，返回处理后的内容和情感标签"""
        if not content:
            return None, []
        
        processed_response = process_llm_response(content)
        
        return processed_response


class InitiativeMessageGenerate:
    def __init__(self):
        self.db = Database.get_instance()
        self.model_r1 = LLM_request(model=global_config.llm_reasoning, temperature=0.7)
        self.model_v3 = LLM_request(model=global_config.llm_normal, temperature=0.7)
        self.model_r1_distill = LLM_request(
            model=global_config.llm_reasoning_minor, temperature=0.7
        )

    def gen_response(self, message: Message):
        topic_select_prompt, dots_for_select, prompt_template = (
            prompt_builder._build_initiative_prompt_select(message.group_id)
        )
        content_select, reasoning = self.model_v3.generate_response(topic_select_prompt)
        print(f"[DEBUG] {content_select} {reasoning}")
        topics_list = [dot[0] for dot in dots_for_select]
        if content_select:
            if content_select in topics_list:
                select_dot = dots_for_select[topics_list.index(content_select)]
            else:
                return None
        else:
            return None
        prompt_check, memory = prompt_builder._build_initiative_prompt_check(
            select_dot[1], prompt_template
        )
        content_check, reasoning_check = self.model_v3.generate_response(prompt_check)
        print(f"[DEBUG] {content_check} {reasoning_check}")
        if "yes" not in content_check.lower():
            return None
        prompt = prompt_builder._build_initiative_prompt(
            select_dot, prompt_template, memory
        )
        content, reasoning = self.model_r1.generate_response_async(prompt)
        print(f"[DEBUG] {content} {reasoning}")
        return content

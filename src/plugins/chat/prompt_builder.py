import random
import time
from typing import Optional, List
from loguru import logger

from ...common.database import Database
from ..memory_system.memory import hippocampus, memory_graph
from ..moods.moods import MoodManager
from ..schedule.schedule_generator import bot_schedule
from .config import global_config
from .utils import get_embedding, get_recent_group_detailed_plain_text
from .chat_stream import chat_manager


class PromptBuilder:
    def __init__(self):
        self.prompt_built = ''
        self.activate_messages = ''
        self.db = Database.get_instance()

    async def _build_prompt(self,
                            message_txt: str,
                            sender_name: str = "某人",
                            relationship_value: float = 0.0,
                            stream_id: Optional[int] = None) -> tuple[str, str]:
        """构建prompt
        
        Args:
            message_txt: 消息文本
            sender_name: 发送者昵称
            relationship_value: 关系值
            stream_id: 消息上下文ID
            
        Returns:
            str: 构建好的prompt
        """

        # 开始构建prompt
        role_core = await self._build_role_core_prompt(message_txt, sender_name, relationship_value, stream_id)
        chat_context = await self._build_chat_context_prompt(message_txt, sender_name, relationship_value, stream_id)
        constraints = await self._build_constraints_prompt(message_txt, sender_name, relationship_value, stream_id)

        # 合并prompt
        prompt = '\n\n'.join((
            '# 角色核心设定\n* ' + '\n* '.join(role_core),
            '# 对话背景\n* ' + '\n* '.join(chat_context),
            '# 要求\n* ' + '\n* '.join(constraints),
            '# 目标: 发言或回复用户'
        ))

        '''读空气prompt处理 [未启用]'''
        # activate_prompt_chec
        # extra_check_info = f"请注意把握k = f"以上是群里正在进行的聊天，昵称为 '{sender_name}' 的用户说的:{message_txt}。引起了你的注意,你和他{relation_prompt}，你想要{relation_prompt_2}，但是这不一定是合适的时机，请你决定是否要回应这条消息。"
        #         #
        #         # prompt_personality_check = ''群里的聊天内容的基础上，综合群内的氛围，例如，和{global_config.BOT_NICKNAME}相关的话题要积极回复,如果是at自己的消息一定要回复，如果自己正在和别人聊天一定要回复，其他话题如果合适搭话也可以回复，如果认为应该回复请输出yes，否则输出no，请注意是决定是否需要回复，而不是编写回复内容，除了yes和no不要输出任何回复内容。"
        # if personality_choice < probability_1:  # 第一种人格
        #     prompt_personality_check = f'''你的网名叫{global_config.BOT_NICKNAME}，{personality[0]}, 你正在浏览qq群，{promt_info_prompt} {activate_prompt_check} {extra_check_info}'''
        # elif personality_choice < probability_1 + probability_2:  # 第二种人格
        #     prompt_personality_check = f'''你的网名叫{global_config.BOT_NICKNAME}，{personality[1]}, 你正在浏览qq群，{promt_info_prompt} {activate_prompt_check} {extra_check_info}'''
        # else:  # 第三种人格
        #     prompt_personality_check = f'''你的网名叫{global_config.BOT_NICKNAME}，{personality[2]}, 你正在浏览qq群，{promt_info_prompt} {activate_prompt_check} {extra_check_info}'''
        # prompt_check_if_response = f"{prompt_info}\n{prompt_date}\n{chat_talking_prompt}\n{prompt_personality_check}"
        prompt_check_if_response = ''

        return prompt, prompt_check_if_response

    async def _build_role_core_prompt(self,
                                      message_txt: str,
                                      sender_name: str = "某人",
                                      relationship_value: float = 0.0,
                                      stream_id: Optional[int] = None) -> List[str]:
        role_core_prompt = []

        # 人格选择
        personality = random.choices(global_config.PROMPT_PERSONALITY, global_config.PERSONALITY_PROBS)[0]
        role_core_prompt.append(personality)

        role_core_prompt.append(f'你的网名叫{global_config.BOT_NICKNAME}')
        if len(global_config.BOT_ALIAS_NAMES) > 0:
            role_core_prompt.append(f'别人也叫你:{"/".join(global_config.BOT_ALIAS_NAMES)}')

        # 心情
        role_core_prompt.append(MoodManager.get_instance().get_prompt())

        # 日程构建
        current_date = time.strftime("%Y-%m-%d", time.localtime())
        current_time = time.strftime("%H:%M:%S", time.localtime())
        bot_schedule_now_time, bot_schedule_now_activity = bot_schedule.get_current_task()
        schedule_str = '\n'.join([f"\t- {time} {activity}"
                                for time, activity in bot_schedule.today_schedule.items()])
        role_core_prompt.append(f'今天是{current_date}，现在是{current_time}，你今天的日程是：\n{schedule_str}')
        role_core_prompt.append(f'你现在正在{bot_schedule_now_activity}')

        # 知识构建 [未启用]
        start_time = time.time()
        knowledge_prompt = ''
        promt_info_prompt = ''
        knowledge_prompt = await self.get_prompt_info(message_txt, threshold=0.5)
        if knowledge_prompt:
            knowledge_prompt = f'''你有以下这些[知识]：{knowledge_prompt}请你记住上面的[
            知识]，之后可能会用到-'''
        end_time = time.time()
        logger.debug(f"知识检索耗时: {(end_time - start_time):.3f}秒")

        # 中文高手(新加的好玩功能)
        prompt_ger = ''
        if random.random() < 0.04:
            prompt_ger += '你喜欢用倒装句'
        if random.random() < 0.02:
            prompt_ger += '你喜欢用反问句'
        if random.random() < 0.01:
            prompt_ger += '你喜欢用文言文'
        if len(prompt_ger) > 0:
            role_core_prompt.append(prompt_ger)

        return role_core_prompt

    async def _build_chat_context_prompt(self,
                                         message_txt: str,
                                         sender_name: str = "某人",
                                         relationship_value: float = 0.0,
                                         stream_id: Optional[int] = None) -> List[str]:
        chat_context_prompt = []

        # 获取聊天上下文
        chat_in_group = True
        chat_talking_prompt = ''
        if stream_id:
            chat_context: List[str] = get_recent_group_detailed_plain_text(self.db, stream_id,
                                                                           limit=global_config.MAX_CONTEXT_SIZE,
                                                                           combine=False)
            chat_stream = chat_manager.get_stream(stream_id)
            if chat_stream.group_info:
                chat_talking_prompt = "以下是群里正在聊的内容：\n\t- "
            else:
                chat_in_group = False
                chat_talking_prompt = f"以下是你正在和{sender_name}私聊的内容：\n"
                # print(f"\033[1;34m[调试]\033[0m 已从数据库获取群 {stream_id} 的消息记录:{chat_talking_prompt}")
            chat_talking_prompt += "\n\t- ".join(chat_context)
        chat_context_prompt.append(chat_talking_prompt)

        # [未启用]
        if chat_in_group:
            prompt_in_group = f"你正在浏览{chat_stream.platform}群"
        else:
            prompt_in_group = f"你正在{chat_stream.platform}上和{sender_name}私聊"

        # 使用新的记忆获取方法
        memory_prompt = await self._build_memory_prompt(message_txt)
        if len(memory_prompt) > 0:
            chat_context_prompt.append(memory_prompt)


        # 关系 [未启用]
        if 0 > 30:
            relation_prompt = "关系特别特别好，你很喜欢喜欢他"
            relation_prompt_2 = "热情发言或者回复"
        elif 0 < -20:
            relation_prompt = "关系很差，你很讨厌他"
            relation_prompt_2 = "骂他"
        else:
            relation_prompt = "关系一般"
            relation_prompt_2 = "发言或者回复"

        # 激活prompt构建
        activate_prompt = ''
        if chat_in_group:
            activate_prompt = f"现在昵称为 '{sender_name}' 的用户说的:{message_txt}。引起了你的注意,你和ta{relation_prompt},你想要{relation_prompt_2}。"
        else:
            activate_prompt = f"现在昵称为 '{sender_name}' 的用户说的:{message_txt}。引起了你的注意,你和ta{relation_prompt},你想要{relation_prompt_2}。"
        chat_context_prompt.append(activate_prompt)

        return chat_context_prompt

    async def _build_memory_prompt(self, message_txt: str) -> str:
        memory_prompt = ''
        start_time = time.time()

        # 调用 hippocampus 的 get_relevant_memories 方法
        relevant_memories = await hippocampus.get_relevant_memories(
            text=message_txt,
            max_topics=5,
            similarity_threshold=0.4,
            max_memory_num=5
        )

        if relevant_memories:
            # 格式化记忆内容
            memory_items = []
            for memory in relevant_memories:
                memory_items.append(f"\t- 关于「{memory['topic']}」的记忆：{memory['content']}")

            memory_prompt = "看到这些聊天，你想起来：\n" + "\n".join(memory_items)

            # 打印调试信息
            logger.debug("[记忆检索]找到以下相关记忆：")
            for memory in relevant_memories:
                logger.debug(f"- 主题「{memory['topic']}」[相似度: {memory['similarity']:.2f}]: {memory['content']}")

        end_time = time.time()
        logger.info(f"回忆耗时: {(end_time - start_time):.3f}秒")

        return memory_prompt

    async def _build_constraints_prompt(self,
                                        message_txt: str,
                                        sender_name: str = "某人",
                                        relationship_value: float = 0.0,
                                        stream_id: Optional[int] = None) -> List[str]:
        constraints_prompt = []

        keyword_prompt = self._build_keywords_reaction_prompt(message_txt)
        if len(keyword_prompt) > 0:
            constraints_prompt.append(keyword_prompt)

        # 额外信息要求
        constraints_prompt.append('请给出日常且口语化的回复，平淡一些，尽量简短一些，尤其注意在没明确提到时不要过多提及自身的背景.')
        constraints_prompt.append('不要直接回复别人发的表情包.')
        constraints_prompt.append('请注意把握群里的聊天内容，不要刻意突出自身学科背景，不要回复的太有条理，可以有个性.')
        constraints_prompt.append('只输出回复内容，不要输出其他任何内容，包括前后缀、冒号、引号、括号、表情等.')
        constraints_prompt.append('请表现你自己的见解和观点，不要一昧迎合，可以表现个性，尽量简短一些.')

        return constraints_prompt

    def _build_keywords_reaction_prompt(self, message_txt: str) -> str:
        """关键词检测与反应

        Returns: 没命中返回空字符串；命中时返回prompt格式如下：
        群聊的发言命中了预设规则，你需要按照要求的反应回复:
            - 命中关键字: 'test', '测试'; 回复要求: '回答测试成功'
            - 命中关键字: '人机'; 回复要求: '否定这一事实，攻击或反问他。注意，只有认为你是机器人才回复，否则不要否认'
        """

        # 获取当前规则 (实际命中的关键词-反应)
        triggered_keyword_prompt_arr = []
        lower_msg_text = message_txt.lower()
        for rule in global_config.keywords_reaction_rules:
            matched_kws = [kw for kw in rule.get("keywords", []) if kw in lower_msg_text]
            if not matched_kws:
                continue

            reaction = rule.get("reaction", "")
            logger.info(f"检测到关键词：{matched_kws}，触发反应：{reaction}")
            triggered_keyword_prompt_arr.append((matched_kws, reaction))

        keywords_reaction_prompt = ''
        if len(triggered_keyword_prompt_arr) > 0:
            keywords_reaction_prompt = '群聊的发言命中了预设规则，你需要按照要求的反应回复:\n' \
                                       + "\n".join(
                f'\t - 命中关键字: {", ".join(map(repr, matched_kws))}; 回复要求: {reaction!r}' for
                matched_kws, reaction in triggered_keyword_prompt_arr)

        return keywords_reaction_prompt

    def _build_initiative_prompt_select(self, group_id, probability_1=0.8, probability_2=0.1):
        current_date = time.strftime("%Y-%m-%d", time.localtime())
        current_time = time.strftime("%H:%M:%S", time.localtime())
        bot_schedule_now_time, bot_schedule_now_activity = bot_schedule.get_current_task()
        prompt_date = f'''今天是{current_date}，现在是{current_time}，你今天的日程是：\n{bot_schedule.today_schedule}\n你现在正在{bot_schedule_now_activity}\n'''

        chat_talking_prompt = ''
        if group_id:
            chat_talking_prompt = get_recent_group_detailed_plain_text(self.db, group_id,
                                                                       limit=global_config.MAX_CONTEXT_SIZE,
                                                                       combine=True)

        chat_talking_prompt = f"以下是群里正在聊天的内容：\n{chat_talking_prompt}"
        # print(f"\033[1;34m[调试]\033[0m 已从数据库获取群 {group_id} 的消息记录:{chat_talking_prompt}")

        # 获取主动发言的话题
        all_nodes = memory_graph.dots
        all_nodes = filter(lambda dot: len(dot[1]['memory_items']) > 3, all_nodes)
        nodes_for_select = random.sample(all_nodes, 5)
        topics = [info[0] for info in nodes_for_select]
        infos = [info[1] for info in nodes_for_select]

        # 激活prompt构建
        activate_prompt = ''
        activate_prompt = "以上是群里正在进行的聊天。"
        personality = global_config.PROMPT_PERSONALITY
        prompt_personality = ''
        personality_choice = random.random()
        if personality_choice < probability_1:  # 第一种人格
            prompt_personality = f'''{activate_prompt}你的网名叫{global_config.BOT_NICKNAME}，{personality[0]}'''
        elif personality_choice < probability_1 + probability_2:  # 第二种人格
            prompt_personality = f'''{activate_prompt}你的网名叫{global_config.BOT_NICKNAME}，{personality[1]}'''
        else:  # 第三种人格
            prompt_personality = f'''{activate_prompt}你的网名叫{global_config.BOT_NICKNAME}，{personality[2]}'''

        topics_str = ','.join(f"\"{topics}\"")
        prompt_for_select = f"你现在想在群里发言，回忆了一下，想到几个话题，分别是{topics_str}，综合当前状态以及群内气氛，请你在其中选择一个合适的话题，注意只需要输出话题，除了话题什么也不要输出(双引号也不要输出)"

        prompt_initiative_select = f"{prompt_date}\n{prompt_personality}\n{prompt_for_select}"
        prompt_regular = f"{prompt_date}\n{prompt_personality}"

        return prompt_initiative_select, nodes_for_select, prompt_regular

    def _build_initiative_prompt_check(self, selected_node, prompt_regular):
        memory = random.sample(selected_node['memory_items'], 3)
        memory = '\n'.join(memory)
        prompt_for_check = f"{prompt_regular}你现在想在群里发言，回忆了一下，想到一个话题,是{selected_node['concept']}，关于这个话题的记忆有\n{memory}\n，以这个作为主题发言合适吗？请在把握群里的聊天内容的基础上，综合群内的氛围，如果认为应该发言请输出yes，否则输出no，请注意是决定是否需要发言，而不是编写回复内容，除了yes和no不要输出任何回复内容。"
        return prompt_for_check, memory

    def _build_initiative_prompt(self, selected_node, prompt_regular, memory):
        prompt_for_initiative = f"{prompt_regular}你现在想在群里发言，回忆了一下，想到一个话题,是{selected_node['concept']}，关于这个话题的记忆有\n{memory}\n，请在把握群里的聊天内容的基础上，综合群内的氛围，以日常且口语化的口吻，简短且随意一点进行发言，不要说的太有条理，可以有个性。记住不要输出多余内容(包括前后缀，冒号和引号，括号，表情等)"
        return prompt_for_initiative

    async def get_prompt_info(self, message: str, threshold: float):
        related_info = ''
        logger.debug(f"获取知识库内容，元消息：{message[:30]}...，消息长度: {len(message)}")
        embedding = await get_embedding(message)
        related_info += self.get_info_from_db(embedding, threshold=threshold)

        return related_info

    def get_info_from_db(self, query_embedding: list, limit: int = 1, threshold: float = 0.5) -> str:
        if not query_embedding:
            return ''
        # 使用余弦相似度计算
        pipeline = [
            {
                "$addFields": {
                    "dotProduct": {
                        "$reduce": {
                            "input": {"$range": [0, {"$size": "$embedding"}]},
                            "initialValue": 0,
                            "in": {
                                "$add": [
                                    "$$value",
                                    {"$multiply": [
                                        {"$arrayElemAt": ["$embedding", "$$this"]},
                                        {"$arrayElemAt": [query_embedding, "$$this"]}
                                    ]}
                                ]
                            }
                        }
                    },
                    "magnitude1": {
                        "$sqrt": {
                            "$reduce": {
                                "input": "$embedding",
                                "initialValue": 0,
                                "in": {"$add": ["$$value", {"$multiply": ["$$this", "$$this"]}]}
                            }
                        }
                    },
                    "magnitude2": {
                        "$sqrt": {
                            "$reduce": {
                                "input": query_embedding,
                                "initialValue": 0,
                                "in": {"$add": ["$$value", {"$multiply": ["$$this", "$$this"]}]}
                            }
                        }
                    }
                }
            },
            {
                "$addFields": {
                    "similarity": {
                        "$divide": ["$dotProduct", {"$multiply": ["$magnitude1", "$magnitude2"]}]
                    }
                }
            },
            {
                "$match": {
                    "similarity": {"$gte": threshold}  # 只保留相似度大于等于阈值的结果
                }
            },
            {"$sort": {"similarity": -1}},
            {"$limit": limit},
            {"$project": {"content": 1, "similarity": 1}}
        ]

        results = list(self.db.db.knowledges.aggregate(pipeline))
        # print(f"\033[1;34m[调试]\033[0m获取知识库内容结果: {results}")

        if not results:
            return ''

        # 返回所有找到的内容，用换行分隔
        return '\n'.join(str(result['content']) for result in results)


prompt_builder = PromptBuilder()

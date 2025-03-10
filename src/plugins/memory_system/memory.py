# -*- coding: utf-8 -*-
import datetime
import math
import random
import time

import jieba
import networkx as nx

from loguru import logger
from ...common.database import Database  # 使用正确的导入语法
from ..chat.config import global_config
from ..chat.utils import (
    calculate_information_content,
    cosine_similarity,
    get_cloest_chat_from_db,
    text_to_vector,
)
from ..models.utils_model import LLM_request


class Memory_graph:
    def __init__(self):
        self.G = nx.Graph()  # 使用 networkx 的图结构
        self.db = Database.get_instance()

    def connect_dot(self, concept1, concept2):
        # 如果边已存在，增加 strength
        if self.G.has_edge(concept1, concept2):
            self.G[concept1][concept2]['strength'] = self.G[concept1][concept2].get('strength', 1) + 1
        else:
            # 如果是新边，初始化 strength 为 1
            self.G.add_edge(concept1, concept2, strength=1)

    def add_dot(self, concept, memory):
        if concept in self.G:
            # 如果节点已存在，将新记忆添加到现有列表中
            if 'memory_items' in self.G.nodes[concept]:
                if not isinstance(self.G.nodes[concept]['memory_items'], list):
                    # 如果当前不是列表，将其转换为列表
                    self.G.nodes[concept]['memory_items'] = [self.G.nodes[concept]['memory_items']]
                self.G.nodes[concept]['memory_items'].append(memory)
            else:
                self.G.nodes[concept]['memory_items'] = [memory]
        else:
            # 如果是新节点，创建新的记忆列表
            self.G.add_node(concept, memory_items=[memory])

    def get_dot(self, concept):
        # 检查节点是否存在于图中
        if concept in self.G:
            # 从图中获取节点数据
            node_data = self.G.nodes[concept]
            return concept, node_data
        return None

    def get_related_item(self, topic, depth=1):
        if topic not in self.G:
            return [], []

        first_layer_items = []
        second_layer_items = []

        # 获取相邻节点
        neighbors = list(self.G.neighbors(topic))

        # 获取当前节点的记忆项
        node_data = self.get_dot(topic)
        if node_data:
            concept, data = node_data
            if 'memory_items' in data:
                memory_items = data['memory_items']
                if isinstance(memory_items, list):
                    first_layer_items.extend(memory_items)
                else:
                    first_layer_items.append(memory_items)

        # 只在depth=2时获取第二层记忆
        if depth >= 2:
            # 获取相邻节点的记忆项
            for neighbor in neighbors:
                node_data = self.get_dot(neighbor)
                if node_data:
                    concept, data = node_data
                    if 'memory_items' in data:
                        memory_items = data['memory_items']
                        if isinstance(memory_items, list):
                            second_layer_items.extend(memory_items)
                        else:
                            second_layer_items.append(memory_items)

        return first_layer_items, second_layer_items

    @property
    def dots(self):
        # 返回所有节点对应的 Memory_dot 对象
        return [self.get_dot(node) for node in self.G.nodes()]

    def forget_topic(self, topic):
        """随机删除指定话题中的一条记忆，如果话题没有记忆则移除该话题节点"""
        if topic not in self.G:
            return None

        # 获取话题节点数据
        node_data = self.G.nodes[topic]

        # 如果节点存在memory_items
        if 'memory_items' in node_data:
            memory_items = node_data['memory_items']

            # 确保memory_items是列表
            if not isinstance(memory_items, list):
                memory_items = [memory_items] if memory_items else []

            # 如果有记忆项可以删除
            if memory_items:
                # 随机选择一个记忆项删除
                removed_item = random.choice(memory_items)
                memory_items.remove(removed_item)

                # 更新节点的记忆项
                if memory_items:
                    self.G.nodes[topic]['memory_items'] = memory_items
                else:
                    # 如果没有记忆项了，删除整个节点
                    self.G.remove_node(topic)

                return removed_item

        return None


# 海马体 
class Hippocampus:
    def __init__(self, memory_graph: Memory_graph):
        self.memory_graph = memory_graph
        self.llm_topic_judge = LLM_request(model=global_config.llm_topic_judge, temperature=0.5)
        self.llm_summary_by_topic = LLM_request(model=global_config.llm_summary_by_topic, temperature=0.5)

    def get_all_node_names(self) -> list:
        """获取记忆图中所有节点的名字列表
        
        Returns:
            list: 包含所有节点名字的列表
        """
        return list(self.memory_graph.G.nodes())

    def calculate_node_hash(self, concept, memory_items):
        """计算节点的特征值"""
        if not isinstance(memory_items, list):
            memory_items = [memory_items] if memory_items else []
        sorted_items = sorted(memory_items)
        content = f"{concept}:{'|'.join(sorted_items)}"
        return hash(content)

    def calculate_edge_hash(self, source, target):
        """计算边的特征值"""
        nodes = sorted([source, target])
        return hash(f"{nodes[0]}:{nodes[1]}")

    def get_memory_sample(self, chat_size=20, time_frequency: dict = {'near': 2, 'mid': 4, 'far': 3}):
        """获取记忆样本
        
        Returns:
            list: 消息记录列表，每个元素是一个消息记录字典列表
        """
        current_timestamp = datetime.datetime.now().timestamp()
        chat_samples = []

        # 短期：1h   中期：4h   长期：24h
        for _ in range(time_frequency.get('near')):
            random_time = current_timestamp - random.randint(1, 3600)
            messages = get_cloest_chat_from_db(db=self.memory_graph.db, length=chat_size, timestamp=random_time)
            if messages:
                chat_samples.append(messages)

        for _ in range(time_frequency.get('mid')):
            random_time = current_timestamp - random.randint(3600, 3600 * 4)
            messages = get_cloest_chat_from_db(db=self.memory_graph.db, length=chat_size, timestamp=random_time)
            if messages:
                chat_samples.append(messages)

        for _ in range(time_frequency.get('far')):
            random_time = current_timestamp - random.randint(3600 * 4, 3600 * 24)
            messages = get_cloest_chat_from_db(db=self.memory_graph.db, length=chat_size, timestamp=random_time)
            if messages:
                chat_samples.append(messages)

        return chat_samples

    async def memory_compress(self, messages: list, compress_rate=0.1):
        """压缩消息记录为记忆
        
        Args:
            messages: 消息记录字典列表，每个字典包含text和time字段
            compress_rate: 压缩率
            
        Returns:
            set: (话题, 记忆) 元组集合
        """
        if not messages:
            return set()

        # 合并消息文本，同时保留时间信息
        input_text = ""
        time_info = ""
        # 计算最早和最晚时间
        earliest_time = min(msg['time'] for msg in messages)
        latest_time = max(msg['time'] for msg in messages)

        earliest_dt = datetime.datetime.fromtimestamp(earliest_time)
        latest_dt = datetime.datetime.fromtimestamp(latest_time)

        # 如果是同一年
        if earliest_dt.year == latest_dt.year:
            earliest_str = earliest_dt.strftime("%m-%d %H:%M:%S")
            latest_str = latest_dt.strftime("%m-%d %H:%M:%S")
            time_info += f"是在{earliest_dt.year}年，{earliest_str} 到 {latest_str} 的对话:\n"
        else:
            earliest_str = earliest_dt.strftime("%Y-%m-%d %H:%M:%S")
            latest_str = latest_dt.strftime("%Y-%m-%d %H:%M:%S")
            time_info += f"是从 {earliest_str} 到 {latest_str} 的对话:\n"

        for msg in messages:
            input_text += f"{msg['text']}\n"

        logger.debug(input_text)

        topic_num = self.calculate_topic_num(input_text, compress_rate)
        topics_response = await self.llm_topic_judge.generate_response(self.find_topic_llm(input_text, topic_num))

        # 过滤topics
        filter_keywords = global_config.memory_ban_words
        topics = [topic.strip() for topic in
                  topics_response[0].replace("，", ",").replace("、", ",").replace(" ", ",").split(",") if topic.strip()]
        filtered_topics = [topic for topic in topics if not any(keyword in topic for keyword in filter_keywords)]

        logger.info(f"过滤后话题: {filtered_topics}")

        # 创建所有话题的请求任务
        tasks = []
        for topic in filtered_topics:
            topic_what_prompt = self.topic_what(input_text, topic, time_info)
            task = self.llm_summary_by_topic.generate_response_async(topic_what_prompt)
            tasks.append((topic.strip(), task))

        # 等待所有任务完成
        compressed_memory = set()
        for topic, task in tasks:
            response = await task
            if response:
                compressed_memory.add((topic, response[0]))

        return compressed_memory

    def calculate_topic_num(self, text, compress_rate):
        """计算文本的话题数量"""
        information_content = calculate_information_content(text)
        topic_by_length = text.count('\n') * compress_rate
        topic_by_information_content = max(1, min(5, int((information_content - 3) * 2)))
        topic_num = int((topic_by_length + topic_by_information_content) / 2)
        logger.debug(
            f"topic_by_length: {topic_by_length}, topic_by_information_content: {topic_by_information_content}, "
            f"topic_num: {topic_num}")
        return topic_num

    async def operation_build_memory(self, chat_size=20):
        # 最近消息获取频率
        time_frequency = {'near': 2, 'mid': 4, 'far': 2}
        memory_sample = self.get_memory_sample(chat_size, time_frequency)

        for i, input_text in enumerate(memory_sample, 1):
            # 加载进度可视化
            all_topics = []
            progress = (i / len(memory_sample)) * 100
            bar_length = 30
            filled_length = int(bar_length * i // len(memory_sample))
            bar = '█' * filled_length + '-' * (bar_length - filled_length)
            logger.debug(f"进度: [{bar}] {progress:.1f}% ({i}/{len(memory_sample)})")

            # 生成压缩后记忆 ,表现为 (话题,记忆) 的元组
            compressed_memory = set()
            compress_rate = 0.1
            compressed_memory = await self.memory_compress(input_text, compress_rate)
            logger.info(f"压缩后记忆数量: {len(compressed_memory)}")

            # 将记忆加入到图谱中
            for topic, memory in compressed_memory:
                logger.info(f"添加节点: {topic}")
                self.memory_graph.add_dot(topic, memory)
                all_topics.append(topic)  # 收集所有话题
            for i in range(len(all_topics)):
                for j in range(i + 1, len(all_topics)):
                    logger.info(f"连接节点: {all_topics[i]} 和 {all_topics[j]}")
                    self.memory_graph.connect_dot(all_topics[i], all_topics[j])

        self.sync_memory_to_db()

    def sync_memory_to_db(self):
        """检查并同步内存中的图结构与数据库"""
        # 获取数据库中所有节点和内存中所有节点
        db_nodes = list(self.memory_graph.db.db.graph_data.nodes.find())
        memory_nodes = list(self.memory_graph.G.nodes(data=True))

        # 转换数据库节点为字典格式，方便查找
        db_nodes_dict = {node['concept']: node for node in db_nodes}

        # 检查并更新节点
        for concept, data in memory_nodes:
            memory_items = data.get('memory_items', [])
            if not isinstance(memory_items, list):
                memory_items = [memory_items] if memory_items else []

            # 计算内存中节点的特征值
            memory_hash = self.calculate_node_hash(concept, memory_items)

            if concept not in db_nodes_dict:
                # 数据库中缺少的节点，添加
                node_data = {
                    'concept': concept,
                    'memory_items': memory_items,
                    'hash': memory_hash
                }
                self.memory_graph.db.db.graph_data.nodes.insert_one(node_data)
            else:
                # 获取数据库中节点的特征值
                db_node = db_nodes_dict[concept]
                db_hash = db_node.get('hash', None)

                # 如果特征值不同，则更新节点
                if db_hash != memory_hash:
                    self.memory_graph.db.db.graph_data.nodes.update_one(
                        {'concept': concept},
                        {'$set': {
                            'memory_items': memory_items,
                            'hash': memory_hash
                        }}
                    )

        # 检查并删除数据库中多余的节点
        memory_concepts = set(node[0] for node in memory_nodes)
        for db_node in db_nodes:
            if db_node['concept'] not in memory_concepts:
                self.memory_graph.db.db.graph_data.nodes.delete_one({'concept': db_node['concept']})

        # 处理边的信息
        db_edges = list(self.memory_graph.db.db.graph_data.edges.find())
        memory_edges = list(self.memory_graph.G.edges())

        # 创建边的哈希值字典
        db_edge_dict = {}
        for edge in db_edges:
            edge_hash = self.calculate_edge_hash(edge['source'], edge['target'])
            db_edge_dict[(edge['source'], edge['target'])] = {
                'hash': edge_hash,
                'strength': edge.get('strength', 1)
            }

        # 检查并更新边
        for source, target in memory_edges:
            edge_hash = self.calculate_edge_hash(source, target)
            edge_key = (source, target)
            strength = self.memory_graph.G[source][target].get('strength', 1)

            if edge_key not in db_edge_dict:
                # 添加新边
                edge_data = {
                    'source': source,
                    'target': target,
                    'strength': strength,
                    'hash': edge_hash
                }
                self.memory_graph.db.db.graph_data.edges.insert_one(edge_data)
            else:
                # 检查边的特征值是否变化
                if db_edge_dict[edge_key]['hash'] != edge_hash:
                    self.memory_graph.db.db.graph_data.edges.update_one(
                        {'source': source, 'target': target},
                        {'$set': {
                            'hash': edge_hash,
                            'strength': strength
                        }}
                    )

        # 删除多余的边
        memory_edge_set = set(memory_edges)
        for edge_key in db_edge_dict:
            if edge_key not in memory_edge_set:
                source, target = edge_key
                self.memory_graph.db.db.graph_data.edges.delete_one({
                    'source': source,
                    'target': target
                })

    def sync_memory_from_db(self):
        """从数据库同步数据到内存中的图结构"""
        # 清空当前图
        self.memory_graph.G.clear()

        # 从数据库加载所有节点
        nodes = self.memory_graph.db.db.graph_data.nodes.find()
        for node in nodes:
            concept = node['concept']
            memory_items = node.get('memory_items', [])
            # 确保memory_items是列表
            if not isinstance(memory_items, list):
                memory_items = [memory_items] if memory_items else []
            # 添加节点到图中
            self.memory_graph.G.add_node(concept, memory_items=memory_items)

        # 从数据库加载所有边
        edges = self.memory_graph.db.db.graph_data.edges.find()
        for edge in edges:
            source = edge['source']
            target = edge['target']
            strength = edge.get('strength', 1)  # 获取 strength，默认为 1
            # 只有当源节点和目标节点都存在时才添加边
            if source in self.memory_graph.G and target in self.memory_graph.G:
                self.memory_graph.G.add_edge(source, target, strength=strength)

    async def operation_forget_topic(self, percentage=0.1):
        """随机选择图中一定比例的节点进行检查，根据条件决定是否遗忘"""
        # 获取所有节点
        all_nodes = list(self.memory_graph.G.nodes())
        # 计算要检查的节点数量
        check_count = max(1, int(len(all_nodes) * percentage))
        # 随机选择节点
        nodes_to_check = random.sample(all_nodes, check_count)

        forgotten_nodes = []
        for node in nodes_to_check:
            # 获取节点的连接数
            connections = self.memory_graph.G.degree(node)

            # 获取节点的内容条数
            memory_items = self.memory_graph.G.nodes[node].get('memory_items', [])
            if not isinstance(memory_items, list):
                memory_items = [memory_items] if memory_items else []
            content_count = len(memory_items)

            # 检查连接强度
            weak_connections = True
            if connections > 1:  # 只有当连接数大于1时才检查强度
                for neighbor in self.memory_graph.G.neighbors(node):
                    strength = self.memory_graph.G[node][neighbor].get('strength', 1)
                    if strength > 2:
                        weak_connections = False
                        break

            # 如果满足遗忘条件
            if (connections <= 1 and weak_connections) or content_count <= 2:
                removed_item = self.memory_graph.forget_topic(node)
                if removed_item:
                    forgotten_nodes.append((node, removed_item))
                    logger.debug(f"遗忘节点 {node} 的记忆: {removed_item}")

        # 同步到数据库
        if forgotten_nodes:
            self.sync_memory_to_db()
            logger.debug(f"完成遗忘操作，共遗忘 {len(forgotten_nodes)} 个节点的记忆")
        else:
            logger.debug("本次检查没有节点满足遗忘条件")

    async def merge_memory(self, topic):
        """
        对指定话题的记忆进行合并压缩
        
        Args:
            topic: 要合并的话题节点
        """
        # 获取节点的记忆项
        memory_items = self.memory_graph.G.nodes[topic].get('memory_items', [])
        if not isinstance(memory_items, list):
            memory_items = [memory_items] if memory_items else []

        # 如果记忆项不足，直接返回
        if len(memory_items) < 10:
            return

        # 随机选择10条记忆
        selected_memories = random.sample(memory_items, 10)

        # 拼接成文本
        merged_text = "\n".join(selected_memories)
        logger.debug(f"\n[合并记忆] 话题: {topic}")
        logger.debug(f"选择的记忆:\n{merged_text}")

        # 使用memory_compress生成新的压缩记忆
        compressed_memories = await self.memory_compress(selected_memories, 0.1)

        # 从原记忆列表中移除被选中的记忆
        for memory in selected_memories:
            memory_items.remove(memory)

        # 添加新的压缩记忆
        for _, compressed_memory in compressed_memories:
            memory_items.append(compressed_memory)
            logger.info(f"添加压缩记忆: {compressed_memory}")

        # 更新节点的记忆项
        self.memory_graph.G.nodes[topic]['memory_items'] = memory_items
        logger.debug(f"完成记忆合并，当前记忆数量: {len(memory_items)}")

    async def operation_merge_memory(self, percentage=0.1):
        """
        随机检查一定比例的节点，对内容数量超过100的节点进行记忆合并
        
        Args:
            percentage: 要检查的节点比例，默认为0.1（10%）
        """
        # 获取所有节点
        all_nodes = list(self.memory_graph.G.nodes())
        # 计算要检查的节点数量
        check_count = max(1, int(len(all_nodes) * percentage))
        # 随机选择节点
        nodes_to_check = random.sample(all_nodes, check_count)

        merged_nodes = []
        for node in nodes_to_check:
            # 获取节点的内容条数
            memory_items = self.memory_graph.G.nodes[node].get('memory_items', [])
            if not isinstance(memory_items, list):
                memory_items = [memory_items] if memory_items else []
            content_count = len(memory_items)

            # 如果内容数量超过100，进行合并
            if content_count > 100:
                logger.debug(f"检查节点: {node}, 当前记忆数量: {content_count}")
                await self.merge_memory(node)
                merged_nodes.append(node)

        # 同步到数据库
        if merged_nodes:
            self.sync_memory_to_db()
            logger.debug(f"完成记忆合并操作，共处理 {len(merged_nodes)} 个节点")
        else:
            logger.debug("本次检查没有需要合并的节点")

    def find_topic_llm(self, text, topic_num):
        prompt = f'这是一段文字：{text}。请你从这段话中总结出{topic_num}个关键的概念，可以是名词，动词，或者特定人物，帮我列出来，用逗号,隔开，尽可能精简。只需要列举{topic_num}个话题就好，不要有序号，不要告诉我其他内容。'
        return prompt

    def topic_what(self, text, topic, time_info):
        prompt = f'这是一段文字，{time_info}：{text}。我想让你基于这段文字来概括"{topic}"这个概念，帮我总结成一句自然的话，可以包含时间和人物，以及具体的观点。只输出这句话就好'
        return prompt

    async def _identify_topics(self, text: str) -> list:
        """从文本中识别可能的主题
        
        Args:
            text: 输入文本
            
        Returns:
            list: 识别出的主题列表
        """
        topics_response = await self.llm_topic_judge.generate_response(self.find_topic_llm(text, 5))
        # print(f"话题: {topics_response[0]}")
        topics = [topic.strip() for topic in
                  topics_response[0].replace("，", ",").replace("、", ",").replace(" ", ",").split(",") if topic.strip()]
        # print(f"话题: {topics}")

        return topics

    def _find_similar_topics(self, topics: list, similarity_threshold: float = 0.4, debug_info: str = "") -> list:
        """查找与给定主题相似的记忆主题
        
        Args:
            topics: 主题列表
            similarity_threshold: 相似度阈值
            debug_info: 调试信息前缀
            
        Returns:
            list: (主题, 相似度) 元组列表
        """
        all_memory_topics = self.get_all_node_names()
        all_similar_topics = []

        # 计算每个识别出的主题与记忆主题的相似度
        for topic in topics:
            if debug_info:
                # print(f"\033[1;32m[{debug_info}]\033[0m 正在思考有没有见过: {topic}")
                pass

            topic_vector = text_to_vector(topic)
            has_similar_topic = False

            for memory_topic in all_memory_topics:
                memory_vector = text_to_vector(memory_topic)
                # 获取所有唯一词
                all_words = set(topic_vector.keys()) | set(memory_vector.keys())
                # 构建向量
                v1 = [topic_vector.get(word, 0) for word in all_words]
                v2 = [memory_vector.get(word, 0) for word in all_words]
                # 计算相似度
                similarity = cosine_similarity(v1, v2)

                if similarity >= similarity_threshold:
                    has_similar_topic = True
                    if debug_info:
                        # print(f"\033[1;32m[{debug_info}]\033[0m 找到相似主题: {topic} -> {memory_topic} (相似度: {similarity:.2f})")
                        pass
                    all_similar_topics.append((memory_topic, similarity))

            if not has_similar_topic and debug_info:
                # print(f"\033[1;31m[{debug_info}]\033[0m 没有见过: {topic}  ，呃呃")
                pass

        return all_similar_topics

    def _get_top_topics(self, similar_topics: list, max_topics: int = 5) -> list:
        """获取相似度最高的主题
        
        Args:
            similar_topics: (主题, 相似度) 元组列表
            max_topics: 最大主题数量
            
        Returns:
            list: (主题, 相似度) 元组列表
        """
        seen_topics = set()
        top_topics = []

        for topic, score in sorted(similar_topics, key=lambda x: x[1], reverse=True):
            if topic not in seen_topics and len(top_topics) < max_topics:
                seen_topics.add(topic)
                top_topics.append((topic, score))

        return top_topics

    async def memory_activate_value(self, text: str, max_topics: int = 5, similarity_threshold: float = 0.3) -> int:
        """计算输入文本对记忆的激活程度"""
        logger.info(f"识别主题: {await self._identify_topics(text)}")

        # 识别主题
        identified_topics = await self._identify_topics(text)
        if not identified_topics:
            return 0

        # 查找相似主题
        all_similar_topics = self._find_similar_topics(
            identified_topics,
            similarity_threshold=similarity_threshold,
            debug_info="记忆激活"
        )

        if not all_similar_topics:
            return 0

        # 获取最相关的主题
        top_topics = self._get_top_topics(all_similar_topics, max_topics)

        # 如果只找到一个主题，进行惩罚
        if len(top_topics) == 1:
            topic, score = top_topics[0]
            # 获取主题内容数量并计算惩罚系数
            memory_items = self.memory_graph.G.nodes[topic].get('memory_items', [])
            if not isinstance(memory_items, list):
                memory_items = [memory_items] if memory_items else []
            content_count = len(memory_items)
            penalty = 1.0 / (1 + math.log(content_count + 1))

            activation = int(score * 50 * penalty)
            logger.info(
                f"[记忆激活]单主题「{topic}」- 相似度: {score:.3f}, 内容数: {content_count}, 激活值: {activation}")
            return activation

        # 计算关键词匹配率，同时考虑内容数量
        matched_topics = set()
        topic_similarities = {}

        for memory_topic, similarity in top_topics:
            # 计算内容数量惩罚
            memory_items = self.memory_graph.G.nodes[memory_topic].get('memory_items', [])
            if not isinstance(memory_items, list):
                memory_items = [memory_items] if memory_items else []
            content_count = len(memory_items)
            penalty = 1.0 / (1 + math.log(content_count + 1))

            # 对每个记忆主题，检查它与哪些输入主题相似
            for input_topic in identified_topics:
                topic_vector = text_to_vector(input_topic)
                memory_vector = text_to_vector(memory_topic)
                all_words = set(topic_vector.keys()) | set(memory_vector.keys())
                v1 = [topic_vector.get(word, 0) for word in all_words]
                v2 = [memory_vector.get(word, 0) for word in all_words]
                sim = cosine_similarity(v1, v2)
                if sim >= similarity_threshold:
                    matched_topics.add(input_topic)
                    adjusted_sim = sim * penalty
                    topic_similarities[input_topic] = max(topic_similarities.get(input_topic, 0), adjusted_sim)
                    logger.info(
                        f"[记忆激活]主题「{input_topic}」-> 「{memory_topic}」(内容数: {content_count}, 相似度: {adjusted_sim:.3f})")

        # 计算主题匹配率和平均相似度
        topic_match = len(matched_topics) / len(identified_topics)
        average_similarities = sum(topic_similarities.values()) / len(topic_similarities) if topic_similarities else 0

        # 计算最终激活值
        activation = int((topic_match + average_similarities) / 2 * 100)
        logger.info(
            f"[记忆激活]匹配率: {topic_match:.3f}, 平均相似度: {average_similarities:.3f}, 激活值: {activation}")

        return activation

    async def get_relevant_memories(self, text: str, max_topics: int = 5, similarity_threshold: float = 0.4,
                                    max_memory_num: int = 5) -> list:
        """根据输入文本获取相关的记忆内容"""
        # 识别主题
        identified_topics = await self._identify_topics(text)

        # 查找相似主题
        all_similar_topics = self._find_similar_topics(
            identified_topics,
            similarity_threshold=similarity_threshold,
            debug_info="记忆检索"
        )

        # 获取最相关的主题
        relevant_topics = self._get_top_topics(all_similar_topics, max_topics)

        # 获取相关记忆内容
        relevant_memories = []
        for topic, score in relevant_topics:
            # 获取该主题的记忆内容
            first_layer, _ = self.memory_graph.get_related_item(topic, depth=1)
            if first_layer:
                # 如果记忆条数超过限制，随机选择指定数量的记忆
                if len(first_layer) > max_memory_num / 2:
                    first_layer = random.sample(first_layer, max_memory_num // 2)
                # 为每条记忆添加来源主题和相似度信息
                for memory in first_layer:
                    relevant_memories.append({
                        'topic': topic,
                        'similarity': score,
                        'content': memory
                    })

        # 如果记忆数量超过5个,随机选择5个
        # 按相似度排序
        relevant_memories.sort(key=lambda x: x['similarity'], reverse=True)

        if len(relevant_memories) > max_memory_num:
            relevant_memories = random.sample(relevant_memories, max_memory_num)

        return relevant_memories


def segment_text(text):
    seg_text = list(jieba.cut(text))
    return seg_text


from nonebot import get_driver

driver = get_driver()
config = driver.config

start_time = time.time()

Database.initialize(
    host=config.MONGODB_HOST,
    port=int(config.MONGODB_PORT),
    db_name=config.DATABASE_NAME,
    username=config.MONGODB_USERNAME,
    password=config.MONGODB_PASSWORD,
    auth_source=config.MONGODB_AUTH_SOURCE
)
# 创建记忆图
memory_graph = Memory_graph()
# 创建海马体
hippocampus = Hippocampus(memory_graph)
# 从数据库加载记忆图
hippocampus.sync_memory_from_db()

end_time = time.time()
logger.success(f"加载海马体耗时: {end_time - start_time:.2f} 秒")

# -*- coding: utf-8 -*-
import os
import sys
import time

import jieba
import matplotlib.pyplot as plt
import networkx as nx
from dotenv import load_dotenv
from loguru import logger

# 添加项目根目录到 Python 路径
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.append(root_path)

from src.common.database import Database  # 使用正确的导入语法

# 加载.env.dev文件
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), '.env.dev')
load_dotenv(env_path)


class Memory_graph:
    def __init__(self):
        self.G = nx.Graph()  # 使用 networkx 的图结构
        self.db = Database.get_instance()

    def connect_dot(self, concept1, concept2):
        self.G.add_edge(concept1, concept2)

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
            # print(node_data)
            # 创建新的Memory_dot对象
            return concept, node_data
        return None

    def get_related_item(self, topic, depth=1):
        if topic not in self.G:
            return [], []

        first_layer_items = []
        second_layer_items = []

        # 获取相邻节点
        neighbors = list(self.G.neighbors(topic))
        # print(f"第一层: {topic}")

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
                # print(f"第二层: {neighbor}")
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

    def store_memory(self):
        for node in self.G.nodes():
            dot_data = {
                "concept": node
            }
            self.db.db.store_memory_dots.insert_one(dot_data)

    @property
    def dots(self):
        # 返回所有节点对应的 Memory_dot 对象
        return [self.get_dot(node) for node in self.G.nodes()]

    def get_random_chat_from_db(self, length: int, timestamp: str):
        # 从数据库中根据时间戳获取离其最近的聊天记录
        chat_text = ''
        closest_record = self.db.db.messages.find_one({"time": {"$lte": timestamp}}, sort=[('time', -1)])  # 调试输出
        logger.info(
            f"距离time最近的消息时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(closest_record['time'])))}")

        if closest_record:
            closest_time = closest_record['time']
            group_id = closest_record['group_id']  # 获取groupid
            # 获取该时间戳之后的length条消息，且groupid相同
            chat_record = list(
                self.db.db.messages.find({"time": {"$gt": closest_time}, "group_id": group_id}).sort('time', 1).limit(
                    length))
            for record in chat_record:
                time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(record['time'])))
                try:
                    displayname = "[(%s)%s]%s" % (record["user_id"], record["user_nickname"], record["user_cardname"])
                except:
                    displayname = record["user_nickname"] or "用户" + str(record["user_id"])
                chat_text += f'[{time_str}] {displayname}: {record["processed_plain_text"]}\n'  # 添加发送者和时间信息
            return chat_text

        return []  # 如果没有找到记录，返回空列表

    def save_graph_to_db(self):
        # 清空现有的图数据
        self.db.db.graph_data.delete_many({})
        # 保存节点
        for node in self.G.nodes(data=True):
            node_data = {
                'concept': node[0],
                'memory_items': node[1].get('memory_items', [])  # 默认为空列表
            }
            self.db.db.graph_data.nodes.insert_one(node_data)
        # 保存边
        for edge in self.G.edges():
            edge_data = {
                'source': edge[0],
                'target': edge[1]
            }
            self.db.db.graph_data.edges.insert_one(edge_data)

    def load_graph_from_db(self):
        # 清空当前图
        self.G.clear()
        # 加载节点
        nodes = self.db.db.graph_data.nodes.find()
        for node in nodes:
            memory_items = node.get('memory_items', [])
            if not isinstance(memory_items, list):
                memory_items = [memory_items] if memory_items else []
            self.G.add_node(node['concept'], memory_items=memory_items)
        # 加载边
        edges = self.db.db.graph_data.edges.find()
        for edge in edges:
            self.G.add_edge(edge['source'], edge['target'])


def main():
    # 初始化数据库
    Database.initialize(
        uri=os.getenv("MONGODB_URI"),
        host=os.getenv("MONGODB_HOST", "127.0.0.1"),
        port=int(os.getenv("MONGODB_PORT", "27017")),
        db_name=os.getenv("DATABASE_NAME", "MegBot"),
        username=os.getenv("MONGODB_USERNAME"),
        password=os.getenv("MONGODB_PASSWORD"),
        auth_source=os.getenv("MONGODB_AUTH_SOURCE"),
    )

    memory_graph = Memory_graph()
    memory_graph.load_graph_from_db()

    # 只显示一次优化后的图形
    visualize_graph_lite(memory_graph)

    while True:
        query = input("请输入新的查询概念（输入'退出'以结束）：")
        if query.lower() == '退出':
            break
        first_layer_items, second_layer_items = memory_graph.get_related_item(query)
        if first_layer_items or second_layer_items:
            logger.debug("第一层记忆：")
            for item in first_layer_items:
                logger.debug(item)
            logger.debug("第二层记忆：")
            for item in second_layer_items:
                logger.debug(item)
        else:
            logger.debug("未找到相关记忆。")


def segment_text(text):
    seg_text = list(jieba.cut(text))
    return seg_text


def find_topic(text, topic_num):
    prompt = f'这是一段文字：{text}。请你从这段话中总结出{topic_num}个话题，帮我列出来，用逗号隔开，尽可能精简。只需要列举{topic_num}个话题就好，不要告诉我其他内容。'
    return prompt


def topic_what(text, topic):
    prompt = f'这是一段文字：{text}。我想知道这记忆里有什么关于{topic}的话题，帮我总结成一句自然的话，可以包含时间和人物。只输出这句话就好'
    return prompt


def visualize_graph_lite(memory_graph: Memory_graph, color_by_memory: bool = False):
    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
    plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

    G = memory_graph.G

    # 创建一个新图用于可视化
    H = G.copy()

    # 移除只有一条记忆的节点和连接数少于3的节点
    nodes_to_remove = []
    for node in H.nodes():
        memory_items = H.nodes[node].get('memory_items', [])
        memory_count = len(memory_items) if isinstance(memory_items, list) else (1 if memory_items else 0)
        degree = H.degree(node)
        if memory_count < 3 or degree < 2:  # 改为小于2而不是小于等于2
            nodes_to_remove.append(node)

    H.remove_nodes_from(nodes_to_remove)

    # 如果过滤后没有节点，则返回
    if len(H.nodes()) == 0:
        logger.debug("过滤后没有符合条件的节点可显示")
        return

    # 保存图到本地
    # nx.write_gml(H, "memory_graph.gml")  # 保存为 GML 格式

    # 计算节点大小和颜色
    node_colors = []
    node_sizes = []
    nodes = list(H.nodes())

    # 获取最大记忆数和最大度数用于归一化
    max_memories = 1
    max_degree = 1
    for node in nodes:
        memory_items = H.nodes[node].get('memory_items', [])
        memory_count = len(memory_items) if isinstance(memory_items, list) else (1 if memory_items else 0)
        degree = H.degree(node)
        max_memories = max(max_memories, memory_count)
        max_degree = max(max_degree, degree)

    # 计算每个节点的大小和颜色
    for node in nodes:
        # 计算节点大小（基于记忆数量）
        memory_items = H.nodes[node].get('memory_items', [])
        memory_count = len(memory_items) if isinstance(memory_items, list) else (1 if memory_items else 0)
        # 使用指数函数使变化更明显
        ratio = memory_count / max_memories
        size = 500 + 5000 * (ratio)  # 使用1.5次方函数使差异不那么明显
        node_sizes.append(size)

        # 计算节点颜色（基于连接数）
        degree = H.degree(node)
        # 红色分量随着度数增加而增加
        r = (degree / max_degree) ** 0.3
        red = min(1.0, r)
        # 蓝色分量随着度数减少而增加
        blue = max(0.0, 1 - red)
        # blue = 1
        color = (red, 0.1, blue)
        node_colors.append(color)

    # 绘制图形
    plt.figure(figsize=(12, 8))
    pos = nx.spring_layout(H, k=1, iterations=50)  # 增加k值使节点分布更开
    nx.draw(H, pos,
            with_labels=True,
            node_color=node_colors,
            node_size=node_sizes,
            font_size=10,
            font_family='SimHei',
            font_weight='bold',
            edge_color='gray',
            width=0.5,
            alpha=0.9)

    title = '记忆图谱可视化 - 节点大小表示记忆数量，颜色表示连接数'
    plt.title(title, fontsize=16, fontfamily='SimHei')
    plt.show()


if __name__ == "__main__":
    main()

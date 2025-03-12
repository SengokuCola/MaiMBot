import math
import random
import time
from collections import Counter
from typing import Dict, List

import jieba
import numpy as np
from nonebot import get_driver
from loguru import logger

from ..models.utils_model import LLM_request
from ..utils.typo_generator import ChineseTypoGenerator
from .config import global_config
from .message import MessageRecv,Message
from .message_base import UserInfo
from .chat_stream import ChatStream
from ..moods.moods import MoodManager

driver = get_driver()
config = driver.config



def db_message_to_str(message_dict: Dict) -> str:
    logger.debug(f"message_dict: {message_dict}")
    time_str = time.strftime("%m-%d %H:%M:%S", time.localtime(message_dict["time"]))
    try:
        name = "[(%s)%s]%s" % (
            message_dict['user_id'], message_dict.get("user_nickname", ""), message_dict.get("user_cardname", ""))
    except:
        name = message_dict.get("user_nickname", "") or f"用户{message_dict['user_id']}"
    content = message_dict.get("processed_plain_text", "")
    result = f"[{time_str}] {name}: {content}\n"
    logger.debug(f"result: {result}")
    return result


def is_mentioned_bot_in_message(message: MessageRecv) -> bool:
    """检查消息是否提到了机器人"""
    keywords = [global_config.BOT_NICKNAME]
    nicknames = global_config.BOT_ALIAS_NAMES
    for keyword in keywords:
        if keyword in message.processed_plain_text:
            return True
    for nickname in nicknames:
        if nickname in message.processed_plain_text:
            return True
    return False


async def get_embedding(text):
    """获取文本的embedding向量"""
    llm = LLM_request(model=global_config.embedding)
    # return llm.get_embedding_sync(text)
    return await llm.get_embedding(text)


def cosine_similarity(v1, v2):
    dot_product = np.dot(v1, v2)
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    return dot_product / (norm1 * norm2)


def calculate_information_content(text):
    """计算文本的信息量（熵）"""
    char_count = Counter(text)
    total_chars = len(text)

    entropy = 0
    for count in char_count.values():
        probability = count / total_chars
        entropy -= probability * math.log2(probability)

    return entropy


def get_cloest_chat_from_db(db, length: int, timestamp: str):
    """从数据库中获取最接近指定时间戳的聊天记录
    
    Args:
        db: 数据库实例
        length: 要获取的消息数量
        timestamp: 时间戳
        
    Returns:
        list: 消息记录列表，每个记录包含时间和文本信息
    """
    chat_records = []
    closest_record = db.db.messages.find_one({"time": {"$lte": timestamp}}, sort=[('time', -1)])
    
    if closest_record:            
        closest_time = closest_record['time']
        chat_id = closest_record['chat_id']  # 获取chat_id
        # 获取该时间戳之后的length条消息，保持相同的chat_id
        chat_records = list(db.db.messages.find(
            {
                "time": {"$gt": closest_time},
                "chat_id": chat_id  # 添加chat_id过滤
            }
        ).sort('time', 1).limit(length))
        
        # 转换记录格式
        formatted_records = []
        for record in chat_records:
            formatted_records.append({
                'time': record["time"],
                'chat_id': record["chat_id"],
                'detailed_plain_text': record.get("detailed_plain_text", "")  # 添加文本内容
            })
            
        return formatted_records
            
    return []


async def get_recent_group_messages(db, chat_id:str, limit: int = 12) -> list:
    """从数据库获取群组最近的消息记录
    
    Args:
        db: Database实例
        group_id: 群组ID
        limit: 获取消息数量，默认12条
        
    Returns:
        list: Message对象列表，按时间正序排列
    """

    # 从数据库获取最近消息
    recent_messages = list(db.db.messages.find(
        {"chat_id": chat_id},
    ).sort("time", -1).limit(limit))

    if not recent_messages:
        return []

    # 转换为 Message对象列表
    message_objects = []
    for msg_data in recent_messages:
        try:
            chat_info=msg_data.get("chat_info",{})
            chat_stream=ChatStream.from_dict(chat_info)
            user_info=msg_data.get("user_info",{})
            user_info=UserInfo.from_dict(user_info)
            msg = Message(
                message_id=msg_data["message_id"],
                chat_stream=chat_stream,
                time=msg_data["time"],
                user_info=user_info,
                processed_plain_text=msg_data.get("processed_text", ""),
                detailed_plain_text=msg_data.get("detailed_plain_text", "")
            )
            message_objects.append(msg)
        except KeyError:
            logger.warning("数据库中存在无效的消息")
            continue

    # 按时间正序排列
    message_objects.reverse()
    return message_objects


def get_recent_group_detailed_plain_text(db, chat_stream_id: int, limit: int = 12, combine=False):
    recent_messages = list(db.db.messages.find(
        {"chat_id": chat_stream_id},
        {
            "time": 1,  # 返回时间字段
            "chat_id":1,
            "chat_info":1,
            "user_info": 1,
            "message_id": 1,  # 返回消息ID字段
            "detailed_plain_text": 1  # 返回处理后的文本字段
        }
    ).sort("time", -1).limit(limit))

    if not recent_messages:
        return []

    message_detailed_plain_text = ''
    message_detailed_plain_text_list = []

    # 反转消息列表，使最新的消息在最后
    recent_messages.reverse()

    if combine:
        for msg_db_data in recent_messages:
            message_detailed_plain_text += str(msg_db_data["detailed_plain_text"])
        return message_detailed_plain_text
    else:
        for msg_db_data in recent_messages:
            message_detailed_plain_text_list.append(msg_db_data["detailed_plain_text"])
        return message_detailed_plain_text_list


def split_into_sentences_w_remove_punctuation(text: str) -> List[str]:
    """将文本分割成句子，但保持书名号中的内容完整
    Args:
        text: 要分割的文本字符串
    Returns:
        List[str]: 分割后的句子列表
    """
    len_text = len(text)
    if len_text < 5:
        if random.random() < 0.01:
            return list(text)  # 如果文本很短且触发随机条件,直接按字符分割
        else:
            return [text]
    if len_text < 12:
        split_strength = 0.3
    elif len_text < 32:
        split_strength = 0.7
    else:
        split_strength = 0.9
    # 先移除换行符
    # print(f"split_strength: {split_strength}")

    # print(f"处理前的文本: {text}")

    # 统一将英文逗号转换为中文逗号
    text = text.replace(',', '，')
    text = text.replace('\n', ' ')

    # print(f"处理前的文本: {text}")

    text_no_1 = ''
    for letter in text:
        # print(f"当前字符: {letter}")
        # if letter in ['!', '！', '?', '？']:
        #     # print(f"当前字符: {letter}, 随机数: {random.random()}")
        #     if random.random() < split_strength:
        #         letter = ''
        if letter in ['。', '…']:
            # print(f"当前字符: {letter}, 随机数: {random.random()}")
            if random.random() < 1 - split_strength:
                letter = ''
        text_no_1 += letter

    # 对每个逗号单独判断是否分割
    sentences = [text_no_1]
    new_sentences = []
    for sentence in sentences:
        parts = sentence.split('，')
        current_sentence = parts[0]
        for part in parts[1:]:
            if random.random() < split_strength:
                new_sentences.append(current_sentence.strip())
                current_sentence = part
            else:
                current_sentence += '，' + part
        # 处理空格分割
        space_parts = current_sentence.split(' ')
        current_sentence = space_parts[0]
        for part in space_parts[1:]:
            if random.random() < split_strength:
                new_sentences.append(current_sentence.strip())
                current_sentence = part
            else:
                current_sentence += ' ' + part
        new_sentences.append(current_sentence.strip())
    sentences = [s for s in new_sentences if s]  # 移除空字符串

    # print(f"分割后的句子: {sentences}")
    sentences_done = []
    for sentence in sentences:
        sentence = sentence.rstrip('，,')
        if random.random() < split_strength * 0.5:
            sentence = sentence.replace('，', '').replace(',', '')
        elif random.random() < split_strength:
            sentence = sentence.replace('，', ' ').replace(',', ' ')
        sentences_done.append(sentence)

    logger.info(f"处理后的句子: {sentences_done}")
    return sentences_done


def random_remove_punctuation(text: str) -> str:
    """随机处理标点符号，模拟人类打字习惯
    
    Args:
        text: 要处理的文本
        
    Returns:
        str: 处理后的文本
    """
    result = ''
    text_len = len(text)

    for i, char in enumerate(text):
        if char == '。' and i == text_len - 1:  # 结尾的句号
            if random.random() > 0.4:  # 80%概率删除结尾句号
                continue
        elif char == '，':
            rand = random.random()
            if rand < 0.25:  # 5%概率删除逗号
                continue
            elif rand < 0.25:  # 20%概率把逗号变成空格
                result += ' '
                continue
        result += char
    return result


def process_llm_response(text: str) -> List[str]:
    # processed_response = process_text_with_typos(content)
    if len(text) > 200:
        logger.warning(f"回复过长 ({len(text)} 字符)，返回默认回复")
        return ['懒得说']
    # 处理长消息
    typo_generator = ChineseTypoGenerator(
        error_rate=global_config.chinese_typo_error_rate,
        min_freq=global_config.chinese_typo_min_freq,
        tone_error_rate=global_config.chinese_typo_tone_error_rate,
        word_replace_rate=global_config.chinese_typo_word_replace_rate
    )
    split_sentences = split_into_sentences_w_remove_punctuation(text)
    sentences = []
    for sentence in split_sentences:
        if global_config.chinese_typo_enable:
            typoed_text, typo_corrections = typo_generator.create_typo_sentence(sentence)
            sentences.append(typoed_text)
            if typo_corrections:
                sentences.append(typo_corrections)
        else:
            sentences.append(sentence)
    # 检查分割后的消息数量是否过多（超过3条）

    if len(sentences) > 5:
        logger.warning(f"分割后消息数量过多 ({len(sentences)} 条)，返回默认回复")
        return [f'{global_config.BOT_NICKNAME}不知道哦']

    return sentences


def calculate_typing_time(input_string: str, chinese_time: float = 0.4, english_time: float = 0.2) -> float:
    """
    计算输入字符串所需的时间，中文和英文字符有不同的输入时间
        input_string (str): 输入的字符串
        chinese_time (float): 中文字符的输入时间，默认为0.2秒
        english_time (float): 英文字符的输入时间，默认为0.1秒
        
    特殊情况：
    - 如果只有一个中文字符，将使用3倍的中文输入时间
    - 在所有输入结束后，额外加上回车时间0.3秒
    """
    mood_manager = MoodManager.get_instance()
    # 将0-1的唤醒度映射到-1到1
    mood_arousal = mood_manager.current_mood.arousal
    # 映射到0.5到2倍的速度系数
    typing_speed_multiplier = 1.5 ** mood_arousal  # 唤醒度为1时速度翻倍,为-1时速度减半
    chinese_time *= 1 / typing_speed_multiplier
    english_time *= 1 / typing_speed_multiplier
    # 计算中文字符数
    chinese_chars = sum(1 for char in input_string if '\u4e00' <= char <= '\u9fff')

    # 如果只有一个中文字符，使用3倍时间
    if chinese_chars == 1 and len(input_string.strip()) == 1:
        return chinese_time * 3 + 0.3  # 加上回车时间

    # 正常计算所有字符的输入时间
    total_time = 0.0
    for char in input_string:
        if '\u4e00' <= char <= '\u9fff':  # 判断是否为中文字符
            total_time += chinese_time
        else:  # 其他字符（如英文）
            total_time += english_time
    return total_time + 0.3  # 加上回车时间


def cosine_similarity(v1, v2):
    """计算余弦相似度"""
    dot_product = np.dot(v1, v2)
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 0
    return dot_product / (norm1 * norm2)


def text_to_vector(text):
    """将文本转换为词频向量"""
    # 分词
    words = jieba.lcut(text)
    # 统计词频
    word_freq = Counter(words)
    return word_freq


def find_similar_topics_simple(text: str, topics: list, top_k: int = 5) -> list:
    """使用简单的余弦相似度计算文本相似度"""
    # 将输入文本转换为词频向量
    text_vector = text_to_vector(text)

    # 计算每个主题的相似度
    similarities = []
    for topic in topics:
        topic_vector = text_to_vector(topic)
        # 获取所有唯一词
        all_words = set(text_vector.keys()) | set(topic_vector.keys())
        # 构建向量
        v1 = [text_vector.get(word, 0) for word in all_words]
        v2 = [topic_vector.get(word, 0) for word in all_words]
        # 计算相似度
        similarity = cosine_similarity(v1, v2)
        similarities.append((topic, similarity))

    # 按相似度降序排序并返回前k个
    return sorted(similarities, key=lambda x: x[1], reverse=True)[:top_k]

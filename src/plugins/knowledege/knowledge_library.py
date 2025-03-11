import os
import sys
import time

import requests
from dotenv import load_dotenv

# 添加项目根目录到 Python 路径
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.append(root_path)

# 加载根目录下的env.edv文件
env_path = os.path.join(root_path, ".env.dev")
if not os.path.exists(env_path):
    raise FileNotFoundError(f"配置文件不存在: {env_path}")
load_dotenv(env_path)

from src.common.database import Database

# 从环境变量获取配置
Database.initialize(
    uri=os.getenv("MONGODB_URI"),
    host=os.getenv("MONGODB_HOST", "127.0.0.1"),
    port=int(os.getenv("MONGODB_PORT", "27017")),
    db_name=os.getenv("DATABASE_NAME", "MegBot"),
    username=os.getenv("MONGODB_USERNAME"),
    password=os.getenv("MONGODB_PASSWORD"),
    auth_source=os.getenv("MONGODB_AUTH_SOURCE"),
)

class KnowledgeLibrary:
    def __init__(self):
        self.db = Database.get_instance()
        self.raw_info_dir = "data/raw_info"
        self._ensure_dirs()
        self.api_key = os.getenv("SILICONFLOW_KEY")
        if not self.api_key:
            raise ValueError("SILICONFLOW_API_KEY 环境变量未设置")
        
    def _ensure_dirs(self):
        """确保必要的目录存在"""
        os.makedirs(self.raw_info_dir, exist_ok=True)
        
    def get_embedding(self, text: str) -> list:
        """获取文本的embedding向量"""
        url = "https://api.siliconflow.cn/v1/embeddings"
        payload = {
            "model": "BAAI/bge-m3",
            "input": text,
            "encoding_format": "float"
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            print(f"获取embedding失败: {response.text}")
            return None
            
        return response.json()['data'][0]['embedding']
        
    def process_files(self):
        """处理raw_info目录下的所有txt文件"""
        for filename in os.listdir(self.raw_info_dir):
            if filename.endswith('.txt'):
                file_path = os.path.join(self.raw_info_dir, filename)
                self.process_single_file(file_path)
                
    def process_single_file(self, file_path: str):
        """处理单个文件"""
        try:
            # 检查文件是否已处理
            if self.db.db.processed_files.find_one({"file_path": file_path}):
                print(f"文件已处理过，跳过: {file_path}")
                return
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 按1024字符分段
            segments = [content[i:i+600] for i in range(0, len(content), 300)]
            
            # 处理每个分段
            for segment in segments:
                if not segment.strip():  # 跳过空段
                    continue
                    
                # 获取embedding
                embedding = self.get_embedding(segment)
                if not embedding:
                    continue
                    
                # 存储到数据库
                doc = {
                    "content": segment,
                    "embedding": embedding,
                    "file_path": file_path,
                    "segment_length": len(segment)
                }
                
                # 使用文本内容的哈希值作为唯一标识
                content_hash = hash(segment)
                
                # 更新或插入文档
                self.db.db.knowledges.update_one(
                    {"content_hash": content_hash},
                    {"$set": doc},
                    upsert=True
                )
                
            # 记录文件已处理
            self.db.db.processed_files.insert_one({
                "file_path": file_path,
                "processed_time": time.time()
            })
                
            print(f"成功处理文件: {file_path}")
            
        except Exception as e:
            print(f"处理文件 {file_path} 时出错: {str(e)}")
            
    def search_similar_segments(self, query: str, limit: int = 5) -> list:
        """搜索与查询文本相似的片段"""
        query_embedding = self.get_embedding(query)
        if not query_embedding:
            return []
            
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
            {"$sort": {"similarity": -1}},
            {"$limit": limit},
            {"$project": {"content": 1, "similarity": 1, "file_path": 1}}
        ]
        
        results = list(self.db.db.knowledges.aggregate(pipeline))
        return results

# 创建单例实例
knowledge_library = KnowledgeLibrary()

if __name__ == "__main__":
    # 测试知识库功能
    print("开始处理知识库文件...")
    knowledge_library.process_files()
    
    # 测试搜索功能
    test_query = "麦麦评价一下僕と花"
    print(f"\n搜索与'{test_query}'相似的内容:")
    results = knowledge_library.search_similar_segments(test_query)
    for result in results:
        print(f"相似度: {result['similarity']:.4f}")
        print(f"内容: {result['content'][:100]}...")
        print("-" * 50)

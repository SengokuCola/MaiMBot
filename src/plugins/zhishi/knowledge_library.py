import os
import sys
import time
import requests
from dotenv import load_dotenv
import hashlib
from datetime import datetime
from tqdm import tqdm
from rich.console import Console
from rich.table import Table

# 添加项目根目录到 Python 路径
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.append(root_path)

# 现在可以导入src模块
from src.common.database import Database

# 加载根目录下的env.edv文件
env_path = os.path.join(root_path, ".env.prod")
if not os.path.exists(env_path):
    raise FileNotFoundError(f"配置文件不存在: {env_path}")
load_dotenv(env_path)

class KnowledgeLibrary:
    def __init__(self):
        # 初始化数据库连接
        if Database._instance is None:
            Database.initialize(
                uri=os.getenv("MONGODB_URI"),
                host=os.getenv("MONGODB_HOST", "127.0.0.1"),
                port=int(os.getenv("MONGODB_PORT", "27017")),
                db_name=os.getenv("DATABASE_NAME", "MegBot"),
                username=os.getenv("MONGODB_USERNAME"),
                password=os.getenv("MONGODB_PASSWORD"),
                auth_source=os.getenv("MONGODB_AUTH_SOURCE"),
            )
        self.db = Database.get_instance()
        self.raw_info_dir = "data/raw_info"
        self._ensure_dirs()
        self.api_key = os.getenv("SILICONFLOW_KEY")
        if not self.api_key:
            raise ValueError("SILICONFLOW_API_KEY 环境变量未设置")
        self.console = Console()
        
    def _ensure_dirs(self):
        """确保必要的目录存在"""
        os.makedirs(self.raw_info_dir, exist_ok=True)
        
    def read_file(self, file_path: str) -> str:
        """读取文件内容"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
            
    def split_content(self, content: str, max_length: int = 512) -> list:
        """将内容分割成适当大小的块，保持段落完整性
        
        Args:
            content: 要分割的文本内容
            max_length: 每个块的最大长度
            
        Returns:
            list: 分割后的文本块列表
        """
        # 首先按段落分割
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        chunks = []
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            para_length = len(para)
            
            # 如果单个段落就超过最大长度
            if para_length > max_length:
                # 如果当前chunk不为空，先保存
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = []
                    current_length = 0
                
                # 将长段落按句子分割
                sentences = [s.strip() for s in para.replace('。', '。\n').replace('！', '！\n').replace('？', '？\n').split('\n') if s.strip()]
                temp_chunk = []
                temp_length = 0
                
                for sentence in sentences:
                    sentence_length = len(sentence)
                    if sentence_length > max_length:
                        # 如果单个句子超长，强制按长度分割
                        if temp_chunk:
                            chunks.append('\n'.join(temp_chunk))
                            temp_chunk = []
                            temp_length = 0
                        for i in range(0, len(sentence), max_length):
                            chunks.append(sentence[i:i + max_length])
                    elif temp_length + sentence_length + 1 <= max_length:
                        temp_chunk.append(sentence)
                        temp_length += sentence_length + 1
                    else:
                        chunks.append('\n'.join(temp_chunk))
                        temp_chunk = [sentence]
                        temp_length = sentence_length
                
                if temp_chunk:
                    chunks.append('\n'.join(temp_chunk))
                
            # 如果当前段落加上现有chunk不超过最大长度
            elif current_length + para_length + 1 <= max_length:
                current_chunk.append(para)
                current_length += para_length + 1
            else:
                # 保存当前chunk并开始新的chunk
                chunks.append('\n'.join(current_chunk))
                current_chunk = [para]
                current_length = para_length
        
        # 添加最后一个chunk
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return chunks
        
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
        
    def process_files(self, knowledge_length:int=512):
        """处理raw_info目录下的所有txt文件"""
        txt_files = [f for f in os.listdir(self.raw_info_dir) if f.endswith('.txt')]
        
        if not txt_files:
            self.console.print("[red]警告：在 {} 目录下没有找到任何txt文件[/red]".format(self.raw_info_dir))
            self.console.print("[yellow]请将需要处理的文本文件放入该目录后再运行程序[/yellow]")
            return
            
        total_stats = {
            "processed_files": 0,
            "total_chunks": 0,
            "failed_files": [],
            "skipped_files": []
        }
        
        self.console.print(f"\n[bold blue]开始处理知识库文件 - 共{len(txt_files)}个文件[/bold blue]")
        
        for filename in tqdm(txt_files, desc="处理文件进度"):
            file_path = os.path.join(self.raw_info_dir, filename)
            result = self.process_single_file(file_path, knowledge_length)
            self._update_stats(total_stats, result, filename)
            
        self._display_processing_results(total_stats)
                
    def process_single_file(self, file_path: str, knowledge_length: int = 512):
        """处理单个文件"""
        result = {
            "status": "success",
            "chunks_processed": 0,
            "error": None
        }
        
        try:
            current_hash = self.calculate_file_hash(file_path)
            processed_record = self.db.db.processed_files.find_one({"file_path": file_path})
            
            if processed_record:
                if processed_record.get("hash") == current_hash:
                    if knowledge_length in processed_record.get("split_by", []):
                        result["status"] = "skipped"
                        return result
            
            content = self.read_file(file_path)
            chunks = self.split_content(content, knowledge_length)
            
            for chunk in tqdm(chunks, desc=f"处理 {os.path.basename(file_path)} 的文本块", leave=False):
                embedding = self.get_embedding(chunk)
                if embedding:
                    knowledge = {
                        "content": chunk,
                        "embedding": embedding,
                        "source_file": file_path,
                        "split_length": knowledge_length,
                        "created_at": datetime.now()
                    }
                    self.db.db.knowledges.insert_one(knowledge)
                    result["chunks_processed"] += 1
            
            split_by = processed_record.get("split_by", []) if processed_record else []
            if knowledge_length not in split_by:
                split_by.append(knowledge_length)
            
            self.db.db.processed_files.update_one(
                {"file_path": file_path},
                {
                    "$set": {
                        "hash": current_hash,
                        "last_processed": datetime.now(),
                        "split_by": split_by
                    }
                },
                upsert=True
            )
            
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            
        return result
        
    def _update_stats(self, total_stats, result, filename):
        """更新总体统计信息"""
        if result["status"] == "success":
            total_stats["processed_files"] += 1
            total_stats["total_chunks"] += result["chunks_processed"]
        elif result["status"] == "failed":
            total_stats["failed_files"].append((filename, result["error"]))
        elif result["status"] == "skipped":
            total_stats["skipped_files"].append(filename)
            
    def _display_processing_results(self, stats):
        """显示处理结果统计"""
        self.console.print("\n[bold green]处理完成！统计信息如下：[/bold green]")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("统计项", style="dim")
        table.add_column("数值")
        
        table.add_row("成功处理文件数", str(stats["processed_files"]))
        table.add_row("处理的知识块总数", str(stats["total_chunks"]))
        table.add_row("跳过的文件数", str(len(stats["skipped_files"])))
        table.add_row("失败的文件数", str(len(stats["failed_files"])))
        
        self.console.print(table)
        
        if stats["failed_files"]:
            self.console.print("\n[bold red]处理失败的文件：[/bold red]")
            for filename, error in stats["failed_files"]:
                self.console.print(f"[red]- {filename}: {error}[/red]")
                
        if stats["skipped_files"]:
            self.console.print("\n[bold yellow]跳过的文件（已处理）：[/bold yellow]")
            for filename in stats["skipped_files"]:
                self.console.print(f"[yellow]- {filename}[/yellow]")
            
    def calculate_file_hash(self, file_path):
        """计算文件的MD5哈希值"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

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
    console = Console()
    console.print("[bold green]知识库处理工具[/bold green]")
    
    while True:
        console.print("\n请选择要执行的操作：")
        console.print("[1] 麦麦开始学习")
        console.print("[2] 麦麦全部忘光光（仅知识）")
        console.print("[q] 退出程序")
        
        choice = input("\n请输入选项: ").strip()
        
        if choice.lower() == 'q':
            console.print("[yellow]程序退出[/yellow]")
            sys.exit(0)
        elif choice == '2':
            confirm = input("确定要删除所有知识吗？这个操作不可撤销！(y/n): ").strip().lower()
            if confirm == 'y':
                knowledge_library.db.db.knowledges.delete_many({})
                console.print("[green]已清空所有知识！[/green]")
            continue
        elif choice == '1':
            if not os.path.exists(knowledge_library.raw_info_dir):
                console.print(f"[yellow]创建目录：{knowledge_library.raw_info_dir}[/yellow]")
                os.makedirs(knowledge_library.raw_info_dir, exist_ok=True)
            
            # 询问分割长度
            while True:
                try:
                    length_input = input("请输入知识分割长度（默认512，输入q退出，回车使用默认值）: ").strip()
                    if length_input.lower() == 'q':
                        break
                    if not length_input:  # 如果直接回车，使用默认值
                        knowledge_length = 512
                        break
                    knowledge_length = int(length_input)
                    if knowledge_length <= 0:
                        print("分割长度必须大于0，请重新输入")
                        continue
                    break
                except ValueError:
                    print("请输入有效的数字")
                    continue
            
            if length_input.lower() == 'q':
                continue
                
            # 测试知识库功能
            print(f"开始处理知识库文件，使用分割长度: {knowledge_length}...")
            knowledge_library.process_files(knowledge_length=knowledge_length)
        else:
            console.print("[red]无效的选项，请重新选择[/red]")
            continue

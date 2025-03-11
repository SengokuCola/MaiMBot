from typing import Optional

from pymongo import MongoClient


class Database:
    _instance: Optional["Database"] = None
    
    def __init__(
        self,
        host: str,
        port: int,
        db_name: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        auth_source: Optional[str] = None,
        uri: Optional[str] = None,
    ):
        if uri and uri.startswith("mongodb://"):
            # 优先使用URI连接
            self.client = MongoClient(uri)
        elif username and password:
            # 如果有用户名和密码，使用认证连接
            self.client = MongoClient(
                host, port, username=username, password=password, authSource=auth_source
            )
        else:
            # 否则使用无认证连接
            self.client = MongoClient(host, port)
        self.db = self.client[db_name]
        
    @classmethod
    def initialize(
        cls,
        host: str,
        port: int,
        db_name: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        auth_source: Optional[str] = None,
        uri: Optional[str] = None,
    ) -> "Database":
        if cls._instance is None:
            cls._instance = cls(
                host, port, db_name, username, password, auth_source, uri
            )
        return cls._instance
        
    @classmethod
    def get_instance(cls) -> "Database":
        if cls._instance is None:
            raise RuntimeError("Database not initialized")
        return cls._instance


    #测试用
    
    def get_random_group_messages(self, group_id: str, limit: int = 5):
        # 先随机获取一条消息
        random_message = list(self.db.messages.aggregate([
            {"$match": {"group_id": group_id}},
            {"$sample": {"size": 1}}
        ]))[0]
        
        # 获取该消息之后的消息
        subsequent_messages = list(self.db.messages.find({
            "group_id": group_id,
            "time": {"$gt": random_message["time"]}
        }).sort("time", 1).limit(limit))
        
        # 将随机消息和后续消息合并
        messages = [random_message] + subsequent_messages
        
        return messages
import os
from typing import cast
from pymongo import MongoClient
from pymongo.database import Database

_client = None
_db = None


def __create_database_instance():
    uri = os.getenv("MONGODB_URI")
    host = os.getenv("MONGODB_HOST", "127.0.0.1")
    port = int(os.getenv("MONGODB_PORT", "27017"))
    db_name = os.getenv("DATABASE_NAME", "MegBot")
    username = os.getenv("MONGODB_USERNAME")
    password = os.getenv("MONGODB_PASSWORD")
    auth_source = os.getenv("MONGODB_AUTH_SOURCE")

    if uri and uri.startswith("mongodb://"):
        # 优先使用URI连接
        return MongoClient(uri)

    if username and password:
        # 如果有用户名和密码，使用认证连接
        return MongoClient(host, port, username=username, password=password, authSource=auth_source)

    # 否则使用无认证连接
    return MongoClient(host, port)


def get_db():
    """获取数据库连接实例，延迟初始化。"""
    global _client, _db
    if _client is None:
        _client = __create_database_instance()
        _db = _client[os.getenv("DATABASE_NAME", "MegBot")]
    return _db


class DBWrapper:
    """数据库代理类，保持接口兼容性同时实现懒加载。"""

    def __getattr__(self, name):
        return getattr(get_db(), name)

    def __getitem__(self, key):
        return get_db()[key]


# 全局数据库访问点
db: Database = DBWrapper()

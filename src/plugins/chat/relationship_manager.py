import asyncio
from loguru import logger
from typing import Optional

from ...common.database import Database


class Impression:
    traits: str = None
    called: str = None
    know_time: float = None

    relationship_value: float = None


class Relationship:
    user_id: int = None
    # impression: Impression = None
    # group_id: int = None
    # group_name: str = None
    gender: str = None
    age: int = None
    nickname: str = None
    relationship_value: float = None
    saved = False

    def __init__(self, user_id: int, data=None, **kwargs):
        if isinstance(data, dict):
            # 如果输入是字典，使用字典解析
            self.user_id = data.get('user_id')
            self.gender = data.get('gender')
            self.age = data.get('age')
            self.nickname = data.get('nickname')
            self.relationship_value = data.get('relationship_value', 0.0)
            self.saved = data.get('saved', False)
        else:
            # 如果是直接传入属性值
            self.user_id = kwargs.get('user_id')
            self.gender = kwargs.get('gender')
            self.age = kwargs.get('age')
            self.nickname = kwargs.get('nickname')
            self.relationship_value = kwargs.get('relationship_value', 0.0)
            self.saved = kwargs.get('saved', False)


class RelationshipManager:
    def __init__(self):
        self.relationships: dict[int, Relationship] = {}

    async def update_relationship(self, user_id: int, data=None, **kwargs):
        # 检查是否在内存中已存在
        relationship = self.relationships.get(user_id)
        if relationship:
            # 如果存在，更新现有对象
            if isinstance(data, dict):
                for key, value in data.items():
                    if hasattr(relationship, key) and value is not None:
                        setattr(relationship, key, value)
            else:
                for key, value in kwargs.items():
                    if hasattr(relationship, key) and value is not None:
                        setattr(relationship, key, value)
        else:
            # 如果不存在，创建新对象
            relationship = Relationship(user_id, data=data) if isinstance(data, dict) else Relationship(user_id,
                                                                                                        **kwargs)
            self.relationships[user_id] = relationship

        # 更新 id_name_nickname_table
        # self.id_name_nickname_table[user_id] = [relationship.nickname]  # 别称设置为空列表

        # 保存到数据库
        await self.storage_relationship(relationship)
        relationship.saved = True

        return relationship

    async def update_relationship_value(self, user_id: int, **kwargs):
        # 检查是否在内存中已存在
        relationship = self.relationships.get(user_id)
        if relationship:
            for key, value in kwargs.items():
                if key == 'relationship_value':
                    relationship.relationship_value += value
            await self.storage_relationship(relationship)
            relationship.saved = True
            return relationship
        else:
            logger.warning(f"用户 {user_id} 不存在，无法更新")
            return None

    def get_relationship(self, user_id: int) -> Optional[Relationship]:
        """获取用户关系对象"""
        if user_id in self.relationships:
            return self.relationships[user_id]
        else:
            return 0

    async def load_relationship(self, data: dict) -> Relationship:
        """从数据库加载或创建新的关系对象"""
        rela = Relationship(user_id=data['user_id'], data=data)
        rela.saved = True
        self.relationships[rela.user_id] = rela
        return rela

    async def load_all_relationships(self):
        """加载所有关系对象"""
        db = Database.get_instance()
        all_relationships = db.db.relationships.find({})
        for data in all_relationships:
            await self.load_relationship(data)

    async def _start_relationship_manager(self):
        """每5分钟自动保存一次关系数据"""
        db = Database.get_instance()
        # 获取所有关系记录
        all_relationships = db.db.relationships.find({})
        # 依次加载每条记录
        for data in all_relationships:
            user_id = data['user_id']
            relationship = await self.load_relationship(data)
            self.relationships[user_id] = relationship
        logger.debug(f"已加载 {len(self.relationships)} 条关系记录")

        while True:
            logger.debug("正在自动保存关系")
            await asyncio.sleep(300)  # 等待300秒(5分钟)
            await self._save_all_relationships()

    async def _save_all_relationships(self):
        """将所有关系数据保存到数据库"""
        # 保存所有关系数据
        for userid, relationship in self.relationships.items():
            if not relationship.saved:
                relationship.saved = True
                await self.storage_relationship(relationship)

    async def storage_relationship(self, relationship: Relationship):
        """
        将关系记录存储到数据库中
        """
        user_id = relationship.user_id
        nickname = relationship.nickname
        relationship_value = relationship.relationship_value
        gender = relationship.gender
        age = relationship.age
        saved = relationship.saved

        db = Database.get_instance()
        db.db.relationships.update_one(
            {'user_id': user_id},
            {'$set': {
                'nickname': nickname,
                'relationship_value': relationship_value,
                'gender': gender,
                'age': age,
                'saved': saved
            }},
            upsert=True
        )

    def get_name(self, user_id: int) -> str:
        # 确保user_id是整数类型
        user_id = int(user_id)
        if user_id in self.relationships:

            return self.relationships[user_id].nickname
        else:
            return "某人"


relationship_manager = RelationshipManager()

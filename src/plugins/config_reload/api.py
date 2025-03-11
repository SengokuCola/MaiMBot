from fastapi import APIRouter, HTTPException
from src.plugins.chat.config import BotConfig
import os

# 创建APIRouter而不是FastAPI实例
router = APIRouter()

@router.post("/reload-config")
async def reload_config():
    try:
        bot_config_path = os.path.join(BotConfig.get_config_dir(), "bot_config.toml")
        global_config = BotConfig.load_config(config_path=bot_config_path)
        return {"message": "配置重载成功", "status": "success"}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重载配置时发生错误: {str(e)}")
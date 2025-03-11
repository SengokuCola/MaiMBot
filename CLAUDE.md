# MaiMBot 开发指南

## 🛠️ 常用命令

- **运行机器人**: `python run.py` 或 `python bot.py`
- **安装依赖**: `pip install --upgrade -r requirements.txt`
- **Docker 部署**: `docker-compose up`
- **代码检查**: `ruff check .`
- **代码格式化**: `ruff format .`
- **内存可视化**: `run_memory_vis.bat` 或 `python -m src.plugins.memory_system.draw_memory`
- **推理过程可视化**: `script/run_thingking.bat`

## 🔧 脚本工具

- **运行MongoDB**: `script/run_db.bat` - 在端口27017启动MongoDB
- **Windows完整启动**: `script/run_windows.bat` - 检查Python版本、设置虚拟环境、安装依赖并运行机器人
- **快速启动**: `script/run_maimai.bat` - 设置UTF-8编码并执行"nb run"命令

## 📝 代码风格

- **Python版本**: 3.9+
- **行长度限制**: 88字符
- **命名规范**:
  - `snake_case` 用于函数和变量
  - `PascalCase` 用于类
  - `_prefix` 用于私有成员
- **导入顺序**: 标准库 → 第三方库 → 本地模块
- **异步编程**: 对I/O操作使用async/await
- **日志记录**: 使用loguru进行一致的日志记录
- **错误处理**: 使用带有具体异常的try/except
- **文档**: 为类和公共函数编写docstrings

## 🧩 系统架构

- **框架**: NoneBot2框架与插件架构
- **数据库**: MongoDB持久化存储
- **设计模式**: 工厂模式和单例管理器
- **配置管理**: 使用环境变量和TOML文件
- **内存系统**: 基于图的记忆结构，支持记忆构建、压缩、检索和遗忘
- **情绪系统**: 情绪模拟与概率权重
- **LLM集成**: 支持多个LLM服务提供商(ChatAnywhere, SiliconFlow, DeepSeek)

## ⚙️ 环境配置

- 使用`template.env`作为环境变量模板
- 使用`template/bot_config_template.toml`作为机器人配置模板
- MongoDB配置: 主机、端口、数据库名
- API密钥配置: 各LLM提供商的API密钥

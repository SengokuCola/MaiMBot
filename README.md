# 麦麦！MaiMBot (编辑中) 


<div align="center">

![Python Version](https://img.shields.io/badge/Python-3.9+-blue)
![License](https://img.shields.io/github/license/SengokuCola/MaiMBot)
![Status](https://img.shields.io/badge/状态-开发中-yellow)

</div>

## 📝 项目简介

**🍔麦麦是一个基于大语言模型的智能QQ群聊机器人**

- 基于 nonebot2 框架开发
- LLM 提供对话能力
- MongoDB 提供数据持久化支持
- NapCat 作为QQ协议端支持

**最新版本: v0.5.***

<div align="center">
<a href="https://www.bilibili.com/video/BV1amAneGE3P" target="_blank">
    <img src="docs/video.png" width="300" alt="麦麦演示视频">
    <br>
    👆 点击观看麦麦演示视频 👆

</a>
</div>

> ⚠️ **注意事项**
> - 项目处于活跃开发阶段，代码可能随时更改
> - 文档未完善，有问题可以提交 Issue 或者 Discussion
> - QQ机器人存在被限制风险，请自行了解，谨慎使用
> - 由于持续迭代，可能存在一些已知或未知的bug
> - 由于开发中，可能消耗较多token

**交流群**: 766798517 一群人较多，建议加下面的（开发和建议相关讨论）不一定有空回复，会优先写文档和代码
**交流群**: 571780722 另一个群（开发和建议相关讨论）不一定有空回复，会优先写文档和代码
**交流群**: 1035228475 另一个群（开发和建议相关讨论）不一定有空回复，会优先写文档和代码

## 
<div align="left">
<h2>📚 文档        ⬇️ 快速开始使用麦麦 ⬇️</h2>
</div>

### 部署方式

如果你不知道Docker是什么，建议寻找相关教程或使用手动部署（现在不建议使用docker，更新慢，可能不适配）

- [🐳 Docker部署指南](docs/docker_deploy.md)


- [📦 手动部署指南 Windows](docs/manual_deploy_windows.md)


- [📦 手动部署指南 Linux](docs/manual_deploy_linux.md)

-  📦 Windows 一键傻瓜式部署，请运行项目根目录中的 ```run.bat```，部署完成后请参照后续配置指南进行配置

### 配置说明
- [🎀 新手配置指南](docs/installation_cute.md) - 通俗易懂的配置教程，适合初次使用的猫娘
- [⚙️ 标准配置指南](docs/installation_standard.md) - 简明专业的配置说明，适合有经验的用户

<div align="left">
<h3>了解麦麦 </h3>
</div>

- [项目架构说明](docs/doc1.md) - 项目结构和核心功能实现细节

## 🎯 功能介绍

### 💬 聊天功能
- 支持关键词检索主动发言：对消息的话题topic进行识别，如果检测到麦麦存储过的话题就会主动进行发言
- 支持bot名字呼唤发言：检测到"麦麦"会主动发言，可配置
- 支持多模型，多厂商自定义配置
- 动态的prompt构建器，更拟人
- 支持图片，转发消息，回复消息的识别
- 错别字和多条回复功能：麦麦可以随机生成错别字，会多条发送回复以及对消息进行reply

### 😊 表情包功能
- 支持根据发言内容发送对应情绪的表情包
- 会自动偷群友的表情包

### 📅 日程功能
- 麦麦会自动生成一天的日程，实现更拟人的回复

### 🧠 记忆功能
- 对聊天记录进行概括存储，在需要时调用，待完善

### 📚 知识库功能
- 基于embedding模型的知识库，手动放入txt会自动识别，写完了，暂时禁用

### 👥 关系功能
- 针对每个用户创建"关系"，可以对不同用户进行个性化回复，目前只有极其简单的好感度（WIP）
- 针对每个群创建"群印象"，可以对不同群进行个性化回复（WIP）



## 开发计划TODO：LIST

规划主线
0.6.0：记忆系统更新
0.7.0: 麦麦RunTime


- 人格功能：WIP
- 群氛围功能：WIP
- 图片发送，转发功能：WIP
- 幽默和meme功能：WIP的WIP
- 让麦麦玩mc：WIP的WIP的WIP
- 兼容gif的解析和保存
- 小程序转发链接解析
- 对思考链长度限制
- 修复已知bug
- ~~完善文档~~
- 修复转发
- ~~config自动生成和检测~~
- ~~log别用print~~
- ~~给发送消息写专门的类~~
- 改进表情包发送逻辑
- 自动生成的回复逻辑，例如自生成的回复方向，回复风格
- 采用截断生成加快麦麦的反应速度
- 改进发送消息的触发


## 设计理念

- **千石可乐说：**
- 这个项目最初只是为了给牛牛bot添加一点额外的功能，但是功能越写越多，最后决定重写。其目的是为了创造一个活跃在QQ群聊的"生命体"。可以目的并不是为了写一个功能齐全的机器人，而是一个尽可能让人感知到真实的类人存在.
- 程序的功能设计理念基于一个核心的原则："最像而不是好"
- 主打一个陪伴
- 如果人类真的需要一个AI来陪伴自己，并不是所有人都需要一个完美的，能解决所有问题的helpful assistant，而是一个会犯错的，拥有自己感知和想法的"生命形式"。
- 代码会保持开源和开放，但个人希望MaiMbot的运行时数据保持封闭，尽量避免以显式命令来对其进行控制和调试.我认为一个你无法完全掌控的个体才更能让你感觉到它的自主性，而视其成为一个对话机器.


## 📌 注意事项
SengokuCola纯编程外行，面向cursor编程，很多代码史一样多多包涵

> ⚠️ **警告**：本应用生成内容来自人工智能模型，由 AI 生成，请仔细甄别，请勿用于违反法律的用途，AI生成内容不代表本人观点和立场。

## 致谢
[nonebot2](https://github.com/nonebot/nonebot2): 跨平台 Python 异步聊天机器人框架  
[NapCat](https://github.com/NapNeko/NapCatQQ): 现代化的基于 NTQQ 的 Bot 协议端实现  

### 贡献者

感谢各位大佬！

<a href="https://github.com/SengokuCola/MaiMBot/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=SengokuCola/MaiMBot&time=true" />
</a>


## Stargazers over time
[![Stargazers over time](https://starchart.cc/SengokuCola/MaiMBot.svg?variant=adaptive)](https://starchart.cc/SengokuCola/MaiMBot)

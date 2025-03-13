import gradio as gr
import os
import sys
import toml
from loguru import logger
import shutil
import ast
import json


is_share = False
debug = False
config_data = toml.load("config/bot_config.toml")

#==============================================
#env环境配置文件读取部分
def parse_env_config(config_file):
    """
    解析配置文件并将配置项存储到相应的变量中（变量名以env_为前缀）。
    """
    env_variables = {}

    # 读取配置文件
    with open(config_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 逐行处理配置
    for line in lines:
        line = line.strip()
        # 忽略空行和注释
        if not line or line.startswith("#"):
            continue

        # 拆分键值对
        key, value = line.split("=", 1)

        # 去掉空格并去除两端引号（如果有的话）
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        # 将配置项存入以env_为前缀的变量
        env_variable = f"env_{key}"
        env_variables[env_variable] = value

        # 动态创建环境变量
        os.environ[env_variable] = value

    return env_variables

#env环境配置文件保存函数
def save_to_env_file(env_variables, filename=".env.prod"):
    """
    将修改后的变量保存到指定的.env文件中，并在第一次保存前备份文件（如果备份文件不存在）。
    """
    backup_filename = f"{filename}.bak"

    # 如果备份文件不存在，则备份原文件
    if not os.path.exists(backup_filename):
        if os.path.exists(filename):
            logger.info(f"{filename} 已存在，正在备份到 {backup_filename}...")
            shutil.copy(filename, backup_filename)  # 备份文件
            logger.success(f"文件已备份到 {backup_filename}")
        else:
            logger.warning(f"{filename} 不存在，无法进行备份。")

    # 保存新配置
    with open(filename, "w",encoding="utf-8") as f:
        for var, value in env_variables.items():
            f.write(f"{var[4:]}={value}\n")  # 移除env_前缀
    logger.info(f"配置已保存到 {filename}")

env_config_file = ".env.prod"  # 配置文件路径
env_config_data = parse_env_config(env_config_file)
#env读取保存结束
#==============================================

#==============================================
#env环境文件中插件修改更新函数
def add_item(new_item, current_list):
    updated_list = current_list.copy()
    if new_item.strip():
        updated_list.append(new_item.strip())
    return [
        updated_list,  # 更新State
        "\n".join(updated_list),  # 更新TextArea
        gr.update(choices=updated_list),  # 更新Dropdown
        ", ".join(updated_list)  # 更新最终结果
    ]

def delete_item(selected_item, current_list):
    updated_list = current_list.copy()
    if selected_item in updated_list:
        updated_list.remove(selected_item)
    return [
        updated_list,
        "\n".join(updated_list),
        gr.update(choices=updated_list),
        ", ".join(updated_list)
    ]
#env文件中插件值处理函数
def parse_list_str(input_str):
    """
    将形如["src2.plugins.chat"]的字符串解析为Python列表
    parse_list_str('["src2.plugins.chat"]')
    ['src2.plugins.chat']
    parse_list_str("['plugin1', 'plugin2']")
    ['plugin1', 'plugin2']
    """
    try:
        return ast.literal_eval(input_str.strip())
    except (ValueError, SyntaxError):
        # 处理不符合Python列表格式的字符串
        cleaned = input_str.strip(" []")  # 去除方括号
        return [item.strip(" '\"") for item in cleaned.split(",") if item.strip()]

def format_list_to_str(lst):
    """
    将Python列表转换为形如["src2.plugins.chat"]的字符串格式
    format_list_to_str(['src2.plugins.chat'])
    '["src2.plugins.chat"]'
    format_list_to_str([1, "two", 3.0])
    '[1, "two", 3.0]'
    """
    resarr = lst.split(", ")
    res = ""
    for items in resarr:
        temp = '"' + str(items) + '"'
        res += temp + ", "

    res = res[:-2]
    return "[" + res + "]"

#env保存函数
def save_trigger(server_address, server_port, final_result_list,t_mongodb_host,t_mongodb_port,t_mongodb_database_name,t_chatanywhere_base_url,t_chatanywhere_key,t_siliconflow_base_url,t_siliconflow_key,t_deepseek_base_url,t_deepseek_key):
    final_result_lists = format_list_to_str(final_result_list)
    env_config_data["env_HOST"] = server_address
    env_config_data["env_PORT"] = server_port
    env_config_data["env_PLUGINS"] = final_result_lists
    env_config_data["env_MONGODB_HOST"] = t_mongodb_host
    env_config_data["env_MONGODB_PORT"] = t_mongodb_port
    env_config_data["env_DATABASE_NAME"] = t_mongodb_database_name
    env_config_data["env_CHAT_ANY_WHERE_BASE_URL"] = t_chatanywhere_base_url
    env_config_data["env_CHAT_ANY_WHERE_KEY"] = t_chatanywhere_key
    env_config_data["env_SILICONFLOW_BASE_URL"] = t_siliconflow_base_url
    env_config_data["env_SILICONFLOW_KEY"] = t_siliconflow_key
    env_config_data["env_DEEP_SEEK_BASE_URL"] = t_deepseek_base_url
    env_config_data["env_DEEP_SEEK_KEY"] = t_deepseek_key
    save_to_env_file(env_config_data)
    logger.success("配置已保存到 .env.prod 文件中")
    return "配置已保存"

#==============================================


#==============================================
#主要配置文件保存函数
def save_config_to_file(t_config_data):
    with open("config/bot_config.toml", "w", encoding="utf-8") as f:
        toml.dump(t_config_data, f)
    logger.success("配置已保存到 bot_config.toml 文件中")
def save_bot_config(t_qqbot_qq, t_nickname):
    config_data["bot"]["qq"] = t_qqbot_qq
    config_data["bot"]["nickname"] = t_nickname
    save_config_to_file(config_data)
    logger.info("Bot配置已保存")
    return "Bot配置已保存"

# 监听滑块的值变化，确保总和不超过 1，并显示警告
def adjust_greater_probabilities(t_personality_1, t_personality_2, t_personality_3):
    total = t_personality_1 + t_personality_2 + t_personality_3
    if total > 1.0:
        warning_message = f"警告: 人格1、人格2和人格3的概率总和为 {total:.2f}，超过了 1.0！请调整滑块使总和不超过 1.0。"
        return warning_message
    else:
        return ""  # 没有警告时返回空字符串

def adjust_less_probabilities(t_personality_1, t_personality_2, t_personality_3):
    total = t_personality_1 + t_personality_2 + t_personality_3
    if total < 1.0:
        warning_message = f"警告: 人格1、人格2和人格3的概率总和为 {total:.2f}，小于 1.0！请调整滑块使总和不超过 1.0。"
        return warning_message
    else:
        return ""  # 没有警告时返回空字符串

#==============================================
#人格保存函数
def save_personality_config(t_personality_1, t_personality_2, t_personality_3, t_prompt_schedule):
    config_data["personality"]["personality_1_probability"] = t_personality_1
    config_data["personality"]["personality_2_probability"] = t_personality_2
    config_data["personality"]["personality_3_probability"] = t_personality_3
    config_data["personality"]["prompt_schedule"] = t_prompt_schedule
    save_config_to_file(config_data)
    logger.info("人格配置已保存到 bot_config.toml 文件中")
    return "人格配置已保存"

with (gr.Blocks(title="MaimBot配置文件编辑") as app):
    gr.Markdown(
        value="""
        欢迎使用由墨梓柒MotricSeven编写的MaimBot配置文件编辑器\n
        """
    )
    gr.Markdown(
        value="配置文件版本：" + config_data["inner"]["version"]
    )
    with gr.Tabs():
        with gr.TabItem("0-环境设置"):
            with gr.Row():
                with gr.Column(scale=3):
                    with gr.Row():
                        gr.Markdown(
                            value="""
                            MaimBot服务器地址，默认127.0.0.1\n
                            不熟悉配置的不要轻易改动此项！！\n
                            """
                        )
                    with gr.Row():
                        server_address = gr.Textbox(
                            label="服务器地址",
                            value=env_config_data["env_HOST"],
                            interactive=True
                        )
                    with gr.Row():
                        server_port = gr.Textbox(
                            label="服务器端口",
                            value=env_config_data["env_PORT"],
                            interactive=True
                        )
                    with gr.Row():
                        plugin_list = parse_list_str(env_config_data['env_PLUGINS'])
                        with gr.Blocks():
                            list_state = gr.State(value=plugin_list.copy())

                        with gr.Row():
                            list_display = gr.TextArea(
                                value="\n".join(plugin_list),
                                label="插件列表",
                                interactive=False,
                                lines=5
                            )
                        with gr.Row():
                            with gr.Column(scale=3):
                                new_item_input = gr.Textbox(label="添加新插件")
                                add_btn = gr.Button("添加", scale=1)

                        with gr.Row():
                            with gr.Column(scale=3):
                                item_to_delete = gr.Dropdown(
                                    choices=plugin_list,
                                    label="选择要删除的插件"
                                )
                            delete_btn = gr.Button("删除", scale=1)

                        final_result = gr.Text(label="修改后的列表")
                        add_btn.click(
                            add_item,
                           inputs=[new_item_input, list_state],
                            outputs=[list_state, list_display, item_to_delete, final_result]
                        )

                        delete_btn.click(
                            delete_item,
                            inputs=[item_to_delete, list_state],
                            outputs=[list_state, list_display, item_to_delete, final_result]
                            )
                    with gr.Row():
                        gr.Markdown(
                            '''MongoDB设置项\n
                            保持默认即可，如果你有能力承担修改过后的后果（简称能改回来（笑））\n
                            可以对以下配置项进行修改\n
                            '''
                        )
                    with gr.Row():
                        mongodb_host = gr.Textbox(
                            label="MongoDB服务器地址",
                            value=env_config_data["env_MONGODB_HOST"],
                            interactive=True
                        )
                    with gr.Row():
                        mongodb_port = gr.Textbox(
                            label="MongoDB服务器端口",
                            value=env_config_data["env_MONGODB_PORT"],
                            interactive=True
                        )
                    with gr.Row():
                        mongodb_database_name = gr.Textbox(
                            label="MongoDB数据库名称",
                            value=env_config_data["env_DATABASE_NAME"],
                            interactive=True
                        )
                    with gr.Row():
                        gr.Markdown(
                            '''ChatAntWhere的baseURL和APIkey\n
                            改完了记得保存！！！
                            '''
                        )
                    with gr.Row():
                        chatanywhere_base_url = gr.Textbox(
                            label="ChatAntWhere的BaseURL",
                            value=env_config_data["env_CHAT_ANY_WHERE_BASE_URL"],
                            interactive=True
                        )
                    with gr.Row():
                        chatanywhere_key = gr.Textbox(
                            label="ChatAntWhere的key",
                            value=env_config_data["env_CHAT_ANY_WHERE_KEY"],
                            interactive=True
                        )
                    with gr.Row():
                        gr.Markdown(
                            '''SiliconFlow的baseURL和APIkey\n
                            改完了记得保存！！！
                            '''
                        )
                    with gr.Row():
                        siliconflow_base_url = gr.Textbox(
                            label="SiliconFlow的BaseURL",
                            value=env_config_data["env_SILICONFLOW_BASE_URL"],
                            interactive=True
                        )
                    with gr.Row():
                        siliconflow_key = gr.Textbox(
                            label="SiliconFlow的key",
                            value=env_config_data["env_SILICONFLOW_KEY"],
                            interactive=True
                        )
                    with gr.Row():
                        gr.Markdown(
                            '''DeepSeek的baseURL和APIkey\n
                            改完了记得保存！！！
                            '''
                        )
                    with gr.Row():
                        deepseek_base_url = gr.Textbox(
                            label="DeepSeek的BaseURL",
                            value=env_config_data["env_DEEP_SEEK_BASE_URL"],
                            interactive=True
                        )
                    with gr.Row():
                        deepseek_key = gr.Textbox(
                            label="DeepSeek的key",
                            value=env_config_data["env_DEEP_SEEK_KEY"],
                            interactive=True
                        )
                    with gr.Row():
                        save_env_btn = gr.Button("保存环境配置")
                    with gr.Row():
                        save_env_btn.click(
                            save_trigger,
                            inputs=[server_address,server_port,final_result,mongodb_host,mongodb_port,mongodb_database_name,chatanywhere_base_url,chatanywhere_key,siliconflow_base_url,siliconflow_key,deepseek_base_url,deepseek_key],
                            outputs=[gr.Textbox(
                                label="保存结果",
                                interactive=False
                            )]
                        )
        with gr.TabItem("1-Bot基础设置"):
            with gr.Row():
                with gr.Column(scale=3):
                    with gr.Row():
                        qqbot_qq = gr.Textbox(
                            label="QQ机器人QQ号",
                            value=config_data["bot"]["qq"],
                            interactive=True
                        )
                    with gr.Row():
                        nickname = gr.Textbox(
                            label="昵称",
                            value=config_data["bot"]["nickname"],
                            interactive=True
                        )
                    with gr.Row():
                        nickname_list = config_data['bot']['alias_names']
                        with gr.Blocks():
                            nickname_list_state = gr.State(value=nickname_list.copy())

                        with gr.Row():
                            nickname_list_display = gr.TextArea(
                                value="\n".join(nickname_list),
                                label="别名列表",
                                interactive=False,
                                lines=5
                            )
                        with gr.Row():
                            with gr.Column(scale=3):
                                nickname_new_item_input = gr.Textbox(label="添加新别名")
                                nickname_add_btn = gr.Button("添加", scale=1)

                        with gr.Row():
                            with gr.Column(scale=3):
                                nickname_item_to_delete = gr.Dropdown(
                                    choices=nickname_list,
                                    label="选择要删除的别名"
                                )
                            nickname_delete_btn = gr.Button("删除", scale=1)

                        nickname_final_result = gr.Text(label="修改后的列表")
                        nickname_add_btn.click(
                            add_item,
                            inputs=[nickname_new_item_input, nickname_list_state],
                            outputs=[nickname_list_state, nickname_list_display, nickname_item_to_delete, nickname_final_result]
                        )

                        nickname_delete_btn.click(
                            delete_item,
                            inputs=[nickname_item_to_delete, nickname_list_state],
                            outputs=[nickname_list_state, nickname_list_display, nickname_item_to_delete, nickname_final_result]
                        )
                    gr.Button(
                        "保存Bot配置",
                        variant="primary",
                        elem_id="save_bot_btn",
                        elem_classes="save_bot_btn"
                    ).click(
                        save_bot_config,
                        inputs=[qqbot_qq, nickname],
                        outputs=[gr.Textbox(
                            label="保存Bot结果"
                        )]
                    )
        with gr.TabItem("2-人格设置"):
            with gr.Row():
                with gr.Column(scale=3):
                    with gr.Row():
                        prompt_personality_1 = gr.Textbox(
                            label="人格1提示词",
                            value=config_data['personality']['prompt_personality'][0],
                            interactive=True
                        )
                    with gr.Row():
                        prompt_personality_2 = gr.Textbox(
                            label="人格2提示词",
                            value=config_data['personality']['prompt_personality'][1],
                            interactive=True
                        )
                    with gr.Row():
                        prompt_personality_3 = gr.Textbox(
                            label="人格3提示词",
                            value=config_data['personality']['prompt_personality'][2],
                            interactive=True
                        )
                with gr.Column(scale=3):
                    # 创建三个滑块
                    personality_1 = gr.Slider(minimum=0, maximum=1, step=0.01, value=config_data["personality"]["personality_1_probability"], label="人格1概率")
                    personality_2 = gr.Slider(minimum=0, maximum=1, step=0.01, value=config_data["personality"]["personality_2_probability"], label="人格2概率")
                    personality_3 = gr.Slider(minimum=0, maximum=1, step=0.01, value=config_data["personality"]["personality_3_probability"], label="人格3概率")

                    # 用于显示警告消息
                    warning_greater_text = gr.Markdown()
                    warning_less_text = gr.Markdown()

                    # 绑定滑块的值变化事件，确保总和必须等于 1.0
                    personality_1.change(adjust_greater_probabilities, inputs=[personality_1, personality_2, personality_3], outputs=[warning_greater_text])
                    personality_2.change(adjust_greater_probabilities, inputs=[personality_1, personality_2, personality_3], outputs=[warning_greater_text])
                    personality_3.change(adjust_greater_probabilities, inputs=[personality_1, personality_2, personality_3], outputs=[warning_greater_text])
                    personality_1.change(adjust_less_probabilities, inputs=[personality_1, personality_2, personality_3], outputs=[warning_less_text])
                    personality_2.change(adjust_less_probabilities, inputs=[personality_1, personality_2, personality_3], outputs=[warning_less_text])
                    personality_3.change(adjust_less_probabilities, inputs=[personality_1, personality_2, personality_3], outputs=[warning_less_text])
            with gr.Row():
                prompt_schedule = gr.Textbox(
                    label="日程生成提示词",
                    value=config_data["personality"]["prompt_schedule"],
                    interactive=True
                )
            with gr.Row():
                gr.Button(
                    "保存人格配置",
                    variant="primary",
                    elem_id="save_personality_btn",
                    elem_classes="save_personality_btn"
                ).click(
                    save_personality_config,
                    inputs=[personality_1, personality_2, personality_3, prompt_schedule],
                    outputs=[gr.Textbox(
                        label="保存人格结果"
                    )]
                )
        with gr.TabItem("3-消息设置"):
            with gr.Row():
                with gr.Column(scale=3):
                    gr.Markdown(
                        '''Coming Soooooooooooooooooooooooooooooooooooooooon'''
                    )





    app.queue().launch(#concurrency_count=511, max_size=1022
        server_name="0.0.0.0",
        inbrowser=True,
        share=is_share,
        server_port=7000,
        debug=debug,
        quiet=True,
    )
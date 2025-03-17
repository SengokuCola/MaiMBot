import gradio as gr
import os
import sys
import toml
from src.common.logger import get_module_logger
import shutil
import ast
import json
from packaging import version

logger = get_module_logger("webui")

is_share = False
debug = True
config_data = toml.load("config/bot_config.toml")

CONFIG_VERSION = config_data["inner"]["version"]
PARSED_CONFIG_VERSION = version.parse(CONFIG_VERSION)
HAVE_ONLINE_STATUS_VERSION = version.parse("0.0.9")

# ==============================================
# env环境配置文件读取部分
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

# env环境配置文件保存函数
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


# 载入env文件并解析
env_config_file = ".env.prod"  # 配置文件路径
env_config_data = parse_env_config(env_config_file)
if "env_VOLCENGINE_BASE_URL" in env_config_data:
    logger.info("VOLCENGINE_BASE_URL 已存在，使用默认值")
    env_config_data["env_VOLCENGINE_BASE_URL"] = "https://ark.cn-beijing.volces.com/api/v3"
else:
    logger.info("VOLCENGINE_BASE_URL 不存在，已创建并使用默认值")
    env_config_data["env_VOLCENGINE_BASE_URL"] = "https://ark.cn-beijing.volces.com/api/v3"

if "env_VOLCENGINE_KEY" in env_config_data:
    logger.info("VOLCENGINE_KEY 已存在，保持不变")
else:
    logger.info("VOLCENGINE_KEY 不存在，已创建并使用默认值")
    env_config_data["env_VOLCENGINE_KEY"] = "volc_key"
save_to_env_file(env_config_data, env_config_file)
MODEL_PROVIDER_LIST = [
    "VOLCENGINE",
    "CHAT_ANY_WHERE",
    "SILICONFLOW",
    "DEEP_SEEK"
]
# env读取保存结束
# ==============================================

# ==============================================
# env环境文件中插件修改更新函数
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

def add_int_item(new_item, current_list):
    updated_list = current_list.copy()
    stripped_item = new_item.strip()
    if stripped_item:
        try:
            item = int(stripped_item)
            updated_list.append(item)
        except ValueError:
            pass
    return [
        updated_list,  # 更新State
        "\n".join(map(str, updated_list)),  # 更新TextArea
        gr.update(choices=updated_list),  # 更新Dropdown
        ", ".join(map(str, updated_list))  # 更新最终结果
    ]

def delete_int_item(selected_item, current_list):
    updated_list = current_list.copy()
    if selected_item in updated_list:
        updated_list.remove(selected_item)
    return [
        updated_list,
        "\n".join(map(str, updated_list)),
        gr.update(choices=updated_list),
        ", ".join(map(str, updated_list))
    ]
# env文件中插件值处理函数
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
        res += temp + ","

    res = res[:-1]
    return "[" + res + "]"


# env保存函数
def save_trigger(server_address, server_port, final_result_list,t_mongodb_host,t_mongodb_port,t_mongodb_database_name,t_chatanywhere_base_url,t_chatanywhere_key,t_siliconflow_base_url,t_siliconflow_key,t_deepseek_base_url,t_deepseek_key,t_volcengine_base_url,t_volcengine_key):
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
    env_config_data["env_VOLCENGINE_BASE_URL"] = t_volcengine_base_url
    env_config_data["env_VOLCENGINE_KEY"] = t_volcengine_key
    save_to_env_file(env_config_data)
    logger.success("配置已保存到 .env.prod 文件中")
    return "配置已保存"

# ==============================================


# ==============================================
# 主要配置文件保存函数
def save_config_to_file(t_config_data):
    filename = "config/bot_config.toml"
    backup_filename = f"{filename}.bak"
    if not os.path.exists(backup_filename):
        if os.path.exists(filename):
            logger.info(f"{filename} 已存在，正在备份到 {backup_filename}...")
            shutil.copy(filename, backup_filename)  # 备份文件
            logger.success(f"文件已备份到 {backup_filename}")
        else:
            logger.warning(f"{filename} 不存在，无法进行备份。")


    with open(filename, "w", encoding="utf-8") as f:
        toml.dump(t_config_data, f)
    logger.success("配置已保存到 bot_config.toml 文件中")
def save_bot_config(t_qqbot_qq, t_nickname,t_nickname_final_result):
    config_data["bot"]["qq"] = int(t_qqbot_qq)
    config_data["bot"]["nickname"] = t_nickname
    config_data["bot"]["alias_names"] = t_nickname_final_result
    save_config_to_file(config_data)
    logger.info("Bot配置已保存")
    return "Bot配置已保存"

# 监听滑块的值变化，确保总和不超过 1，并显示警告
def adjust_personality_greater_probabilities(t_personality_1_probability, t_personality_2_probability, t_personality_3_probability):
    total = t_personality_1_probability + t_personality_2_probability + t_personality_3_probability
    if total > 1.0:
        warning_message = f"警告: 人格1、人格2和人格3的概率总和为 {total:.2f}，超过了 1.0！请调整滑块使总和等于 1.0。"
        return warning_message
    return ""  # 没有警告时返回空字符串

def adjust_personality_less_probabilities(t_personality_1_probability, t_personality_2_probability, t_personality_3_probability):
    total = t_personality_1_probability + t_personality_2_probability + t_personality_3_probability
    if total < 1.0:
        warning_message = f"警告: 人格1、人格2和人格3的概率总和为 {total:.2f}，小于 1.0！请调整滑块使总和等于 1.0。"
        return warning_message
    return ""  # 没有警告时返回空字符串

def adjust_model_greater_probabilities(t_model_1_probability, t_model_2_probability, t_model_3_probability):
    total = t_model_1_probability + t_model_2_probability + t_model_3_probability
    if total > 1.0:
        warning_message = f"警告: 选择模型1、模型2和模型3的概率总和为 {total:.2f}，超过了 1.0！请调整滑块使总和等于 1.0。"
        return warning_message
    return ""  # 没有警告时返回空字符串

def adjust_model_less_probabilities(t_model_1_probability, t_model_2_probability, t_model_3_probability):
    total = t_model_1_probability + t_model_2_probability + t_model_3_probability
    if total > 1.0:
        warning_message = f"警告: 选择模型1、模型2和模型3的概率总和为 {total:.2f}，小于了 1.0！请调整滑块使总和等于 1.0。"
        return warning_message
    return ""  # 没有警告时返回空字符串


# ==============================================
# 人格保存函数
def save_personality_config(t_prompt_personality_1,
                            t_prompt_personality_2,
                            t_prompt_personality_3,
                            t_prompt_schedule,
                            t_personality_1_probability,
                            t_personality_2_probability,
                            t_personality_3_probability):
    # 保存人格提示词
    config_data["personality"]["prompt_personality"][0] = t_prompt_personality_1
    config_data["personality"]["prompt_personality"][1] = t_prompt_personality_2
    config_data["personality"]["prompt_personality"][2] = t_prompt_personality_3

    # 保存日程生成提示词
    config_data["personality"]["prompt_schedule"] = t_prompt_schedule

    # 保存三个人格的概率
    config_data["personality"]["personality_1_probability"] = t_personality_1_probability
    config_data["personality"]["personality_2_probability"] = t_personality_2_probability
    config_data["personality"]["personality_3_probability"] = t_personality_3_probability

    save_config_to_file(config_data)
    logger.info("人格配置已保存到 bot_config.toml 文件中")
    return "人格配置已保存"


def save_message_and_emoji_config(t_min_text_length,
                                  t_max_context_size,
                                  t_emoji_chance,
                                  t_thinking_timeout,
                                  t_response_willing_amplifier,
                                  t_response_interested_rate_amplifier,
                                  t_down_frequency_rate,
                                  t_ban_words_final_result,
                                  t_ban_msgs_regex_final_result,
                                  t_check_interval,
                                  t_register_interval,
                                  t_auto_save,
                                  t_enable_check,
                                  t_check_prompt):
    config_data["message"]["min_text_length"] = t_min_text_length
    config_data["message"]["max_context_size"] = t_max_context_size
    config_data["message"]["emoji_chance"] = t_emoji_chance
    config_data["message"]["thinking_timeout"] = t_thinking_timeout
    config_data["message"]["response_willing_amplifier"] = t_response_willing_amplifier
    config_data["message"]["response_interested_rate_amplifier"] = t_response_interested_rate_amplifier
    config_data["message"]["down_frequency_rate"] = t_down_frequency_rate
    config_data["message"]["ban_words"] =t_ban_words_final_result
    config_data["message"]["ban_msgs_regex"] = t_ban_msgs_regex_final_result
    config_data["emoji"]["check_interval"] = t_check_interval
    config_data["emoji"]["register_interval"] = t_register_interval
    config_data["emoji"]["auto_save"] = t_auto_save
    config_data["emoji"]["enable_check"] = t_enable_check
    config_data["emoji"]["check_prompt"] = t_check_prompt
    save_config_to_file(config_data)
    logger.info("消息和表情配置已保存到 bot_config.toml 文件中")
    return "消息和表情配置已保存"

def save_response_model_config(t_model_r1_probability,
                               t_model_r2_probability,
                               t_model_r3_probability,
                               t_max_response_length,
                               t_model1_name,
                               t_model1_provider,
                               t_model1_pri_in,
                               t_model1_pri_out,
                               t_model2_name,
                               t_model2_provider,
                               t_model3_name,
                               t_model3_provider,
                               t_emotion_model_name,
                               t_emotion_model_provider,
                               t_topic_judge_model_name,
                               t_topic_judge_model_provider,
                               t_summary_by_topic_model_name,
                               t_summary_by_topic_model_provider,
                               t_vlm_model_name,
                               t_vlm_model_provider):
    config_data["response"]["model_r1_probability"] = t_model_r1_probability
    config_data["response"]["model_v3_probability"] = t_model_r2_probability
    config_data["response"]["model_r1_distill_probability"] = t_model_r3_probability
    config_data["response"]["max_response_length"] = t_max_response_length
    config_data['model']['llm_reasoning']['name'] = t_model1_name
    config_data['model']['llm_reasoning']['provider'] = t_model1_provider
    config_data['model']['llm_reasoning']['pri_in'] = t_model1_pri_in
    config_data['model']['llm_reasoning']['pri_out'] = t_model1_pri_out
    config_data['model']['llm_normal']['name'] = t_model2_name
    config_data['model']['llm_normal']['provider'] = t_model2_provider
    config_data['model']['llm_reasoning_minor']['name'] = t_model3_name
    config_data['model']['llm_normal']['provider'] = t_model3_provider
    config_data['model']['llm_emotion_judge']['name'] = t_emotion_model_name
    config_data['model']['llm_emotion_judge']['provider'] = t_emotion_model_provider
    config_data['model']['llm_topic_judge']['name'] = t_topic_judge_model_name
    config_data['model']['llm_topic_judge']['provider'] = t_topic_judge_model_provider
    config_data['model']['llm_summary_by_topic']['name'] = t_summary_by_topic_model_name
    config_data['model']['llm_summary_by_topic']['provider'] = t_summary_by_topic_model_provider
    config_data['model']['vlm']['name'] = t_vlm_model_name
    config_data['model']['vlm']['provider'] = t_vlm_model_provider
    save_config_to_file(config_data)
    logger.info("回复&模型设置已保存到 bot_config.toml 文件中")
    return "回复&模型设置已保存"
def save_memory_mood_config(t_build_memory_interval, t_memory_compress_rate, t_forget_memory_interval, t_memory_forget_time, t_memory_forget_percentage, t_memory_ban_words_final_result, t_mood_update_interval, t_mood_decay_rate, t_mood_intensity_factor):
    config_data["memory"]["build_memory_interval"] = t_build_memory_interval
    config_data["memory"]["memory_compress_rate"] = t_memory_compress_rate
    config_data["memory"]["forget_memory_interval"] = t_forget_memory_interval
    config_data["memory"]["memory_forget_time"] = t_memory_forget_time
    config_data["memory"]["memory_forget_percentage"] = t_memory_forget_percentage
    config_data["memory"]["memory_ban_words"] = t_memory_ban_words_final_result
    config_data["mood"]["update_interval"] = t_mood_update_interval
    config_data["mood"]["decay_rate"] = t_mood_decay_rate
    config_data["mood"]["intensity_factor"] = t_mood_intensity_factor
    save_config_to_file(config_data)
    logger.info("记忆和心情设置已保存到 bot_config.toml 文件中")
    return "记忆和心情设置已保存"

def save_other_config(t_keywords_reaction_enabled,t_enable_advance_output, t_enable_kuuki_read, t_enable_debug_output, t_enable_friend_chat, t_chinese_typo_enabled, t_error_rate, t_min_freq, t_tone_error_rate, t_word_replace_rate,t_remote_status):
    config_data['keywords_reaction']['enable'] = t_keywords_reaction_enabled
    config_data['others']['enable_advance_output'] = t_enable_advance_output
    config_data['others']['enable_kuuki_read'] = t_enable_kuuki_read
    config_data['others']['enable_debug_output'] = t_enable_debug_output
    config_data['others']['enable_friend_chat'] = t_enable_friend_chat
    config_data["chinese_typo"]["enable"] = t_chinese_typo_enabled
    config_data["chinese_typo"]["error_rate"] = t_error_rate
    config_data["chinese_typo"]["min_freq"] = t_min_freq
    config_data["chinese_typo"]["tone_error_rate"] = t_tone_error_rate
    config_data["chinese_typo"]["word_replace_rate"] = t_word_replace_rate
    if PARSED_CONFIG_VERSION > 0.8:
        config_data["remote"]["enable"] = t_remote_status
    save_config_to_file(config_data)
    logger.info("其他设置已保存到 bot_config.toml 文件中")
    return "其他设置已保存"

def save_group_config(t_talk_allowed_final_result,
                      t_talk_frequency_down_final_result,
                      t_ban_user_id_final_result,):
    config_data["groups"]["talk_allowed"] = t_talk_allowed_final_result
    config_data["groups"]["talk_frequency_down"] = t_talk_frequency_down_final_result
    config_data["groups"]["ban_user_id"] = t_ban_user_id_final_result
    save_config_to_file(config_data)
    logger.info("群聊设置已保存到 bot_config.toml 文件中")
    return "群聊设置已保存"

with gr.Blocks(title="MaimBot配置文件编辑") as app:
    gr.Markdown(
        value="""
        ### 欢迎使用由墨梓柒MotricSeven编写的MaimBot配置文件编辑器\n
        """
    )
    gr.Markdown(
        value="### 配置文件版本：" + config_data["inner"]["version"]
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
                        volcengine_base_url = gr.Textbox(
                            label="VolcEngine的BaseURL",
                            value=env_config_data["env_VOLCENGINE_BASE_URL"],
                            interactive=True
                        )
                    with gr.Row():
                        volcengine_key = gr.Textbox(
                            label="VolcEngine的key",
                            value=env_config_data["env_VOLCENGINE_KEY"],
                            interactive=True
                        )
                    with gr.Row():
                        save_env_btn = gr.Button("保存环境配置",variant="primary")
                    with gr.Row():
                        save_env_btn.click(
                            save_trigger,
                            inputs=[server_address,server_port,final_result,mongodb_host,mongodb_port,mongodb_database_name,chatanywhere_base_url,chatanywhere_key,siliconflow_base_url,siliconflow_key,deepseek_base_url,deepseek_key,volcengine_base_url,volcengine_key],
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
                        inputs=[qqbot_qq, nickname,nickname_list_state],
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
                            value=config_data["personality"]["prompt_personality"][0],
                            interactive=True,
                        )
                    with gr.Row():
                        prompt_personality_2 = gr.Textbox(
                            label="人格2提示词",
                            value=config_data["personality"]["prompt_personality"][1],
                            interactive=True,
                        )
                    with gr.Row():
                        prompt_personality_3 = gr.Textbox(
                            label="人格3提示词",
                            value=config_data["personality"]["prompt_personality"][2],
                            interactive=True,
                        )
                with gr.Column(scale=3):
                    # 创建三个滑块, 代表三个人格的概率
                    personality_1_probability = gr.Slider(
                        minimum=0,
                        maximum=1,
                        step=0.01,
                        value=config_data["personality"]["personality_1_probability"],
                        label="人格1概率",
                    )
                    personality_2_probability = gr.Slider(
                        minimum=0,
                        maximum=1,
                        step=0.01,
                        value=config_data["personality"]["personality_2_probability"],
                        label="人格2概率",
                    )
                    personality_3_probability = gr.Slider(
                        minimum=0,
                        maximum=1,
                        step=0.01,
                        value=config_data["personality"]["personality_3_probability"],
                        label="人格3概率",
                    )

                    # 用于显示警告消息
                    warning_greater_text = gr.Markdown()
                    warning_less_text = gr.Markdown()

                    # 绑定滑块的值变化事件，确保总和必须等于 1.0

                    # 输入的 3 个概率
                    personality_probability_change_inputs = [
                        personality_1_probability,
                        personality_2_probability,
                        personality_3_probability,
                    ]

                    # 绑定滑块的值变化事件，确保总和不大于 1.0
                    personality_1_probability.change(
                        adjust_personality_greater_probabilities,
                        inputs=personality_probability_change_inputs,
                        outputs=[warning_greater_text],
                    )
                    personality_2_probability.change(
                        adjust_personality_greater_probabilities,
                        inputs=personality_probability_change_inputs,
                        outputs=[warning_greater_text],
                    )
                    personality_3_probability.change(
                        adjust_personality_greater_probabilities,
                        inputs=personality_probability_change_inputs,
                        outputs=[warning_greater_text],
                    )

                    # 绑定滑块的值变化事件，确保总和不小于 1.0
                    personality_1_probability.change(
                        adjust_personality_less_probabilities,
                        inputs=personality_probability_change_inputs,
                        outputs=[warning_less_text],
                    )
                    personality_2_probability.change(
                        adjust_personality_less_probabilities,
                        inputs=personality_probability_change_inputs,
                        outputs=[warning_less_text],
                    )
                    personality_3_probability.change(
                        adjust_personality_less_probabilities,
                        inputs=personality_probability_change_inputs,
                        outputs=[warning_less_text],
                    )

            with gr.Row():
                prompt_schedule = gr.Textbox(
                    label="日程生成提示词",
                    value=config_data["personality"]["prompt_schedule"],
                    interactive=True
                )
            with gr.Row():
                personal_save_btn = gr.Button(
                    "保存人格配置",
                    variant="primary",
                    elem_id="save_personality_btn",
                    elem_classes="save_personality_btn"
                )
            with gr.Row():
                personal_save_message = gr.Textbox(label="保存人格结果")
            personal_save_btn.click(
                save_personality_config,
                inputs=[
                    prompt_personality_1,
                    prompt_personality_2,
                    prompt_personality_3,
                    prompt_schedule,
                    personality_1_probability,
                    personality_2_probability,
                    personality_3_probability,
                ],
                outputs=[personal_save_message],
            )
        with gr.TabItem("3-消息&表情包设置"):
            with gr.Row():
                with gr.Column(scale=3):
                    with gr.Row():
                        min_text_length = gr.Number(value=config_data['message']['min_text_length'], label="与麦麦聊天时麦麦只会回答文本大于等于此数的消息")
                    with gr.Row():
                        max_context_size = gr.Number(value=config_data['message']['max_context_size'], label="麦麦获得的上文数量")
                    with gr.Row():
                        emoji_chance = gr.Slider(minimum=0, maximum=1, step=0.01, value=config_data['message']['emoji_chance'], label="麦麦使用表情包的概率")
                    with gr.Row():
                        thinking_timeout = gr.Number(value=config_data['message']['thinking_timeout'], label="麦麦正在思考时，如果超过此秒数，则停止思考")
                    with gr.Row():
                        response_willing_amplifier = gr.Number(value=config_data['message']['response_willing_amplifier'], label="麦麦回复意愿放大系数，一般为1")
                    with gr.Row():
                        response_interested_rate_amplifier = gr.Number(value=config_data['message']['response_interested_rate_amplifier'], label="麦麦回复兴趣度放大系数,听到记忆里的内容时放大系数")
                    with gr.Row():
                        down_frequency_rate = gr.Number(value=config_data['message']['down_frequency_rate'], label="降低回复频率的群组回复意愿降低系数")
                    with gr.Row():
                        gr.Markdown("### 违禁词列表")
                    with gr.Row():
                        ban_words_list = config_data['message']['ban_words']
                        with gr.Blocks():
                            ban_words_list_state = gr.State(value=ban_words_list.copy())
                        with gr.Row():
                            ban_words_list_display = gr.TextArea(
                                value="\n".join(ban_words_list),
                                label="违禁词列表",
                                interactive=False,
                                lines=5
                            )
                        with gr.Row():
                            with gr.Column(scale=3):
                                ban_words_new_item_input = gr.Textbox(label="添加新违禁词")
                                ban_words_add_btn = gr.Button("添加", scale=1)

                        with gr.Row():
                            with gr.Column(scale=3):
                                ban_words_item_to_delete = gr.Dropdown(
                                    choices=ban_words_list,
                                    label="选择要删除的违禁词"
                                )
                            ban_words_delete_btn = gr.Button("删除", scale=1)

                        ban_words_final_result = gr.Text(label="修改后的违禁词")
                        ban_words_add_btn.click(
                            add_item,
                            inputs=[ban_words_new_item_input, ban_words_list_state],
                            outputs=[ban_words_list_state, ban_words_list_display, ban_words_item_to_delete, ban_words_final_result]
                        )

                        ban_words_delete_btn.click(
                            delete_item,
                            inputs=[ban_words_item_to_delete, ban_words_list_state],
                            outputs=[ban_words_list_state, ban_words_list_display, ban_words_item_to_delete, ban_words_final_result]
                        )
                    with gr.Row():
                        gr.Markdown("### 检测违禁消息正则表达式列表")
                    with gr.Row():
                        gr.Markdown(
                            """
                                 需要过滤的消息（原始消息）匹配的正则表达式，匹配到的消息将被过滤（支持CQ码），若不了解正则表达式请勿修改\n
                                "https?://[^\\s]+", # 匹配https链接\n
                                "\\d{4}-\\d{2}-\\d{2}", # 匹配日期\n
                                 "\\[CQ:at,qq=\\d+\\]" # 匹配@\n
                            """
                        )
                    with gr.Row():
                        ban_msgs_regex_list = config_data['message']['ban_msgs_regex']
                        with gr.Blocks():
                            ban_msgs_regex_list_state = gr.State(value=ban_msgs_regex_list.copy())
                        with gr.Row():
                            ban_msgs_regex_list_display = gr.TextArea(
                                value="\n".join(ban_msgs_regex_list),
                                label="违禁消息正则列表",
                                interactive=False,
                                lines=5
                            )
                        with gr.Row():
                            with gr.Column(scale=3):
                                ban_msgs_regex_new_item_input = gr.Textbox(label="添加新违禁消息正则")
                                ban_msgs_regex_add_btn = gr.Button("添加", scale=1)

                        with gr.Row():
                            with gr.Column(scale=3):
                                ban_msgs_regex_item_to_delete = gr.Dropdown(
                                    choices=ban_msgs_regex_list,
                                    label="选择要删除的违禁消息正则"
                                )
                            ban_msgs_regex_delete_btn = gr.Button("删除", scale=1)

                        ban_msgs_regex_final_result = gr.Text(label="修改后的违禁消息正则")
                        ban_msgs_regex_add_btn.click(
                            add_item,
                            inputs=[ban_msgs_regex_new_item_input, ban_msgs_regex_list_state],
                            outputs=[ban_msgs_regex_list_state, ban_msgs_regex_list_display, ban_msgs_regex_item_to_delete, ban_msgs_regex_final_result]
                        )

                        ban_msgs_regex_delete_btn.click(
                            delete_item,
                            inputs=[ban_msgs_regex_item_to_delete, ban_msgs_regex_list_state],
                            outputs=[ban_msgs_regex_list_state, ban_msgs_regex_list_display, ban_msgs_regex_item_to_delete, ban_msgs_regex_final_result]
                        )
                    with gr.Row():
                        check_interval = gr.Number(value=config_data['emoji']['check_interval'], label="检查表情包的时间间隔")
                    with gr.Row():
                        register_interval = gr.Number(value=config_data['emoji']['register_interval'], label="注册表情包的时间间隔")
                    with gr.Row():
                        auto_save = gr.Checkbox(value=config_data['emoji']['auto_save'], label="自动保存表情包")
                    with gr.Row():
                        enable_check = gr.Checkbox(value=config_data['emoji']['enable_check'], label="启用表情包检查")
                    with gr.Row():
                        check_prompt = gr.Textbox(value=config_data['emoji']['check_prompt'], label="表情包过滤要求")
                    with gr.Row():
                        emoji_save_btn = gr.Button(
                            "保存消息&表情包设置",
                            variant="primary",
                            elem_id="save_personality_btn",
                            elem_classes="save_personality_btn"
                        )
                    with gr.Row():
                        emoji_save_message = gr.Textbox(
                            label="消息&表情包设置保存结果"
                        )
                    emoji_save_btn.click(
                        save_message_and_emoji_config,
                        inputs=[
                            min_text_length,
                            max_context_size,
                            emoji_chance,
                            thinking_timeout,
                            response_willing_amplifier,
                            response_interested_rate_amplifier,
                            down_frequency_rate,
                            ban_words_list_state,
                            ban_msgs_regex_list_state,
                            check_interval,
                            register_interval,
                            auto_save,
                            enable_check,
                            check_prompt
                        ],
                        outputs=[emoji_save_message]
                    )
        with gr.TabItem("4-回复&模型设置"):
            with gr.Row():
                with gr.Column(scale=3):
                    with gr.Row():
                        gr.Markdown(
                            """### 回复设置"""
                        )
                    with gr.Row():
                        model_r1_probability = gr.Slider(minimum=0, maximum=1, step=0.01, value=config_data['response']['model_r1_probability'], label="麦麦回答时选择主要回复模型1 模型的概率")
                    with gr.Row():
                        model_r2_probability = gr.Slider(minimum=0, maximum=1, step=0.01, value=config_data['response']['model_v3_probability'], label="麦麦回答时选择主要回复模型2 模型的概率")
                    with gr.Row():
                        model_r3_probability = gr.Slider(minimum=0, maximum=1, step=0.01, value=config_data['response']['model_r1_distill_probability'], label="麦麦回答时选择主要回复模型3 模型的概率")
                        # 用于显示警告消息
                    with gr.Row():
                        model_warning_greater_text = gr.Markdown()
                        model_warning_less_text = gr.Markdown()

                        # 绑定滑块的值变化事件，确保总和必须等于 1.0
                        model_r1_probability.change(adjust_model_greater_probabilities, inputs=[model_r1_probability, model_r2_probability, model_r3_probability], outputs=[model_warning_greater_text])
                        model_r2_probability.change(adjust_model_greater_probabilities, inputs=[model_r1_probability, model_r2_probability, model_r3_probability], outputs=[model_warning_greater_text])
                        model_r3_probability.change(adjust_model_greater_probabilities, inputs=[model_r1_probability, model_r2_probability, model_r3_probability], outputs=[model_warning_greater_text])
                        model_r1_probability.change(adjust_model_less_probabilities, inputs=[model_r1_probability, model_r2_probability, model_r3_probability], outputs=[model_warning_less_text])
                        model_r2_probability.change(adjust_model_less_probabilities, inputs=[model_r1_probability, model_r2_probability, model_r3_probability], outputs=[model_warning_less_text])
                        model_r3_probability.change(adjust_model_less_probabilities, inputs=[model_r1_probability, model_r2_probability, model_r3_probability], outputs=[model_warning_less_text])
                    with gr.Row():
                        max_response_length = gr.Number(value=config_data['response']['max_response_length'], label="麦麦回答的最大token数")
                    with gr.Row():
                        gr.Markdown(
                            """### 模型设置"""
                        )
                    with gr.Row():
                        gr.Markdown(
                            """### 注意\n
                            如果你是用的是火山引擎的API，建议查看[这篇文档](https://zxmucttizt8.feishu.cn/wiki/MQj7wp6dki6X8rkplApc2v6Enkd)中的修改火山API部分\n
                            因为修改至火山API涉及到修改源码部分，由于自己修改源码造成的问题MaiMBot官方并不因此负责！\n
                            感谢理解，感谢你使用MaiMBot
                            """
                        )
                    with gr.Tabs():
                        with gr.TabItem("1-主要回复模型"):
                            with gr.Row():
                                model1_name = gr.Textbox(value=config_data['model']['llm_reasoning']['name'], label="模型1的名称")
                            with gr.Row():
                                model1_provider = gr.Dropdown(choices=MODEL_PROVIDER_LIST, value=config_data['model']['llm_reasoning']['provider'], label="模型1（主要回复模型）提供商")
                            with gr.Row():
                                model1_pri_in = gr.Number(value=config_data['model']['llm_reasoning']['pri_in'], label="模型1（主要回复模型）的输入价格（非必填，可以记录消耗）")
                            with gr.Row():
                                model1_pri_out = gr.Number(value=config_data['model']['llm_reasoning']['pri_out'], label="模型1（主要回复模型）的输出价格（非必填，可以记录消耗）")
                        with gr.TabItem("2-次要回复模型"):
                            with gr.Row():
                                model2_name = gr.Textbox(value=config_data['model']['llm_normal']['name'], label="模型2的名称")
                            with gr.Row():
                                model2_provider = gr.Dropdown(choices=MODEL_PROVIDER_LIST, value=config_data['model']['llm_normal']['provider'], label="模型2提供商")
                        with gr.TabItem("3-次要模型"):
                            with gr.Row():
                                model3_name = gr.Textbox(value=config_data['model']['llm_reasoning_minor']['name'], label="模型3的名称")
                            with gr.Row():
                                model3_provider = gr.Dropdown(choices=MODEL_PROVIDER_LIST, value=config_data['model']['llm_reasoning_minor']['provider'], label="模型3提供商")
                        with gr.TabItem("4-情感&主题模型"):
                            with gr.Row():
                                gr.Markdown(
                                    """### 情感模型设置"""
                                )
                            with gr.Row():
                                emotion_model_name = gr.Textbox(value=config_data['model']['llm_emotion_judge']['name'], label="情感模型名称")
                            with gr.Row():
                                emotion_model_provider = gr.Dropdown(choices=MODEL_PROVIDER_LIST, value=config_data['model']['llm_emotion_judge']['provider'], label="情感模型提供商")
                            with gr.Row():
                                gr.Markdown(
                                    """### 主题模型设置"""
                                )
                            with gr.Row():
                                topic_judge_model_name = gr.Textbox(value=config_data['model']['llm_topic_judge']['name'], label="主题判断模型名称")
                            with gr.Row():
                                topic_judge_model_provider = gr.Dropdown(choices=MODEL_PROVIDER_LIST, value=config_data['model']['llm_topic_judge']['provider'], label="主题判断模型提供商")
                            with gr.Row():
                                summary_by_topic_model_name = gr.Textbox(value=config_data['model']['llm_summary_by_topic']['name'], label="主题总结模型名称")
                            with gr.Row():
                                summary_by_topic_model_provider = gr.Dropdown(choices=MODEL_PROVIDER_LIST, value=config_data['model']['llm_summary_by_topic']['provider'], label="主题总结模型提供商")
                        with gr.TabItem("5-识图模型"):
                            with gr.Row():
                                gr.Markdown(
                                    """### 识图模型设置"""
                                )
                            with gr.Row():
                                vlm_model_name = gr.Textbox(value=config_data['model']['vlm']['name'], label="识图模型名称")
                            with gr.Row():
                                vlm_model_provider = gr.Dropdown(choices=MODEL_PROVIDER_LIST, value=config_data['model']['vlm']['provider'], label="识图模型提供商")
                    with gr.Row():
                        save_model_btn = gr.Button("保存回复&模型设置",variant="primary", elem_id="save_model_btn")
                    with gr.Row():
                        save_btn_message = gr.Textbox()
                        save_model_btn.click(
                            save_response_model_config,
                            inputs=[model_r1_probability,model_r2_probability,model_r3_probability,max_response_length,model1_name, model1_provider, model1_pri_in, model1_pri_out, model2_name, model2_provider, model3_name, model3_provider, emotion_model_name, emotion_model_provider, topic_judge_model_name, topic_judge_model_provider, summary_by_topic_model_name,summary_by_topic_model_provider,vlm_model_name, vlm_model_provider],
                            outputs=[save_btn_message]
                        )
        with gr.TabItem("5-记忆&心情设置"):
            with gr.Row():
                with gr.Column(scale=3):
                    with gr.Row():
                        gr.Markdown(
                            """### 记忆设置"""
                        )
                    with gr.Row():
                        build_memory_interval = gr.Number(value=config_data['memory']['build_memory_interval'], label="记忆构建间隔 单位秒,间隔越低，麦麦学习越多，但是冗余信息也会增多")
                    with gr.Row():
                        memory_compress_rate = gr.Number(value=config_data['memory']['memory_compress_rate'], label="记忆压缩率 控制记忆精简程度 建议保持默认,调高可以获得更多信息，但是冗余信息也会增多")
                    with gr.Row():
                        forget_memory_interval = gr.Number(value=config_data['memory']['forget_memory_interval'], label="记忆遗忘间隔 单位秒   间隔越低，麦麦遗忘越频繁，记忆更精简，但更难学习")
                    with gr.Row():
                        memory_forget_time = gr.Number(value=config_data['memory']['memory_forget_time'], label="多长时间后的记忆会被遗忘 单位小时 ")
                    with gr.Row():
                        memory_forget_percentage = gr.Slider(minimum=0, maximum=1, step=0.01, value=config_data['memory']['memory_forget_percentage'], label="记忆遗忘比例 控制记忆遗忘程度 越大遗忘越多 建议保持默认")
                    with gr.Row():
                        memory_ban_words_list = config_data['memory']['memory_ban_words']
                        with gr.Blocks():
                            memory_ban_words_list_state = gr.State(value=memory_ban_words_list.copy())

                        with gr.Row():
                            memory_ban_words_list_display = gr.TextArea(
                                value="\n".join(memory_ban_words_list),
                                label="不希望记忆词列表",
                                interactive=False,
                                lines=5
                            )
                        with gr.Row():
                            with gr.Column(scale=3):
                                memory_ban_words_new_item_input = gr.Textbox(label="添加不希望记忆词")
                                memory_ban_words_add_btn = gr.Button("添加", scale=1)

                        with gr.Row():
                            with gr.Column(scale=3):
                                memory_ban_words_item_to_delete = gr.Dropdown(
                                    choices=memory_ban_words_list,
                                    label="选择要删除的不希望记忆词"
                                )
                            memory_ban_words_delete_btn = gr.Button("删除", scale=1)

                        memory_ban_words_final_result = gr.Text(label="修改后的不希望记忆词列表")
                        memory_ban_words_add_btn.click(
                            add_item,
                            inputs=[memory_ban_words_new_item_input, memory_ban_words_list_state],
                            outputs=[memory_ban_words_list_state, memory_ban_words_list_display, memory_ban_words_item_to_delete, memory_ban_words_final_result]
                        )

                        memory_ban_words_delete_btn.click(
                            delete_item,
                            inputs=[memory_ban_words_item_to_delete, memory_ban_words_list_state],
                            outputs=[memory_ban_words_list_state, memory_ban_words_list_display, memory_ban_words_item_to_delete, memory_ban_words_final_result]
                        )
                    with gr.Row():
                        mood_update_interval = gr.Number(value=config_data['mood']['mood_update_interval'], label="心情更新间隔 单位秒")
                    with gr.Row():
                        mood_decay_rate = gr.Slider(minimum=0, maximum=1, step=0.01, value=config_data['mood']['mood_decay_rate'], label="心情衰减率")
                    with gr.Row():
                        mood_intensity_factor = gr.Number(value=config_data['mood']['mood_intensity_factor'], label="心情强度因子")
                    with gr.Row():
                        save_memory_mood_btn = gr.Button("保存记忆&心情设置",variant="primary")
                    with gr.Row():
                        save_memory_mood_message = gr.Textbox()
                    with gr.Row():
                        save_memory_mood_btn.click(
                            save_memory_mood_config,
                            inputs=[build_memory_interval, memory_compress_rate, forget_memory_interval, memory_forget_time, memory_forget_percentage, memory_ban_words_list_state, mood_update_interval, mood_decay_rate, mood_intensity_factor],
                            outputs=[save_memory_mood_message]
                        )
        with gr.TabItem("6-群组设置"):
            with gr.Row():
                with gr.Column(scale=3):
                    with gr.Row():
                        gr.Markdown(
                            """## 群组设置"""
                        )
                    with gr.Row():
                        gr.Markdown(
                            """### 可以回复消息的群"""
                        )
                    with gr.Row():
                        talk_allowed_list = config_data['groups']['talk_allowed']
                        with gr.Blocks():
                            talk_allowed_list_state = gr.State(value=talk_allowed_list.copy())

                        with gr.Row():
                            talk_allowed_list_display = gr.TextArea(
                                value="\n".join(map(str, talk_allowed_list)),
                                label="可以回复消息的群列表",
                                interactive=False,
                                lines=5
                            )
                        with gr.Row():
                            with gr.Column(scale=3):
                                talk_allowed_new_item_input = gr.Textbox(label="添加新群")
                                talk_allowed_add_btn = gr.Button("添加", scale=1)

                        with gr.Row():
                            with gr.Column(scale=3):
                                talk_allowed_item_to_delete = gr.Dropdown(
                                    choices=talk_allowed_list,
                                    label="选择要删除的群"
                                )
                            talk_allowed_delete_btn = gr.Button("删除", scale=1)

                        talk_allowed_final_result = gr.Text(label="修改后的可以回复消息的群列表")
                        talk_allowed_add_btn.click(
                            add_int_item,
                            inputs=[talk_allowed_new_item_input, talk_allowed_list_state],
                            outputs=[talk_allowed_list_state, talk_allowed_list_display, talk_allowed_item_to_delete, talk_allowed_final_result]
                        )

                        talk_allowed_delete_btn.click(
                            delete_int_item,
                            inputs=[talk_allowed_item_to_delete, talk_allowed_list_state],
                            outputs=[talk_allowed_list_state, talk_allowed_list_display, talk_allowed_item_to_delete, talk_allowed_final_result]
                        )
                    with gr.Row():
                        talk_frequency_down_list = config_data['groups']['talk_frequency_down']
                        with gr.Blocks():
                            talk_frequency_down_list_state = gr.State(value=talk_frequency_down_list.copy())

                        with gr.Row():
                            talk_frequency_down_list_display = gr.TextArea(
                                value="\n".join(map(str, talk_frequency_down_list)),
                                label="降低回复频率的群列表",
                                interactive=False,
                                lines=5
                            )
                        with gr.Row():
                            with gr.Column(scale=3):
                                talk_frequency_down_new_item_input = gr.Textbox(label="添加新群")
                                talk_frequency_down_add_btn = gr.Button("添加", scale=1)

                        with gr.Row():
                            with gr.Column(scale=3):
                                talk_frequency_down_item_to_delete = gr.Dropdown(
                                    choices=talk_frequency_down_list,
                                    label="选择要删除的群"
                                )
                            talk_frequency_down_delete_btn = gr.Button("删除", scale=1)

                        talk_frequency_down_final_result = gr.Text(label="修改后的降低回复频率的群列表")
                        talk_frequency_down_add_btn.click(
                            add_int_item,
                            inputs=[talk_frequency_down_new_item_input, talk_frequency_down_list_state],
                            outputs=[talk_frequency_down_list_state, talk_frequency_down_list_display, talk_frequency_down_item_to_delete, talk_frequency_down_final_result]
                        )

                        talk_frequency_down_delete_btn.click(
                            delete_int_item,
                            inputs=[talk_frequency_down_item_to_delete, talk_frequency_down_list_state],
                            outputs=[talk_frequency_down_list_state, talk_frequency_down_list_display, talk_frequency_down_item_to_delete, talk_frequency_down_final_result]
                        )
                    with gr.Row():
                        ban_user_id_list = config_data['groups']['ban_user_id']
                        with gr.Blocks():
                            ban_user_id_list_state = gr.State(value=ban_user_id_list.copy())

                        with gr.Row():
                            ban_user_id_list_display = gr.TextArea(
                                value="\n".join(map(str, ban_user_id_list)),
                                label="禁止回复消息的QQ号列表",
                                interactive=False,
                                lines=5
                            )
                        with gr.Row():
                            with gr.Column(scale=3):
                                ban_user_id_new_item_input = gr.Textbox(label="添加新QQ号")
                                ban_user_id_add_btn = gr.Button("添加", scale=1)

                        with gr.Row():
                            with gr.Column(scale=3):
                                ban_user_id_item_to_delete = gr.Dropdown(
                                    choices=ban_user_id_list,
                                    label="选择要删除的QQ号"
                                )
                            ban_user_id_delete_btn = gr.Button("删除", scale=1)

                        ban_user_id_final_result = gr.Text(label="修改后的禁止回复消息的QQ号列表")
                        ban_user_id_add_btn.click(
                            add_int_item,
                            inputs=[ban_user_id_new_item_input, ban_user_id_list_state],
                            outputs=[ban_user_id_list_state, ban_user_id_list_display, ban_user_id_item_to_delete, ban_user_id_final_result]
                        )

                        ban_user_id_delete_btn.click(
                            delete_int_item,
                            inputs=[ban_user_id_item_to_delete, ban_user_id_list_state],
                            outputs=[ban_user_id_list_state, ban_user_id_list_display, ban_user_id_item_to_delete, ban_user_id_final_result]
                        )
                    with gr.Row():
                        save_group_btn = gr.Button("保存群组设置",variant="primary")
                    with gr.Row():
                        save_group_btn_message = gr.Textbox()
                    with gr.Row():
                        save_group_btn.click(
                            save_group_config,
                            inputs=[
                                talk_allowed_list_state,
                                talk_frequency_down_list_state,
                                ban_user_id_list_state,
                            ],
                            outputs=[save_group_btn_message]
                        )
        with gr.TabItem("7-其他设置"):
            with gr.Row():
                with gr.Column(scale=3):
                    with gr.Row():
                        gr.Markdown(
                            """### 其他设置"""
                        )
                    with gr.Row():
                        keywords_reaction_enabled = gr.Checkbox(value=config_data['keywords_reaction']['enable'], label="是否针对某个关键词作出反应")
                    with gr.Row():
                        enable_advance_output = gr.Checkbox(value=config_data['others']['enable_advance_output'], label="是否开启高级输出")
                    with gr.Row():
                        enable_kuuki_read = gr.Checkbox(value=config_data['others']['enable_kuuki_read'], label="是否启用读空气功能")
                    with gr.Row():
                        enable_debug_output = gr.Checkbox(value=config_data['others']['enable_debug_output'], label="是否开启调试输出")
                    with gr.Row():
                        enable_friend_chat = gr.Checkbox(value=config_data['others']['enable_friend_chat'], label="是否开启好友聊天")
                    if PARSED_CONFIG_VERSION > HAVE_ONLINE_STATUS_VERSION:
                        with gr.Row():
                            gr.Markdown(
                                """### 远程统计设置\n
                                测试功能，发送统计信息，主要是看全球有多少只麦麦
                                """
                            )
                        with gr.Row():
                            remote_status = gr.Checkbox(value=config_data['remote']['enable'], label="是否开启麦麦在线全球统计")

                    with gr.Row():
                        gr.Markdown(
                            """### 中文错别字设置"""
                        )
                    with gr.Row():
                        chinese_typo_enabled = gr.Checkbox(value=config_data['chinese_typo']['enable'], label="是否开启中文错别字")
                    with gr.Row():
                        error_rate = gr.Slider(minimum=0, maximum=1, step=0.001, value=config_data['chinese_typo']['error_rate'], label="单字替换概率")
                    with gr.Row():
                        min_freq = gr.Number(value=config_data['chinese_typo']['min_freq'], label="最小字频阈值")
                    with gr.Row():
                        tone_error_rate = gr.Slider(minimum=0, maximum=1, step=0.01, value=config_data['chinese_typo']['tone_error_rate'], label="声调错误概率")
                    with gr.Row():
                        word_replace_rate = gr.Slider(minimum=0, maximum=1, step=0.001, value=config_data['chinese_typo']['word_replace_rate'], label="整词替换概率")
                    with gr.Row():
                        save_other_config_btn = gr.Button("保存其他配置",variant="primary")
                    with gr.Row():
                        save_other_config_message = gr.Textbox()
                    with gr.Row():
                        if PARSED_CONFIG_VERSION <= HAVE_ONLINE_STATUS_VERSION:
                            remote_status = gr.Checkbox(value=False,visible=False)
                        save_other_config_btn.click(
                            save_other_config,
                            inputs=[keywords_reaction_enabled,enable_advance_output, enable_kuuki_read, enable_debug_output, enable_friend_chat, chinese_typo_enabled, error_rate, min_freq, tone_error_rate, word_replace_rate,remote_status],
                            outputs=[save_other_config_message]
                        )
    app.queue().launch(#concurrency_count=511, max_size=1022
        server_name="0.0.0.0",
        inbrowser=True,
        share=is_share,
        server_port=7000,
        debug=debug,
        quiet=True,
    )

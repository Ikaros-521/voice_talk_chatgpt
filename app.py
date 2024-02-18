import gradio as gr
import logging
import json
import numpy as np
from scipy.io import wavfile

from utils.chatgpt import Chatgpt
from utils.my_tts import MY_TTS
from utils.config import Config
from utils.common import Common
from utils.logger import Configure_logger


common = Common()

# 日志文件路径
log_path = "./log/log-" + common.get_bj_time(1) + ".txt"
Configure_logger(log_path)

# 获取 httpx 库的日志记录器
httpx_logger = logging.getLogger("httpx")
# 设置 httpx 日志记录器的级别为 WARNING
httpx_logger.setLevel(logging.WARNING)

config_path = "config.json"
config = Config(config_path)

# Chatgpt
chatgpt = Chatgpt(config.get("openai"), config.get("chatgpt"))

my_tts = MY_TTS(config_path)


"""
通用函数
"""
def textarea_data_change(data):
    """
    字符串数组数据格式转换
    """
    tmp_str = ""
    for tmp in data:
        tmp_str = tmp_str + tmp + "\n"
    
    return tmp_str

def reset_record():
    # 这里的代码将在客户端执行，以重置录音组件
    return """
    document.getElementById("component-2").getElementsByTagName("button")[0].click();
   
    """

def send_msg(audio, text):
    try:
        if text:
            stt_ret = text

        if audio:
            # 创建一个示例的 int16 音频数据
            int16_audio_data = np.array(audio[1], dtype=np.int16)

            # 创建一个临时文件来存储录制的音频数据
            output_file = "out/" + common.get_bj_time(4) + ".wav"

            # 使用 scipy.io.wavfile 将数据保存为 WAV 文件
            wavfile.write(output_file, audio[0], int16_audio_data)

            audio_file= open(output_file, "rb")

            # 调用 openai 接口，并传递音频文件路径
            stt_ret = chatgpt.STT(audio_file)

            logging.info(f"语音识别内容：{stt_ret}")

            # 数据回显
            text_input.value = stt_ret

        chat_ret = chatgpt.get_gpt_resp("主人", stt_ret)

        logging.info(f"对话返回：{chat_ret}")

        data = {
            "type": config.get("openai_tts", "type"),
            "api_ip_port": config.get("openai_tts", "api_ip_port"),
            "model": config.get("openai_tts", "model"),
            "voice": config.get("openai_tts", "voice"),
            "api_key": config.get("openai_tts", "api_key"),
            "content": chat_ret
        }
        audio_path = my_tts.openai_tts_api(data)
        logging.info(f"合成音频输出在：{audio_path}")

        

        return audio_path, chat_ret

    except Exception as e:
        logging.error(f"Error processing audio: {str(e)}")
        return None
    
# 保存配置
def save_config(api, api_key, model, temperature, max_tokens, top_p, presence_penalty, frequency_penalty, preset, openai_tts_api_ip_port, openai_tts_api_key, openai_tts_model, openai_tts_voice):
    try:
        with open(config_path, 'r', encoding="utf-8") as config_file:
            config_data = json.load(config_file)
    except Exception as e:
        logging.error(f"无法读取配置文件！\n{e}")
        gr.Error(f"无法读取配置文件！\n{e}")
        return f"无法读取配置文件！{e}"
    
    def common_textarea_handle(content):
        """通用的textEdit 多行文本内容处理

        Args:
            content (str): 原始多行文本内容

        Returns:
            _type_: 处理好的多行文本内容
        """
        # 通用多行分隔符
        separators = [" ", "\n"]

        ret = [token.strip() for separator in separators for part in content.split(separator) if (token := part.strip())]
        if 0 != len(ret):
            ret = ret[1:]

        return ret

    config_data["openai"]["api"] = api
    config_data["openai"]["api_key"] = common_textarea_handle(api_key)
    config_data["chatgpt"]["model"] = model
    config_data["chatgpt"]["temperature"] = float(temperature)
    config_data["chatgpt"]["max_tokens"] = int(max_tokens)
    config_data["chatgpt"]["top_p"] = float(top_p)
    config_data["chatgpt"]["presence_penalty"] = float(presence_penalty)
    config_data["chatgpt"]["frequency_penalty"] = float(frequency_penalty)
    config_data["chatgpt"]["preset"] = preset
    config_data["openai_tts"]["api_ip_port"] = openai_tts_api_ip_port
    config_data["openai_tts"]["api_key"] = openai_tts_api_key
    config_data["openai_tts"]["model"] = openai_tts_model
    config_data["openai_tts"]["voice"] = openai_tts_voice

    # 写入配置到配置文件
    try:
        with open(config_path, 'w', encoding="utf-8") as config_file:
            json.dump(config_data, config_file, indent=2, ensure_ascii=False)
            config_file.flush()  # 刷新缓冲区，确保写入立即生效

        logging.info("配置数据已成功写入文件！")
        gr.Info("配置数据已成功写入文件！")

        return "配置数据已成功写入文件！"
    except Exception as e:
        logging.error(f"无法读取配置文件！\n{e}")
        gr.Error(f"无法读取配置文件！\n{e}")
        return f"无法读取配置文件！{e}"

with gr.Blocks() as demo:
    # 创建 Tab 组件，用于容纳不同的页面
    with gr.Tab("对话页") as tab1:
        with gr.Row():
            record = gr.Audio(interactive=True)
            text_input = gr.Textbox(label="输入文本", lines=10)
            submit_button = gr.Button("发送")
        # 添加一个空的Textbox来增加间距
        with gr.Row():
            gr.Textbox(value="", visible=False, interactive=False, label="")
        with gr.Row():
            resp_display = gr.Textbox(label="Bot回复")
        with gr.Row():
            # 创建一个音频播放器组件，它将使用音频路径来加载音频
            audio_player = gr.Audio(interactive=False, label="合成的音频", autoplay=True)
            
        submit_button.click(
            send_msg, 
            inputs=[record, text_input], 
            outputs=[audio_player, resp_display],
            js=reset_record
        )
    with gr.Tab("配置页") as tab2:
        with gr.Group():
            with gr.Row():
                openai_api_input = gr.Textbox(label="OpenAI API地址", value=config.get("openai", "api"))
                openai_api_key_input = gr.Textbox(
                    label="OpenAI API密钥", 
                    value=textarea_data_change(config.get("openai", "api_key")), 
                    lines=3
                )
            with gr.Row():
                chatgpt_model_dropdown = gr.Dropdown(
                    choices=[
                        "gpt-3.5-turbo",
                        "gpt-3.5-turbo-0301",
                        "gpt-3.5-turbo-0613",
                        "gpt-3.5-turbo-1106",
                        "gpt-3.5-turbo-16k",
                        "gpt-3.5-turbo-16k-0613",
                        "gpt-3.5-turbo-instruct",
                        "gpt-3.5-turbo-instruct-0914",
                        "gpt-4",
                        "gpt-4-0314",
                        "gpt-4-0613",
                        "gpt-4-32k",
                        "gpt-4-32k-0314",
                        "gpt-4-32k-0613",
                        "gpt-4-1106-preview",
                        "text-embedding-ada-002",
                        "text-davinci-003",
                        "text-davinci-002",
                        "text-curie-001",
                        "text-babbage-001",
                        "text-ada-001",
                        "text-moderation-latest",
                        "text-moderation-stable",
                    ], 
                    label="模型",
                    value=config.get("chatgpt", "model"), 
                )
            with gr.Row(): 
                chatgpt_temperature_input = gr.Textbox(value=config.get("chatgpt", "temperature"), label="temperature")
                chatgpt_max_tokens_input = gr.Textbox(value=config.get("chatgpt", "max_tokens"), label="max_tokens")
                chatgpt_top_p_input = gr.Textbox(value=config.get("chatgpt", "top_p"), label="top_p")
            with gr.Row():
                chatgpt_presence_penalty_input = gr.Textbox(value=config.get("chatgpt", "presence_penalty"), label="presence_penalty")
                chatgpt_frequency_penalty_input = gr.Textbox(value=config.get("chatgpt", "frequency_penalty"), label="frequency_penalty")
                chatgpt_preset_input = gr.Textbox(value=config.get("chatgpt", "preset"), label="预设", lines=5)
        with gr.Group():
            with gr.Row():
                openai_tts_api_ip_port_input = gr.Textbox(
                    label="OpenAI TTS API地址", 
                    value=config.get("openai_tts", "api_ip_port"),
                    lines=1
                )
                openai_tts_api_key_input = gr.Textbox(
                    label="OpenAI API密钥", 
                    value=config.get("openai_tts", "api_key"),
                    lines=1
                )
            with gr.Row():
                openai_tts_model_dropdown = gr.Dropdown(
                    choices=[
                        "tts-1",
                        "tts-1-hd",
                    ], 
                    label="模型",
                    value=config.get("openai_tts", "model"), 
                )
                openai_tts_voice_dropdown = gr.Dropdown(
                    choices=[
                        "alloy",
                        "echo",
                        "fable",
                        "onyx",
                        "nova",
                        "shimmer",
                    ], 
                    label="说话人",
                    value=config.get("openai_tts", "voice"), 
                )
        with gr.Group():
            with gr.Row():
                save_btn = gr.Button("保存")
                output_label = gr.Label(label="结果")

                save_btn.click(
                    save_config,
                    inputs=[openai_api_input, openai_api_key_input,
                        chatgpt_model_dropdown, chatgpt_temperature_input, chatgpt_max_tokens_input, chatgpt_top_p_input,
                        chatgpt_presence_penalty_input, chatgpt_frequency_penalty_input, chatgpt_preset_input,
                        openai_tts_api_ip_port_input, openai_tts_api_key_input, openai_tts_model_dropdown, openai_tts_voice_dropdown],
                    outputs=output_label
                )

demo.launch(share=config.get("gradio", "share"))

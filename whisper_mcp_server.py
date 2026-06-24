import asyncio
import json
import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

app = Server("whisper-transcriber")

# ---------- 配置区域 ----------
# 模型路径，可通过环境变量 WHISPER_MODEL_PATH 覆盖
MODEL_PATH = os.environ.get(
    "WHISPER_MODEL_PATH",
    os.path.expanduser("~/whisper-models/ggml-medium.bin"),
)
# whisper.cpp 可执行文件路径，优先使用环境变量 WHISPER_CLI_PATH，
# 其次是 PATH 中能搜到的 whisper-cli，最后回退到当前目录
_which_cli = shutil.which("whisper-cli")
WHISPER_CLI_PATH = os.environ.get(
    "WHISPER_CLI_PATH",
    _which_cli or "whisper-cli",
)
# 线程数，通过环境变量 WHISPER_THREADS 覆盖
THREADS = int(os.environ.get("WHISPER_THREADS", "4"))
# -----------------------------

def convert_audio_to_wav(input_path: str) -> str:
    """用 FFmpeg 转为 16kHz 单声道 WAV"""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("FFmpeg 未安装，请安装并加入 PATH")
    temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_wav.close()
    cmd = [
        "ffmpeg",
        "-i", input_path,
        "-ar", "16000",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        "-y",
        temp_wav.name
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return temp_wav.name

@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="transcribe_audio",
            description=(
                "将音频文件（任意格式）通过 whisper.cpp 转译为文字。"
                "内部自动用 FFmpeg 转为 WAV，然后调用 ggml 模型推理。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "audio_path": {
                        "type": "string",
                        "description": "音频文件绝对路径",
                    },
                    "language": {
                        "type": "string",
                        "description": "语言代码，如 'zh'、'en'，默认自动检测",
                    },
                },
                "required": ["audio_path"],
            },
        )
    ]

@app.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent]:
    if name != "transcribe_audio":
        raise ValueError(f"Unknown tool: {name}")

    audio_path = arguments.get("audio_path")
    if not audio_path or not os.path.exists(audio_path):
        return [types.TextContent(type="text", text=f"错误：文件不存在或未提供 - {audio_path}")]

    language = arguments.get("language", "auto")
    # whisper.cpp 的参数：-l 指定语言，auto 则不指定（默认自动）
    lang_arg = [] if language == "auto" else ["-l", language]

    temp_wav = None
    try:
        # 1. 转码
        temp_wav = convert_audio_to_wav(audio_path)

        # 2. 调用 whisper-cli
        cmd = [
            WHISPER_CLI_PATH,
            "-m", MODEL_PATH,
            "-f", temp_wav,
            "-t", str(THREADS),
            "-otxt",           # 输出文本到文件（我们会读取）
            "--print-progress", "false",  # 减少输出干扰
            *lang_arg
        ]
        # 运行，捕获输出（但输出会同时生成一个同名的 .txt 文件）
        # 为了获取文本，我们直接读取生成的 .txt 文件
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        # whisper-cli 默认会在输入文件同目录生成 .txt，但我们可以指定输出路径
        # 更稳健：使用 -of 指定输出文件前缀，我们指定临时目录
        # 修改命令：加上 -of 参数
        # 我们改进一下：使用 -of 指定输出文件路径
        output_base = tempfile.NamedTemporaryFile(suffix="", delete=False).name
        cmd_with_of = [
            WHISPER_CLI_PATH,
            "-m", MODEL_PATH,
            "-f", temp_wav,
            "-t", str(THREADS),
            "-of", output_base,   # 输出文件前缀
            *lang_arg
        ]
        subprocess.run(cmd_with_of, check=True, capture_output=True, text=True)
        # 读取生成的 .txt 文件
        txt_path = output_base + ".txt"
        if not os.path.exists(txt_path):
            raise RuntimeError("whisper-cli 未生成输出文件")
        with open(txt_path, "r", encoding="utf-8") as f:
            transcribed_text = f.read().strip()

        # 清理输出文件
        os.unlink(txt_path)
        if os.path.exists(output_base + ".vtt"):
            os.unlink(output_base + ".vtt")  # 可能生成其他格式
        # 清理临时文件
        os.unlink(output_base)

        return [types.TextContent(type="text", text=transcribed_text)]

    except subprocess.CalledProcessError as e:
        return [types.TextContent(type="text", text=f"whisper-cli 运行失败: {e.stderr}")]
    except RuntimeError as e:
        return [types.TextContent(type="text", text=f"错误: {str(e)}")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"未知错误: {str(e)}")]
    finally:
        if temp_wav and os.path.exists(temp_wav):
            try:
                os.unlink(temp_wav)
            except OSError:
                pass

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
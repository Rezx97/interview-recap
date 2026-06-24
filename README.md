# interview-recap — 面试复盘助手

将面试录音或转译文本自动转化为结构化复盘报告：语音转译 → 智能纠错 → 角色分离 → 问答提取 → 复盘建议。

---

## 前置依赖

| 依赖 | 用途 | 安装方式 |
|------|------|----------|
| **Python 3.10+** | 运行 MCP 服务器 | [python.org](https://www.python.org/) |
| **whisper.cpp** | 语音转文字引擎 | 见下方说明 |
| **ggml 模型文件** | whisper.cpp 推理模型 | 见下方说明 |
| **FFmpeg** | 音频格式转换（任意格式→WAV） | [ffmpeg.org](https://ffmpeg.org/) |
| **Python `mcp` 包** | MCP 协议支持 | `pip install mcp` |

### 安装 whisper.cpp 与模型

```bash
# 1. 下载 whisper.cpp 预编译版本（Windows），或自行编译
#    https://github.com/ggerganov/whisper.cpp/releases
#    解压后获得 whisper-cli.exe

# 2. 下载 ggml 模型（推荐 medium，平衡速度与精度）
#    https://huggingface.co/ggerganov/whisper.cpp/tree/main
#    下载 ggml-medium.bin 或 ggml-large-v3.bin
```

---

## 安装步骤

### 1. 克隆仓库

```bash
git clone <your-repo-url>
cd interview-recap
```

### 2. 安装 Python 依赖

```bash
pip install mcp
```

### 3. 配置环境变量（可选）

如果 whisper-cli 和模型不在默认位置，通过环境变量指定：

```bash
# Windows PowerShell
$env:WHISPER_CLI_PATH = "D:\whisper.cpp\whisper-cli.exe"
$env:WHISPER_MODEL_PATH = "D:\whisper.cpp\models\ggml-medium.bin"
$env:WHISPER_THREADS = "4"
```

不设置则使用默认值：
- `WHISPER_CLI_PATH` → 自动搜索 PATH 中的 `whisper-cli`，否则回退到当前目录
- `WHISPER_MODEL_PATH` → `~/whisper-models/ggml-medium.bin`
- `WHISPER_THREADS` → `4`

### 4. 注册 MCP 服务器

在 Claude Code 的全局配置 `~/.claude.json` 中添加（或通过 `/config` 命令）：

```json
{
  "mcpServers": {
    "whisper": {
      "type": "stdio",
      "command": "python",
      "args": ["<仓库路径>/whisper_mcp_server.py"],
      "env": {}
    }
  }
}
```

如果有设置环境变量：

```json
{
  "mcpServers": {
    "whisper": {
      "type": "stdio",
      "command": "python",
      "args": ["<仓库路径>/whisper_mcp_server.py"],
      "env": {
        "WHISPER_CLI_PATH": "D:/whisper.cpp/whisper-cli.exe",
        "WHISPER_MODEL_PATH": "D:/whisper.cpp/models/ggml-medium.bin"
      }
    }
  }
}
```

### 5. 安装技能

将 `SKILL.md` 复制到项目的 `.claude/skills/interview-recap/` 目录下：

```bash
mkdir -p .claude/skills/interview-recap
cp SKILL.md .claude/skills/interview-recap/
```

重启 Claude Code 后，技能自动生效。

---

## 使用方法

在 Claude Code 中输入 `/interview-recap`，然后提供以下任一输入：

### 输入方式 A：音频文件路径

```
/interview-recap
D:\录音\XX科技面试.wav
```

支持格式：`.wav`、`.mp3`、`.m4a`、`.aac` 等（FFmpeg 支持的任意音频格式）。

### 输入方式 B：直接粘贴转译文本

```
/interview-recap
以下是面试录音的转译文本：
面试官：请做一下自我介绍。
我：你好，我是...
```

---

## 输出说明

技能会生成一份结构化复盘报告，保存为 `面试复盘报告-{文件名}.md`，包含：

1. **文本预处理说明** — 识别并标注主要转译错误
2. **问答对汇总** — 提取每个问题及候选人的完整回答
3. **简要复盘建议** — 2-4 条可操作的改进方向

---

## 仓库结构

```
interview-recap/
├── README.md                  # 本文件
├── SKILL.md                   # Claude Code 技能定义
└── whisper_mcp_server.py      # whisper.cpp MCP 服务器
```

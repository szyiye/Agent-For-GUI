# Agent-For-GUI

全自动电脑控制助手 — 通过 AI 指令操作 Windows 电脑（鼠标、键盘、截屏、文件、媒体控制等）。

## 功能

| 功能 | 说明 |
|------|------|
| 🖥️ 屏幕截图 | AI 可查看屏幕内容（原始分辨率，无缩放） |
| 🖱️ 鼠标控制 | 移动、点击（左/右/中键）、长按 |
| ⌨️ 键盘控制 | 按键、长按、组合键（最多5键） |
| 📄 文件操作 | 写入文件、删除文件 |
| 🔧 命令执行 | 运行 CMD / PowerShell 命令 |
| 📋 进程管理 | 查看系统/用户/全部进程、搜索进程 |
| 🪟 窗口截图 | 按 PID/进程名/路径截取指定窗口 |
| 🎵 媒体控制 | 播放/暂停/上下曲、列出正在播放的内容 |
| 🤖 AI 自动决策 | 全自动循环，无需人工干预 |

## 系统要求

- Windows 10 / 11
- Python 3.8+

## 使用教程

### 第一步：安装依赖

```bash
pip install pyautogui Pillow requests mss
```

### 第二步：配置 API

首次运行程序前，需要配置 AI API。有两种方式：

**方式一：使用配置向导（推荐）**

运行 `config_wizard.exe`（如果有的话），在图形界面中填写：

1. 选择 API 格式（OpenAI 兼容 / Anthropic 兼容）
2. 填写 API 地址和 API 密钥
3. 点击「获取模型」从 API 加载可用模型列表
4. 选择模型
5. 点击「保存并继续」

**方式二：手动编辑 config.ini**

复制 `config.ini.example` 为 `config.ini`，然后编辑：

```ini
[api]
api_url = https://api.openai.com/v1
api_key = sk-xxxxxxxxxxxxxxxx
model = gpt-4o
api_format = openai
thinking_mode = default
```

**配置说明：**

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `api_url` | API 地址 | `https://api.openai.com/v1` |
| `api_key` | API 密钥 | `sk-xxxxxxxx` |
| `model` | 模型名称 | `gpt-4o`、`mimo-v2.6-pro`、`claude-sonnet-4-20250514` |
| `api_format` | API 格式 | `openai`（OpenAI兼容）或 `anthropic`（Claude） |
| `thinking_mode` | 思考模式 | `default`（默认）或 `medium`（中等） |
| `transcribe_model` | 截图转述模型 | `mimo-v2.5`（留空则关闭转述） |
| `use_transcribe` | 是否开启转述 | `true`（截图转文字）或 `false`（截图直接给主模型） |

### 第三步：运行程序

```bash
python main.py
```

### 第四步：输入任务

程序启动后，输入你要 AI 完成的任务，然后 AI 会**全自动**执行，无需人工干预。

**示例任务：**

```
任务> 帮我打开记事本并输入"Hello World"

任务> 查看当前屏幕，告诉我打开了什么程序

任务> 在D盘创建一个test.txt文件，内容为"Hello"

任务> 播放音乐，然后截图看看播放器界面
```

**运行流程：**

```
你输入任务
    ↓
AI 输出操作命令（如 {print screen}）
    ↓
程序自动执行命令
    ↓
如果是截图 → 转述模型把截图转成文字 → 喂给主模型
如果不是截图 → 执行结果直接喂给主模型
    ↓
AI 继续输出下一个命令 → 循环...
    ↓
AI 输出 {stop} → 任务结束
```

## AI 可用命令

AI 会根据你的任务自动输出以下命令：

### 基础操作

| 命令 | 功能 | 示例 |
|------|------|------|
| `{print screen}` | 截取当前屏幕 | `{print screen}` |
| `{movemouse x,y}` | 移动鼠标到坐标 | `{movemouse 500,300}` |
| `{clickmouse left/right/middle}` | 点击鼠标 | `{clickmouse left}` |
| `{clickbutton 按键名}` | 点击键盘按键 | `{clickbutton enter}` |
| `{wait 秒数}` | 等待指定秒数 | `{wait 2}` |
| `{stop}` | 结束任务 | `{stop}` |

### 长按与组合键

| 命令 | 功能 | 示例 |
|------|------|------|
| `{long-clickmouse left/right/middle 秒}` | 长按鼠标 | `{long-clickmouse left 2}` |
| `{long-clickbutton 按键名 秒}` | 长按键盘 | `{long-clickbutton shift 1}` |
| `{more_clickbutton 按键1 按键2 ...}` | 组合键（最多5个） | `{more_clickbutton ctrl s}` |

### 文件操作

| 命令 | 功能 | 示例 |
|------|------|------|
| `{addfile 文件路径 文件内容}` | 写入文件 | `{addfile D:\test.txt Hello}` |
| `{delfile 文件路径}` | 删除文件 | `{delfile D:\test.txt}` |

### 系统操作

| 命令 | 功能 | 示例 |
|------|------|------|
| `{run cmd/powershell 指令}` | 运行命令 | `{run powershell Get-Process}` |
| `{list_tasks system/user/all}` | 进程列表 | `{list_tasks user}` |
| `{search_tasks 关键词}` | 搜索进程 | `{search_tasks chrome}` |
| `{print window PID/进程名/路径}` | 窗口截图 | `{print window notepad}` |

### 媒体控制

| 命令 | 功能 | 示例 |
|------|------|------|
| `{smtc pause/play/previous/next}` | 媒体控制 | `{smtc pause}` |
| `{list_smtc}` | 列出正在播放的媒体 | `{list_smtc}` |

## 支持的 API 格式

| 格式 | 说明 | 模型示例 |
|------|------|----------|
| OpenAI 兼容 | OpenAI、DeepSeek、MiMo、Ollama 等 | `gpt-4o`、`mimo-v2.6-pro`、`deepseek-chat` |
| Anthropic 兼容 | Claude 系列 | `claude-sonnet-4-20250514` |

## 高级配置

### 截图转述

程序支持将截图先转成文字再给主模型（省 token）：

```ini
# config.ini
use_transcribe = true              # 开启转述
transcribe_model = mimo-v2.5       # 转述模型
transcribe_api_url =               # 留空则复用主模型API
transcribe_api_key =               # 留空则复用主模型密钥
```

- `use_transcribe = true`：截图 → 转述模型转文字 → 文字给主模型
- `use_transcribe = false`：截图直接发给主模型（需要主模型支持图片输入）

### 坐标系统

- 截图使用**原始分辨率**，不缩放
- AI 输出的坐标就是真实屏幕坐标
- 截图上会标注红色十字（当前鼠标位置）和黄色圆圈（目标位置）

### 执行顺序

- 如果 AI 同时输出截图和操作命令，系统会自动把截图放到最后执行
- 截图前会延时 0.1 秒，确保操作已生效

## 常见问题

**Q: 提示 API 错误？**
检查 config.ini 中的 API 地址、密钥和模型名是否正确。

**Q: 提示找不到 config.ini？**
复制 `config.ini.example` 为 `config.ini` 并填写 API 信息。

**Q: 截图转述失败？**
检查 `transcribe_model` 和对应的 API 配置是否正确。

**Q: 如何停止 AI 操作？**
按 `Ctrl+C` 立即中止。

## 项目结构

```
├── main.py                  # 主程序
├── config.ini.example       # 配置模板
├── system_prompt.txt        # 系统提示词
└── README.md                # 本文档
```

## License

MIT License

# Agent-For-GUI

全自动电脑控制助手 — 通过 AI 指令操作 Windows 电脑（鼠标、键盘、截屏、文件、媒体控制等）。

## 功能

- 🖥️ **屏幕截图** — AI 可查看屏幕内容（原始分辨率，无缩放）
- 🖱️ **鼠标控制** — 移动、点击（左/右/中键）、长按
- ⌨️ **键盘控制** — 按键、长按、组合键（最多5键）
- 📄 **文件操作** — 写入文件、删除文件
- 🔧 **命令执行** — 运行 CMD / PowerShell 命令
- 📋 **进程管理** — 查看系统/用户/全部进程、搜索进程
- 🪟 **窗口截图** — 按 PID/进程名/路径截取指定窗口
- 🎵 **媒体控制** — 播放/暂停/上下曲、列出正在播放的内容
- 🤖 **AI 自动决策** — 全自动循环，无需人工干预

## 系统要求

- Windows 10/11
- .NET Framework 4.0+（系统自带）

## 安装

1. 运行 `AI_Controller_Setup.exe`
2. 选择安装目录，点击「安装」
3. 安装完成后，首次运行 `AI_Controller.exe` 会弹出配置向导
4. 在配置向导中填写 API 信息，点击「获取模型」选择模型
5. 点击「保存并继续」开始使用

## 配置

配置向导会自动创建 `config.ini`，也可以手动编辑：

```ini
[api]
api_url = https://api.openai.com/v1
api_key = your_api_key_here
model = gpt-4o
api_format = openai          # openai 或 anthropic
thinking_mode = default      # default 或 medium
```

### 支持的 API 格式

| 格式 | 说明 |
|------|------|
| OpenAI 兼容 | OpenAI、DeepSeek、MiMo、Ollama 等 |
| Anthropic 兼容 | Claude 系列 |

## AI 可用命令

| 命令 | 功能 |
|------|------|
| `{print screen}` | 截取当前屏幕 |
| `{movemouse x,y}` | 移动鼠标到坐标 |
| `{clickmouse left/right/middle}` | 点击鼠标 |
| `{clickbutton 按键名}` | 点击键盘按键 |
| `{long-clickmouse left/right/middle 秒}` | 长按鼠标 |
| `{long-clickbutton 按键名 秒}` | 长按键盘按键 |
| `{more_clickbutton 按键1 按键2 ...}` | 组合键（最多5个） |
| `{addfile 文件路径 文件内容}` | 写入文件 |
| `{delfile 文件路径}` | 删除文件 |
| `{run cmd/powershell 指令}` | 运行命令 |
| `{list_tasks system/user/all}` | 进程列表 |
| `{search_tasks 关键词}` | 搜索进程 |
| `{print window PID/进程名/路径}` | 窗口截图 |
| `{smtc pause/play/previous/next}` | 媒体控制 |
| `{list_smtc}` | 列出正在播放的媒体 |
| `{wait 秒数}` | 等待 |
| `{stop}` | 结束任务 |

## 项目结构

```
├── main.py                    # 主程序（Python）
├── config_wizard_src.cs       # 配置向导源码（C#）
├── setup_cn.cs                # 安装器源码（C#）
├── wizard_cn.cs               # 中文配置向导源码（C#）
├── config.ini.example         # 配置模板
├── system_prompt.txt          # 系统提示词
└── dist/
    └── icon/                  # 图标文件（16-256px）
```

## 构建

### 主程序
```bash
pip install pyautogui Pillow requests mss
python -m PyInstaller --onefile --console --name AI_Controller --icon dist/app.ico main.py
```

### 配置向导 / 安装器
```bash
csc /target:winexe /win32icon:app.ico /out:config_wizard.exe /r:System.Windows.Forms.dll /r:System.Drawing.dll wizard_cn.cs
csc /target:winexe /win32icon:app.ico /out:AI_Controller_Setup.exe /resource:app.resources /r:System.Windows.Forms.dll /r:System.Drawing.dll setup_cn.cs
```

## License

MIT License

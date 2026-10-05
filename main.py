#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI屏幕控制器 - 全自动CLI版本
主模型(mimo-v2.6-pro)自主决策，截图经转述模型(mimo-v2.5)转成文字后喂回主模型
"""

import configparser
import os
import sys
import re
import time
import base64
import io
import subprocess
import ctypes
from ctypes import wintypes
from pathlib import Path

try:
    import pyautogui
    from PIL import Image, ImageDraw, ImageFont
    import requests
    import mss
except ImportError as e:
    print(f"[错误] 缺少必要的库: {e}")
    print("请运行: pip install pyautogui Pillow requests mss")
    input("按Enter键退出...")
    sys.exit(1)

# 禁用pyautogui的安全暂停和失败保护
pyautogui.PAUSE = 0.1
pyautogui.FAILSAFE = False


class AIController:
    """AI控制器主类（全自动模式）"""

    def __init__(self, config_path='config.ini'):
        """初始化控制器"""
        self.config_path = config_path
        self.config = configparser.ConfigParser()
        self.load_config()

        # API配置
        self._read_api_config()

        # 首次运行检测
        if self._is_first_run():
            self._launch_wizard()

        # 提示词（从txt文件读取）
        self.base_dir = os.path.dirname(os.path.abspath(self.config_path))
        prompt_file = self.config.get('prompts', 'system_prompt_file', fallback='system_prompt.txt')
        self.system_prompt = self._load_prompt_file(prompt_file)
        self.default_prompt = self.config.get('prompts', 'default_prompt')

        # 设置
        self.screenshot_temp = self.config.get('settings', 'screenshot_temp')
        self.screenshot_quality = self.config.getint('settings', 'screenshot_quality')
        self.max_image_width = self.config.getint('settings', 'max_image_width')
        self.command_delay = self.config.getfloat('settings', 'command_delay')
        self.max_turns = self.config.getint('settings', 'max_turns')

        # 运行状态
        self.conversation_history = []
        self.last_screenshot = None          # 最近一次截图的base64
        self.system_info = None              # 系统配置信息（缓存，只收集一次）
        self.image_width = 0                 # 当前截图宽度（缩放后）
        self.image_height = 0                # 当前截图高度（缩放后）
        self.last_mouse_target = None        # 最近一次movemouse的目标坐标（截图空间）

        # 屏幕分辨率（用于坐标换算，不缩放时与截图尺寸相同）
        try:
            self.screen_width, self.screen_height = pyautogui.size()
        except Exception:
            self.screen_width, self.screen_height = 1920, 1080

        # 初始化对话历史
        self.conversation_history.append({
            "role": "system",
            "content": self.system_prompt
        })

        print("=" * 60)
        print("AI屏幕控制器 v2.0 [全自动模式]")
        print("=" * 60)
        print(f"主模型   : {self.model}")
        print(f"主模型API: {self.api_url}")
        print(f"API格式  : {'Anthropic' if self.api_format == 'anthropic' else 'OpenAI兼容'}")
        print(f"思考模式 : {self.thinking_mode}")
        if self.use_transcribe:
            print(f"转述模型 : {self.transcribe_model} (已开启)")
            if self.transcribe_api_url != self.api_url:
                print(f"转述模型API: {self.transcribe_api_url}")
            else:
                print(f"转述模型API: 与主模型相同")
        else:
            print(f"转述模型 : 已关闭，截图直接发送给主模型")
        print(f"最大轮次 : {self.max_turns if self.max_turns > 0 else '不限制'}")
        if self.max_image_width > 0:
            print(f"屏幕分辨率: {self.screen_width}x{self.screen_height}，截图缩放到宽{self.max_image_width}")
        else:
            print(f"屏幕分辨率: {self.screen_width}x{self.screen_height}，截图不缩放（原始分辨率）")
        print("=" * 60)

    # ------------------------------------------------------------------
    # 配置与初始化
    # ------------------------------------------------------------------
    def load_config(self):
        """加载配置文件（自动兼容旧版格式）"""
        # 配置文件不存在时，自动生成默认配置
        if not os.path.exists(self.config_path):
            print(f"[提示] 配置文件不存在，正在生成默认配置...")
            self._generate_default_config()
            self._generate_default_prompt()
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config.read_file(f)
        except configparser.Error as e:
            print(f"[警告] config.ini 解析失败（可能是旧版格式）: {e}")
            print("[提示] 正在自动修复配置文件...")
            self._repair_config()

    def _get_bool(self, section, option, fallback=False):
        """健壮的布尔值读取（容忍 ture/flase/treu 等常见拼写错误）"""
        try:
            return self.config.getboolean(section, option, fallback=fallback)
        except ValueError:
            raw = self.config.get(section, option, fallback='').strip().lower()
            # 按首字母判断：t/y/1/on → True，f/n/0/off → False
            if raw.startswith(('t', 'y', '1', 'on')):
                return True
            if raw.startswith(('f', 'n', '0', 'off')):
                return False
            return fallback

    def _extract_api_settings(self):
        """从损坏的旧版config.ini中提取API设置"""
        settings = {}
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            for key in ['api_url', 'api_key', 'model', 'api_format', 'thinking_mode', 'transcribe_api_url', 'transcribe_api_key', 'transcribe_model']:
                match = re.search(rf'^\s*{key}\s*=\s*(.+)$', content, re.MULTILINE)
                if match:
                    val = match.group(1).strip()
                    if val:  # 跳过空值
                        settings[key] = val
        except Exception:
            pass
        return settings

    def _generate_default_config(self, api_settings=None):
        """生成默认config.ini"""
        if api_settings is None:
            api_settings = {}
        lines = [
            "[api]",
            "# 主模型API配置",
            f"api_url = {api_settings.get('api_url', 'https://api.openai.com/v1')}",
            f"api_key = {api_settings.get('api_key', 'your_api_key_here')}",
            f"model = {api_settings.get('model', 'gpt-4')}",
            f"api_format = {api_settings.get('api_format', 'openai')}",
            f"thinking_mode = {api_settings.get('thinking_mode', 'default')}",
            "",
            "# 图片转述模型API配置（留空则复用主模型的api_url和api_key）",
            f"transcribe_api_url = {api_settings.get('transcribe_api_url', '')}",
            f"transcribe_api_key = {api_settings.get('transcribe_api_key', '')}",
            f"transcribe_model = {api_settings.get('transcribe_model', 'mimo-v2.5')}",
            "",
            "# 是否开启图片转述模型 (true=截图先转文字再给主模型, false=截图直接发给主模型)",
            "use_transcribe = true",
            "",
            "[prompts]",
            "system_prompt_file = system_prompt.txt",
            "default_prompt = 请帮我查看当前屏幕内容，并告诉我你看到了什么。",
            "",
            "[settings]",
            "screenshot_temp = temp_screenshot.png",
            "screenshot_quality = 80",
            "max_image_width = 0",
            "command_delay = 0.3",
            "auto_execute = true",
            "max_turns = 100",
            "",
        ]
        with open(self.config_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
        print(f"[完成] 已生成新配置: {self.config_path}")

    def _generate_default_prompt(self):
        """生成默认system_prompt.txt"""
        prompt_path = os.path.join(self.base_dir if hasattr(self, 'base_dir') else os.path.dirname(os.path.abspath(self.config_path)), 'system_prompt.txt')
        if os.path.exists(prompt_path):
            return
        content = (
            "你是全自动电脑控制助手。你的任务是自主操作用户的电脑完成目标，全程不需要询问用户。\n\n"
            "核心规则：\n"
            "1. 你每次回复必须包含至少一个操作命令，或者输出 {wait 秒数}，或者输出 {stop}。\n"
            "2. 你绝不允许向用户提问或等待用户输入。\n"
            "3. 不确定屏幕状态时，先输出 {print screen}。\n"
            "4. 任务完成后输出 {stop}。\n\n"
            "可用命令：\n"
            "1. {print screen} - 截取当前屏幕\n"
            "2. {movemouse x,y} - 移动鼠标\n"
            "3. {clickmouse left/right/middle} - 点击鼠标\n"
            "4. {clickbutton 按键名} - 点击键盘按键\n"
            "5. {long-clickmouse left/right/middle 秒} - 长按鼠标\n"
            "6. {long-clickbutton 按键名 秒} - 长按键盘按键\n"
            "7. {more_clickbutton 按键1 按键2 ...} - 组合键（最多5个）\n"
            "8. {addfile 文件路径 文件内容} - 写入文件\n"
            "9. {delfile 文件路径} - 删除文件\n"
            "10. {wait 秒数} - 等待\n"
            "11. {stop} - 结束任务\n\n"
            "请用中文回复，每次回复开头用一句话说明你要做什么，然后输出命令。\n"
        )
        with open(prompt_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[完成] 已生成提示词: {prompt_path}")

    def _collect_system_info(self):
        """收集系统配置信息（支持多CPU/GPU/网卡/ROM，缓存）"""
        if self.system_info is not None:
            return self.system_info

        lines = []
        try:
            # PowerShell收集所有硬件，类别间用tab分隔，同类多项用~@~分隔
            ps = (
                "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8;"
                "$ErrorActionPreference='SilentlyContinue';"
                "$os=(Get-CimInstance Win32_OperatingSystem).Caption -replace 'Microsoft ','';"
                "$dv=(Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion').DisplayVersion;"
                "$cpus=(Get-CimInstance Win32_Processor|ForEach-Object{$_.Name.Trim()}) -join '~@~';"
                "$totalGB=[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB);"
                "$memSpeed=(Get-CimInstance Win32_PhysicalMemory|Select-Object -First 1).Speed;"
                "$ddr=if($memSpeed -le 1066){'DDR2'}elseif($memSpeed -le 1866){'DDR3'}elseif($memSpeed -le 4000){'DDR4'}else{'DDR5'};"
                "$disks=(Get-CimInstance Win32_DiskDrive|Sort-Object Size -Descending|ForEach-Object{$g=[math]::Round($_.Size/1GB);$t=if($_.MediaType -like '*SSD*'){'SSD'}else{'HDD'};\"${g}GB ${t}\"}) -join '~@~';"
                "$gpus=(Get-CimInstance Win32_VideoController|ForEach-Object{$_.Name.Trim()}) -join '~@~';"
                "$nics=(Get-CimInstance Win32_NetworkAdapter|Where-Object{$_.NetEnabled -eq $true -and $_.Speed -gt 0}|ForEach-Object{$m=[math]::Round($_.Speed/1e6);if($m -ge 1000){\"${m}M ($([math]::Round($m/1000))Gbps)\"}else{\"${m}M (${m}Mbps)\"}}) -join '~@~';"
                "Write-Output \"OS`t$os $dv\";"
                "Write-Output \"CPU`t$cpus\";"
                "Write-Output \"RAM`t$ddr ${totalGB}GB\";"
                "Write-Output \"ROM`t$disks\";"
                "Write-Output \"GPU`t$gpus\";"
                "Write-Output \"NIC`t$nics\""
            )
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command', ps],
                capture_output=True, timeout=20,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            )
            stdout = self._smart_decode(result.stdout).strip()

            # 按行解析，每行格式：KEY\t值1~@~值2~@~值3
            data = {}
            for line in stdout.splitlines():
                line = line.strip()
                if '\t' in line:
                    key, val = line.split('\t', 1)
                    data[key.strip()] = val.strip()

            def fmt_items(key, label):
                """格式化单项或多项硬件"""
                val = data.get(key, '')
                if not val:
                    return
                items = [v for v in val.split('~@~') if v.strip()]
                if len(items) == 1:
                    lines.append(f"{label}: {items[0].strip()}")
                else:
                    for i, item in enumerate(items, 1):
                        lines.append(f"{label}{i}: {item.strip()}")

            # SYSTEM
            if data.get('OS'):
                lines.append(f"SYSTEM: {data['OS'].strip()}")
            # CPU（多个时编号）
            fmt_items('CPU', 'CPU')
            # RAM
            if data.get('RAM'):
                lines.append(f"RAM: {data['RAM'].strip()}")
            # ROM/磁盘（多个时编号）
            fmt_items('ROM', 'ROM')
            # GPU（多个时编号）
            fmt_items('GPU', 'GPU')
            # 网卡（多个时编号）
            fmt_items('NIC', '网卡')

        except Exception as e:
            print(f"[警告] 获取系统信息失败: {e}")

        self.system_info = "\n".join(lines) if lines else ""
        return self.system_info

    def _repair_config(self):
        """修复旧版config.ini：提取API设置，重新生成新格式"""
        api_settings = self._extract_api_settings()
        if api_settings:
            print(f"[信息] 已从旧配置中提取: api_url={api_settings.get('api_url', '?')}, model={api_settings.get('model', '?')}")
        # 备份旧文件
        try:
            backup_path = self.config_path + '.bak'
            import shutil
            shutil.copy2(self.config_path, backup_path)
            print(f"[信息] 旧配置已备份到: {backup_path}")
        except Exception:
            pass
        # 生成新配置（保留API设置）
        self._generate_default_config(api_settings)
        self._generate_default_prompt()
        # 重新加载
        self.config = configparser.ConfigParser()
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config.read_file(f)
        print("[完成] 配置已修复并重新加载")

    def _is_first_run(self):
        """检测是否首次运行（API key 为空或占位符）"""
        key = (self.api_key or '').strip()
        return not key or key == 'your_api_key_here'

    def _launch_wizard(self):
        """首次运行时启动配置向导"""
        wizard_path = os.path.join(self.base_dir, 'config_wizard.exe')
        print("\n" + "=" * 60)
        print("[首次运行] 检测到未配置API，启动配置向导...")
        print("=" * 60)

        if os.path.exists(wizard_path):
            try:
                subprocess.run([wizard_path], cwd=self.base_dir)
            except Exception as e:
                print(f"[错误] 启动配置向导失败: {e}")
                return

            # 向导关闭后重新加载配置
            self.config = configparser.ConfigParser()
            self.load_config()
            self._read_api_config()
            print("[完成] 配置已重新加载")
        else:
            print(f"[警告] 未找到配置向导: {wizard_path}")
            print("请手动编辑 config.ini 填写API配置")

    def _read_api_config(self):
        """读取API相关配置（供初始化和向导后重载使用）"""
        self.api_key = self.config.get('api', 'api_key')
        self.model = self.config.get('api', 'model')
        self.api_format = self.config.get('api', 'api_format', fallback='openai').strip().lower()
        self.thinking_mode = self.config.get('api', 'thinking_mode', fallback='default').strip().lower()
        self.api_url = self._normalize_api_url(self.config.get('api', 'api_url'))

        self.transcribe_model = self.config.get('api', 'transcribe_model', fallback='mimo-v2.5')
        self.use_transcribe = self._get_bool('api', 'use_transcribe', fallback=True)
        transcribe_url = self.config.get('api', 'transcribe_api_url', fallback='').strip()
        transcribe_key = self.config.get('api', 'transcribe_api_key', fallback='').strip()
        if transcribe_url:
            self.transcribe_api_url = self._normalize_api_url(transcribe_url)
        else:
            self.transcribe_api_url = self.api_url
        self.transcribe_api_key = transcribe_key if transcribe_key else self.api_key

    def _normalize_api_url(self, url):
        """自动补全API接口路径（根据API格式）"""
        url = url.strip().rstrip('/')

        if self.api_format == 'anthropic':
            # Anthropic: {base}/messages
            if url.endswith('/messages'):
                return url
            return url + '/messages'

        # OpenAI兼容: {base}/chat/completions
        known_endpoints = ['/chat/completions', '/completions', '/embeddings']
        if any(url.endswith(ep) for ep in known_endpoints):
            return url
        if url.endswith('/v1'):
            return url + '/chat/completions'
        return url + '/v1/chat/completions'

    def _load_prompt_file(self, prompt_file):
        """从txt文件加载系统提示词"""
        if os.path.isabs(prompt_file):
            path = prompt_file
        else:
            path = os.path.join(self.base_dir, prompt_file)

        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                if content:
                    print(f"[配置] 已加载提示词: {path}")
                    return content
            except Exception as e:
                print(f"[警告] 读取提示词文件失败: {e}")

        print(f"[警告] 提示词文件不存在: {path}，使用内置默认提示词")
        return (
            "你是全自动电脑控制助手。你每次回复必须包含至少一个操作命令，"
            "或者输出 {wait 秒数}，或者输出 {stop} 结束任务。绝不允许向用户提问。"
        )

    # ------------------------------------------------------------------
    # API调用
    # ------------------------------------------------------------------
    def _call_main_model(self):
        """调用主模型（根据api_format分发到OpenAI或Anthropic），返回文本或None"""
        if self.api_format == 'anthropic':
            return self._call_anthropic()
        return self._call_openai()

    def _call_openai(self):
        """OpenAI兼容格式调用"""
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            payload = {
                "model": self.model,
                "messages": self.conversation_history,
                "max_tokens": 4096,
                "temperature": 0.7
            }
            # 思考模式
            if self.thinking_mode == 'medium':
                payload["reasoning_effort"] = "medium"

            response = requests.post(self.api_url, headers=headers, json=payload, timeout=180)

            if response.status_code != 200:
                print(f"[错误] API返回 {response.status_code}: {response.text[:300]}")
                return None

            result = response.json()
            message = result['choices'][0]['message']
            content = message.get('content') or ''
            # 推理模型兜底
            if not content.strip():
                reasoning = message.get('reasoning_content') or ''
                if reasoning.strip():
                    content = reasoning.strip()[-800:]
            return content if content.strip() else None

        except requests.exceptions.Timeout:
            print("[错误] API请求超时")
            return None
        except requests.exceptions.ConnectionError:
            print("[错误] 无法连接到API服务器")
            return None
        except Exception as e:
            print(f"[错误] API调用失败: {e}")
            return None

    def _call_anthropic(self):
        """Anthropic格式调用"""
        try:
            # 分离system消息（Anthropic用单独的system参数）
            system_msg = ""
            messages = []
            for msg in self.conversation_history:
                if msg['role'] == 'system':
                    system_msg = msg['content'] if isinstance(msg['content'], str) else str(msg['content'])
                else:
                    role = msg['role'] if msg['role'] in ('user', 'assistant') else 'user'
                    content = msg['content']
                    # 处理多模态内容（图片）
                    if isinstance(content, list):
                        parts = []
                        for part in content:
                            if isinstance(part, dict):
                                if part.get('type') == 'text':
                                    parts.append({"type": "text", "text": part.get('text', '')})
                                elif part.get('type') == 'image_url':
                                    url = part.get('image_url', {}).get('url', '')
                                    if url.startswith('data:'):
                                        try:
                                            header, data = url.split(',', 1)
                                            media_type = header.split(';')[0].split(':')[1]
                                            parts.append({
                                                "type": "image",
                                                "source": {"type": "base64", "media_type": media_type, "data": data}
                                            })
                                        except Exception:
                                            pass
                        if parts:
                            messages.append({"role": role, "content": parts})
                    elif isinstance(content, str):
                        messages.append({"role": role, "content": content})

            if not messages:
                return None

            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            }
            payload = {
                "model": self.model,
                "max_tokens": 4096,
                "messages": messages
            }
            if system_msg:
                payload["system"] = system_msg
            # 思考模式
            if self.thinking_mode == 'medium':
                payload["thinking"] = {"type": "enabled", "budget_tokens": 10000}

            response = requests.post(self.api_url, headers=headers, json=payload, timeout=180)

            if response.status_code != 200:
                print(f"[错误] Anthropic API返回 {response.status_code}: {response.text[:300]}")
                return None

            result = response.json()
            content_blocks = result.get('content', [])
            text = ""
            for block in content_blocks:
                if isinstance(block, dict) and block.get('type') == 'text':
                    text += block.get('text', '')
            return text if text.strip() else None

        except requests.exceptions.Timeout:
            print("[错误] Anthropic API请求超时")
            return None
        except requests.exceptions.ConnectionError:
            print("[错误] 无法连接到Anthropic API服务器")
            return None
        except Exception as e:
            print(f"[错误] Anthropic API调用失败: {e}")
            return None

    def _transcribe_image(self, image_base64):
        """调用转述模型，把截图转成文字描述（使用独立的转述API配置）"""
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.transcribe_api_key}"
            }
            payload = {
                "model": self.transcribe_model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "请用中文详细描述这张电脑屏幕截图："
                                    "当前打开了什么窗口、显示了什么内容、有哪些图标/按钮/文字、"
                                    "任务栏状态、鼠标可能在什么位置。"
                                    "描述要具体准确，便于另一个AI据此操作电脑。"
                                    "只输出描述文字，不要输出任何命令。"
                                )
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 4096,
                "temperature": 0.3
            }

            response = requests.post(self.transcribe_api_url, headers=headers, json=payload, timeout=180)

            if response.status_code != 200:
                print(f"[警告] 转述模型返回 {response.status_code}: {response.text[:200]}")
                return None

            result = response.json()
            content = result['choices'][0]['message'].get('content') or ''

            # 推理模型可能把答案放在reasoning_content里，或content为空时兜底
            if not content.strip():
                reasoning = result['choices'][0]['message'].get('reasoning_content') or ''
                if reasoning.strip():
                    # 取推理内容的最后部分作为描述
                    content = reasoning.strip()[-800:]

            return content if content.strip() else None

        except Exception as e:
            print(f"[警告] 转述模型调用失败: {e}")
            return None

    # ------------------------------------------------------------------
    # 硬件操作
    # ------------------------------------------------------------------
    def capture_screen(self):
        """截取屏幕并返回base64编码（在图上按比例标注鼠标坐标）"""
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

            # 记录真实屏幕尺寸
            self.screen_width, self.screen_height = img.size

            # 缩放图片（max_image_width <= 0 时不缩放，直接用原始分辨率）
            if self.max_image_width > 0 and img.width > self.max_image_width:
                ratio = self.max_image_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((self.max_image_width, new_height), Image.Resampling.LANCZOS)

            # 记录截图尺寸（用于坐标换算，不缩放时与屏幕尺寸相同）
            self.image_width, self.image_height = img.size

            # 绘制鼠标坐标标注
            self._draw_mouse_marker(img)

            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=self.screenshot_quality)
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

            print(f"[执行] 截图完成 {img.width}x{img.height}（真实屏幕 {self.screen_width}x{self.screen_height}）")
            return img_base64

        except Exception as e:
            print(f"[错误] 截图失败: {e}")
            return None

    def _get_marker_font(self, size=14):
        """尝试加载清晰的字体"""
        font_paths = [
            "arial.ttf",
            "segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/simhei.ttf",
        ]
        for path in font_paths:
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
        return ImageFont.load_default()

    def _draw_mouse_marker(self, img):
        """在截图上按比例标注鼠标坐标位置"""
        try:
            draw = ImageDraw.Draw(img)
            font = self._get_marker_font(14)
            scale_x = img.width / self.screen_width if self.screen_width else 1
            scale_y = img.height / self.screen_height if self.screen_height else 1

            # 1. 标注当前实际鼠标位置（红色十字 + 圆圈）
            try:
                actual_x, actual_y = pyautogui.position()
            except Exception:
                actual_x, actual_y = 0, 0

            ix = int(actual_x * scale_x)
            iy = int(actual_y * scale_y)
            r = 8
            # 圆圈
            draw.ellipse([ix - r, iy - r, ix + r, iy + r], outline=(255, 60, 60), width=2)
            # 十字线
            draw.line([ix - 14, iy, ix + 14, iy], fill=(255, 60, 60), width=2)
            draw.line([ix, iy - 14, ix, iy + 14], fill=(255, 60, 60), width=2)
            # 标签（截图空间坐标，AI输出的就是这个）
            label = f"mouse ({ix},{iy})"
            # 文字背景条，提高可读性
            bbox = draw.textbbox((ix + 12, iy - 22), label, font=font)
            draw.rectangle(bbox, fill=(0, 0, 0))
            draw.text((ix + 12, iy - 22), label, fill=(255, 80, 80), font=font)

            # 2. 标注最近一次movemouse目标（黄色，若与实际位置不同）
            if self.last_mouse_target is not None:
                tx, ty = self.last_mouse_target  # 已经是截图空间坐标
                if (tx, ty) != (ix, iy):
                    draw.ellipse([tx - r, ty - r, tx + r, ty + r], outline=(255, 220, 0), width=2)
                    tlabel = f"target ({tx},{ty})"
                    bbox2 = draw.textbbox((tx + 12, ty + 8), tlabel, font=font)
                    draw.rectangle(bbox2, fill=(0, 0, 0))
                    draw.text((tx + 12, ty + 8), tlabel, fill=(255, 220, 0), font=font)

        except Exception as e:
            print(f"[警告] 坐标标注失败: {e}")

    def _image_to_screen(self, x, y):
        """把截图坐标换算为真实屏幕坐标"""
        if self.image_width > 0 and self.screen_width > 0:
            real_x = round(x * self.screen_width / self.image_width)
            real_y = round(y * self.screen_height / self.image_height)
        else:
            real_x, real_y = x, y
        # 限制在屏幕范围内
        real_x = max(0, min(real_x, self.screen_width - 1))
        real_y = max(0, min(real_y, self.screen_height - 1))
        return real_x, real_y

    def move_mouse(self, coord_str):
        """移动鼠标到指定坐标（AI输出截图坐标，自动换算为真实屏幕坐标）"""
        try:
            coords = coord_str.strip().split(',')
            if len(coords) != 2:
                print(f"[错误] 坐标格式错误: {coord_str}，应为 x,y")
                return False
            x = int(coords[0].strip())
            y = int(coords[1].strip())

            # 截图坐标 -> 真实屏幕坐标（按比例换算）
            real_x, real_y = self._image_to_screen(x, y)

            pyautogui.moveTo(real_x, real_y, duration=0.3)
            # 记录目标坐标（截图空间），用于截图标注
            self.last_mouse_target = (x, y)

            if (real_x, real_y) != (x, y):
                print(f"[执行] 鼠标移动: 截图坐标({x},{y}) -> 屏幕坐标({real_x},{real_y})")
            else:
                print(f"[执行] 鼠标移动到 ({real_x}, {real_y})")
            return True
        except Exception as e:
            print(f"[错误] 移动鼠标失败: {e}")
            return False

    def click_mouse(self, button):
        """点击鼠标"""
        try:
            button = button.strip().lower()
            if button not in ['left', 'right', 'middle']:
                print(f"[错误] 无效的鼠标按钮: {button}")
                return False
            pyautogui.click(button=button)
            print(f"[执行] 点击鼠标{button}键")
            return True
        except Exception as e:
            print(f"[错误] 点击鼠标失败: {e}")
            return False

    def click_button(self, key):
        """点击键盘按键"""
        try:
            key = key.strip().lower()
            pyautogui.press(key)
            print(f"[执行] 点击按键: {key}")
            return True
        except Exception as e:
            print(f"[错误] 点击按键失败: {e}")
            return False

    def long_click_mouse(self, button, duration):
        """长按鼠标"""
        try:
            button = button.strip().lower()
            duration = float(duration)
            if button not in ['left', 'right', 'middle']:
                print(f"[错误] 无效的鼠标按钮: {button}")
                return False
            if duration <= 0 or duration > 30:
                print(f"[错误] 持续时间无效: {duration}秒")
                return False
            pyautogui.mouseDown(button=button)
            time.sleep(duration)
            pyautogui.mouseUp(button=button)
            print(f"[执行] 长按鼠标{button}键 {duration}秒")
            return True
        except Exception as e:
            print(f"[错误] 长按鼠标失败: {e}")
            return False

    def long_click_button(self, key, duration):
        """长按键盘按键"""
        try:
            key = key.strip().lower()
            duration = float(duration)
            if duration <= 0 or duration > 30:
                print(f"[错误] 持续时间无效: {duration}秒")
                return False
            pyautogui.keyDown(key)
            time.sleep(duration)
            pyautogui.keyUp(key)
            print(f"[执行] 长按按键 {key} {duration}秒")
            return True
        except Exception as e:
            print(f"[错误] 长按按键失败: {e}")
            return False

    def combo_click_button(self, keys):
        """组合键：从第一个按键开始按住，依次按下后续按键，全部按下后依次松开"""
        pressed = []
        try:
            keys = [k.strip().lower() for k in keys if k.strip()]
            if not keys:
                print("[错误] 组合键不能为空")
                return False
            if len(keys) > 5:
                print(f"[错误] 组合键最多5个按键，收到 {len(keys)} 个")
                return False

            combo_str = ' + '.join(keys)
            print(f"[执行] 组合键: {combo_str}")

            # 依次按下所有按键（间隔0.05s，远小于0.5s限制）
            for k in keys:
                pyautogui.keyDown(k)
                pressed.append(k)
                time.sleep(0.05)

            # 全部按完后，反向依次松开
            for k in reversed(pressed):
                pyautogui.keyUp(k)
                time.sleep(0.02)

            print(f"[完成] 组合键已执行: {combo_str}")
            return True

        except Exception as e:
            # 异常时确保所有按键被释放，防止卡键
            for k in reversed(pressed):
                try:
                    pyautogui.keyUp(k)
                except Exception:
                    pass
            print(f"[错误] 组合键执行失败: {e}")
            return False

    def add_file(self, filepath, content):
        """写入文件（UTF-8 BOM编码，确保PowerShell等Windows工具正确读取）"""
        try:
            filepath = filepath.strip()
            content = content.strip()
            dir_path = os.path.dirname(filepath)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
            # utf-8-sig = UTF-8 with BOM，PowerShell Add-Type等工具能正确识别
            with open(filepath, 'w', encoding='utf-8-sig') as f:
                f.write(content)
            print(f"[执行] 写入文件: {filepath}")
            return True
        except Exception as e:
            print(f"[错误] 写入文件失败: {e}")
            return False

    def delete_file(self, filepath):
        """删除文件"""
        try:
            filepath = filepath.strip()
            if not os.path.exists(filepath):
                print(f"[错误] 文件不存在: {filepath}")
                return False
            os.remove(filepath)
            print(f"[执行] 删除文件: {filepath}")
            return True
        except Exception as e:
            print(f"[错误] 删除文件失败: {e}")
            return False

    # ------------------------------------------------------------------
    # 命令执行 / 进程 / 窗口截图
    # ------------------------------------------------------------------
    @staticmethod
    def _smart_decode(raw):
        """智能解码：优先UTF-8，失败回退GBK（中文Windows默认编码）"""
        if raw is None:
            return ''
        if isinstance(raw, str):
            return raw
        try:
            return raw.decode('utf-8')
        except (UnicodeDecodeError, AttributeError):
            try:
                return raw.decode('gbk')
            except (UnicodeDecodeError, AttributeError):
                return raw.decode('utf-8', errors='replace')

    def run_command(self, shell, command):
        """运行cmd或powershell命令，返回输出文本（已处理编码）"""
        try:
            if shell == 'cmd':
                # CMD输出系统编码(GBK)，不做特殊处理
                full_cmd = ['cmd', '/c', command]
            else:
                # PowerShell：强制输出UTF-8编码
                full_cmd = ['powershell', '-NoProfile', '-Command',
                            '[Console]::OutputEncoding=[System.Text.Encoding]::UTF8;' + command]

            result = subprocess.run(
                full_cmd,
                capture_output=True, timeout=30,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            )

            # 智能解码（UTF-8优先，GBK回退）
            output = self._smart_decode(result.stdout).strip()
            error = self._smart_decode(result.stderr).strip()

            # 限制输出长度
            max_len = 3000
            truncated = False
            if len(output) > max_len:
                output = output[:max_len]
                truncated = True

            combined = output
            if error:
                if combined:
                    combined += '\n\n[stderr]\n'
                combined += error[:500]

            if not combined:
                combined = '(命令执行完成，无输出)'
            if truncated:
                combined += f'\n... (输出过长已截断)'

            print(f"[执行] {shell}: {command[:80]}")
            return combined[:4000]

        except subprocess.TimeoutExpired:
            return '[错误] 命令执行超时(30秒)'
        except Exception as e:
            return f'[错误] 命令执行失败: {e}'

    def get_processes(self, filter_type='all'):
        """获取进程列表，filter_type: system=系统进程, user=用户程序, all=全部"""
        # 构建PowerShell过滤条件
        if filter_type == 'system':
            # C:\Windows\ 下的进程 + 无路径的内核级系统进程
            where_clause = 'Where-Object { if ($_.Path) { $_.Path -like "C:\\Windows\\*" } else { $true } }'
            label = '系统进程'
        elif filter_type == 'user':
            # 有路径且不在 C:\Windows\ 下的进程（用户安装的程序）
            where_clause = 'Where-Object { $_.Path -and $_.Path -notlike "C:\\Windows\\*" }'
            label = '用户程序'
        else:
            # 全部进程
            where_clause = ''
            label = '全部进程'

        try:
            filter_part = f'| {where_clause}' if where_clause else ''
            ps_cmd = (
                '[Console]::OutputEncoding=[System.Text.Encoding]::UTF8;'
                '$all=Get-Process ' + filter_part + '; '
                'Write-Output ("TOTAL:" + $all.Count); '
                '$all | Select-Object Id,ProcessName,@{N="Mem(MB)";E={[math]::Round($_.WorkingSet64/1MB,1)}} | '
                'Sort-Object ProcessName | Format-Table -AutoSize | Out-String -Width 120'
            )
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command', ps_cmd],
                capture_output=True, timeout=20,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            )
            output = self._smart_decode(result.stdout).strip()

            total = '?'
            lines = output.splitlines()
            table_lines = []
            for line in lines:
                if line.startswith('TOTAL:'):
                    total = line.replace('TOTAL:', '').strip()
                else:
                    table_lines.append(line)

            table = '\n'.join(table_lines).strip()
            header = f"[{label}列表] 共{total}个（按名称排序）：\n"
            return header + table if table else f'(未找到{label})'

        except Exception as e:
            return f'[错误] 获取进程失败: {e}'

    def search_processes(self, keyword):
        """按关键词搜索进程（匹配进程名，不区分大小写）"""
        try:
            keyword = keyword.strip()
            if not keyword:
                return 'Error:Not have result.'

            # 用PowerShell搜索包含关键词的进程名
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command',
                 '[Console]::OutputEncoding=[System.Text.Encoding]::UTF8;'
                 f'$kw="{keyword}"; '
                 '$all=Get-Process | Where-Object { $_.ProcessName -like "*$kw*" }; '
                 'Write-Output ("TOTAL:" + @($all).Count); '
                 '$all | Select-Object Id,ProcessName,@{N="Mem(MB)";E={[math]::Round($_.WorkingSet64/1MB,1)}} | '
                 'Sort-Object ProcessName | Format-Table -AutoSize | Out-String -Width 120'],
                capture_output=True, timeout=15,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            )
            output = self._smart_decode(result.stdout).strip()

            total = '0'
            lines = output.splitlines()
            table_lines = []
            for line in lines:
                if line.startswith('TOTAL:'):
                    total = line.replace('TOTAL:', '').strip()
                else:
                    table_lines.append(line)

            # 无结果时按要求返回错误信息
            if total == '0' or not any(l.strip() for l in table_lines):
                return 'Error:Not have result.'

            table = '\n'.join(table_lines).strip()
            header = f"[搜索结果] 关键词: {keyword}，找到{total}个匹配进程：\n"
            return header + table

        except Exception as e:
            return f'Error:Not have result.'

    def _find_pid_by_name(self, name):
        """根据进程名找PID（支持带或不带.exe后缀）"""
        try:
            result = subprocess.run(
                ['tasklist', '/FO', 'CSV', '/NH'],
                capture_output=True, timeout=10,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            )
            output = self._smart_decode(result.stdout)
            name_lower = name.lower()
            name_no_ext = name_lower.replace('.exe', '')
            for line in output.splitlines():
                parts = line.replace('"', '').split(',')
                if len(parts) >= 2:
                    proc = parts[0].lower()
                    proc_no_ext = proc.replace('.exe', '')
                    if proc == name_lower or proc_no_ext == name_no_ext:
                        return int(parts[1])
        except Exception:
            pass
        return None

    def _find_pid_by_path(self, path):
        """根据可执行文件路径找PID"""
        try:
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command',
                 '[Console]::OutputEncoding=[System.Text.Encoding]::UTF8;'
                 f'(Get-Process | Where-Object {{$_.Path -eq "{path}"}} | Select-Object -First 1).Id'],
                capture_output=True, timeout=10,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            )
            output = self._smart_decode(result.stdout).strip()
            if output.isdigit():
                return int(output)
        except Exception:
            pass
        return None

    def _get_windows_by_pid(self, pid):
        """根据PID获取可见窗口列表"""
        windows = []
        try:
            user32 = ctypes.windll.user32

            def enum_callback(hwnd, _):
                if user32.IsWindowVisible(hwnd):
                    window_pid = wintypes.DWORD()
                    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
                    if window_pid.value == pid:
                        rect = wintypes.RECT()
                        user32.GetWindowRect(hwnd, ctypes.byref(rect))
                        length = user32.GetWindowTextLengthW(hwnd)
                        buf = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buf, length + 1)
                        title = buf.value
                        if title:
                            windows.append({
                                'hwnd': hwnd,
                                'title': title,
                                'rect': (rect.left, rect.top, rect.right, rect.bottom)
                            })
                return True

            WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
        except Exception as e:
            print(f"[警告] 枚举窗口失败: {e}")
        return windows

    def print_window(self, identifier):
        """截取指定进程的窗口截图，返回 (base64, 信息文本)"""
        try:
            identifier = identifier.strip()
            pid = None

            if identifier.isdigit():
                pid = int(identifier)
            elif '\\' in identifier or '/' in identifier:
                pid = self._find_pid_by_path(identifier)
            else:
                pid = self._find_pid_by_name(identifier)

            if pid is None:
                return None, f'[错误] 找不到进程: {identifier}'

            windows = self._get_windows_by_pid(pid)
            if not windows:
                return None, f'[错误] PID {pid} 没有可见窗口'

            win = windows[0]
            left, top, right, bottom = win['rect']
            width = right - left
            height = bottom - top

            if width <= 0 or height <= 0:
                return None, f'[错误] 窗口尺寸异常: {width}x{height}'

            with mss.mss() as sct:
                monitor = {'left': left, 'top': top, 'width': width, 'height': height}
                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=self.screenshot_quality)
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

            info = f'窗口: {win["title"]} | PID: {pid} | 尺寸: {width}x{height}'
            print(f"[执行] 窗口截图: {info}")
            return img_base64, info

        except Exception as e:
            return None, f'[错误] 窗口截图失败: {e}'

    # ------------------------------------------------------------------
    # SMTC 媒体服务控制
    # ------------------------------------------------------------------
    # PowerShell SMTC 前置代码（WinRT Await 兼容写法）
    _SMTC_PREAMBLE = (
        "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8;"
        "$ErrorActionPreference='SilentlyContinue';"
        "Add-Type -AssemblyName System.Runtime.WindowsRuntime;"
        "function Await($WinRtTask,$ResultType){"
        "$asTaskGeneric=([System.WindowsRuntimeSystemExtensions].GetMethods()|Where-Object{$_.Name-eq'AsTask'-and$_.GetParameters().Count-eq 1-and$_.GetParameters()[0].ParameterType.Name-eq'IAsyncOperation`1'})[0];"
        "$asTask=$asTaskGeneric.MakeGenericMethod($ResultType);"
        "$netTask=$asTask.Invoke($null,@($WinRtTask));"
        "$netTask.Wait(-1)|Out-Null;"
        "$netTask.Result}"
        "$null=[Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager,Windows.Media.Control,ContentType=WindowsRuntime];"
        "$async=[Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager,Windows.Media.Control,ContentType=WindowsRuntime]::RequestAsync();"
        "$mgr=Await $async ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager,Windows.Media.Control,ContentType=WindowsRuntime]);"
    )

    def _run_powershell(self, ps_command, timeout=20):
        """运行PowerShell命令，返回输出文本（智能解码）"""
        try:
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command', ps_command],
                capture_output=True, timeout=timeout,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            )
            return self._smart_decode(result.stdout).strip()
        except subprocess.TimeoutExpired:
            return '[错误] PowerShell执行超时'
        except Exception as e:
            return f'[错误] PowerShell执行失败: {e}'

    def smtc_control(self, action):
        """通过SMTC控制媒体播放"""
        action_map = {
            'play': ('TryPlayAsync', '播放'),
            'pause': ('TryPauseAsync', '暂停'),
            'next': ('TrySkipNextAsync', '下一曲'),
            'previous': ('TrySkipPreviousAsync', '上一曲'),
        }
        if action not in action_map:
            return f'[错误] 无效的媒体控制操作: {action}'

        method, label = action_map[action]
        ps = (
            self._SMTC_PREAMBLE +
            "$session=$mgr.GetCurrentSession();"
            "if($session){"
            f"$r=Await $session.{method}()([bool]);"
            f"if($r){{Write-Output '{label}成功'}}else{{Write-Output '{label}失败'}}"
            "}else{Write-Output '当前没有媒体在播放'}"
        )
        output = self._run_powershell(ps)
        print(f"[执行] 媒体控制: {label}")
        return f'[{output}]' if output else '[媒体控制完成]'

    def list_smtc(self):
        """列出当前SMTC媒体会话（正在播放的内容）"""
        ps = (
            self._SMTC_PREAMBLE +
            "$sessions=$mgr.GetSessions();"
            "$i=0;"
            "foreach($s in $sessions){"
            "$i++;"
            "$appName=$s.SourceAppUserModelId;"
            # 媒体属性（注意：正确的类型名是 MediaProperties，不是 SessionInfo）
            "$title='-';$artist='-';"
            "try{"
            "$infoAsync=$s.TryGetMediaPropertiesAsync();"
            "$info=Await $infoAsync ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionMediaProperties,Windows.Media.Control,ContentType=WindowsRuntime]);"
            "if($info){"
            "if($info.Title){$title=$info.Title};"
            "if($info.Artist){$artist=$info.Artist}"
            "}"
            "}catch{};"
            # 播放状态（注意：GetPlaybackInfo是同步方法，不是Async）
            "$status='未知';"
            "try{"
            "$pb=$s.GetPlaybackInfo();"
            "if($pb){"
            "$status=switch(\"$($pb.PlaybackStatus)\"){"
            "'4'{'播放中'}'Playing'{'播放中'}"
            "'5'{'已暂停'}'Paused'{'已暂停'}"
            "'3'{'已停止'}'Stopped'{'已停止'}"
            "'2'{'切换中'}'Changing'{'切换中'}"
            "'1'{'已打开'}'Opened'{'已打开'}"
            "'0'{'已关闭'}'Closed'{'已关闭'}"
            "default{\"$($pb.PlaybackStatus)\"}}"
            "}"
            "}catch{};"
            "Write-Output \"[$i] 应用: $appName | 曲目: $title - $artist | 状态: $status\""
            "};"
            "if($i-eq 0){Write-Output '当前没有媒体在播放'}"
        )
        output = self._run_powershell(ps)
        return output if output else '(无法获取媒体信息)'

    # ------------------------------------------------------------------
    # 命令解析与执行
    # ------------------------------------------------------------------
    def parse_commands(self, text):
        """解析AI输出中的命令"""
        commands = []

        if '{print screen}' in text:
            commands.append(('print_screen', None))

        for match in re.finditer(r'\{movemouse\s+([^}]+)\}', text):
            commands.append(('movemouse', match.group(1).strip()))

        for match in re.finditer(r'\{clickmouse\s+(left|right|middle)\}', text):
            commands.append(('clickmouse', match.group(1).strip()))

        for match in re.finditer(r'\{clickbutton\s+([^}]+)\}', text):
            commands.append(('clickbutton', match.group(1).strip()))

        for match in re.finditer(r'\{long-clickmouse\s+(left|right|middle)\s+([\d.]+)\}', text):
            commands.append(('long_clickmouse', (match.group(1).strip(), match.group(2).strip())))

        for match in re.finditer(r'\{long-clickbutton\s+(\S+)\s+([\d.]+)\}', text):
            commands.append(('long_clickbutton', (match.group(1).strip(), match.group(2).strip())))

        # 组合键：兼容 more_clickbutton 和 more_clickbotton 两种拼写
        for match in re.finditer(r'\{more_clickb(?:utton|otton)\s+([^}]+)\}', text):
            keys = match.group(1).split()
            commands.append(('combo_clickbutton', keys))

        for match in re.finditer(r'\{addfile\s+(\S+)\s+([^}]+)\}', text):
            commands.append(('addfile', (match.group(1).strip(), match.group(2))))

        for match in re.finditer(r'\{delfile\s+([^}]+)\}', text):
            commands.append(('delfile', match.group(1).strip()))

        for match in re.finditer(r'\{wait\s+([\d.]+)\}', text):
            commands.append(('wait', match.group(1).strip()))

        # {run cmd/powershell 指令} - 逐行匹配，避免指令中的}干扰
        for line in text.splitlines():
            m = re.search(r'\{run\s+(cmd|powershell)\s+(.+)\}', line)
            if m:
                commands.append(('run', (m.group(1).strip().lower(), m.group(2).strip())))

        # {list_tasks system/user/all} - 获取进程列表
        for match in re.finditer(r'\{list_tasks\s+(system|user|all)\}', text):
            commands.append(('list_tasks', match.group(1).strip()))

        # {task} - 简写，等同于 {list_tasks all}
        if re.search(r'\{task\}', text):
            commands.append(('list_tasks', 'all'))

        # {search_tasks 关键词} - 搜索进程
        for match in re.finditer(r'\{search_tasks\s+([^}]+)\}', text):
            commands.append(('search_tasks', match.group(1).strip()))

        # {print window PID/NAME/路径} - 截取指定窗口
        for match in re.finditer(r'\{print window\s+([^}]+)\}', text):
            commands.append(('print_window', match.group(1).strip()))

        # {smtc pause/play/previous/next} - 媒体控制（兼容旧拼写smtp）
        for match in re.finditer(r'\{(?:smtc|smtp)\s+(pause|play|previous|next)\}', text):
            commands.append(('smtc', match.group(1).strip()))

        # {list_smtc} - 列出正在播放的媒体（兼容旧拼写list_smtp）
        if re.search(r'\{(?:list_smtc|list_smtp)\}', text):
            commands.append(('list_smtc', None))

        if '{stop}' in text:
            commands.append(('stop', None))

        return commands

    def execute_commands(self, commands):
        """执行命令列表，返回 (结果列表, 是否停止)"""
        results = []
        stop_flag = False
        self.last_screenshot = None

        # 截图指令移到最后执行，确保截图反映其他指令执行后的屏幕状态
        screenshot_cmds = [c for c in commands if c[0] in ('print_screen', 'print_window')]
        other_cmds = [c for c in commands if c[0] not in ('print_screen', 'print_window')]
        ordered_commands = other_cmds + screenshot_cmds
        other_executed = False

        for cmd_type, params in ordered_commands:
            # 所有其他指令执行完后，延时0.1秒再截图
            if cmd_type in ('print_screen', 'print_window') and other_executed:
                time.sleep(0.1)

            result = None

            if cmd_type == 'print_screen':
                self.last_screenshot = self.capture_screen()
                result = "[截图完成]" if self.last_screenshot else "[截图失败]"

            elif cmd_type == 'print_window':
                img, info = self.print_window(params)
                if img:
                    self.last_screenshot = img
                    result = f"[窗口截图完成] {info}"
                else:
                    result = info

            elif cmd_type == 'run':
                shell, command = params
                result = self.run_command(shell, command)

            elif cmd_type == 'list_tasks':
                result = self.get_processes(params)

            elif cmd_type == 'search_tasks':
                result = self.search_processes(params)

            elif cmd_type == 'smtc':
                result = self.smtc_control(params)

            elif cmd_type == 'list_smtc':
                result = self.list_smtc()

            elif cmd_type == 'movemouse':
                ok = self.move_mouse(params)
                result = f"[鼠标已移动到 {params}]" if ok else "[移动鼠标失败]"

            elif cmd_type == 'clickmouse':
                ok = self.click_mouse(params)
                result = f"[已点击{params}键]" if ok else "[点击鼠标失败]"

            elif cmd_type == 'clickbutton':
                ok = self.click_button(params)
                result = f"[已点击{params}键]" if ok else "[点击按键失败]"

            elif cmd_type == 'long_clickmouse':
                button, duration = params
                ok = self.long_click_mouse(button, duration)
                result = f"[已长按{button}键{duration}秒]" if ok else "[长按鼠标失败]"

            elif cmd_type == 'long_clickbutton':
                key, duration = params
                ok = self.long_click_button(key, duration)
                result = f"[已长按{key}键{duration}秒]" if ok else "[长按按键失败]"

            elif cmd_type == 'combo_clickbutton':
                ok = self.combo_click_button(params)
                combo_str = ' + '.join(params)
                result = f"[已按组合键: {combo_str}]" if ok else "[组合键失败]"

            elif cmd_type == 'addfile':
                filepath, content = params
                ok = self.add_file(filepath, content)
                result = f"[文件已写入: {filepath}]" if ok else "[写入文件失败]"

            elif cmd_type == 'delfile':
                ok = self.delete_file(params)
                result = f"[文件已删除: {params}]" if ok else "[删除文件失败]"

            elif cmd_type == 'wait':
                try:
                    d = max(0.1, min(float(params), 30))
                    time.sleep(d)
                    result = f"[已等待 {d} 秒]"
                except ValueError:
                    result = "[等待参数无效]"

            elif cmd_type == 'stop':
                stop_flag = True
                result = "[AI宣布任务完成]"

            if result is not None:
                results.append(result)

            # 标记非截图命令已执行（截图前需要延时）
            if cmd_type not in ('print_screen', 'print_window', 'stop'):
                other_executed = True

            if self.command_delay > 0 and cmd_type != 'stop':
                time.sleep(self.command_delay)

        return results, stop_flag

    # ------------------------------------------------------------------
    # 全自动主循环
    # ------------------------------------------------------------------
    def run(self):
        """全自动运行循环：输入任务 -> AI自主操作直到 {stop}"""
        print("\n[模式] 全自动：AI自主操作，无需人工干预")
        print("[紧急停止] 任何时候按 Ctrl+C 可立即中止")
        print("-" * 60)

        while True:
            # 获取任务
            print(f"\n[默认任务] {self.default_prompt}")
            print("[提示] 按Enter使用默认任务，或输入新任务；输入 quit 退出")
            task = input("任务> ").strip()

            if task.lower() in ['quit', 'exit', 'q']:
                print("\n[退出] 感谢使用，再见！")
                break
            if not task:
                task = self.default_prompt

            self.conversation_history = [{"role": "system", "content": self.system_prompt}]

            # 任务后面附带系统配置信息（缓存，只收集一次）
            sys_info = self._collect_system_info()
            if sys_info:
                task_msg = f"{task}\n\n---\n系统配置：\n{sys_info}"
                print("\n[系统配置]")
                print(sys_info)
            else:
                task_msg = task

            self.conversation_history.append({"role": "user", "content": task_msg})

            print("\n" + "=" * 60)
            print(f"[任务] {task}")
            print("=" * 60)

            empty_streak = 0

            for turn in range(1, self.max_turns + 1 if self.max_turns > 0 else 10 ** 9):
                # 调用主模型
                print(f"\n[第{turn}轮] 调用主模型 {self.model} ...")
                response_text = self._call_main_model()

                if response_text is None:
                    print("[错误] 主模型无响应，任务中止")
                    break

                print(f"[AI] {response_text.strip()}")

                # 记录AI回复
                self.conversation_history.append({
                    "role": "assistant",
                    "content": response_text
                })

                # 解析命令
                commands = self.parse_commands(response_text)

                if not commands:
                    empty_streak += 1
                    print(f"[警告] 本轮无命令 (连续{empty_streak}次)")
                    if empty_streak >= 3:
                        print("[停止] 连续3轮无命令，自动结束任务")
                        break
                    self.conversation_history.append({
                        "role": "user",
                        "content": "你没有输出任何操作命令。请立即输出下一个操作命令，或者如果任务已完成请输出 {stop}。"
                    })
                    continue

                empty_streak = 0

                # 执行命令
                print(f"[执行] {len(commands)} 个命令...")
                results, stop_flag = self.execute_commands(commands)

                for r in results:
                    print(f"  {r}")

                if stop_flag:
                    print("\n" + "=" * 60)
                    print("[任务完成] AI已停止操作")
                    print("=" * 60)
                    break

                # 构建反馈消息
                result_text = "\n".join(results) if results else "（无执行结果）"

                if self.last_screenshot:
                    if self.use_transcribe:
                        # 模式1：截图 -> 转述模型转文字 -> 文字喂给主模型
                        print("[转述] 截图转文字中...")
                        desc = self._transcribe_image(self.last_screenshot)
                        if desc:
                            print(f"[屏幕描述] {desc.strip()}")
                            next_msg = (
                                f"命令执行结果：\n{result_text}\n\n"
                                f"当前屏幕描述：\n{desc.strip()}\n\n"
                                f"请根据以上信息决定下一步，输出下一个操作命令（或 {{stop}}）。"
                            )
                        else:
                            next_msg = (
                                f"命令执行结果：\n{result_text}\n\n"
                                f"截图转述失败。请重新 {{print screen}} 或直接输出下一步操作命令（或 {{stop}}）。"
                            )
                    else:
                        # 模式2：截图直接发给主模型（同模型，多模态输入）
                        print("[发送] 截图直接发送给主模型...")
                        next_msg = [
                            {
                                "type": "text",
                                "text": (
                                    f"命令执行结果：\n{result_text}\n\n"
                                    f"这是当前屏幕截图，请根据屏幕内容决定下一步，"
                                    f"输出下一个操作命令（或 {{stop}}）。"
                                )
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{self.last_screenshot}",
                                    "detail": "high"
                                }
                            }
                        ]
                else:
                    next_msg = (
                        f"命令执行结果：\n{result_text}\n\n"
                        f"请输出下一个操作命令（或 {{stop}}）。"
                    )

                self.conversation_history.append({"role": "user", "content": next_msg})

            print("\n" + "-" * 60)
            print("[本轮任务结束] 输入 quit 退出，或输入新任务继续")


def main():
    """主函数"""
    try:
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        config_path = os.path.join(base_dir, 'config.ini')
        controller = AIController(config_path)
        controller.run()

    except KeyboardInterrupt:
        print("\n\n[中断] 已按Ctrl+C，程序停止")
    except Exception as e:
        print(f"\n[致命错误] {e}")
        import traceback
        traceback.print_exc()
    finally:
        input("\n按Enter键退出...")


if __name__ == '__main__':
    main()

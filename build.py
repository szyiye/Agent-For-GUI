#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包脚本 - 将AI控制器打包为exe文件
"""

import os
import sys
import subprocess
import shutil


def check_pyinstaller():
    """检查PyInstaller是否安装"""
    try:
        import PyInstaller
        return True
    except ImportError:
        return False


def install_requirements():
    """安装依赖"""
    print("[步骤1] 安装依赖...")
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    
    if not os.path.exists(requirements_path):
        print("[错误] 找不到requirements.txt")
        return False
    
    result = subprocess.run(
        [sys.executable, '-m', 'pip', 'install', '-r', requirements_path],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"[错误] 安装依赖失败:\n{result.stderr}")
        return False
    
    print("[完成] 依赖安装成功")
    return True


def build_exe():
    """打包exe"""
    print("\n[步骤2] 开始打包exe...")
    
    # 获取脚本目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(script_dir, 'main.py')
    config_file = os.path.join(script_dir, 'config.ini')
    icon_file = os.path.join(script_dir, 'icon.ico')  # 可选图标
    
    if not os.path.exists(main_script):
        print(f"[错误] 找不到主脚本: {main_script}")
        return False
    
    # 构建PyInstaller命令
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',                    # 打包成单个exe
        '--console',                    # 控制台程序
        '--name', 'AI_Controller',      # exe名称
        '--clean',                      # 清理临时文件
        '--noconfirm',                  # 不询问确认
    ]
    
    # 添加图标（如果存在）
    if os.path.exists(icon_file):
        cmd.extend(['--icon', icon_file])
    
    # 添加数据文件
    cmd.extend([
        '--add-data', f'{config_file};.',  # 添加config.ini
    ])
    
    # 添加主脚本
    cmd.append(main_script)
    
    print(f"[执行] {' '.join(cmd)}")
    
    # 执行打包
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=script_dir)
    
    if result.returncode != 0:
        print(f"[错误] 打包失败:\n{result.stderr}")
        return False
    
    print("[完成] exe打包成功")
    return True


def copy_config():
    """复制配置文件到输出目录"""
    print("\n[步骤3] 复制配置文件...")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(script_dir, 'dist')
    config_src = os.path.join(script_dir, 'config.ini')
    config_dst = os.path.join(dist_dir, 'config.ini')
    
    if not os.path.exists(dist_dir):
        print(f"[错误] 找不到输出目录: {dist_dir}")
        return False
    
    # 复制config.ini
    shutil.copy2(config_src, config_dst)
    print(f"[完成] 配置文件已复制到: {config_dst}")
    
    return True


def cleanup():
    """清理临时文件"""
    print("\n[步骤4] 清理临时文件...")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 清理build目录
    build_dir = os.path.join(script_dir, 'build')
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
        print(f"[清理] 删除: {build_dir}")
    
    # 清理spec文件
    spec_file = os.path.join(script_dir, 'AI_Controller.spec')
    if os.path.exists(spec_file):
        os.remove(spec_file)
        print(f"[清理] 删除: {spec_file}")
    
    print("[完成] 清理完成")


def main():
    """主函数"""
    print("=" * 60)
    print("AI控制器打包工具")
    print("=" * 60)
    
    # 检查PyInstaller
    if not check_pyinstaller():
        print("[信息] PyInstaller未安装，将自动安装...")
        if not install_requirements():
            input("\n按Enter键退出...")
            return
    
    # 执行打包
    if not build_exe():
        input("\n按Enter键退出...")
        return
    
    # 复制配置文件
    if not copy_config():
        input("\n按Enter键退出...")
        return
    
    # 清理
    cleanup()
    
    # 完成
    script_dir = os.path.dirname(os.path.abspath(__file__))
    exe_path = os.path.join(script_dir, 'dist', 'AI_Controller.exe')
    
    print("\n" + "=" * 60)
    print("打包完成！")
    print("=" * 60)
    print(f"\n[输出] exe文件位置:")
    print(f"  {exe_path}")
    print(f"\n[说明] 请将以下文件放在同一目录:")
    print(f"  1. AI_Controller.exe")
    print(f"  2. config.ini")
    print("\n[提示] 使用前请先编辑config.ini配置API地址和密钥")
    print("=" * 60)
    
    input("\n按Enter键退出...")


if __name__ == '__main__':
    main()

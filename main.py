#!/usr/bin/env python3
"""
统一入口文件
支持PC网页服务器、Android应用和iOS应用
"""
import argparse

# 检测运行环境
def is_android():
    """检测是否在Android环境中运行"""
    try:
        import kivy
        from kivy.utils import platform
        return platform == 'android'
    except ImportError:
        return False

def is_ios():
    """检测是否在iOS环境中运行"""
    try:
        # 检查iOS特定的模块
        import pyto_ui
        return True
    except ImportError:
        try:
            import console
            return True
        except ImportError:
            # 检查系统平台
            import sys
            if 'ios' in sys.platform:
                return True
            return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='增强版聊天应用')
    parser.add_argument('--mode', choices=['web', 'android', 'ios', 'auto'], default='auto',
                       help='运行模式: web=网页服务器, android=Android应用, ios=iOS应用, auto=自动检测')
    
    args = parser.parse_args()
    
    # 确定运行模式
    # if args.mode == 'auto':
    #     if is_android():
    #         mode = 'android'
    #     elif is_ios():
    #         mode = 'ios'
    #     else:
    #         mode = 'web'
    # else:
    #     mode = args.mode
    
    mode = 'web'
    print(f"运行模式: {mode}")
    
    # 导入核心逻辑
    from chat_core import ChatBot
    
    # 创建聊天机器人实例
    chat_bot = ChatBot()
    
    # 启动对应模式
    if mode == 'web':
        from platform_web import WebPlatform
        platform = WebPlatform(chat_bot)
        platform.start()
    elif mode == 'android':
        from platform_android import AndroidPlatform
        platform = AndroidPlatform(chat_bot)
        platform.start()
    elif mode == 'ios':
        from platform_ios import IOSPlatform
        platform = IOSPlatform(chat_bot)
        platform.start()
    else:
        print("错误: 未知的运行模式")


if __name__ == '__main__':
    main()
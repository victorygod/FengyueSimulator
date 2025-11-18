#!/usr/bin/env python3
"""
统一入口文件
支持PC网页服务器和Android应用
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


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='增强版聊天应用')
    parser.add_argument('--mode', choices=['web', 'android', 'auto'], default='auto',
                       help='运行模式: web=网页服务器, android=Android应用, auto=自动检测')
    
    args = parser.parse_args()
    
    # 确定运行模式
    if args.mode == 'auto':
        if is_android():
            mode = 'android'
        else:
            mode = 'web'
    else:
        mode = args.mode
    
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
    else:
        print("错误: 未知的运行模式")


if __name__ == '__main__':
    main()
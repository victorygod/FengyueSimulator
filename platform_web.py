#!/usr/bin/env python3
"""
业务无关的Web平台实现
使用基础平台类，完全与业务逻辑解耦
"""
import os
import webbrowser
from http.server import HTTPServer
from threading import Thread
import time

# 导入基础平台类
from base_platform import BaseHTTPRequestHandler


class WebChatHandler(BaseHTTPRequestHandler):
    """Web聊天请求处理器"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class WebPlatform:
    """Web平台实现"""
    
    def __init__(self, chat_bot):
        self.chat_bot = chat_bot
        self.port = 8000
    
    def start(self):
        """启动Web服务器"""
        # 注册API
        from api_registry import register_chat_apis
        register_chat_apis(self.chat_bot)
        
        # 加载自动保存
        self.chat_bot.load_auto_save()
        
        # 创建自定义请求处理器
        def handler_factory(*args, **kwargs):
            return WebChatHandler(*args, chat_bot=self.chat_bot, **kwargs)
        
        # 启动服务器
        server = HTTPServer(('0.0.0.0', self.port), handler_factory)
        
        print(f"聊天服务器已启动，访问 http://localhost:{self.port}")
        print("按 Ctrl+C 停止服务器")
        
        # 自动打开浏览器
        def open_browser():
            try:
                webbrowser.open(f'http://localhost:{self.port}')
            except:
                print("无法自动打开浏览器，请手动访问上述地址")
        
        # 延迟打开浏览器
        Thread(target=open_browser).start()
        
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n服务器已停止")
            server.shutdown()
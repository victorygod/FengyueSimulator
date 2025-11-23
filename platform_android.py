#!/usr/bin/env python3
"""
业务无关的Android平台实现
使用基础平台类，完全与业务逻辑解耦
"""
import os
from http.server import HTTPServer
from threading import Thread
import time

# 导入基础平台类
from base_platform import BaseHTTPRequestHandler


class AndroidHttpHandler(BaseHTTPRequestHandler):
    """Android HTTP请求处理器"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class AndroidPlatform:
    """Android平台实现"""
    
    def __init__(self, chat_bot):
        self.chat_bot = chat_bot
        self.port = 8080
        self.http_server = None
    
    def start_http_server(self):
        """启动HTTP服务器"""
        def handler_factory(*args, **kwargs):
            return AndroidHttpHandler(*args, chat_bot=self.chat_bot, **kwargs)
        
        self.http_server = HTTPServer(('localhost', self.port), handler_factory)
        print(f"Android HTTP服务器已启动在端口 {self.port}")
        self.http_server.serve_forever()
    
    def start(self):
        """启动Android应用"""
        try:
            # 注册API
            from api_registry import register_chat_apis
            register_chat_apis(self.chat_bot)
            
            # 加载自动保存
            self.chat_bot.load_auto_save()
            
            print("正在启动Android应用...")
            
            # 检测运行环境
            if self.is_android_environment():
                self.start_android_app()
            else:
                self.start_pc_fallback()
                
        except Exception as e:
            print(f"启动Android应用失败: {str(e)}")
            print("回退到PC模式")
            self.start_pc_fallback()
    
    def is_android_environment(self):
        """检测是否为Android环境"""
        try:
            import kivy
            from kivy.utils import platform
            return platform == 'android'
        except ImportError:
            return False
    
    def start_android_app(self):
        """启动Android应用（在Android设备上）"""
        from kivy.app import App
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.webview import WebView
        
        # 启动HTTP服务器线程
        server_thread = Thread(target=self.start_http_server, daemon=True)
        server_thread.start()
        
        class ChatApp(App):
            def build(self):
                self.title = "增强版聊天机器人"
                layout = BoxLayout(orientation='vertical')
                
                # 创建WebView
                webview = WebView()
                webview.url = f'http://localhost:{self.port}'
                layout.add_widget(webview)
                
                return layout
        
        ChatApp().run()
    
    def start_pc_fallback(self):
        """PC环境回退方案"""
        print("启动PC回退模式...")
        
        # 启动HTTP服务器
        server_thread = Thread(target=self.start_http_server, daemon=True)
        server_thread.start()
        
        # 在PC上，我们直接使用浏览器访问
        import webbrowser
        
        time.sleep(2)  # 等待服务器启动
        webbrowser.open(f'http://localhost:{self.port}')
        
        print(f"请在浏览器中访问: http://localhost:{self.port}")
        print("按Ctrl+C退出")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n应用已退出")
#!/usr/bin/env python3
"""
业务无关的iOS平台实现
使用基础平台类，完全与业务逻辑解耦
"""
import os
import sys
from http.server import HTTPServer
from threading import Thread
import time

# 导入基础平台类
from base_platform import BaseHTTPRequestHandler


class IOSHttpHandler(BaseHTTPRequestHandler):
    """iOS HTTP请求处理器"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class IOSPlatform:
    """iOS平台实现"""
    
    def __init__(self, chat_bot):
        self.chat_bot = chat_bot
        self.port = 8080
        self.http_server = None
    
    def start_http_server(self):
        """启动HTTP服务器"""
        def handler_factory(*args, **kwargs):
            return IOSHttpHandler(*args, chat_bot=self.chat_bot, **kwargs)
        
        # iOS上使用0.0.0.0以允许外部访问
        self.http_server = HTTPServer(('0.0.0.0', self.port), handler_factory)
        print(f"iOS HTTP服务器已启动在端口 {self.port}")
        self.http_server.serve_forever()
    
    def start(self):
        """启动iOS应用"""
        try:
            # 注册API
            from api_registry import register_chat_apis
            register_chat_apis(self.chat_bot)
            
            # 加载自动保存
            self.chat_bot.load_auto_save()
            
            print("正在启动iOS应用...")
            
            # 检测运行环境
            if self.is_ios_environment():
                self.start_ios_app()
            else:
                self.start_pc_fallback()
                
        except Exception as e:
            print(f"启动iOS应用失败: {str(e)}")
            print("回退到PC模式")
            self.start_pc_fallback()
    
    def is_ios_environment(self):
        """检测是否为iOS环境"""
        try:
            # 尝试导入iOS特定的模块
            import pyto_ui
            return True
        except ImportError:
            # 检查是否是Pythonista环境
            try:
                import console
                return True
            except ImportError:
                # 检查是否是其他iOS Python环境
                if 'ios' in sys.platform or 'darwin' in sys.platform:
                    return True
                return False
    
    def start_ios_app(self):
        """启动iOS应用（在iOS设备上）"""
        try:
            # 尝试使用Pyto UI
            import pyto_ui
            self.start_pyto_app()
        except ImportError:
            try:
                # 尝试使用Pythonista
                import console
                self.start_pythonista_app()
            except ImportError:
                # 其他iOS环境，使用简单的Web服务器
                self.start_ios_web_server()
    
    def start_pyto_app(self):
        """使用Pyto UI框架启动iOS应用"""
        import pyto_ui
        
        # 启动HTTP服务器线程
        server_thread = Thread(target=self.start_http_server, daemon=True)
        server_thread.start()
        
        class ChatViewController(pyto_ui.ViewController):
            def view_did_appear(self):
                # 创建WebView
                web_view = pyto_ui.WebView()
                web_view.frame = self.view.frame
                web_view.load_url(f'http://localhost:{self.port}')
                self.view.add_subview(web_view)
        
        # 创建并显示视图控制器
        vc = ChatViewController()
        pyto_ui.show_view_controller(vc)
    
    def start_pythonista_app(self):
        """使用Pythonista启动iOS应用"""
        import ui
        
        # 启动HTTP服务器线程
        server_thread = Thread(target=self.start_http_server, daemon=True)
        server_thread.start()
        
        class ChatWebView(ui.View):
            def __init__(self, port, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.port = port
                self.name = "增强版聊天机器人"
                self.background_color = 'white'
            
            def did_load(self):
                # 创建WebView
                web_view = ui.WebView()
                web_view.flex = 'WH'
                web_view.load_url(f'http://localhost:{self.port}')
                self.add_subview(web_view)
        
        # 创建并显示应用
        app_view = ChatWebView(self.port)
        app_view.present(style='fullscreen', hide_title_bar=False)
    
    def start_ios_web_server(self):
        """其他iOS环境的Web服务器方案"""
        # 启动HTTP服务器
        server_thread = Thread(target=self.start_http_server, daemon=True)
        server_thread.start()
        
        print(f"iOS Web服务器已启动")
        print(f"请在Safari浏览器中访问: http://localhost:{self.port}")
        print("应用正在运行...")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n应用已退出")
    
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
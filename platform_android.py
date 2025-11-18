#!/usr/bin/env python3
"""
业务无关的Android平台实现
使用API注册中心处理所有请求，完全与业务逻辑解耦
"""
import os
import json
from http.server import HTTPServer, SimpleHTTPRequestHandler
from threading import Thread
import time

# 导入API注册中心
from api_registry import api_registry


class AndroidHttpHandler(SimpleHTTPRequestHandler):
    """Android HTTP请求处理器"""
    
    def __init__(self, *args, chat_bot=None, **kwargs):
        self.chat_bot = chat_bot
        self.api_registry = api_registry
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """处理GET请求"""
        parsed_path = self.path
        
        # API路由
        if parsed_path.startswith('/api/'):
            self.handle_api_request(parsed_path, 'GET')
            return
        
        # 静态文件路由
        if parsed_path == '/':
            self.path = '/index.html'
        
        # 处理资源文件
        if parsed_path.startswith('/resource/'):
            resource_path = parsed_path[1:]  # 去掉开头的/
            if os.path.exists(resource_path):
                self.serve_file(resource_path)
                return
        
        # 默认静态文件服务
        try:
            return super().do_GET()
        except:
            self.send_error(404, "文件不存在")
    
    def do_POST(self):
        """处理POST请求"""
        parsed_path = self.path
        
        if parsed_path.startswith('/api/'):
            self.handle_api_request(parsed_path, 'POST')
        else:
            self.send_error(404, "接口不存在")
    
    def handle_api_request(self, path: str, method: str):
        """处理API请求"""
        # 提取endpoint
        endpoint = path[len('/api/'):]
        
        try:
            # 解析请求数据
            data = None
            if method == 'POST':
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length > 0:
                    post_data = self.rfile.read(content_length).decode('utf-8')
                    
                    # 尝试解析为JSON
                    try:
                        data = json.loads(post_data)
                    except json.JSONDecodeError:
                        # 简化处理表单数据
                        from urllib.parse import parse_qs
                        parsed_data = parse_qs(post_data)
                        simplified_data = {}
                        for key, value in parsed_data.items():
                            simplified_data[key] = value[0] if value else ''
                        data = simplified_data
            
            # 特殊处理流式聊天
            if endpoint == 'chat/stream' and method == 'POST':
                self.handle_stream_chat(data)
                return
            
            # 调用API处理器
            response = self.api_registry.handle_request(endpoint, method, data)
            
            # 发送响应
            self.send_json_response(response)
            
        except Exception as e:
            self.send_error(500, f"服务器错误: {str(e)}")
    
    def handle_stream_chat(self, data):
        """处理流式聊天请求"""
        if not data or 'message' not in data:
            self.send_json_response({"status": "error", "message": "缺少消息内容"})
            return
        
        user_message = data['message']
        
        if not self.chat_bot:
            self.send_json_response({"status": "error", "message": "聊天机器人未初始化"})
            return
        
        # 设置流式响应头
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        
        # 流式响应（简化版）
        try:
            for chunk in self.chat_bot.stream_chat(user_message):
                if chunk:
                    # 直接发送数据
                    self.wfile.write(chunk.encode('utf-8'))
                    self.wfile.flush()
                
        except Exception as e:
            error_msg = f"流式响应错误: {str(e)}"
            self.wfile.write(error_msg.encode('utf-8'))
        
    def send_json_response(self, data):
        """发送JSON响应"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def serve_file(self, filepath):
        """服务静态文件"""
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            
            # 设置MIME类型
            if filepath.endswith('.css'):
                content_type = 'text/css'
            elif filepath.endswith('.js'):
                content_type = 'application/javascript'
            elif filepath.endswith('.png'):
                content_type = 'image/png'
            elif filepath.endswith('.jpg') or filepath.endswith('.jpeg'):
                content_type = 'image/jpeg'
            elif filepath.endswith('.gif'):
                content_type = 'image/gif'
            else:
                content_type = 'application/octet-stream'
            
            self.send_response(200)
            self.send_header('Content-type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(404, f"文件读取失败: {str(e)}")


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
            print("注意: 完整的Android功能需要在Android设备上运行")
            print("在PC上，我们将启动一个简化版的Web界面")
            
            # 在PC环境下，我们启动一个简化的Web服务器
            # 在真正的Android设备上，应该使用Kivy WebView
            if self.is_pc_environment():
                self.start_pc_fallback()
            else:
                self.start_kivy_app()
                
        except Exception as e:
            print(f"启动Android应用失败: {str(e)}")
            print("回退到PC模式")
            self.start_pc_fallback()
    
    def is_pc_environment(self):
        """检测是否为PC环境"""
        try:
            import kivy
            return False
        except ImportError:
            return True
    
    def start_kivy_app(self):
        """启动Kivy应用（在Android设备上）"""
        from kivy.app import App
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.webview import WebView
        from kivy.clock import Clock
        
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
        import time
        
        time.sleep(2)  # 等待服务器启动
        webbrowser.open(f'http://localhost:{self.port}')
        
        print(f"请在浏览器中访问: http://localhost:{self.port}")
        print("按Ctrl+C退出")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n应用已退出")
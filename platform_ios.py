#!/usr/bin/env python3
"""
业务无关的iOS平台实现
使用API注册中心处理所有请求，完全与业务逻辑解耦
"""
import os
import json
from http.server import HTTPServer, SimpleHTTPRequestHandler
from threading import Thread
import time
from urllib.parse import unquote

# 导入API注册中心
from api_registry import api_registry


class IOSHttpHandler(SimpleHTTPRequestHandler):
    """iOS HTTP请求处理器"""
    
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
        
        # 处理资源文件 - 修复中文文件名问题
        if parsed_path.startswith('/resource/'):
            # 对URL进行解码以处理中文文件名
            decoded_path = unquote(parsed_path)
            resource_path = decoded_path[1:]  # 去掉开头的/
            
            if os.path.exists(resource_path):
                self.serve_file(resource_path)
                return
        
        # 默认静态文件服务
        try:
            return super().do_GET()
        except:
            self.send_error(404, "File not found")
    
    def do_POST(self):
        """处理POST请求"""
        parsed_path = self.path
        
        if parsed_path.startswith('/api/'):
            self.handle_api_request(parsed_path, 'POST')
        else:
            self.send_error(404, "API not found")
    
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
            self.send_error(500, f"Server error: {str(e)}")
    
    def handle_stream_chat(self, data):
        """处理流式聊天请求"""
        if not data or 'message' not in data:
            self.send_json_response({"status": "error", "message": "Missing message content"})
            return
        
        user_message = data['message']
        
        if not self.chat_bot:
            self.send_json_response({"status": "error", "message": "Chat bot not initialized"})
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
                    time.sleep(0.01)  # 少量延迟以模拟流式
            
        except Exception as e:
            error_msg = f"Stream response error: {str(e)}"
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
            self.send_error(404, f"File read error: {str(e)}")
    
    # 重写错误处理方法
    def send_error(self, code, message=None):
        """发送错误响应"""
        try:
            if message is None:
                message = self.responses[code][0]
            
            content = self.error_message_format % {
                'code': code,
                'message': message
            }
            
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header('Content-Length', str(len(content.encode('utf-8'))))
            self.end_headers()
            
            if self.command != 'HEAD' and code >= 200 and code not in (204, 304):
                self.wfile.write(content.encode('utf-8'))
                
        except Exception as e:
            super().send_error(code, "Error")


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
            print("注意: 完整的iOS功能需要在iOS设备上运行")
            print("在PC上，我们将启动一个简化版的Web界面")
            
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
                import sys
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
        
        class ChatViewController(pyto_ui.ViewController):
            def __init__(self, platform):
                super().__init__()
                self.platform = platform
            
            def view_did_appear(self):
                # 启动HTTP服务器线程
                server_thread = Thread(target=self.platform.start_http_server, daemon=True)
                server_thread.start()
                
                # 创建WebView
                web_view = pyto_ui.WebView()
                web_view.frame = self.view.frame
                web_view.load_url(f'http://localhost:{self.platform.port}')
                self.view.add_subview(web_view)
        
        # 创建并显示视图控制器
        vc = ChatViewController(self)
        pyto_ui.show_view_controller(vc)
    
    def start_pythonista_app(self):
        """使用Pythonista启动iOS应用"""
        import console
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
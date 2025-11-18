#!/usr/bin/env python3
"""
业务无关的Web平台实现
使用API注册中心处理所有请求，完全与业务逻辑解耦
"""
import os
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote
import json
import threading

# 导入API注册中心
from api_registry import api_registry


class WebChatHandler(SimpleHTTPRequestHandler):
    """Web聊天请求处理器"""
    
    def __init__(self, *args, **kwargs):
        self.api_registry = api_registry
        # 设置静态文件目录为frontend
        self.directory = 'frontend'
        super().__init__(*args, directory=self.directory, **kwargs)
    
    def do_GET(self):
        """处理GET请求"""
        parsed_path = urlparse(self.path)
        
        # API路由
        if parsed_path.path.startswith('/api/'):
            self.handle_api_request(parsed_path.path, 'GET')
            return
        
        # 静态文件路由 - 特殊处理根路径
        if parsed_path.path == '/':
            self.path = '/index.html'
        
        # 处理资源文件 - 修复中文文件名问题
        if parsed_path.path.startswith('/resource/'):
            # 对URL进行解码以处理中文文件名
            decoded_path = unquote(parsed_path.path)
            resource_path = decoded_path[1:]  # 去掉开头的/
            
            if os.path.exists(resource_path):
                self.serve_file(resource_path)
                return
            else:
                # 使用英文错误信息避免编码问题
                self.send_error(404, "Resource file not found")
                return
        
        # 默认静态文件服务
        try:
            return super().do_GET()
        except Exception as e:
            # 使用英文错误信息
            self.send_error(404, f"File not found: {str(e)}")
    
    def do_POST(self):
        """处理POST请求"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path.startswith('/api/'):
            self.handle_api_request(parsed_path.path, 'POST')
        else:
            # 使用英文错误信息
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
                        # 回退到表单数据解析
                        data = parse_qs(post_data)
                        # 简化数据格式
                        simplified_data = {}
                        for key, value in data.items():
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
            # 使用英文错误信息
            self.send_error(500, f"Server error: {str(e)}")
    
    def handle_stream_chat(self, data):
        """处理流式聊天请求"""
        from chat_core import ChatBot
        
        if not data or 'message' not in data:
            self.send_json_response({"status": "error", "message": "Missing message content"})
            return
        
        user_message = data['message']
        chat_bot = None
        
        # 获取当前的chat_bot实例
        for route_key in self.api_registry.routes:
            handler = self.api_registry.routes[route_key]
            # 通过闭包获取chat_bot引用
            if hasattr(handler, '__closure__') and handler.__closure__:
                for cell in handler.__closure__:
                    if isinstance(cell.cell_contents, ChatBot):
                        chat_bot = cell.cell_contents
                        break
            if chat_bot:
                break
        
        if not chat_bot:
            self.send_json_response({"status": "error", "message": "Chat bot not initialized"})
            return
        
        # 设置流式响应头 - 使用普通文本而不是chunked encoding
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        
        # 流式响应 - 直接发送数据，不使用chunked encoding
        try:
            for chunk in chat_bot.stream_chat(user_message):
                if chunk:
                    # 直接发送数据，不添加chunked编码
                    self.wfile.write(chunk.encode('utf-8'))
                    self.wfile.flush()
                    
        except Exception as e:
            # 发送错误信息
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
            # 使用英文错误信息
            self.send_error(404, f"File read error: {str(e)}")
    
    # 重写错误处理方法以支持UTF-8
    def send_error(self, code, message=None):
        """发送错误响应，支持UTF-8编码"""
        try:
            # 使用UTF-8编码消息
            if message is None:
                message = self.responses[code][0]
            
            # 构建错误页面
            content = self.error_message_format % {
                'code': code,
                'message': message
            }
            
            # 发送响应
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header('Content-Length', str(len(content.encode('utf-8'))))
            self.end_headers()
            
            # 写入内容
            if self.command != 'HEAD' and code >= 200 and code not in (204, 304):
                self.wfile.write(content.encode('utf-8'))
                
        except Exception as e:
            # 如果出错，回退到父类方法
            super().send_error(code, "Error")


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
            return WebChatHandler(*args, **kwargs)
        
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
        threading.Timer(1, open_browser).start()
        
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n服务器已停止")
            server.shutdown()
#!/usr/bin/env python3
"""
基础平台类
包含所有平台共享的逻辑
"""
import os
import json
import tempfile
from http.server import SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote
import re

# 导入API注册中心
from api_registry import api_registry


class BaseHTTPRequestHandler(SimpleHTTPRequestHandler):
    """基础HTTP请求处理器"""
    
    def __init__(self, *args, chat_bot=None, **kwargs):
        self.chat_bot = chat_bot
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
                self.send_error(404, "Resource file not found")
                return
        
        # 默认静态文件服务
        try:
            return super().do_GET()
        except Exception as e:
            self.send_error(404, f"File not found: {str(e)}")
    
    def do_POST(self):
        """处理POST请求"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path.startswith('/api/'):
            # 检查是否为文件上传请求
            content_type = self.headers.get('Content-Type', '')
            if 'multipart/form-data' in content_type and parsed_path.path == '/api/cg/copy':
                self.handle_file_upload()
                return
            else:
                self.handle_api_request(parsed_path.path, 'POST')
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
            self.send_error(500, f"Server error: {str(e)}")
    
    def handle_stream_chat(self, data):
        """处理流式聊天请求"""
        from chat_core import ChatBot
        
        if not data or 'message' not in data:
            self.send_json_response({"status": "error", "message": "Missing message content"})
            return
        
        user_message = data['message']
        chat_bot = self._get_chat_bot_instance()
        
        if not chat_bot:
            self.send_json_response({"status": "error", "message": "Chat bot not initialized"})
            return
        
        # 设置流式响应头
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        
        # 流式响应
        try:
            for chunk in chat_bot.stream_chat(user_message):
                if chunk:
                    self.wfile.write(chunk.encode('utf-8'))
                    self.wfile.flush()
                    
        except Exception as e:
            error_msg = f"Stream response error: {str(e)}"
            self.wfile.write(error_msg.encode('utf-8'))
    
    def handle_file_upload(self):
        """处理文件上传 - 使用标准库替代cgi"""
        try:
            content_type = self.headers.get('Content-Type', '')
            content_length = int(self.headers.get('Content-Length', 0))
            
            # 解析multipart/form-data的boundary
            boundary_match = re.search(r'boundary=(.*)$', content_type)
            if not boundary_match:
                self.send_json_response({"status": "error", "message": "无效的Content-Type"})
                return
            
            boundary = boundary_match.group(1).encode('utf-8')
            
            # 读取整个请求体
            post_data = self.rfile.read(content_length)
            
            # 解析multipart数据
            parts = self._parse_multipart_data(post_data, boundary)
            
            if not parts or 'file' not in parts:
                self.send_json_response({"status": "error", "message": "没有接收到文件"})
                return
            
            file_data = parts['file']
            filename = file_data.get('filename')
            file_content = file_data.get('content')
            
            if not filename or not file_content:
                self.send_json_response({"status": "error", "message": "文件名或文件内容为空"})
                return
            
            # 使用临时文件保存上传内容
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_path = temp_file.name
                temp_file.write(file_content)
            
            try:
                # 通过API路由处理文件复制
                response = self.api_registry.handle_request('cg/copy', 'POST', {
                    'temp_path': temp_path,
                    'filename': filename
                })
                
                self.send_json_response(response)
                
            finally:
                # 清理临时文件
                try:
                    os.unlink(temp_path)
                except:
                    pass
                
        except Exception as e:
            self.send_json_response({"status": "error", "message": f"文件上传失败: {str(e)}"})
    
    def _parse_multipart_data(self, data: bytes, boundary: bytes):
        """解析multipart/form-data数据"""
        parts = {}
        
        # 添加前置boundary
        full_boundary = b'--' + boundary
        
        # 分割数据
        sections = data.split(full_boundary)
        
        for section in sections:
            if not section.strip() or section == b'--\r\n':
                continue
                
            # 解析section头部和内容
            header_end = section.find(b'\r\n\r\n')
            if header_end == -1:
                continue
                
            headers = section[:header_end].decode('utf-8', errors='ignore')
            content = section[header_end + 4:].rstrip(b'\r\n')
            
            # 解析Content-Disposition
            disposition_match = re.search(r'Content-Disposition:\s*form-data;\s*name="([^"]+)";\s*filename="([^"]+)"', headers, re.IGNORECASE)
            if disposition_match:
                field_name = disposition_match.group(1)
                filename = disposition_match.group(2)
                
                parts[field_name] = {
                    'filename': filename,
                    'content': content
                }
            else:
                # 处理普通字段
                name_match = re.search(r'Content-Disposition:\s*form-data;\s*name="([^"]+)"', headers, re.IGNORECASE)
                if name_match:
                    field_name = name_match.group(1)
                    parts[field_name] = {
                        'filename': None,
                        'content': content.decode('utf-8', errors='ignore')
                    }
        
        return parts
    
    def _get_chat_bot_instance(self):
        """获取chat_bot实例"""
        # 如果已经设置了chat_bot实例，直接返回
        if self.chat_bot:
            return self.chat_bot
        
        # 否则从API路由中查找
        from chat_core import ChatBot
        for route_key in self.api_registry.routes:
            handler = self.api_registry.routes[route_key]
            if hasattr(handler, '__closure__') and handler.__closure__:
                for cell in handler.__closure__:
                    if isinstance(cell.cell_contents, ChatBot):
                        return cell.cell_contents
        return None
    
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
    
    def send_error(self, code, message=None):
        """发送错误响应，支持UTF-8编码"""
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
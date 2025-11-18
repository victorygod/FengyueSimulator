#!/usr/bin/env python3
"""
API路由注册中心
统一管理所有API端点，实现业务逻辑与平台解耦
"""
import os
import json
from typing import Dict, Any, Callable, Optional, Tuple

# 导入存储管理器
from storage_manager import storage_manager


class APIRegistry:
    """API注册中心"""
    
    def __init__(self):
        self.routes = {}
        self.static_routes = {}
    
    def register_route(self, endpoint: str, method: str, handler: Callable):
        """注册API路由"""
        key = f"{method.upper()}_{endpoint}"
        self.routes[key] = handler
    
    def register_static_route(self, route: str, directory: str):
        """注册静态文件路由"""
        self.static_routes[route] = directory
    
    def handle_request(self, endpoint: str, method: str, data: Any = None) -> Dict[str, Any]:
        """处理API请求"""
        key = f"{method.upper()}_{endpoint}"
        
        if key in self.routes:
            try:
                return self.routes[key](data)
            except Exception as e:
                return {"status": "error", "message": f"处理请求时出错: {str(e)}"}
        else:
            return {"status": "error", "message": f"未找到接口: {endpoint}"}
    
    def get_static_route(self, path: str) -> Tuple[Optional[str], str]:
        """获取静态文件路由"""
        # 精确匹配
        if path in self.static_routes:
            return self.static_routes[path], ""
        
        # 前缀匹配
        for route, directory in self.static_routes.items():
            if path.startswith(route):
                relative_path = path[len(route):].lstrip('/')
                return directory, relative_path
        
        return None, ""


# 全局API注册中心实例
api_registry = APIRegistry()


def register_chat_apis(chat_bot):
    """注册聊天相关API"""
    
    # 发送消息
    def send_message(data):
        if not data or 'message' not in data:
            return {"status": "error", "message": "缺少消息内容"}
        
        # 这里返回流式处理标识，实际流式处理在前端实现
        return {"status": "success", "message": "消息已发送"}
    
    # 获取聊天历史
    def get_chat_history(data):
        return {
            "status": "success", 
            "chat_history": chat_bot.chat_history,
            "current_prompt": chat_bot.current_prompt
        }
    
    # 清空聊天
    def clear_chat(data):
        chat_bot.clear_chat()
        return {"status": "success", "message": "聊天已清空"}
    
    # 获取API密钥状态
    def get_api_key_status(data):
        return {
            "status": "success", 
            "has_api_key": bool(chat_bot.api_key),
            "api_key_set": chat_bot.api_key != ""
        }
    
    # 设置API密钥
    def set_api_key(data):
        if not data or 'api_key' not in data:
            return {"status": "error", "message": "缺少API密钥"}
        
        chat_bot.api_key = data['api_key']
        chat_bot.save_config()
        return {"status": "success", "message": "API密钥已保存"}
    
    # 获取提示词列表
    def get_prompts(data):
        prompts = chat_bot.get_available_prompts()
        current_prompt = chat_bot.current_prompt
        current_config = chat_bot.prompt_config
        
        return {
            "status": "success",
            "prompts": prompts,
            "current_prompt": current_prompt,
            "current_config": current_config
        }
    
    # 设置当前提示词
    def set_prompt(data):
        if not data or 'prompt_name' not in data:
            return {"status": "error", "message": "缺少提示词名称"}
        
        success = chat_bot.load_prompt(data['prompt_name'])
        if success:
            return {"status": "success", "message": f"已切换到提示词: {data['prompt_name']}"}
        else:
            return {"status": "error", "message": f"切换提示词失败: {data['prompt_name']}"}
    
    # 保存提示词
    def save_prompt(data):
        if not data or 'prompt_name' not in data or 'prompt_data' not in data:
            return {"status": "error", "message": "缺少提示词数据"}
        
        success = storage_manager.save_prompt(data['prompt_name'], data['prompt_data'])
        if success:
            return {"status": "success", "message": f"提示词已保存: {data['prompt_name']}"}
        else:
            return {"status": "error", "message": f"保存提示词失败: {data['prompt_name']}"}
    
    # 删除提示词
    def delete_prompt(data):
        if not data or 'prompt_name' not in data:
            return {"status": "error", "message": "缺少提示词名称"}
        
        success = storage_manager.delete_prompt(data['prompt_name'])
        if success:
            return {"status": "success", "message": f"提示词已删除: {data['prompt_name']}"}
        else:
            return {"status": "error", "message": f"删除提示词失败: {data['prompt_name']}"}
    
    # 重命名提示词
    def rename_prompt(data):
        if not data or 'old_name' not in data or 'new_name' not in data:
            return {"status": "error", "message": "缺少重命名参数"}
        
        success = storage_manager.rename_prompt(data['old_name'], data['new_name'])
        if success:
            return {"status": "success", "message": f"提示词已重命名: {data['old_name']} -> {data['new_name']}"}
        else:
            return {"status": "error", "message": f"重命名提示词失败"}
    
    # 获取存档列表
    def get_saves(data):
        saves = storage_manager.get_saved_chats()
        return {"status": "success", "saves": saves}
    
    # 保存聊天
    def save_chat(data):
        if not data or 'filename' not in data:
            return {"status": "error", "message": "缺少文件名"}
        
        # 检查文件是否已存在
        saves = storage_manager.get_saved_chats()
        if data['filename'] in saves:
            return {"status": "exists", "message": f"存档已存在: {data['filename']}"}
        
        chat_data = {
            "chat_history": chat_bot.chat_history,
            "prompt_name": chat_bot.current_prompt
        }
        
        success = storage_manager.save_chat(data['filename'], chat_data)
        if success:
            return {"status": "success", "message": f"聊天已保存: {data['filename']}"}
        else:
            return {"status": "error", "message": f"保存聊天失败: {data['filename']}"}
    
    # 强制保存聊天（覆盖）
    def force_save_chat(data):
        if not data or 'filename' not in data:
            return {"status": "error", "message": "缺少文件名"}
        
        chat_data = {
            "chat_history": chat_bot.chat_history,
            "prompt_name": chat_bot.current_prompt
        }
        
        success = storage_manager.save_chat(data['filename'], chat_data)
        if success:
            return {"status": "success", "message": f"聊天已保存: {data['filename']}"}
        else:
            return {"status": "error", "message": f"保存聊天失败: {data['filename']}"}
    
    # 加载聊天
    def load_chat(data):
        if not data or 'filename' not in data:
            return {"status": "error", "message": "缺少文件名"}
        
        chat_data = storage_manager.load_chat(data['filename'])
        if chat_data:
            chat_bot.chat_history = chat_data.get('chat_history', [])
            chat_bot.load_prompt(chat_data.get('prompt_name', 'default'))
            return {"status": "success", "message": f"聊天已加载: {data['filename']}"}
        else:
            return {"status": "error", "message": f"加载聊天失败: {data['filename']}"}
    
    # 删除聊天
    def delete_chat(data):
        if not data or 'filename' not in data:
            return {"status": "error", "message": "缺少文件名"}
        
        success = storage_manager.delete_chat(data['filename'])
        if success:
            return {"status": "success", "message": f"聊天已删除: {data['filename']}"}
        else:
            return {"status": "error", "message": f"删除聊天失败: {data['filename']}"}
    
    # 重命名聊天
    def rename_chat(data):
        if not data or 'old_name' not in data or 'new_name' not in data:
            return {"status": "error", "message": "缺少重命名参数"}
        
        success = storage_manager.rename_chat(data['old_name'], data['new_name'])
        if success:
            return {"status": "success", "message": f"聊天已重命名: {data['old_name']} -> {data['new_name']}"}
        else:
            return {"status": "error", "message": f"重命名聊天失败"}
    
    # 获取资源文件
    def get_resources(data):
        files = storage_manager.get_resource_files()
        return {"status": "success", "files": files}
    
    # 删除资源文件
    def delete_resource(data):
        if not data or 'filename' not in data:
            return {"status": "error", "message": "缺少文件名"}
        
        success = storage_manager.delete_resource(data['filename'])
        if success:
            return {"status": "success", "message": f"资源文件已删除: {data['filename']}"}
        else:
            return {"status": "error", "message": f"删除资源文件失败: {data['filename']}"}
    
    # 重命名资源文件
    def rename_resource(data):
        if not data or 'old_name' not in data or 'new_name' not in data:
            return {"status": "error", "message": "缺少重命名参数"}
        
        success = storage_manager.rename_resource(data['old_name'], data['new_name'])
        if success:
            return {"status": "success", "message": f"资源文件已重命名: {data['old_name']} -> {data['new_name']}"}
        else:
            return {"status": "error", "message": f"重命名资源文件失败"}
    
    # 流式聊天（特殊处理）
    def stream_chat(data):
        if not data or 'message' not in data:
            return {"status": "error", "message": "缺少消息内容"}
        
        # 这个API由平台特殊处理，不通过标准路由
        return {"status": "stream", "message": data['message']}
    
    # 注册所有API路由
    api_registry.register_route('chat', 'POST', send_message)
    api_registry.register_route('chat/history', 'GET', get_chat_history)
    api_registry.register_route('chat/clear', 'POST', clear_chat)
    api_registry.register_route('api_key/status', 'GET', get_api_key_status)
    api_registry.register_route('api_key/set', 'POST', set_api_key)
    api_registry.register_route('prompts', 'GET', get_prompts)
    api_registry.register_route('prompt/set', 'POST', set_prompt)
    api_registry.register_route('prompt/save', 'POST', save_prompt)
    api_registry.register_route('prompt/delete', 'POST', delete_prompt)
    api_registry.register_route('prompt/rename', 'POST', rename_prompt)
    api_registry.register_route('saves', 'GET', get_saves)
    api_registry.register_route('save', 'POST', save_chat)
    api_registry.register_route('save/force', 'POST', force_save_chat)
    api_registry.register_route('save/load', 'POST', load_chat)
    api_registry.register_route('save/delete', 'POST', delete_chat)
    api_registry.register_route('save/rename', 'POST', rename_chat)
    api_registry.register_route('resources', 'GET', get_resources)
    api_registry.register_route('resource/delete', 'POST', delete_resource)
    api_registry.register_route('resource/rename', 'POST', rename_resource)
    api_registry.register_route('chat/stream', 'POST', stream_chat)
    
    # 注册静态文件路由
    api_registry.register_static_route('/', 'frontend')
    api_registry.register_static_route('/resource', 'resource')
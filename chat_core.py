#!/usr/bin/env python3
"""
核心聊天逻辑
只处理与DeepSeek API的交互和聊天历史管理
"""
import json
import os
import requests
import re
from typing import List, Dict, Any, Generator

# 导入存储管理器
from storage_manager import storage_manager


class ChatBot:
    """聊天机器人核心类"""
    
    def __init__(self):
        self.chat_history = []
        self.current_prompt = "default_prompt.json"  # 默认提示词文件
        self.api_key = ""
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        self.memory_rounds = 6  # 默认记忆轮数
        
        # 加载配置和自动保存
        self.load_config()
        self.load_auto_save()
    
    def load_config(self):
        """加载API密钥配置"""
        config = storage_manager.load_config()
        self.api_key = config.get('api_key', '')
    
    def save_config(self):
        """保存API密钥配置"""
        storage_manager.save_config({'api_key': self.api_key})
    
    def load_prompt(self, prompt_name: str) -> bool:
        """加载提示词配置"""
        try:
            prompt_config = storage_manager.load_prompt(prompt_name)
            if prompt_config:
                self.prompt_config = prompt_config
                self.current_prompt = prompt_name
                return True
            else:
                # 如果加载失败，尝试加载默认提示词
                if prompt_name != "default_prompt.json":
                    return self.load_prompt("default_prompt.json")
                return False
        except Exception as e:
            print(f"加载提示词失败: {str(e)}")
            return False
    
    def get_available_prompts(self) -> List[str]:
        """获取所有可用的提示词"""
        return storage_manager.get_available_prompts()
    
    def build_messages(self, user_input: str) -> List[Dict[str, str]]:
        """构建消息列表，考虑记忆轮数"""
        messages = []
        
        # 添加系统提示词
        pre_prompt = self.prompt_config.get('pre_prompt', '')
        if pre_prompt:
            messages.append({
                "role": "system",
                "content": pre_prompt
            })
        
        # 添加历史对话（考虑记忆轮数）
        if self.memory_rounds > 0:
            max_messages = self.memory_rounds 
            recent_history = self.chat_history[-max_messages:] if max_messages > 0 else self.chat_history
        else:
            recent_history = []
        
        for msg in recent_history:
            messages.append(msg)
        
        # 添加当前用户输入
        pre_text = self.prompt_config.get('pre_text', '')
        post_text = self.prompt_config.get('post_text', '')
        user_message = f"{pre_text}{user_input}{post_text}"
        
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        return messages
    
    def stream_chat(self, user_input: str) -> Generator[str, None, None]:
        """流式聊天"""
        if not self.api_key:
            raise Exception("请先设置API密钥")
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            data = {
                "model": "deepseek-chat",
                "messages": self.build_messages(user_input),
                "stream": True
            }
            print(data)
            response = requests.post(
                self.base_url,
                headers=headers,
                json=data,
                stream=True,
                timeout=30
            )
            
            if response.status_code != 200:
                error_msg = f"API请求失败: {response.status_code} - {response.text}"
                raise Exception(error_msg)
            
            assistant_response = ""
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data_str = line[6:]
                        if data_str == '[DONE]':
                            break
                        try:
                            data_json = json.loads(data_str)
                            if 'choices' in data_json and len(data_json['choices']) > 0:
                                delta = data_json['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    content = delta['content']
                                    assistant_response += content
                                    yield content
                        except json.JSONDecodeError:
                            continue

            # 添加用户消息到历史
            self.chat_history.append({
                "role": "user",
                "content": user_input
            })
            
            # 添加助手回复到历史
            self.chat_history.append({
                "role": "assistant",
                "content": assistant_response
            })
            
            # 检测并处理图片
            image_files = self.detect_images_in_response(assistant_response)
            for image_file in image_files:
                yield f"\n[图片: {image_file}]"
            
            # 自动保存
            self.auto_save()
            
        except Exception as e:
            raise Exception(f"聊天失败: {str(e)}")
    
    def detect_images_in_response(self, response: str) -> List[str]:
        """检测回复中的图片文件名"""
        image_files = []
        cg_files = storage_manager.get_cg_files()
        
        for file in cg_files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                if file in response:
                    image_files.append(file)
        
        return image_files
    
    def auto_save(self):
        """自动保存聊天记录"""
        chat_data = {
            "chat_history": self.chat_history,
            "prompt_name": self.current_prompt,
            "memory_rounds": self.memory_rounds
        }
        storage_manager.auto_save(chat_data)
    
    def load_auto_save(self):
        """加载自动保存"""
        chat_data = storage_manager.load_auto_save()
        if chat_data:
            # 从autosave加载数据
            self.chat_history = chat_data.get('chat_history', [])
            self.memory_rounds = chat_data.get('memory_rounds', 6)
            self.load_prompt(chat_data.get('prompt_name', 'default_prompt.json'))
            return True
        else:
            # 如果autosave不存在，使用默认值
            self.load_prompt("default_prompt.json")
            self.memory_rounds = 6
            return False
    
    def clear_chat(self):
        """清空聊天记录"""
        self.chat_history = []
    
    def set_memory_rounds(self, rounds: int):
        """设置记忆轮数"""
        self.memory_rounds = max(0, rounds)
        # self.auto_save()
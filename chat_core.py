#!/usr/bin/env python3
"""
核心聊天逻辑
处理与DeepSeek API的交互和聊天历史管理
"""
import json
import os
import requests
import re
from typing import List, Dict, Any, Generator


class ChatBot:
    """聊天机器人核心类"""
    
    def __init__(self):
        self.chat_history = []
        self.current_prompt = "default"
        self.api_key = ""
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        
        # 加载配置
        self.load_config()
        self.load_prompt(self.current_prompt)
    
    def load_config(self):
        """加载API密钥配置"""
        config_path = os.path.join('config', 'api_key.json')
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.api_key = config.get('api_key', '')
        except Exception as e:
            print(f"加载配置失败: {str(e)}")
    
    def save_config(self):
        """保存API密钥配置"""
        config_path = os.path.join('config', 'api_key.json')
        try:
            os.makedirs('config', exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump({'api_key': self.api_key}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {str(e)}")
    
    def load_prompt(self, prompt_name: str) -> bool:
        """加载提示词配置"""
        prompt_path = os.path.join('prompts', f'{prompt_name}.json')
        try:
            if os.path.exists(prompt_path):
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    self.prompt_config = json.load(f)
                self.current_prompt = prompt_name
                return True
            else:
                # 加载默认提示词
                default_path = os.path.join('prompts', 'default_prompt.json')
                if os.path.exists(default_path):
                    with open(default_path, 'r', encoding='utf-8') as f:
                        self.prompt_config = json.load(f)
                else:
                    # 创建默认提示词
                    self.prompt_config = {
                        "pre_prompt": "你是一个有帮助的AI助手。",
                        "pre_text": "用户：",
                        "post_text": ""
                    }
                self.current_prompt = "default"
                return False
        except Exception as e:
            print(f"加载提示词失败: {str(e)}")
            return False
    
    def save_prompt(self, prompt_name: str, prompt_data: Dict[str, str]) -> bool:
        """保存提示词配置"""
        try:
            os.makedirs('prompts', exist_ok=True)
            prompt_path = os.path.join('prompts', f'{prompt_name}.json')
            with open(prompt_path, 'w', encoding='utf-8') as f:
                json.dump(prompt_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存提示词失败: {str(e)}")
            return False
    
    def delete_prompt(self, prompt_name: str) -> bool:
        """删除提示词配置"""
        try:
            prompt_path = os.path.join('prompts', f'{prompt_name}.json')
            if os.path.exists(prompt_path):
                os.remove(prompt_path)
                if self.current_prompt == prompt_name:
                    self.load_prompt("default")
                return True
            return False
        except Exception as e:
            print(f"删除提示词失败: {str(e)}")
            return False
    
    def get_available_prompts(self) -> List[str]:
        """获取所有可用的提示词"""
        try:
            prompts = []
            if os.path.exists('prompts'):
                for file in os.listdir('prompts'):
                    if file.endswith('.json'):
                        prompts.append(file[:-5])  # 去掉.json后缀
            return prompts
        except Exception as e:
            print(f"获取提示词列表失败: {str(e)}")
            return []
    
    def build_messages(self, user_input: str) -> List[Dict[str, str]]:
        """构建消息列表"""
        messages = []
        
        # 添加系统提示词
        if self.prompt_config.get('pre_prompt'):
            messages.append({
                "role": "system",
                "content": self.prompt_config['pre_prompt']
            })
        
        # 添加历史对话
        for msg in self.chat_history:
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
        if not self.api_key or len(self.api_key) == 0:
            yield "错误：请先设置API密钥"
            return
        
        # 添加用户消息到历史
        self.chat_history.append({
            "role": "user",
            "content": user_input
        })
        
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
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=data,
                stream=True,
                timeout=30
            )
            
            if response.status_code != 200:
                error_msg = f"API请求失败: {response.status_code} - {response.text}"
                yield error_msg
                return
            
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
            error_msg = f"聊天失败: {str(e)}"
            yield error_msg
    
    def detect_images_in_response(self, response: str) -> List[str]:
        """检测回复中的图片文件名"""
        image_files = []
        resource_dir = 'resource'
        
        if os.path.exists(resource_dir):
            for file in os.listdir(resource_dir):
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                    if file in response:
                        image_files.append(file)
        
        return image_files
    
    def save_chat(self, filename: str) -> bool:
        """保存聊天记录"""
        try:
            os.makedirs('save', exist_ok=True)
            save_path = os.path.join('save', f'{filename}.json')
            
            save_data = {
                "chat_history": self.chat_history,
                "prompt_name": self.current_prompt
            }
            
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存聊天记录失败: {str(e)}")
            return False
    
    def load_chat(self, filename: str) -> bool:
        """加载聊天记录"""
        try:
            save_path = os.path.join('save', f'{filename}.json')
            if os.path.exists(save_path):
                with open(save_path, 'r', encoding='utf-8') as f:
                    save_data = json.load(f)
                
                self.chat_history = save_data.get('chat_history', [])
                self.load_prompt(save_data.get('prompt_name', 'default'))
                return True
            return False
        except Exception as e:
            print(f"加载聊天记录失败: {str(e)}")
            return False
    
    def delete_chat(self, filename: str) -> bool:
        """删除聊天记录"""
        try:
            save_path = os.path.join('save', f'{filename}.json')
            if os.path.exists(save_path):
                os.remove(save_path)
                return True
            return False
        except Exception as e:
            print(f"删除聊天记录失败: {str(e)}")
            return False
    
    def get_saved_chats(self) -> List[str]:
        """获取所有保存的聊天记录"""
        try:
            chats = []
            if os.path.exists('save'):
                for file in os.listdir('save'):
                    if file.endswith('.json'):
                        chats.append(file[:-5])  # 去掉.json后缀
            return sorted(chats)
        except Exception as e:
            print(f"获取聊天记录列表失败: {str(e)}")
            return []
    
    def auto_save(self):
        """自动保存，保留最近5次存档"""
        try:
            # 删除最旧的存档
            old_save = os.path.join('save', 'autosave_5.json')
            if os.path.exists(old_save):
                os.remove(old_save)
            
            # 重命名现有存档
            for i in range(4, 0, -1):
                old_name = os.path.join('save', f'autosave_{i}.json')
                new_name = os.path.join('save', f'autosave_{i+1}.json')
                if os.path.exists(old_name):
                    os.rename(old_name, new_name)
            
            # 重命名当前autosave
            current_autosave = os.path.join('save', 'autosave.json')
            if os.path.exists(current_autosave):
                os.rename(current_autosave, os.path.join('save', 'autosave_1.json'))
            
            # 创建新的autosave
            self.save_chat('autosave')
            
        except Exception as e:
            print(f"自动保存失败: {str(e)}")
    
    def load_auto_save(self):
        """加载自动保存"""
        autosave_path = os.path.join('save', 'autosave.json')
        if os.path.exists(autosave_path):
            return self.load_chat('autosave')
        return False
    
    def clear_chat(self):
        """清空聊天记录"""
        self.chat_history = []
    
    def get_resource_files(self) -> List[str]:
        """获取资源文件列表"""
        try:
            files = []
            if os.path.exists('resource'):
                for file in os.listdir('resource'):
                    files.append(file)
            return sorted(files)
        except Exception as e:
            print(f"获取资源文件失败: {str(e)}")
            return []
    
    def copy_to_resource(self, source_path: str, filename: str) -> bool:
        """复制文件到资源目录"""
        try:
            import shutil
            os.makedirs('resource', exist_ok=True)
            dest_path = os.path.join('resource', filename)
            shutil.copy2(source_path, dest_path)
            return True
        except Exception as e:
            print(f"复制文件失败: {str(e)}")
            return False
    
    def delete_resource(self, filename: str) -> bool:
        """删除资源文件"""
        try:
            file_path = os.path.join('resource', filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            print(f"删除资源文件失败: {str(e)}")
            return False
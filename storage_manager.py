#!/usr/bin/env python3
"""
存储管理器
专门负责文件存储、自动保存、资源管理等功能
"""
import os
import json
import shutil
from typing import List, Dict, Any
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('StorageManager')


class StorageManager:
    """存储管理器类"""
    
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.ensure_directories()
    
    def ensure_directories(self):
        """确保必要的目录存在"""
        directories = ['config', 'prompts', 'save', 'resource', 'frontend']
        for dir_name in directories:
            dir_path = os.path.join(self.base_dir, dir_name)
            os.makedirs(dir_path, exist_ok=True)
    
    # ===== 配置管理 =====
    def load_config(self) -> Dict[str, Any]:
        """加载配置"""
        config_path = os.path.join(self.base_dir, 'config', 'api_key.json')
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"加载配置失败: {str(e)}")
            return {}
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """保存配置"""
        try:
            config_path = os.path.join(self.base_dir, 'config', 'api_key.json')
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {str(e)}")
            return False
    
    # ===== 提示词管理 =====
    def load_prompt(self, prompt_name: str) -> Dict[str, Any]:
        """加载提示词配置"""
        prompt_path = os.path.join(self.base_dir, 'prompts', f'{prompt_name}.json')
        try:
            if os.path.exists(prompt_path):
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.error(f"无法加载提示词文件: {str(prompt_path)}")
                return {}
        except Exception as e:
            logger.error(f"加载提示词失败: {str(e)}")
            return {}
    
    def save_prompt(self, prompt_name: str, prompt_data: Dict[str, Any]) -> bool:
        """保存提示词配置"""
        try:
            prompt_path = os.path.join(self.base_dir, 'prompts', f'{prompt_name}.json')
            with open(prompt_path, 'w', encoding='utf-8') as f:
                json.dump(prompt_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存提示词失败: {str(e)}")
            return False
    
    def delete_prompt(self, prompt_name: str) -> bool:
        """删除提示词配置"""
        try:
            prompt_path = os.path.join(self.base_dir, 'prompts', f'{prompt_name}.json')
            if os.path.exists(prompt_path):
                os.remove(prompt_path)
                return True
            return False
        except Exception as e:
            logger.error(f"删除提示词失败: {str(e)}")
            return False
    
    def rename_prompt(self, old_name: str, new_name: str) -> bool:
        """重命名提示词"""
        try:
            old_path = os.path.join(self.base_dir, 'prompts', f'{old_name}.json')
            new_path = os.path.join(self.base_dir, 'prompts', f'{new_name}.json')
            
            if os.path.exists(old_path) and not os.path.exists(new_path):
                os.rename(old_path, new_path)
                return True
            return False
        except Exception as e:
            logger.error(f"重命名提示词失败: {str(e)}")
            return False
    
    def get_available_prompts(self) -> List[str]:
        """获取所有可用的提示词"""
        try:
            prompts = []
            prompts_dir = os.path.join(self.base_dir, 'prompts')
            if os.path.exists(prompts_dir):
                for file in os.listdir(prompts_dir):
                    if file.endswith('.json'):
                        prompts.append(file[:-5])  # 去掉.json后缀
            return prompts
        except Exception as e:
            logger.error(f"获取提示词列表失败: {str(e)}")
            return []
    
    # ===== 存档管理 =====
    def save_chat(self, filename: str, chat_data: Dict[str, Any]) -> bool:
        """保存聊天记录"""
        try:
            save_path = os.path.join(self.base_dir, 'save', f'{filename}.json')
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(chat_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存聊天记录失败: {str(e)}")
            return False
    
    def load_chat(self, filename: str) -> Dict[str, Any]:
        """加载聊天记录"""
        try:
            save_path = os.path.join(self.base_dir, 'save', f'{filename}.json')
            if os.path.exists(save_path):
                with open(save_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"加载聊天记录失败: {str(e)}")
            return {}
    
    def delete_chat(self, filename: str) -> bool:
        """删除聊天记录"""
        try:
            save_path = os.path.join(self.base_dir, 'save', f'{filename}.json')
            if os.path.exists(save_path):
                os.remove(save_path)
                return True
            return False
        except Exception as e:
            logger.error(f"删除聊天记录失败: {str(e)}")
            return False
    
    def rename_chat(self, old_name: str, new_name: str) -> bool:
        """重命名聊天记录"""
        try:
            old_path = os.path.join(self.base_dir, 'save', f'{old_name}.json')
            new_path = os.path.join(self.base_dir, 'save', f'{new_name}.json')
            
            if os.path.exists(old_path) and not os.path.exists(new_path):
                os.rename(old_path, new_path)
                return True
            return False
        except Exception as e:
            logger.error(f"重命名聊天记录失败: {str(e)}")
            return False
    
    def get_saved_chats(self) -> List[str]:
        """获取所有保存的聊天记录"""
        try:
            chats = []
            save_dir = os.path.join(self.base_dir, 'save')
            if os.path.exists(save_dir):
                for file in os.listdir(save_dir):
                    if file.endswith('.json'):
                        chats.append(file[:-5])  # 去掉.json后缀
            return sorted(chats)
        except Exception as e:
            logger.error(f"获取聊天记录列表失败: {str(e)}")
            return []
    
    def auto_save(self, chat_data: Dict[str, Any]) -> bool:
        """自动保存，保留最近5次存档"""
        try:
            save_dir = os.path.join(self.base_dir, 'save')
            
            # 删除最旧的存档
            old_save = os.path.join(save_dir, 'autosave_5.json')
            if os.path.exists(old_save):
                os.remove(old_save)
            
            # 重命名现有存档
            for i in range(4, 0, -1):
                old_name = os.path.join(save_dir, f'autosave_{i}.json')
                new_name = os.path.join(save_dir, f'autosave_{i+1}.json')
                if os.path.exists(old_name):
                    os.rename(old_name, new_name)
            
            # 重命名当前autosave
            current_autosave = os.path.join(save_dir, 'autosave.json')
            if os.path.exists(current_autosave):
                os.rename(current_autosave, os.path.join(save_dir, 'autosave_1.json'))
            
            # 创建新的autosave
            return self.save_chat('autosave', chat_data)
            
        except Exception as e:
            logger.error(f"自动保存失败: {str(e)}")
            return False
    
    def load_auto_save(self) -> Dict[str, Any]:
        """加载自动保存"""
        autosave_path = os.path.join(self.base_dir, 'save', 'autosave.json')
        if os.path.exists(autosave_path):
            return self.load_chat('autosave')
        return {}
    
    # ===== 资源文件管理 =====
    def get_resource_files(self) -> List[str]:
        """获取资源文件列表"""
        try:
            files = []
            resource_dir = os.path.join(self.base_dir, 'resource')
            if os.path.exists(resource_dir):
                for file in os.listdir(resource_dir):
                    # 支持中文文件名
                    files.append(file)
            return sorted(files)
        except Exception as e:
            logger.error(f"获取资源文件失败: {str(e)}")
            return []
    
    def copy_to_resource(self, source_path: str, filename: str) -> bool:
        """复制文件到资源目录"""
        try:
            resource_dir = os.path.join(self.base_dir, 'resource')
            dest_path = os.path.join(resource_dir, filename)
            shutil.copy2(source_path, dest_path)
            return True
        except Exception as e:
            logger.error(f"复制文件失败: {str(e)}")
            return False
    
    def delete_resource(self, filename: str) -> bool:
        """删除资源文件"""
        try:
            file_path = os.path.join(self.base_dir, 'resource', filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            logger.error(f"删除资源文件失败: {str(e)}")
            return False
    
    def rename_resource(self, old_name: str, new_name: str) -> bool:
        """重命名资源文件"""
        try:
            old_path = os.path.join(self.base_dir, 'resource', old_name)
            new_path = os.path.join(self.base_dir, 'resource', new_name)
            
            if os.path.exists(old_path) and not os.path.exists(new_path):
                os.rename(old_path, new_path)
                return True
            return False
        except Exception as e:
            logger.error(f"重命名资源文件失败: {str(e)}")
            return False
    
    def get_resource_path(self, filename: str) -> str:
        """获取资源文件的完整路径"""
        return os.path.join(self.base_dir, 'resource', filename)
    
    def resource_exists(self, filename: str) -> bool:
        """检查资源文件是否存在"""
        return os.path.exists(self.get_resource_path(filename))


# 全局存储管理器实例
storage_manager = StorageManager()
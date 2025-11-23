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
    
    # ===== 通用文件操作 =====
    def _read_json_file(self, filepath: str) -> Dict[str, Any]:
        """读取JSON文件"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"读取文件失败 {filepath}: {str(e)}")
            return {}
    
    def _write_json_file(self, filepath: str, data: Dict[str, Any]) -> bool:
        """写入JSON文件"""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"写入文件失败 {filepath}: {str(e)}")
            return False
    
    def _delete_file(self, filepath: str) -> bool:
        """删除文件"""
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
            return False
        except Exception as e:
            logger.error(f"删除文件失败 {filepath}: {str(e)}")
            return False
    
    def _rename_file(self, old_path: str, new_path: str) -> bool:
        """重命名文件"""
        try:
            if os.path.exists(old_path) and not os.path.exists(new_path):
                os.rename(old_path, new_path)
                return True
            return False
        except Exception as e:
            logger.error(f"重命名文件失败 {old_path} -> {new_path}: {str(e)}")
            return False
    
    def _list_files(self, directory: str, extension: str = None) -> List[str]:
        """列出目录中的文件"""
        try:
            files = []
            if os.path.exists(directory):
                for file in os.listdir(directory):
                    if extension is None or file.endswith(extension):
                        files.append(file)
            return sorted(files)
        except Exception as e:
            logger.error(f"列出文件失败 {directory}: {str(e)}")
            return []
    
    # ===== 配置管理 =====
    def load_config(self) -> Dict[str, Any]:
        """加载配置"""
        config_path = os.path.join(self.base_dir, 'config', 'api_key.json')
        return self._read_json_file(config_path)
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """保存配置"""
        config_path = os.path.join(self.base_dir, 'config', 'api_key.json')
        return self._write_json_file(config_path, config)
    
    # ===== 提示词管理 =====
    def load_prompt(self, prompt_name: str) -> Dict[str, Any]:
        """加载提示词配置"""
        prompt_path = os.path.join(self.base_dir, 'prompts', prompt_name)
        prompt_data = self._read_json_file(prompt_path)
        
        if not prompt_data:
            logger.error(f"无法加载提示词文件: {prompt_path}")
        
        return prompt_data
    
    def save_prompt(self, prompt_name: str, prompt_data: Dict[str, Any]) -> bool:
        """保存提示词配置"""
        prompt_path = os.path.join(self.base_dir, 'prompts', prompt_name)
        return self._write_json_file(prompt_path, prompt_data)
    
    def delete_prompt(self, prompt_name: str) -> bool:
        """删除提示词配置"""
        prompt_path = os.path.join(self.base_dir, 'prompts', prompt_name)
        return self._delete_file(prompt_path)
    
    def rename_prompt(self, old_name: str, new_name: str) -> bool:
        """重命名提示词"""
        old_path = os.path.join(self.base_dir, 'prompts', old_name)
        new_path = os.path.join(self.base_dir, 'prompts', new_name)
        return self._rename_file(old_path, new_path)
    
    def get_available_prompts(self) -> List[str]:
        """获取所有可用的提示词"""
        return self._list_files(os.path.join(self.base_dir, 'prompts'), '.json')
    
    # ===== 存档管理 =====
    def save_chat(self, filename: str, chat_data: Dict[str, Any]) -> bool:
        """保存聊天记录"""
        save_path = os.path.join(self.base_dir, 'save', filename)
        return self._write_json_file(save_path, chat_data)
    
    def load_chat(self, filename: str) -> Dict[str, Any]:
        """加载聊天记录"""
        save_path = os.path.join(self.base_dir, 'save', filename)
        return self._read_json_file(save_path)
    
    def delete_chat(self, filename: str) -> bool:
        """删除聊天记录"""
        save_path = os.path.join(self.base_dir, 'save', filename)
        return self._delete_file(save_path)
    
    def rename_chat(self, old_name: str, new_name: str) -> bool:
        """重命名聊天记录"""
        old_path = os.path.join(self.base_dir, 'save', old_name)
        new_path = os.path.join(self.base_dir, 'save', new_name)
        return self._rename_file(old_path, new_path)
    
    def get_saved_chats(self) -> List[str]:
        """获取所有保存的聊天记录"""
        return self._list_files(os.path.join(self.base_dir, 'save'), '.json')
    
    def auto_save(self, chat_data: Dict[str, Any]) -> bool:
        """自动保存，保留最近5次存档"""
        try:
            save_dir = os.path.join(self.base_dir, 'save')
            
            # 删除最旧的存档
            old_save = os.path.join(save_dir, 'autosave_5.json')
            self._delete_file(old_save)
            
            # 重命名现有存档
            for i in range(4, 0, -1):
                old_name = os.path.join(save_dir, f'autosave_{i}.json')
                new_name = os.path.join(save_dir, f'autosave_{i+1}.json')
                self._rename_file(old_name, new_name)
            
            # 重命名当前autosave
            current_autosave = os.path.join(save_dir, 'autosave.json')
            if os.path.exists(current_autosave):
                self._rename_file(current_autosave, os.path.join(save_dir, 'autosave_1.json'))
            
            # 创建新的autosave
            return self.save_chat('autosave.json', chat_data)
            
        except Exception as e:
            logger.error(f"自动保存失败: {str(e)}")
            return False
    
    def load_auto_save(self) -> Dict[str, Any]:
        """加载自动保存"""
        return self.load_chat('autosave.json')
    
    # ===== CG文件管理 =====
    def get_cg_files(self) -> List[str]:
        """获取CG文件列表"""
        return self._list_files(os.path.join(self.base_dir, 'resource'))
    
    def copy_to_cg(self, source_path: str, filename: str) -> bool:
        """复制文件到CG目录"""
        try:
            cg_dir = os.path.join(self.base_dir, 'resource')
            dest_path = os.path.join(cg_dir, filename)
            
            # 确保目标目录存在
            os.makedirs(cg_dir, exist_ok=True)
            
            # 如果目标文件已存在，直接覆盖（前端已经询问过用户）
            if os.path.exists(dest_path):
                os.remove(dest_path)
            
            shutil.copy2(source_path, dest_path)
            logger.info(f"文件已复制到CG目录: {filename}")
            return True
        except Exception as e:
            logger.error(f"复制文件失败: {str(e)}")
            return False
    
    def delete_cg(self, filename: str) -> bool:
        """删除CG文件"""
        file_path = os.path.join(self.base_dir, 'resource', filename)
        return self._delete_file(file_path)
    
    def rename_cg(self, old_name: str, new_name: str) -> bool:
        """重命名CG文件"""
        old_path = os.path.join(self.base_dir, 'resource', old_name)
        new_path = os.path.join(self.base_dir, 'resource', new_name)
        return self._rename_file(old_path, new_path)
    
    def get_cg_path(self, filename: str) -> str:
        """获取CG文件的完整路径"""
        return os.path.join(self.base_dir, 'resource', filename)
    
    def cg_exists(self, filename: str) -> bool:
        """检查CG文件是否存在"""
        return os.path.exists(self.get_cg_path(filename))


# 全局存储管理器实例
storage_manager = StorageManager()
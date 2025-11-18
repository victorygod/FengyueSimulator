// 前端应用主逻辑
class ChatApp {
    constructor() {
        this.apiBase = '/api';
        this.currentResponse = '';
        this.isStreaming = false;
        
        // 初始化
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadChatHistory();
        this.updateApiKeyStatus();
        this.updatePromptIndicator();
    }
    
    bindEvents() {
        // 发送消息
        document.getElementById('sendBtn').addEventListener('click', () => this.sendMessage());
        document.getElementById('messageInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendMessage();
            }
        });
        
        // 控制按钮
        document.getElementById('apiKeyBtn').addEventListener('click', () => this.showApiKeyModal());
        document.getElementById('promptsBtn').addEventListener('click', () => this.showPromptsModal());
        document.getElementById('savesBtn').addEventListener('click', () => this.showSavesModal());
        document.getElementById('resourcesBtn').addEventListener('click', () => this.showResourcesModal());
        document.getElementById('clearChatBtn').addEventListener('click', () => this.clearChat());
        
        // 模态框
        document.getElementById('closeModal').addEventListener('click', () => this.hideModal());
        document.getElementById('modalOverlay').addEventListener('click', (e) => {
            if (e.target === e.currentTarget) {
                this.hideModal();
            }
        });
    }
    
    // API调用方法
    async apiCall(endpoint, method = 'GET', data = null) {
        try {
            const options = {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                },
            };
            
            if (data && method !== 'GET') {
                options.body = JSON.stringify(data);
            }
            
            const response = await fetch(`${this.apiBase}/${endpoint}`, options);
            return await response.json();
        } catch (error) {
            console.error('API调用失败:', error);
            this.showStatus('网络错误: ' + error.message, 'error');
            return { status: 'error', message: '网络请求失败' };
        }
    }
        
    // 流式聊天
    async streamChat(message) {
        this.isStreaming = true;
        this.updateSendButton();
        
        try {
            const response = await fetch(`${this.apiBase}/chat/stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message }),
            });
            
            if (!response.ok) {
                throw new Error(`HTTP错误! 状态码: ${response.status}`);
            }
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            this.currentResponse = '';
            
            // 添加助手消息占位符
            const messageId = this.addMessage('assistant', '');
            
            while (this.isStreaming) {
                const { done, value } = await reader.read();
                
                if (done) {
                    break;
                }
                
                // 直接解码数据，不需要处理chunked encoding
                const chunk = decoder.decode(value, { stream: true });
                this.currentResponse += chunk;
                
                // 更新消息内容
                this.updateMessageContent(messageId, this.currentResponse);
            }
            
            // 处理消息中的图片
            this.processImagesInMessage(messageId, this.currentResponse);
            
        } catch (error) {
            console.error('流式聊天错误:', error);
            
            // 检查是否是API密钥错误
            if (error.message.includes('API密钥') || error.message.includes('请先设置API密钥')) {
                alert('错误：请先设置API密钥');
                this.showApiKeyModal();
            } else {
                this.addMessage('assistant', `错误: ${error.message}`);
            }
        } finally {
            this.isStreaming = false;
            this.updateSendButton();
            this.showStatus('就绪');
        }
    }
    
    // 发送消息
    async sendMessage() {
        const input = document.getElementById('messageInput');
        const message = input.value.trim();
        
        if (!message || this.isStreaming) {
            return;
        }
        
        // 清空输入框
        input.value = '';
        
        // 添加用户消息
        this.addMessage('user', message);
        
        // 滚动到底部
        this.scrollToBottom();
        
        // 显示发送状态
        this.showStatus('正在思考...');
        
        // 发送消息
        await this.streamChat(message);
    }
    
    // 添加消息到聊天历史
    addMessage(role, content) {
        const chatHistory = document.getElementById('chatHistory');
        const messageId = 'msg_' + Date.now();
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}-message`;
        messageDiv.id = messageId;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        if (role === 'assistant' && content === '') {
            // 显示输入中状态
            contentDiv.innerHTML = `
                <div class="typing-indicator">
                    <div class="typing-dots">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            `;
        } else {
            contentDiv.textContent = content;
        }
        
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = new Date().toLocaleTimeString();
        
        messageDiv.appendChild(contentDiv);
        messageDiv.appendChild(timeDiv);
        chatHistory.appendChild(messageDiv);
        
        this.scrollToBottom();
        return messageId;
    }
    
    // 更新消息内容
    updateMessageContent(messageId, content) {
        const messageDiv = document.getElementById(messageId);
        if (messageDiv) {
            const contentDiv = messageDiv.querySelector('.message-content');
            
            // 移除输入中状态
            if (contentDiv.querySelector('.typing-indicator')) {
                contentDiv.innerHTML = '';
            }
            
            // 添加内容（支持简单的Markdown样式）
            const formattedContent = this.formatMessage(content);
            contentDiv.innerHTML = formattedContent;
        }
        
        this.scrollToBottom();
    }
    
    // 处理消息中的图片
    processImagesInMessage(messageId, content) {
        const messageDiv = document.getElementById(messageId);
        if (!messageDiv) return;
        
        // 查找图片文件名模式
        const imagePattern = /\[图片: ([^\]]+)\]/g;
        const matches = [...content.matchAll(imagePattern)];
        
        matches.forEach(match => {
            const filename = match[1];
            const imageUrl = `/resource/${filename}`;
            
            // 创建图片元素
            const img = document.createElement('img');
            img.src = imageUrl;
            img.alt = filename;
            img.className = 'message-image';
            img.onload = () => this.scrollToBottom();
            
            const contentDiv = messageDiv.querySelector('.message-content');
            contentDiv.appendChild(img);
            
            // 移除图片标记
            contentDiv.innerHTML = contentDiv.innerHTML.replace(match[0], '');
        });
    }
    
    // 格式化消息内容
    formatMessage(content) {
        // 简单的格式化处理，保持原有的换行但不添加额外换行
        return content
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>');
    }
    
    // 滚动到底部
    scrollToBottom() {
        const chatHistory = document.getElementById('chatHistory');
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }
    
    // 更新发送按钮状态
    updateSendButton() {
        const sendBtn = document.getElementById('sendBtn');
        if (this.isStreaming) {
            sendBtn.textContent = '发送中...';
            sendBtn.disabled = true;
        } else {
            sendBtn.textContent = '发送';
            sendBtn.disabled = false;
        }
    }
    
    // 显示状态信息
    showStatus(message, type = 'info') {
        const statusText = document.getElementById('statusText');
        statusText.textContent = message;
        
        // 可以根据类型添加不同的样式
        statusText.className = type;
    }
    
    // 模态框管理
    showModal(title, templateId) {
        const modal = document.getElementById('modalOverlay');
        const modalTitle = document.getElementById('modalTitle');
        const modalBody = document.getElementById('modalBody');
        
        modalTitle.textContent = title;
        modalBody.innerHTML = document.getElementById(templateId).innerHTML;
        
        modal.style.display = 'flex';
        this.setupModalEvents(templateId);
    }
    
    hideModal() {
        document.getElementById('modalOverlay').style.display = 'none';
    }
    
    setupModalEvents(templateId) {
        switch (templateId) {
            case 'apiKeyTemplate':
                this.setupApiKeyModal();
                break;
            case 'promptsTemplate':
                this.setupPromptsModal();
                break;
            case 'savesTemplate':
                this.setupSavesModal();
                break;
            case 'resourcesTemplate':
                this.setupResourcesModal();
                break;
        }
    }
    
    // API密钥管理
    async showApiKeyModal() {
        this.showModal('API密钥管理', 'apiKeyTemplate');
        await this.updateApiKeyStatus();
    }
    
    async setupApiKeyModal() {
        // 加载当前API密钥状态
        await this.updateApiKeyStatus();
        
        // 保存API密钥
        document.getElementById('saveApiKey').addEventListener('click', async () => {
            const apiKey = document.getElementById('apiKeyInput').value.trim();
            if (!apiKey) {
                alert('请输入API密钥');
                return;
            }
            
            const result = await this.apiCall('api_key/set', 'POST', { api_key: apiKey });
            if (result.status === 'success') {
                this.showStatus('API密钥已保存');
                this.hideModal();
                this.updateApiKeyStatus();
            } else {
                alert('保存失败: ' + result.message);
            }
        });
        
        // 显示/隐藏API密钥
        document.getElementById('toggleApiKeyVisibility').addEventListener('click', () => {
            const input = document.getElementById('apiKeyInput');
            input.type = input.type === 'password' ? 'text' : 'password';
        });
    }
    
    async updateApiKeyStatus() {
        const result = await this.apiCall('api_key/status');
        if (result.status === 'success') {
            const statusElement = document.getElementById('apiKeyStatus');
            if (statusElement) {
                statusElement.textContent = result.has_api_key ? '已设置' : '未设置';
                statusElement.className = result.has_api_key ? 'status-ok' : 'status-error';
            }
            
            // 更新输入框
            const apiKeyInput = document.getElementById('apiKeyInput');
            if (apiKeyInput) {
                apiKeyInput.value = result.api_key_set || '';
            }
        }
    }
    
    // 提示词管理
    async showPromptsModal() {
        this.showModal('提示词管理', 'promptsTemplate');
        await this.loadPrompts();
    }
    
    async setupPromptsModal() {
        await this.loadPrompts();
        
        // 切换提示词
        document.getElementById('promptSelect').addEventListener('change', async (e) => {
            const promptName = e.target.value;
            if (promptName) {
                const result = await this.apiCall('prompt/set', 'POST', { prompt_name: promptName });
                if (result.status === 'success') {
                    this.showStatus('提示词已切换');
                    this.updatePromptIndicator();
                    this.loadPromptConfig();
                } else {
                    alert('切换失败: ' + result.message);
                }
            }
        });
        
        // 保存提示词
        document.getElementById('savePromptAs').addEventListener('click', async () => {
            const newName = document.getElementById('newPromptName').value.trim();
            if (!newName) {
                alert('请输入提示词名称');
                return;
            }
            
            const promptData = {
                pre_prompt: document.getElementById('prePrompt').value,
                pre_text: document.getElementById('preText').value,
                post_text: document.getElementById('postText').value
            };
            
            const result = await this.apiCall('prompt/save', 'POST', {
                prompt_name: newName,
                prompt_data: promptData
            });
            
            if (result.status === 'success') {
                this.showStatus('提示词已保存');
                this.loadPrompts();
                document.getElementById('newPromptName').value = '';
            } else {
                alert('保存失败: ' + result.message);
            }
        });
        
        // 删除提示词
        document.getElementById('deletePrompt').addEventListener('click', async () => {
            const select = document.getElementById('promptSelect');
            const promptName = select.value;
            
            if (!promptName) {
                alert('请选择要删除的提示词');
                return;
            }
            
            if (promptName === 'default') {
                alert('不能删除默认提示词');
                return;
            }
            
            if (confirm(`确定要删除提示词 "${promptName}" 吗？`)) {
                const result = await this.apiCall('prompt/delete', 'POST', { prompt_name: promptName });
                if (result.status === 'success') {
                    this.showStatus('提示词已删除');
                    this.loadPrompts();
                } else {
                    alert('删除失败: ' + result.message);
                }
            }
        });
        
        // 重命名提示词
        document.getElementById('renamePrompt').addEventListener('click', async () => {
            const select = document.getElementById('promptSelect');
            const oldName = select.value;
            const newName = document.getElementById('newPromptName').value.trim();
            
            if (!oldName) {
                alert('请选择要重命名的提示词');
                return;
            }
            
            if (!newName) {
                alert('请输入新的提示词名称');
                return;
            }
            
            if (oldName === 'default') {
                alert('不能重命名默认提示词');
                return;
            }
            
            if (confirm(`确定要将提示词 "${oldName}" 重命名为 "${newName}" 吗？`)) {
                const result = await this.apiCall('prompt/rename', 'POST', {
                    old_name: oldName,
                    new_name: newName
                });
                
                if (result.status === 'success') {
                    this.showStatus('提示词已重命名');
                    this.loadPrompts();
                    document.getElementById('newPromptName').value = '';
                } else {
                    alert('重命名失败: ' + result.message);
                }
            }
        });
        
        // 加载当前提示词配置
        this.loadPromptConfig();
    }
    
    async loadPrompts() {
        const result = await this.apiCall('prompts');
        if (result.status === 'success') {
            const select = document.getElementById('promptSelect');
            select.innerHTML = '';
            
            result.prompts.forEach(prompt => {
                const option = document.createElement('option');
                option.value = prompt;
                option.textContent = prompt;
                if (prompt === result.current_prompt) {
                    option.selected = true;
                }
                select.appendChild(option);
            });
        }
    }
    
    async loadPromptConfig() {
        const result = await this.apiCall('prompts');
        if (result.status === 'success') {
            document.getElementById('prePrompt').value = result.current_config.pre_prompt || '';
            document.getElementById('preText').value = result.current_config.pre_text || '';
            document.getElementById('postText').value = result.current_config.post_text || '';
        }
    }
    
    updatePromptIndicator() {
        const indicator = document.getElementById('promptIndicator');
        if (indicator) {
            indicator.textContent = '提示词已加载';
        }
    }
    
    // 存档管理
    async showSavesModal() {
        this.showModal('存档管理', 'savesTemplate');
        await this.loadSaves();
    }
    
    async setupSavesModal() {
        await this.loadSaves();
        
        // 存档选择事件 - 自动填充名称
        document.getElementById('savesSelect').addEventListener('change', (e) => {
            const saveName = e.target.value;
            if (saveName) {
                document.getElementById('newSaveName').value = saveName;
            }
        });
        
        // 保存聊天
        document.getElementById('saveChat').addEventListener('click', async () => {
            const saveName = document.getElementById('newSaveName').value.trim();
            if (!saveName) {
                alert('请输入存档名称');
                return;
            }
            
            // 先尝试保存，如果已存在会返回exists状态
            const result = await this.apiCall('save', 'POST', { filename: saveName });
            
            if (result.status === 'exists') {
                // 存档已存在，询问是否覆盖
                if (confirm(`存档"${saveName}"已存在，是否覆盖？`)) {
                    const forceResult = await this.apiCall('save/force', 'POST', { filename: saveName });
                    if (forceResult.status === 'success') {
                        this.showStatus('聊天已保存（覆盖）');
                        this.loadSaves();
                    } else {
                        alert('保存失败: ' + forceResult.message);
                    }
                }
            } else if (result.status === 'success') {
                this.showStatus('聊天已保存');
                this.loadSaves();
            } else {
                alert('保存失败: ' + result.message);
            }
        });
        
        // 加载聊天
        document.getElementById('loadChat').addEventListener('click', async () => {
            const select = document.getElementById('savesSelect');
            const saveName = select.value;
            
            if (!saveName) {
                alert('请选择要加载的存档');
                return;
            }
            
            if (confirm(`确定要加载存档 "${saveName}" 吗？当前聊天将被覆盖。`)) {
                const result = await this.apiCall('save/load', 'POST', { filename: saveName });
                if (result.status === 'success') {
                    this.showStatus('聊天已加载');
                    this.hideModal();
                    this.loadChatHistory();
                } else {
                    alert('加载失败: ' + result.message);
                }
            }
        });
        
        // 删除存档
        document.getElementById('deleteSave').addEventListener('click', async () => {
            const select = document.getElementById('savesSelect');
            const saveName = select.value;
            
            if (!saveName) {
                alert('请选择要删除的存档');
                return;
            }
            
            if (confirm(`确定要删除存档 "${saveName}" 吗？`)) {
                const result = await this.apiCall('save/delete', 'POST', { filename: saveName });
                if (result.status === 'success') {
                    this.showStatus('存档已删除');
                    this.loadSaves();
                    document.getElementById('newSaveName').value = '';
                } else {
                    alert('删除失败: ' + result.message);
                }
            }
        });
        
        // 重命名存档
        document.getElementById('renameSave').addEventListener('click', async () => {
            const select = document.getElementById('savesSelect');
            const oldName = select.value;
            const newName = document.getElementById('newSaveName').value.trim();
            
            if (!oldName) {
                alert('请选择要重命名的存档');
                return;
            }
            
            if (!newName) {
                alert('请输入新的存档名称');
                return;
            }
            
            if (confirm(`确定要将存档 "${oldName}" 重命名为 "${newName}" 吗？`)) {
                const result = await this.apiCall('save/rename', 'POST', {
                    old_name: oldName,
                    new_name: newName
                });
                
                if (result.status === 'success') {
                    this.showStatus('存档已重命名');
                    this.loadSaves();
                    document.getElementById('newSaveName').value = '';
                } else {
                    alert('重命名失败: ' + result.message);
                }
            }
        });
    }
    
    async loadSaves() {
        const result = await this.apiCall('saves');
        if (result.status === 'success') {
            const select = document.getElementById('savesSelect');
            select.innerHTML = '';
            
            result.saves.forEach(save => {
                const option = document.createElement('option');
                option.value = save;
                option.textContent = save;
                select.appendChild(option);
            });
        }
    }
    
    // 资源管理
    async showResourcesModal() {
        this.showModal('资源管理', 'resourcesTemplate');
        await this.loadResources();
    }
    
    async setupResourcesModal() {
        await this.loadResources();
        
        // 资源选择事件 - 显示预览
        document.getElementById('resourcesSelect').addEventListener('change', (e) => {
            const filename = e.target.value;
            const preview = document.getElementById('resourcePreview');
            
            if (filename && this.isImageFile(filename)) {
                preview.src = `/resource/${filename}`;
                preview.style.display = 'block';
            } else {
                preview.style.display = 'none';
            }
        });
        
        // 上传文件
        document.getElementById('uploadResource').addEventListener('click', () => {
            document.getElementById('fileUpload').click();
        });
        
        document.getElementById('fileUpload').addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            
            // 这里需要实现文件上传逻辑
            alert('文件上传功能需要在服务器端实现特殊处理');
        });
        
        // 删除资源
        document.getElementById('deleteResource').addEventListener('click', async () => {
            const select = document.getElementById('resourcesSelect');
            const filename = select.value;
            
            if (!filename) {
                alert('请选择要删除的资源文件');
                return;
            }
            
            if (confirm(`确定要删除资源文件 "${filename}" 吗？`)) {
                const result = await this.apiCall('resource/delete', 'POST', { filename: filename });
                if (result.status === 'success') {
                    this.showStatus('资源文件已删除');
                    this.loadResources();
                    document.getElementById('resourcePreview').style.display = 'none';
                } else {
                    alert('删除失败: ' + result.message);
                }
            }
        });
        
        // 重命名资源
        document.getElementById('renameResource').addEventListener('click', async () => {
            const select = document.getElementById('resourcesSelect');
            const oldName = select.value;
            const newName = document.getElementById('newResourceName').value.trim();
            
            if (!oldName) {
                alert('请选择要重命名的资源文件');
                return;
            }
            
            if (!newName) {
                alert('请输入新的资源文件名称');
                return;
            }
            
            if (confirm(`确定要将资源文件 "${oldName}" 重命名为 "${newName}" 吗？`)) {
                const result = await this.apiCall('resource/rename', 'POST', {
                    old_name: oldName,
                    new_name: newName
                });
                
                if (result.status === 'success') {
                    this.showStatus('资源文件已重命名');
                    this.loadResources();
                    document.getElementById('newResourceName').value = '';
                    document.getElementById('resourcePreview').style.display = 'none';
                } else {
                    alert('重命名失败: ' + result.message);
                }
            }
        });
    }
    
    isImageFile(filename) {
        return filename.toLowerCase().match(/\.(jpg|jpeg|png|gif|bmp)$/);
    }
    
    async loadResources() {
        const result = await this.apiCall('resources');
        if (result.status === 'success') {
            const select = document.getElementById('resourcesSelect');
            select.innerHTML = '';
            
            result.files.forEach(file => {
                const option = document.createElement('option');
                option.value = file;
                option.textContent = file;
                select.appendChild(option);
            });
        }
    }
    
    // 聊天历史管理
    async loadChatHistory() {
        const result = await this.apiCall('chat/history');
        if (result.status === 'success') {
            const chatHistory = document.getElementById('chatHistory');
            chatHistory.innerHTML = '';
            
            result.chat_history.forEach(msg => {
                this.addMessage(msg.role, msg.content);
            });
            
            this.scrollToBottom();
        }
    }
    
    async clearChat() {
        if (confirm('确定要清空聊天记录吗？')) {
            const result = await this.apiCall('chat/clear', 'POST');
            if (result.status === 'success') {
                this.showStatus('聊天已清空');
                this.loadChatHistory();
            } else {
                alert('清空失败: ' + result.message);
            }
        }
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.chatApp = new ChatApp();
});
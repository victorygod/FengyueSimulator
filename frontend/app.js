// 前端应用主逻辑
class ChatApp {
    constructor() {
        this.apiBase = '/api';
        this.currentResponse = '';
        this.isStreaming = false;
        this.currentPromptName = "默认提示词";
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadInitialData();
    }
    
    bindEvents() {
        // 发送消息
        document.getElementById('sendBtn').addEventListener('click', () => this.sendMessage());
        document.getElementById('messageInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendMessage();
        });
        
        // 控制按钮
        document.getElementById('apiKeyBtn').addEventListener('click', () => this.showApiKeyModal());
        document.getElementById('promptsBtn').addEventListener('click', () => this.showPromptsModal());
        document.getElementById('savesBtn').addEventListener('click', () => this.showSavesModal());
        document.getElementById('cgManageBtn').addEventListener('click', () => this.showCGModal());
        document.getElementById('clearChatBtn').addEventListener('click', () => this.clearChat());
        
        // 模态框
        document.getElementById('closeModal').addEventListener('click', () => this.hideModal());
        document.getElementById('modalOverlay').addEventListener('click', (e) => {
            if (e.target === e.currentTarget) this.hideModal();
        });
        
        // 记忆轮数
        document.getElementById('memoryRounds').addEventListener('blur', () => this.setMemoryRounds());
        document.getElementById('memoryRounds').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.setMemoryRounds();
        });
    }
    
    async loadInitialData() {
        await this.loadChatHistory();
        await this.updateApiKeyStatus();
        await this.loadMemoryRounds();
        this.updatePromptIndicator();
    }
    
    // API调用方法
    async apiCall(endpoint, method = 'GET', data = null) {
        try {
            const options = {
                method: method,
                headers: {'Content-Type': 'application/json'},
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
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ message: message }),
            });
            
            if (!response.ok) {
                throw new Error(`HTTP错误! 状态码: ${response.status}`);
            }
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            this.currentResponse = '';
            
            const messageId = this.addMessage('assistant', '');
            
            while (this.isStreaming) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value, { stream: true });
                this.currentResponse += chunk;
                this.updateMessageContent(messageId, this.currentResponse);
            }
            
            this.processImagesInMessage(messageId, this.currentResponse);
            
        } catch (error) {
            console.error('流式聊天错误:', error);
            
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
        
        if (!message || this.isStreaming) return;
        
        input.value = '';
        this.addMessage('user', message);
        this.scrollToBottom();
        this.showStatus('正在思考...');
        
        await this.streamChat(message);
    }
    
    // 消息管理
    addMessage(role, content) {
        const chatHistory = document.getElementById('chatHistory');
        const messageId = 'msg_' + Date.now();
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}-message`;
        messageDiv.id = messageId;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        if (role === 'assistant' && content === '') {
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
            contentDiv.innerHTML = this.formatMessage(content);
        }
        
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = new Date().toLocaleTimeString();
        
        messageDiv.appendChild(contentDiv);
        messageDiv.appendChild(timeDiv);
        chatHistory.appendChild(messageDiv);
        
        return messageId;
    }
    
    updateMessageContent(messageId, content) {
        const messageDiv = document.getElementById(messageId);
        if (messageDiv) {
            const contentDiv = messageDiv.querySelector('.message-content');
            
            if (contentDiv.querySelector('.typing-indicator')) {
                contentDiv.innerHTML = '';
            }
            
            const formattedContent = this.formatMessage(content);
            contentDiv.innerHTML = formattedContent;
        }
        
    }
    
    processImagesInMessage(messageId, content) {
        const messageDiv = document.getElementById(messageId);
        if (!messageDiv) return;
        
        const imagePattern = /\[图片: ([^\]]+)\]/g;
        const matches = [...content.matchAll(imagePattern)];
        
        matches.forEach(match => {
            const filename = match[1];
            const imageUrl = `/resource/${encodeURIComponent(filename)}`;
            
            const img = document.createElement('img');
            img.src = imageUrl;
            img.alt = filename;
            img.className = 'message-image';
            
            const contentDiv = messageDiv.querySelector('.message-content');
            contentDiv.appendChild(img);
            contentDiv.innerHTML = contentDiv.innerHTML.replace(match[0], '');
        });
    }
    
    formatMessage(content) {
        // 创建一个安全的HTML解析函数
        const sanitizeHtml = (html) => {
            const temp = document.createElement('div');
            temp.textContent = html;
            return temp.innerHTML;
        };

        // 保留HTML标签，但进行安全处理
        let formatted = content
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>');

        // 恢复一些安全的HTML标签
        formatted = formatted
            .replace(/&lt;(\/?(div|span|p|br|strong|em|b|i|u|code|pre|ul|ol|li|h[1-6]|blockquote|table|tr|td|th))&gt;/g, '<$1>')
            .replace(/&lt;(\/?(div|span|p|br|strong|em|b|i|u|code|pre|ul|ol|li|h[1-6]|blockquote|table|tr|td|th))\s([^&]*)&gt;/g, '<$1 $3>');

        return formatted;
    }
    
    scrollToBottom() {
        const chatHistory = document.getElementById('chatHistory');
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }
    
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
    
    showStatus(message, type = 'info') {
        const statusText = document.getElementById('statusText');
        statusText.textContent = message;
        statusText.className = type;
    }
    
    // 记忆轮数
    async loadMemoryRounds() {
        const result = await this.apiCall('chat/history');
        if (result.status === 'success') {
            document.getElementById('memoryRounds').value = result.memory_rounds || 6;
        }
    }
    
    async setMemoryRounds() {
        const rounds = parseInt(document.getElementById('memoryRounds').value);
        if (isNaN(rounds) || rounds < 0) {
            alert('请输入有效的记忆轮数（0-20）');
            return;
        }
        
        const result = await this.apiCall('memory_rounds/set', 'POST', { memory_rounds: rounds });
        if (result.status === 'success') {
            this.showStatus(`记忆轮数已设置为: ${rounds}`);
        } else {
            alert('设置失败: ' + result.message);
        }
    }
    
    // 更新提示词指示器和标题
    updatePromptIndicator() {
        const indicator = document.getElementById('promptIndicator');
        const title = document.getElementById('pageTitle');
        const mainTitle = document.getElementById('mainTitle');
        
        if (indicator && title && mainTitle) {
            indicator.textContent = this.currentPromptName;
            title.textContent = `${this.currentPromptName} - 聊天机器人`;
            mainTitle.textContent = this.currentPromptName;
        }
    }
    
    updateTitles(promptConfig) {
        this.currentPromptName = promptConfig.name || '默认提示词';
        this.updatePromptIndicator();
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
            case 'cgTemplate':
                this.setupCGModal();
                break;
        }
    }
    
    // API密钥管理
    async showApiKeyModal() {
        this.showModal('API密钥管理', 'apiKeyTemplate');
        await this.updateApiKeyStatus();
    }
    
    async setupApiKeyModal() {
        await this.updateApiKeyStatus();
        
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
            
            const apiKeyInput = document.getElementById('apiKeyInput');
            if (apiKeyInput) {
                // 显示真实API密钥
                apiKeyInput.value = result.api_key || '';
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
        
        document.getElementById('savePrompt').addEventListener('click', async () => {
            const select = document.getElementById('promptSelect');
            const currentPrompt = select.value;
            
            if (!currentPrompt) {
                alert('请先选择或创建一个提示词');
                return;
            }
            
            try {
                // 获取用户输入的JSON文本
                const promptJson = document.getElementById('promptJsonEditor').value;
                
                // 使用自定义解析器处理包含换行的JSON
                const promptData = this.parseJsonWithNewlines(promptJson);
                
                const result = await this.apiCall('prompt/save', 'POST', {
                    prompt_name: currentPrompt,
                    prompt_data: promptData
                });
                
                if (result.status === 'success') {
                    this.showStatus('提示词已保存');
                    this.loadPrompts();
                } else {
                    alert('保存失败: ' + result.message);
                }
            } catch (e) {
                alert('JSON格式错误: ' + e.message);
            }
        });
        
        document.getElementById('newPrompt').addEventListener('click', async () => {
            const newName = document.getElementById('newPromptName').value.trim();
            if (!newName) {
                alert('请输入新提示词文件名');
                return;
            }
            
            const fileName = newName.endsWith('.json') ? newName : newName + '.json';
            
            try {
                const promptJson = document.getElementById('promptJsonEditor').value;
                const promptData = this.parseJsonWithNewlines(promptJson);
                
                const result = await this.apiCall('prompt/save', 'POST', {
                    prompt_name: fileName,
                    prompt_data: promptData
                });
                
                if (result.status === 'success') {
                    this.showStatus('新提示词已创建');
                    this.loadPrompts();
                    document.getElementById('newPromptName').value = '';
                    
                    const switchResult = await this.apiCall('prompt/set', 'POST', { prompt_name: fileName });
                    if (switchResult.status === 'success') {
                        this.updatePromptIndicator();
                    }
                } else {
                    alert('创建失败: ' + result.message);
                }
            } catch (e) {
                alert('JSON格式错误: ' + e.message);
            }
        });
        
        document.getElementById('deletePrompt').addEventListener('click', async () => {
            const select = document.getElementById('promptSelect');
            const promptName = select.value;
            
            if (!promptName) {
                alert('请选择要删除的提示词');
                return;
            }
            
            if (promptName === 'default_prompt.json') {
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
        
        document.getElementById('renamePrompt').addEventListener('click', async () => {
            const select = document.getElementById('promptSelect');
            const oldName = select.value;
            const newName = document.getElementById('newPromptName').value.trim();
            
            if (!oldName) {
                alert('请选择要重命名的提示词');
                return;
            }
            
            if (!newName) {
                alert('请输入新的提示词文件名');
                return;
            }
            
            if (oldName === 'default_prompt.json') {
                alert('不能重命名默认提示词');
                return;
            }
            
            const fileName = newName.endsWith('.json') ? newName : newName + '.json';
            
            if (confirm(`确定要将提示词 "${oldName}" 重命名为 "${fileName}" 吗？`)) {
                const result = await this.apiCall('prompt/rename', 'POST', {
                    old_name: oldName,
                    new_name: fileName
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
            
            this.updateTitles(result.current_config);
        }
    }
    
    async loadPromptConfig() {
        const result = await this.apiCall('prompts');
        if (result.status === 'success') {
            // 将JSON对象转换为支持换行显示的格式
            const formattedJson = this.formatJsonWithNewlines(result.current_config);
            document.getElementById('promptJsonEditor').value = formattedJson;
            this.updateTitles(result.current_config);
        }
    }

    // 添加自定义JSON解析方法
    parseJsonWithNewlines(jsonString) {
        // 先预处理：将字符串中的换行符转义
        let processedJson = jsonString.replace(/("([^"\\]|\\.)*")/g, (match) => {
            // 只处理字符串内容，不处理键名
            if (match.startsWith('"') && match.endsWith('"')) {
                // 将字符串内的换行符转义为 \n
                let inner = match.slice(1, -1);
                inner = inner.replace(/\n/g, '\\n');
                inner = inner.replace(/\r/g, '\\r');
                inner = inner.replace(/\t/g, '\\t');
                return '"' + inner + '"';
            }
            return match;
        });
        
        // 现在可以安全地解析JSON
        return JSON.parse(processedJson);
    }

    // 添加自定义JSON格式化方法
    formatJsonWithNewlines(obj) {
        // 先将对象转换为JSON字符串
        let jsonString = JSON.stringify(obj, null, 2);
        
        // 将转义的换行符恢复为真正的换行符，只在字符串值中
        jsonString = jsonString.replace(/("([^"\\]|\\.)*")/g, (match) => {
            if (match.startsWith('"') && match.endsWith('"')) {
                let inner = match.slice(1, -1);
                // 恢复转义字符
                inner = inner.replace(/\\n/g, '\n');
                inner = inner.replace(/\\r/g, '\r');
                inner = inner.replace(/\\t/g, '\t');
                inner = inner.replace(/\\\\/g, '\\');
                return '"' + inner + '"';
            }
            return match;
        });
        
        return jsonString;
    }
    
    // 存档管理
    async showSavesModal() {
        this.showModal('存档管理', 'savesTemplate');
        await this.loadSaves();
    }
    
    async setupSavesModal() {
        await this.loadSaves();
        
        document.getElementById('savesSelect').addEventListener('change', (e) => {
            const saveName = e.target.value;
            if (saveName) {
                document.getElementById('newSaveName').value = saveName;
            }
        });
        
        document.getElementById('saveChat').addEventListener('click', async () => {
            let saveName = document.getElementById('newSaveName').value.trim();
            if (!saveName) {
                alert('请输入存档文件名');
                return;
            }
            
            saveName = saveName.endsWith('.json') ? saveName : saveName + '.json';
            
            const result = await this.apiCall('save', 'POST', { filename: saveName });
            
            if (result.status === 'exists') {
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
                    this.loadMemoryRounds();
                } else {
                    alert('加载失败: ' + result.message);
                }
            }
        });
        
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
        
        document.getElementById('renameSave').addEventListener('click', async () => {
            const select = document.getElementById('savesSelect');
            const oldName = select.value;
            let newName = document.getElementById('newSaveName').value.trim();
            
            if (!oldName) {
                alert('请选择要重命名的存档');
                return;
            }
            
            if (!newName) {
                alert('请输入新的存档文件名');
                return;
            }
            
            newName = newName.endsWith('.json') ? newName : newName + '.json';
            
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
    
    // CG管理
    async showCGModal() {
        this.showModal('CG管理', 'cgTemplate');
        await this.loadCG();
    }

    async setupCGModal() {
        await this.loadCG();
        
        document.getElementById('cgSelect').addEventListener('change', (e) => {
            const filename = e.target.value;
            const preview = document.getElementById('cgPreview');
            
            if (filename && this.isImageFile(filename)) {
                preview.src = `/resource/${encodeURIComponent(filename)}`;
                preview.style.display = 'block';
                document.getElementById('previewPlaceholder').style.display = 'none';
            } else {
                preview.style.display = 'none';
                document.getElementById('previewPlaceholder').style.display = 'flex';
            }
        });
        
        document.getElementById('copyToCG').addEventListener('click', () => {
            document.getElementById('fileUpload').click();
        });
        
        // 文件上传处理
        document.getElementById('fileUpload').addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                const response = await fetch(`${this.apiBase}/cg/copy`, {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.status === 'success') {
                    if (result.file_exists) {
                        // 文件已存在，显示包含重命名输入框的对话框
                        await this.showFileExistsDialogWithRename(file.name, result.existing_files);
                        return;
                    }
                    this.showStatus('文件已复制到CG目录');
                    this.loadCG();
                } else {
                    alert('复制失败: ' + result.message);
                }
            } catch (error) {
                console.error('复制文件失败:', error);
                alert('复制文件失败: ' + error.message);
            }
            
            // 清空文件输入
            e.target.value = '';
        });
        
        document.getElementById('deleteCG').addEventListener('click', async () => {
            const select = document.getElementById('cgSelect');
            const filename = select.value;
            
            if (!filename) {
                alert('请选择要删除的CG文件');
                return;
            }
            
            if (confirm(`确定要删除CG文件 "${filename}" 吗？`)) {
                const result = await this.apiCall('cg/delete', 'POST', { filename: filename });
                if (result.status === 'success') {
                    this.showStatus('CG文件已删除');
                    this.loadCG();
                    document.getElementById('cgPreview').style.display = 'none';
                    document.getElementById('previewPlaceholder').style.display = 'flex';
                } else {
                    alert('删除失败: ' + result.message);
                }
            }
        });
        
        document.getElementById('renameCG').addEventListener('click', async () => {
            const select = document.getElementById('cgSelect');
            const oldName = select.value;
            const newName = document.getElementById('newCGName').value.trim();
            
            if (!oldName) {
                alert('请选择要重命名的CG文件');
                return;
            }
            
            if (!newName) {
                alert('请输入新的CG文件名称');
                return;
            }
            
            if (confirm(`确定要将CG文件 "${oldName}" 重命名为 "${newName}" 吗？`)) {
                const result = await this.apiCall('cg/rename', 'POST', {
                    old_name: oldName,
                    new_name: newName
                });
                
                if (result.status === 'success') {
                    this.showStatus('CG文件已重命名');
                    this.loadCG();
                    document.getElementById('newCGName').value = '';
                    document.getElementById('cgPreview').style.display = 'none';
                    document.getElementById('previewPlaceholder').style.display = 'flex';
                } else {
                    alert('重命名失败: ' + result.message);
                }
            }
        });
    }

    // 显示包含重命名输入框的文件存在对话框
    async showFileExistsDialogWithRename(filename, existingFiles) {
        return new Promise((resolve) => {
            // 创建模态框
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.style.display = 'flex';
            modal.style.zIndex = '2000';
            
            // 生成唯一文件名
            const uniqueName = this.generateUniqueFilename(filename, existingFiles);
            
            modal.innerHTML = `
                <div class="modal-content metro-modal" style="max-width: 500px;">
                    <div class="modal-header">
                        <h2>文件已存在</h2>
                        <button class="close-btn metro-close" id="closeRenameModal">&times;</button>
                    </div>
                    <div class="modal-body">
                        <p>文件 "<strong>${filename}</strong>" 在CG目录中已存在。</p>
                        <p>请选择操作：</p>
                        
                        <div class="form-group">
                            <label for="renameInput">重命名文件:</label>
                            <input type="text" id="renameInput" value="${uniqueName}" class="metro-input">
                        </div>
                        
                        <div class="button-group" style="margin-top: 20px;">
                            <button id="overwriteBtn" class="metro-btn danger" style="flex: 1;">覆盖原文件</button>
                            <button id="renameBtn" class="metro-btn primary" style="flex: 1;">使用新名称</button>
                            <button id="cancelBtn" class="metro-btn secondary" style="flex: 1;">取消</button>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            // 绑定事件
            const closeBtn = document.getElementById('closeRenameModal');
            const overwriteBtn = document.getElementById('overwriteBtn');
            const renameBtn = document.getElementById('renameBtn');
            const cancelBtn = document.getElementById('cancelBtn');
            const renameInput = document.getElementById('renameInput');
            
            const closeModal = (result) => {
                document.body.removeChild(modal);
                resolve(result);
            };
            
            closeBtn.addEventListener('click', () => closeModal({ action: 'cancel' }));
            modal.addEventListener('click', (e) => {
                if (e.target === modal) closeModal({ action: 'cancel' });
            });
            
            overwriteBtn.addEventListener('click', () => closeModal({ 
                action: 'overwrite',
                filename: filename
            }));
            
            renameBtn.addEventListener('click', () => {
                const newName = renameInput.value.trim();
                if (!newName) {
                    alert('请输入文件名');
                    return;
                }
                closeModal({ 
                    action: 'rename',
                    filename: newName
                });
            });
            
            cancelBtn.addEventListener('click', () => closeModal({ action: 'cancel' }));
        }).then(async (result) => {
            if (result.action === 'cancel') {
                this.showStatus('操作已取消');
                return;
            }
            
            if (result.action === 'overwrite') {
                // 覆盖文件
                const fileInput = document.getElementById('fileUpload');
                const file = fileInput.files[0];
                const formData = new FormData();
                formData.append('file', file);
                
                try {
                    const response = await fetch(`${this.apiBase}/cg/copy`, {
                        method: 'POST',
                        body: formData
                    });
                    
                    const result = await response.json();
                    
                    if (result.status === 'success') {
                        this.showStatus('文件已覆盖');
                        this.loadCG();
                    } else {
                        alert('覆盖失败: ' + result.message);
                    }
                } catch (error) {
                    console.error('覆盖文件失败:', error);
                    alert('覆盖文件失败: ' + error.message);
                }
            } else if (result.action === 'rename') {
                // 使用新名称上传
                const fileInput = document.getElementById('fileUpload');
                const file = fileInput.files[0];
                
                // 检查新名称是否仍然存在
                const cgListResult = await this.apiCall('cg/list');
                if (cgListResult.status === 'success' && cgListResult.files.includes(result.filename)) {
                    if (confirm(`文件 "${result.filename}" 仍然存在，是否覆盖？`)) {
                        // 覆盖已存在的文件
                        await this.uploadFileWithNewName(file, result.filename, true);
                    } else {
                        this.showStatus('操作已取消');
                    }
                } else {
                    // 新名称不存在，直接上传
                    await this.uploadFileWithNewName(file, result.filename, false);
                }
            }
        });
    }

    // 生成唯一文件名
    generateUniqueFilename(filename, existingFiles) {
        const baseName = filename.substring(0, filename.lastIndexOf('.'));
        const extension = filename.substring(filename.lastIndexOf('.'));
        
        let newName = filename;
        let counter = 1;
        
        while (existingFiles.includes(newName)) {
            newName = `${baseName}(${counter})${extension}`;
            counter++;
        }
        
        return newName;
    }

    // 使用新名称上传文件
    async uploadFileWithNewName(file, newName, overwrite = false) {
        const formData = new FormData();
        
        // 创建一个新的File对象，使用新名称
        const newFile = new File([file], newName, { type: file.type });
        formData.append('file', newFile);
        
        try {
            const response = await fetch(`${this.apiBase}/cg/copy`, {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                if (overwrite) {
                    this.showStatus(`文件已重命名为 "${newName}" 并覆盖`);
                } else {
                    this.showStatus(`文件已重命名为 "${newName}" 并复制到CG目录`);
                }
                this.loadCG();
            } else {
                alert('上传失败: ' + result.message);
            }
        } catch (error) {
            console.error('上传失败:', error);
            alert('上传失败: ' + error.message);
        }
    }
    
    isImageFile(filename) {
        return filename.toLowerCase().match(/\.(jpg|jpeg|png|gif|bmp)$/);
    }
    
    async loadCG() {
        const result = await this.apiCall('cg/list');
        if (result.status === 'success') {
            const select = document.getElementById('cgSelect');
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
            
            // 修复bug：从后端获取当前提示词配置并更新标题
            this.updateTitles(result.current_config);
            
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
/**
 * 对话管理
 * 管理消息状态、渲染和 API 调用
 */

class ChatManager {
    constructor(templateManager, ragManager) {
        this.templateManager = templateManager;
        this.ragManager = ragManager;
        this.sessionId = null;
        this.isLoading = false;
        this.messages = [];

        // DOM 元素
        this.container = document.getElementById('messagesContainer');
        this.typingIndicator = document.getElementById('typingIndicator');
        this.input = document.getElementById('messageInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.clearBtn = document.getElementById('clearBtn');
        this.sessionInfo = document.getElementById('sessionInfo');

        // 绑定事件
        this.bindEvents();
    }

    /**
     * 绑定 UI 事件
     */
    bindEvents() {
        this.sendBtn.addEventListener('click', () => {
            this.handleSend();
        });

        this.input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSend();
            }
        });

        this.input.addEventListener('input', () => {
            this.input.style.height = 'auto';
            this.input.style.height = Math.min(this.input.scrollHeight, 160) + 'px';
        });

        this.clearBtn.addEventListener('click', () => {
            if (confirm('确定要清空所有对话吗？')) {
                this.clear();
            }
        });
    }

    /**
     * 处理发送消息
     */
    async handleSend() {
        const message = this.input.value.trim();
        if (!message || this.isLoading) return;

        this.input.value = '';
        this.input.style.height = 'auto';

        // 获取模板和 RAG 状态
        const template = this.templateManager.getActiveTemplate();
        const ragParams = this.ragManager.getRagParams();

        // 如果有模板选中，清除激活状态
        if (template) {
            this.templateManager.clearActive();
        }

        // 构建显示消息
        let displayMessage = message;
        if (template) {
            displayMessage = `[${template}] ${message}`;
        }
        if (ragParams.rag) {
            displayMessage = `📚 ${displayMessage}`;
        }

        this.addMessage('user', displayMessage);

        this.setLoading(true);
        this.showTyping();

        try {
            // 构建请求参数
            const payload = {
                message: message,
                ...ragParams
            };

            if (this.sessionId) {
                payload.session_id = this.sessionId;
            }
            if (template) {
                payload.template = template;
            }

            const result = await ApiClient.chat(payload);

            this.sessionId = result.session_id;
            this.updateSessionInfo();

            this.hideTyping();
            this.setLoading(false);

            // 处理 RAG 来源引用
            if (result.rag) {
                this.addRagMessage(result);
            } else {
                this.addMessage('assistant', result.response);
            }

        } catch (error) {
            this.hideTyping();
            this.setLoading(false);
            this.addMessage('assistant', `❌ 出错了：${error.message}`);
        }
    }

    /**
     * 添加 RAG 消息（含来源引用）
     */
    addRagMessage(result) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message assistant';

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = '🤖';

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';

        // 添加 RAG 标签
        const ragBadge = document.createElement('span');
        if (result.is_fallback) {
            ragBadge.className = 'fallback-badge';
            ragBadge.textContent = '📚 未找到相关文档';
        } else {
            ragBadge.className = 'rag-badge';
            ragBadge.textContent = '📚 知识库增强';
        }
        bubble.appendChild(ragBadge);

        // 添加回复内容（简单处理，后续可支持 Markdown 渲染）
        const contentText = document.createTextNode(result.response);
        bubble.appendChild(contentText);

        // 添加来源引用（如果有）
        if (result.sources && result.sources.length > 0 && !result.is_fallback) {
            const sourceRef = document.createElement('div');
            sourceRef.className = 'source-reference';

            const title = document.createElement('div');
            title.className = 'source-title';
            title.textContent = '📎 引用来源：';
            sourceRef.appendChild(title);

            result.sources.forEach(source => {
                const item = document.createElement('div');
                item.className = 'source-item';
                const name = document.createElement('span');
                name.textContent = source.source || '未知来源';
                const score = document.createElement('span');
                score.className = 'source-score';
                score.textContent = `相关度: ${(source.score || 0) * 100}%`;
                item.appendChild(name);
                item.appendChild(score);
                sourceRef.appendChild(item);
            });

            bubble.appendChild(sourceRef);
        }

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(bubble);

        this.container.appendChild(messageDiv);
        this.scrollToBottom();

        this.messages.push({ role: 'assistant', content: result.response });
    }

    /**
     * 添加普通消息
     */
    addMessage(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = role === 'user' ? '👤' : '🤖';

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        bubble.textContent = content;

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(bubble);

        this.container.appendChild(messageDiv);
        this.scrollToBottom();

        this.messages.push({ role, content });
    }

    /**
     * 显示打字指示器
     */
    showTyping() {
        this.typingIndicator.style.display = 'block';
        this.scrollToBottom();
    }

    /**
     * 隐藏打字指示器
     */
    hideTyping() {
        this.typingIndicator.style.display = 'none';
    }

    /**
     * 设置加载状态
     */
    setLoading(loading) {
        this.isLoading = loading;
        this.input.disabled = loading;
        this.sendBtn.disabled = loading;
    }

    /**
     * 更新会话信息
     */
    updateSessionInfo() {
        if (this.sessionId) {
            const shortId = this.sessionId.substring(0, 8);
            this.sessionInfo.textContent = `会话: ${shortId}...`;
        }
    }

    /**
     * 清空对话
     */
    clear() {
        this.container.innerHTML = '';
        this.messages = [];
        this.sessionId = null;
        this.sessionInfo.textContent = '新会话';
        this.templateManager.clearActive();
        // 关闭 RAG
        if (this.ragManager.isEnabled()) {
            this.ragManager.toggleRag();
        }
        this.showWelcome();
    }

    /**
     * 显示欢迎消息
     */
    showWelcome() {
        const welcomeDiv = document.createElement('div');
        welcomeDiv.className = 'message assistant welcome-message';
        welcomeDiv.innerHTML = `
            <div class="message-avatar">🤖</div>
            <div class="message-bubble">
                <strong>你好！我是 AI 测试助手</strong><br>
                我可以帮你生成测试用例、编写测试代码、构造 Mock 数据。<br>
                点击模板按钮快速开始，或开启 📚 知识库获得业务文档支持。
            </div>
        `;
        this.container.appendChild(welcomeDiv);
    }

    /**
     * 滚动到底部
     */
    scrollToBottom() {
        const mainContent = document.getElementById('mainContent');
        setTimeout(() => {
            mainContent.scrollTop = mainContent.scrollHeight;
        }, 50);
    }
}
/**
 * 对话管理
 * 管理消息状态、渲染和 API 调用
 */

class ChatManager {
    constructor(templateManager) {
        this.templateManager = templateManager;
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
        // 发送按钮
        this.sendBtn.addEventListener('click', () => {
            this.handleSend();
        });

        // 回车发送（Shift+Enter 换行）
        this.input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSend();
            }
        });

        // 自动调整输入框高度
        this.input.addEventListener('input', () => {
            this.input.style.height = 'auto';
            this.input.style.height = Math.min(this.input.scrollHeight, 160) + 'px';
        });

        // 清空对话
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

        // 清空输入框
        this.input.value = '';
        this.input.style.height = 'auto';

        // 获取当前选中的模板
        const template = this.templateManager.getActiveTemplate();

        // 如果有模板选中，清除激活状态
        if (template) {
            this.templateManager.clearActive();
        }

        // 添加用户消息
        const displayMessage = template ? `[${template}] ${message}` : message;
        this.addMessage('user', displayMessage);

        // 显示加载状态
        this.setLoading(true);
        this.showTyping();

        try {
            // 构建请求参数
            const payload = { message };
            if (this.sessionId) {
                payload.session_id = this.sessionId;
            }
            if (template) {
                payload.template = template;
            }

            // 调用 API
            const result = await ApiClient.chat(payload);

            // 保存会话ID
            this.sessionId = result.session_id;
            this.updateSessionInfo();

            // 隐藏加载状态
            this.hideTyping();
            this.setLoading(false);

            // 添加 AI 回复
            this.addMessage('assistant', result.response);

        } catch (error) {
            // 隐藏加载状态
            this.hideTyping();
            this.setLoading(false);

            // 显示错误消息
            this.addMessage('assistant', `❌ 出错了：${error.message}`);
        }
    }

    /**
     * 添加消息到界面
     */
    addMessage(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        if (role === 'user') {
            avatar.textContent = '👤';
        } else {
            avatar.textContent = '🤖';
        }

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
                点击下方的模板按钮快速开始 👇
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
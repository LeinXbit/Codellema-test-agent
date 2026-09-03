/**
 * RAG 管理
 * 处理知识库相关的操作：上传文档、RAG 开关等
 */

class RAGManager {
    constructor() {
        this.isRagEnabled = false;
        this.ragToggle = document.getElementById('ragToggle');
        this.ragStatus = document.getElementById('ragStatus');
        this.uploadBtn = document.getElementById('uploadBtn');
        this.fileInput = document.getElementById('fileInput');
        this.input = document.getElementById('messageInput');
        this.placeholderBackup = '输入您的问题...';

        this.bindEvents();
        this.loadStats();
    }

    /**
     * 绑定事件
     */
    bindEvents() {
        // RAG 开关
        this.ragToggle.addEventListener('click', () => {
            this.toggleRag();
        });

        // 上传按钮
        this.uploadBtn.addEventListener('click', () => {
            this.fileInput.click();
        });

        // 文件选择
        this.fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.uploadDocument(e.target.files[0]);
            }
            e.target.value = ''; // 重置，允许重复选择同一文件
        });
    }

    /**
     * 切换 RAG 状态
     */
    toggleRag() {
        this.isRagEnabled = !this.isRagEnabled;
        this.updateUI();

        if (this.isRagEnabled) {
            this.input.placeholder = '📚 知识库已启用，输入您的问题...';
        } else {
            this.input.placeholder = this.placeholderBackup;
        }
        this.input.focus();
    }

    /**
     * 更新 UI 状态
     */
    updateUI() {
        if (this.isRagEnabled) {
            this.ragToggle.classList.add('active');
            this.ragStatus.textContent = 'on';
        } else {
            this.ragToggle.classList.remove('active');
            this.ragStatus.textContent = 'off';
        }
    }

    /**
     * 获取 RAG 状态
     */
    isEnabled() {
        return this.isRagEnabled;
    }

    /**
     * 上传文档到知识库
     */
    async uploadDocument(file) {
        const formData = new FormData();
        formData.append('file', file);

        // 显示上传中提示
        this.showToast(`正在上传 ${file.name}...`, 'info');

        try {
            const response = await fetch('/api/rag/documents', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                const data = result.data;
                this.showToast(
                    `✅ ${file.name} 上传成功！共 ${data.chunks_added} 个文档块`,
                    'success'
                );
                // 刷新统计信息
                this.loadStats();
            } else {
                this.showToast(
                    `❌ 上传失败：${result.error}`,
                    'error'
                );
            }
        } catch (error) {
            this.showToast(
                `❌ 上传失败：${error.message}`,
                'error'
            );
        }
    }

    /**
     * 加载知识库统计信息
     */
    async loadStats() {
        try {
            const response = await fetch('/api/rag/stats');
            const result = await response.json();

            if (result.success) {
                const stats = result.data;
                const count = stats.total_documents || 0;
                // 可以显示在某个位置，目前仅在控制台输出
                console.log(`知识库状态: ${count} 个文档块`);
            }
        } catch (error) {
            console.warn('获取知识库统计失败:', error);
        }
    }

    /**
     * 显示上传提示
     */
    showToast(message, type = 'info') {
        // 移除已有提示
        const existing = document.querySelector('.upload-toast');
        if (existing) {
            existing.remove();
        }

        const toast = document.createElement('div');
        toast.className = `upload-toast ${type}`;
        toast.textContent = message;
        document.body.appendChild(toast);

        // 3秒后自动消失
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.3s';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    /**
     * 获取 RAG 参数（用于 API 请求）
     */
    getRagParams() {
        if (this.isRagEnabled) {
            return {
                rag: true,
                rag_top_k: 3
            };
        }
        return {
            rag: false
        };
    }
}
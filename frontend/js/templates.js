/**
 * 模板管理
 * 获取模板列表并渲染模板按钮
 */

class TemplateManager {
    constructor() {
        this.templates = [];
        this.activeTemplate = null;
        this.bar = document.getElementById('templateBar');
        this.input = document.getElementById('messageInput');
    }

    /**
     * 加载模板列表
     */
    async loadTemplates() {
        try {
            const response = await fetch('/api/templates');
            const result = await response.json();

            if (result.success) {
                this.templates = result.data;
                this.renderButtons();
                return this.templates;
            } else {
                console.error('加载模板失败:', result.error);
                return [];
            }
        } catch (error) {
            console.error('加载模板异常:', error);
            return [];
        }
    }

    /**
     * 渲染模板按钮
     */
    renderButtons() {
        if (this.templates.length === 0) {
            this.bar.innerHTML = '';
            return;
        }

        this.bar.innerHTML = this.templates.map(t => `
            <button class="template-btn" data-template="${t.name}" data-placeholder="${t.placeholder || '请输入...'}">
                <span class="icon">${this.getIcon(t.name)}</span>
                ${t.label}
            </button>
        `).join('');

        // 绑定点击事件
        this.bar.querySelectorAll('.template-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.selectTemplate(btn.dataset.template);
            });
        });
    }

    /**
     * 获取模板图标
     */
    getIcon(name) {
        const icons = {
            'testcase_generator': '📋',
            'pytest_generator': '🧪',
            'mock_generator': '🎭'
        };
        return icons[name] || '📄';
    }

    /**
     * 选择模板
     */
    selectTemplate(templateName) {
        const template = this.templates.find(t => t.name === templateName);
        if (!template) return;

        // 切换激活状态
        if (this.activeTemplate === templateName) {
            // 取消选择
            this.activeTemplate = null;
            this.input.placeholder = '输入您的问题...';
            this.bar.querySelectorAll('.template-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            return;
        }

        // 激活新模板
        this.activeTemplate = templateName;
        this.input.placeholder = template.placeholder || `请输入${template.label}的内容...`;
        this.input.focus();

        this.bar.querySelectorAll('.template-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.template === templateName);
        });
    }

    /**
     * 获取当前选中的模板
     */
    getActiveTemplate() {
        return this.activeTemplate;
    }

    /**
     * 清除选中状态
     */
    clearActive() {
        this.activeTemplate = null;
        this.input.placeholder = '输入您的问题...';
        this.bar.querySelectorAll('.template-btn').forEach(btn => {
            btn.classList.remove('active');
        });
    }
}
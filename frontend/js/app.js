/**
 * 应用入口
 * 初始化整个应用
 */

document.addEventListener('DOMContentLoaded', async function() {
    // 初始化模板管理器
    const templateManager = new TemplateManager();
    await templateManager.loadTemplates();

    // 初始化 RAG 管理器
    const ragManager = new RAGManager();

    // 初始化对话管理器
    const chat = new ChatManager(templateManager, ragManager);

    // 显示欢迎消息
    chat.showWelcome();

    // 输入框自动聚焦
    document.getElementById('messageInput').focus();

    console.log('AI-Test-Workbench 已启动');
    console.log('可用模板:', templateManager.templates.map(t => t.name));
    console.log('知识库已就绪');
});
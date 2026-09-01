/**
 * API 客户端
 * 封装所有后端 API 调用
 */

const API_BASE = '/api';

class ApiClient {
    /**
     * 发送对话消息（支持普通对话和模板生成）
     * @param {Object} payload - 请求体
     * @param {string} payload.message - 用户消息
     * @param {string} [payload.session_id] - 会话ID
     * @param {string} [payload.template] - 模板名称
     * @returns {Promise<Object>} API 响应数据
     */
    static async chat(payload) {
        const response = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.error || '请求失败');
        }

        return data.data;
    }
}
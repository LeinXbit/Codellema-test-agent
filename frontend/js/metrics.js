/**
 * 监控看板
 * 负责展示质量指标、趋势图和统计数据
 */

// ==================== 全局状态 ====================
let trendChart = null;
let currentMetric = 'retrieval_recall_rate';

// 指标名称映射
const METRIC_LABELS = {
    'retrieval_recall_rate': '检索召回率',
    'case_usability_rate': '用例可用率',
    'code_executable_rate': '代码可执行率',
    'hallucination_rate': '幻觉率'
};

const METRIC_ICONS = {
    'retrieval_recall_rate': '🔍',
    'case_usability_rate': '📋',
    'code_executable_rate': '🧪',
    'hallucination_rate': '⚠️'
};

const METRIC_TARGETS = {
    'retrieval_recall_rate': { target: 80, direction: 'higher' },
    'case_usability_rate': { target: 70, direction: 'higher' },
    'code_executable_rate': { target: 75, direction: 'higher' },
    'hallucination_rate': { target: 20, direction: 'lower' }
};

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', function() {
    loadDashboard();
    setupEventListeners();
});

// ==================== 事件绑定 ====================
function setupEventListeners() {
    // 刷新按钮
    document.getElementById('refreshBtn').addEventListener('click', function() {
        this.classList.add('spinning');
        loadDashboard().finally(() => {
            setTimeout(() => this.classList.remove('spinning'), 500);
        });
    });

    // 图表切换按钮
    document.querySelectorAll('.chart-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.chart-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            currentMetric = this.dataset.metric;
            loadTrend(currentMetric);
        });
    });
}

// ==================== 数据加载 ====================
async function loadDashboard() {
    try {
        const response = await fetch('/api/metrics/dashboard');
        const result = await response.json();

        if (result.success) {
            const data = result.data;
            updateOverview(data.latest_metrics);
            updateFeedback(data.feedback_stats);
            updateSamples(data.sampling_stats);
            updateTemplates(data.template_stats);
            // 加载默认趋势图
            loadTrend('retrieval_recall_rate');
        } else {
            console.error('加载看板数据失败:', result.error);
        }
    } catch (error) {
        console.error('加载看板数据异常:', error);
    }
}

// ==================== 概览卡片更新 ====================
function updateOverview(latestMetrics) {
    const cards = document.querySelectorAll('.metric-card');

    cards.forEach(card => {
        const metricType = card.dataset.metric;
        const metric = latestMetrics[metricType];
        const valueEl = card.querySelector('.metric-value');
        const statusEl = card.querySelector('.metric-status');

        if (metric) {
            const value = metric.value;
            valueEl.textContent = value.toFixed(1) + '%';

            // 判断状态
            const targetInfo = METRIC_TARGETS[metricType];
            let status = 'no_data';
            let statusText = '无数据';

            if (targetInfo) {
                const isHigher = targetInfo.direction === 'higher';
                if (isHigher) {
                    status = value >= targetInfo.target ? 'good' : 'needs_improvement';
                    statusText = value >= targetInfo.target ? '✅ 达标' : '⚠️ 待改进';
                } else {
                    status = value <= targetInfo.target ? 'good' : 'needs_improvement';
                    statusText = value <= targetInfo.target ? '✅ 达标' : '⚠️ 待改进';
                }
            }

            statusEl.className = `metric-status ${status}`;
            statusEl.textContent = statusText;
        } else {
            valueEl.textContent = '--%';
            statusEl.className = 'metric-status no_data';
            statusEl.textContent = '无数据';
        }
    });
}

// ==================== 趋势图 ====================
async function loadTrend(metricType) {
    try {
        const response = await fetch(`/api/metrics/metrics/trend?metric_type=${metricType}&days=30`);
        const result = await response.json();

        if (result.success) {
            const trend = result.data.trend || [];
            renderTrendChart(trend, metricType);
        } else {
            console.error('加载趋势数据失败:', result.error);
        }
    } catch (error) {
        console.error('加载趋势数据异常:', error);
    }
}

function renderTrendChart(trend, metricType) {
    const ctx = document.getElementById('trendChart').getContext('2d');

    const labels = trend.map(d => d.date);
    const values = trend.map(d => d.value);

    const label = METRIC_LABELS[metricType] || metricType;
    const targetInfo = METRIC_TARGETS[metricType];
    const target = targetInfo ? targetInfo.target : null;

    if (trendChart) {
        trendChart.destroy();
    }

    trendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: label,
                    data: values,
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99, 102, 241, 0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 3,
                    pointBackgroundColor: '#6366f1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.parsed.y.toFixed(1) + '%';
                        }
                    }
                }
            },
            scales: {
                y: {
                    min: 0,
                    max: 100,
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                },
                x: {
                    ticks: {
                        maxTicksLimit: 15,
                        maxRotation: 45
                    }
                }
            }
        }
    });

    // 添加目标线
    if (target !== null && target !== undefined) {
        // Chart.js 可以通过 annotation 插件实现，但为简化，使用自定义绘制
        // 这里不做复杂处理，仅保持简洁
    }
}

// ==================== 反馈列表更新 ====================
function updateFeedback(feedbackStats) {
    const container = document.getElementById('feedbackList');
    const countBadge = document.getElementById('feedbackCount');

    const total = feedbackStats?.total_feedbacks || 0;
    countBadge.textContent = `${total} 条`;

    if (total === 0) {
        container.innerHTML = '<div class="empty-state">暂无反馈数据</div>';
        return;
    }

    // 显示统计摘要
    const avgUsability = feedbackStats.avg_usability || '--';
    const avgAccuracy = feedbackStats.avg_accuracy || '--';
    const avgCompleteness = feedbackStats.avg_completeness || '--';

    container.innerHTML = `
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:12px;">
            <div style="text-align:center;padding:8px;background:var(--bg-primary);border-radius:8px;">
                <div style="font-size:12px;color:var(--text-muted);">可用性</div>
                <div style="font-size:20px;font-weight:700;color:var(--text-primary);">${avgUsability}</div>
            </div>
            <div style="text-align:center;padding:8px;background:var(--bg-primary);border-radius:8px;">
                <div style="font-size:12px;color:var(--text-muted);">准确性</div>
                <div style="font-size:20px;font-weight:700;color:var(--text-primary);">${avgAccuracy}</div>
            </div>
            <div style="text-align:center;padding:8px;background:var(--bg-primary);border-radius:8px;">
                <div style="font-size:12px;color:var(--text-muted);">完整性</div>
                <div style="font-size:20px;font-weight:700;color:var(--text-primary);">${avgCompleteness}</div>
            </div>
        </div>
        <div style="font-size:12px;color:var(--text-muted);text-align:center;">
            基于 ${total} 条反馈
        </div>
    `;
}

// ==================== 样本统计更新 ====================
function updateSamples(samplingStats) {
    const container = document.getElementById('sampleStats');
    const countBadge = document.getElementById('sampleCount');

    const sampleStats = samplingStats?.sample_stats || {};
    const total = sampleStats.total_samples || 0;
    const labeled = sampleStats.labeled_samples || 0;
    const unlabeled = sampleStats.unlabeled_samples || 0;

    countBadge.textContent = `${total} 个样本`;

    if (total === 0) {
        container.innerHTML = '<div class="empty-state">暂无样本数据</div>';
        return;
    }

    // 按类型统计
    const byType = sampleStats.by_type || {};
    let typeHtml = '';
    for (const [type, stats] of Object.entries(byType)) {
        const typeLabel = {
            'rag_relevance': 'RAG 相关性',
            'case_usability': '用例可用性',
            'code_executable': '代码可执行性',
            'hallucination': '幻觉检测'
        }[type] || type;

        typeHtml += `
            <div class="sample-stat-item">
                <span class="stat-label">${typeLabel}</span>
                <span class="stat-value">${stats.labeled}/${stats.total} 已标注</span>
            </div>
        `;
    }

    container.innerHTML = `
        <div class="sample-stats-grid">
            <div class="sample-stat-item">
                <span class="stat-label">总样本</span>
                <span class="stat-value">${total}</span>
            </div>
            <div class="sample-stat-item">
                <span class="stat-label">已标注</span>
                <span class="stat-value">${labeled}</span>
            </div>
            <div class="sample-stat-item">
                <span class="stat-label">待标注</span>
                <span class="stat-value">${unlabeled}</span>
            </div>
            <div class="sample-stat-item">
                <span class="stat-label">标注率</span>
                <span class="stat-value">${total > 0 ? Math.round(labeled/total*100) : 0}%</span>
            </div>
        </div>
        ${typeHtml ? `<div style="margin-top:10px;">${typeHtml}</div>` : ''}
    `;
}

// ==================== 模板统计更新 ====================
function updateTemplates(templateStats) {
    const container = document.getElementById('templateStats');

    if (!templateStats || templateStats.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无模板数据</div>';
        return;
    }

    container.innerHTML = templateStats.map(t => `
        <div class="template-stat-item">
            <span class="template-name">${t.label || t.name}</span>
            <span class="template-rate ${t.latest_rate === null ? 'no-data' : ''}">
                ${t.latest_rate !== null ? t.latest_rate.toFixed(1) + '%' : '暂无数据'}
            </span>
        </div>
    `).join('');
}
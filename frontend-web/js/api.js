const API_BASE = 'http://127.0.0.1:8000';

async function apiFetch(path, options = {}) {
    const url = API_BASE + '/api' + path;
    const response = await fetch(url, {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    });
    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || '请求失败');
    }
    return response.json();
}

export { apiFetch };

// ---------- 会话 ----------
export async function getSessions() { return apiFetch('/sessions'); }
export async function createSession(title = '新会话') {
    return apiFetch('/sessions', {
        method: 'POST',
        body: JSON.stringify({ title })
    });
}
export async function deleteSession(id) {
    return apiFetch(`/sessions/${id}`, { method: 'DELETE' });
}
export async function updateSessionTitle(id, title) {
    return apiFetch(`/sessions/${id}`, {
        method: 'PUT',
        body: JSON.stringify({ title })
    });
}

// ---------- 议题 ----------
export async function createTopic(sessionId, question) {
    return apiFetch(`/topics?session_id=${sessionId}`, {
        method: 'POST',
        body: JSON.stringify({ question })
    });
}
export async function getTopicHistory(topicId) {
    return apiFetch(`/topics/${topicId}/history`);
}
export async function startTopic(topicId) {
    return apiFetch(`/topics/${topicId}/start`, { method: 'POST' });
}
export async function closeTopic(topicId) {
    return apiFetch(`/topics/${topicId}/close`, { method: 'POST' });
}

// ---------- 设置 ----------
export async function getSettings() { return apiFetch('/settings'); }
export async function updateModelConfig(providers) {
    return apiFetch('/settings/model', {
        method: 'POST',
        body: JSON.stringify({ providers })
    });
}

// ===== 军师模型映射 =====
export async function getAdvisorModels() {
    return apiFetch('/settings/advisor/models');
}

export async function updateAdvisorMapping(data) {
    // data 格式: { mapping: { "zhuge_liang": "zhipu", ... } }
    return apiFetch('/settings/advisor', {
        method: 'POST',
        body: JSON.stringify(data)
    });
}

// ===== 保存用户消息到后端（落盘） =====
export async function saveUserMessage(topicId, content) {
    return apiFetch(`/topics/${topicId}/messages`, {
        method: 'POST',
        body: JSON.stringify({ content })
    });
}
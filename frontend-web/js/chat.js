import { getAdvisorModels } from './api.js';

let messageList = [];

// 军师 → 模型名映射，如 { "诸葛亮": "glm-4-flash", ... }
let advisorModels = {};
// 同步获取某军师的模型名（供外部使用）
export function getAdvisorModel(advisorName) {
    return advisorModels[advisorName] || null;
}

// 模块加载时获取军师模型映射（失败不影响渲染，只是不显示模型名）
export async function initAdvisorModels() {
    try {
        const data = await getAdvisorModels();
        if (data && data.advisors) {
            advisorModels = data.advisors;
        }
    } catch (e) {
        console.warn('获取军师模型映射失败', e);
    }
}

// 每次渲染新消息前刷新一次映射（保证设置修改后能及时更新，有缓存节流）
let lastRefreshTime = 0;
async function maybeRefreshAdvisorModels() {
    const now = Date.now();
    // 60 秒内最多刷新一次
    if (now - lastRefreshTime > 60000) {
        lastRefreshTime = now;
        initAdvisorModels();
    }
}

// 供外部主动刷新（例如设置保存成功后调用）
export function refreshAdvisorModels() {
    lastRefreshTime = 0;
    maybeRefreshAdvisorModels();
}

function renderMessage(msg) {
    const container = document.getElementById('chatMessages');
    const div = document.createElement('div');

    // 从统一格式中提取字段
    const senderType = msg.sender_type || msg.sender; // 'user' 或 'advisor'
    const senderName = msg.sender_name || msg.advisorName || null;
    const content = msg.content || '';

    if (senderType === 'user') {
        div.className = 'message user';
    } else if (senderType === 'advisor') {
        div.className = 'message advisor';
    } else {
        div.className = 'message system';
    }

    const avatar = document.createElement('div');
    avatar.className = 'avatar';

    if (senderType === 'user') {
        avatar.textContent = '😎';
    } else if (senderType === 'advisor' && senderName) {
        avatar.textContent = senderName.charAt(0);
    } else {
        avatar.textContent = '📢';
    }

    const contentDiv = document.createElement('div');
    contentDiv.className = 'content';

    if (senderType === 'advisor' && senderName) {
        const nameSpan = document.createElement('div');
        nameSpan.className = 'sender';

        // 军师名字
        const nameText = document.createElement('span');
        nameText.textContent = senderName;
        nameSpan.appendChild(nameText);

        // ===== 关键新增：军师名字旁显示当前使用的模型名 =====
        const modelName = advisorModels[senderName];
        if (modelName) {
            const modelTag = document.createElement('span');
            modelTag.className = 'model-tag';
            modelTag.textContent = `（${modelName}）`;
            nameSpan.appendChild(modelTag);
        }

        contentDiv.appendChild(nameSpan);
    }

    const textSpan = document.createElement('div');
    textSpan.textContent = content;
    contentDiv.appendChild(textSpan);

    div.appendChild(avatar);
    div.appendChild(contentDiv);

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

export function clearMessages() {
    document.getElementById('chatMessages').innerHTML = '';
    messageList = [];
}

export function addMessage(senderType, content, senderName = null) {
    // 实时消息时尝试刷新模型映射（有节流）
    maybeRefreshAdvisorModels();
    const msg = {
        sender_type: senderType,
        content,
        sender_name: senderName
    };
    messageList.push(msg);
    renderMessage(msg);
}

export function loadHistory(messages) {
    clearMessages();
    messages.forEach(msg => {
        renderMessage(msg);
    });
}

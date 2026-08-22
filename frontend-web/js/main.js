import { initSessionList, getCurrentSession, getCurrentTopic, selectSession, setCurrentTopic } from './session.js';
import { initInput, setWebSocketMessageHandler } from './input.js';
import { initSettings } from './settings.js';
import { connectWebSocket, closeWebSocket } from './websocket.js';
import { addMessage, clearMessages, loadHistory, initAdvisorModels } from './chat.js';
import { getTopicHistory } from './api.js';
// ===== localStorage 操作 =====
function getSavedSessionId() {
    try {
        const val = localStorage.getItem('currentSessionId');
        return val ? parseInt(val) : null;
    } catch { return null; }
}

function getSavedTopicId() {
    try {
        const val = localStorage.getItem('currentTopicId');
        return val ? parseInt(val) : null;
    } catch { return null; }
}

function saveCurrentSession(sessionId, topicId) {
    try {
        if (sessionId) localStorage.setItem('currentSessionId', String(sessionId));
        else localStorage.removeItem('currentSessionId');
        if (topicId) localStorage.setItem('currentTopicId', String(topicId));
        else localStorage.removeItem('currentTopicId');
    } catch (e) {
        console.warn('保存会话状态失败', e);
    }
}

export function saveCurrentSessionState() {
    const sid = getCurrentSession();
    const tid = getCurrentTopic();
    if (sid && tid) {
        saveCurrentSession(sid, tid);
    }
}

// ===== 恢复当前会话（页面刷新后调用） =====
async function restoreCurrentSession() {
    const savedSessionId = getSavedSessionId();
    const savedTopicId = getSavedTopicId();
    
    if (!savedSessionId || !savedTopicId) {
        console.log('[Restore] 没有保存的会话，进入默认状态');
        return;
    }

    console.log(`[Restore] 尝试恢复: session=${savedSessionId}, topic=${savedTopicId}`);

    try {
        // 1. 获取会话列表，验证会话是否存在
        const sessions = await import('./api.js').then(api => api.getSessions());
        const session = sessions.find(s => s.id === savedSessionId);
        if (!session) {
            console.warn('[Restore] 保存的会话不存在，已清除');
            localStorage.removeItem('currentSessionId');
            localStorage.removeItem('currentTopicId');
            return;
        }

        // 2. 获取该会话的议题列表
        const topics = await import('./api.js').then(api => 
            api.apiFetch(`/sessions/${savedSessionId}/topics`)
        );
        
        // 3. 确定要恢复的议题
        let topic = topics.find(t => t.id === savedTopicId);
        if (!topic && topics.length > 0) {
            // 如果保存的议题不存在，取第一个
            topic = topics[0];
            saveCurrentSession(savedSessionId, topic.id);
            console.log('[Restore] 使用第一个议题代替:', topic.id);
        }
        if (!topic) {
            console.warn('[Restore] 没有可用议题');
            localStorage.removeItem('currentTopicId');
            return;
        }

        // 4. 更新 session.js 中的状态
        // 由于 session.js 没有导出 setCurrentSession，我们通过 setCurrentTopic 和 selectSession 间接设置
        const sessionModule = await import('./session.js');
        sessionModule.setCurrentTopic(topic.id);
        // 注意：selectSession 会加载历史并建立 WebSocket，但我们后续会手动处理，
        // 所以这里调用 selectSession 时传入空回调，避免重复操作
        sessionModule.selectSession(savedSessionId, (sid, tid) => {
            // 空回调，不做额外操作
            console.log(`[Restore] selectSession 完成: ${sid}, ${tid}`);
        });

        // 5. 更新顶部标题（优先使用会话标题，若为空则用议题 question）
        const displayTitle = session.title || topic.question || '未命名';
        document.getElementById('topicTitle').textContent = displayTitle;

        // 6. 更新侧边栏：高亮当前会话，并更新名称
        const items = document.querySelectorAll('.session-item');
        for (let item of items) {
            const id = parseInt(item.dataset.id);
            if (id === savedSessionId) {
                item.classList.add('active');
                const nameSpan = item.querySelector('.session-name');
                if (nameSpan) nameSpan.textContent = displayTitle;
            } else {
                item.classList.remove('active');
            }
        }

        // 7. 加载历史消息（直接从后端获取）
        try {
            const historyData = await getTopicHistory(topic.id);
            if (historyData.messages && historyData.messages.length > 0) {
                loadHistory(historyData.messages);
            } else {
                clearMessages();
            }
        } catch (err) {
            console.warn('[Restore] 加载历史失败', err);
            clearMessages();
        }

        // 8. 连接 WebSocket
        closeWebSocket();
        connectWebSocket(
            savedSessionId,
            topic.id,
            onWebSocketMessage,
            () => console.log('[Restore] WebSocket 已连接'),
            () => console.log('[Restore] WebSocket 断开'),
            (err) => console.error('[Restore] WebSocket 错误', err)
        );

        console.log('[Restore] 会话恢复完成');

    } catch (err) {
        console.error('[Restore] 恢复会话异常:', err);
        localStorage.removeItem('currentSessionId');
        localStorage.removeItem('currentTopicId');
    }
}

// 导出 restoreCurrentSession 供其他模块（如 session.js）调用
export { restoreCurrentSession };

// ===== 初始化 =====
initSessionList(onSessionSelected);
initInput();
initSettings();
// 初始化时预取军师模型映射
initAdvisorModels();

// 页面加载后恢复会话
document.addEventListener('DOMContentLoaded', restoreCurrentSession);

// 页面关闭前保存会话状态
window.addEventListener('beforeunload', () => {
    const sid = getCurrentSession();
    const tid = getCurrentTopic();
    if (sid && tid) {
        saveCurrentSession(sid, tid);
    }
});

// 侧边栏折叠
document.getElementById('toggleSidebarBtn').addEventListener('click', () => {
    document.getElementById('sidebar').classList.toggle('collapsed');
});

// 右上角菜单
document.getElementById('menuBtn').addEventListener('click', (e) => {
    e.stopPropagation();
    const menu = document.getElementById('dropdownMenu');
    menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
});
document.addEventListener('click', () => {
    document.getElementById('dropdownMenu').style.display = 'none';
});

function onSessionSelected(sessionId, topicId) {
    // 保存当前会话状态到 localStorage
    saveCurrentSession(sessionId, topicId);
    
    closeWebSocket();
    connectWebSocket(sessionId, topicId, onWebSocketMessage, () => {
        console.log('WS 打开');
    }, () => {
        console.log('WS 关闭');
    }, (err) => {
        console.error('WS 错误', err);
    });
}

function onWebSocketMessage(data) {
    const type = data.type;
    if (type === 'advisor_message') {
        addMessage('advisor', data.content, data.advisor_name);
    } else if (type === 'ask_lord') {
        addMessage('system', '💡 军师们请主公发表看法', '');
    } else if (type === 'topic_closed') {
        addMessage('system', '📌 议题已结束，总结：' + data.summary, '');
        document.getElementById('topicTitle').textContent = '议题已结束';
    } else if (type === 'advisor_start') {
        // "正在思考"提示也显示模型名（通过 chat.js 暴露的获取函数）
        import('./chat.js').then(chat => {
            const modelName = chat.getAdvisorModel ? chat.getAdvisorModel(data.advisor_name) : null;
            const suffix = modelName ? `（${modelName}）` : '';
            addMessage('system', `⏳ ${data.advisor_name}${suffix} 正在思考...`, '');
        });
    } else if (type === 'system') {
        if (data.content !== '连接已建立，可以开始对话。') {
            addMessage('system', data.content, '');
        }
    } else if (type === 'user_message') {
        if (data.sender === 'client') {
            return;
        }
        addMessage('user', data.content);
    } else {
        console.log('未知消息', data);
    }
}


setWebSocketMessageHandler(onWebSocketMessage);
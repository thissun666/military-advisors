import { sendWebSocketMessage, connectWebSocket, closeWebSocket, getWebSocketState } from './websocket.js';
import { getCurrentTopic, getCurrentSession, setCurrentTopic, selectSession, loadSessions, updateSessionTitle } from './session.js';
import { createTopic, closeTopic, createSession, saveUserMessage } from './api.js';
import { addMessage, clearMessages } from './chat.js';

let onMessageHandler = null;
let isProcessing = false;
let isPageReady = false;

export function setWebSocketMessageHandler(handler) {
    onMessageHandler = handler;
}

function handleWebSocketMessage(data) {
    if (onMessageHandler) {
        onMessageHandler(data);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    isPageReady = true;
});

export function initInput() {
    const input = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendBtn');

    // 辅助函数：创建新议题并通过 WebSocket 发送消息
    async function createNewTopicAndSend(sessionId, question) {
        try {
            const newTopic = await createTopic(sessionId, question);
            setCurrentTopic(newTopic.id);

            document.getElementById('topicTitle').textContent = question;

            const items = document.querySelectorAll('.session-item');
            for (let item of items) {
                if (parseInt(item.dataset.id) === sessionId) {
                    const nameSpan = item.querySelector('.session-name');
                    if (nameSpan) nameSpan.textContent = question;
                    break;
                }
            }

            try {
                await updateSessionTitle(sessionId, question);
            } catch (err) {
                console.warn('更新会话标题失败:', err);
            }

            clearMessages();
            addMessage('system', `📌 新议题已创建：${question}`, '');

            closeWebSocket();
            await new Promise((resolve, reject) => {
                connectWebSocket(
                    sessionId,
                    newTopic.id,
                    handleWebSocketMessage,
                    () => {
                        sendWebSocketMessage({ type: 'user_message', content: question, sender: 'client' });
                        addMessage('user', question);
                        resolve();
                    },
                    () => {},
                    (err) => reject(err)
                );
            });
        } catch (err) {
            addMessage('system', `❌ 创建新议题失败：${err.message}`, '');
            console.error(err);
        }
    }

    async function sendMessage() {
        if (!isPageReady) {
            console.log('[Input] 页面未完全加载，忽略发送');
            return;
        }

        const text = input.value.trim();
        if (!text || isProcessing) return;

        isProcessing = true;

        try {
            // 1. 确保有会话
            let sessionId = getCurrentSession();
            if (!sessionId) {
                const newSession = await createSession('新会话');
                sessionId = newSession.id;
                loadSessions();
                await new Promise((resolve) => {
                    selectSession(sessionId, (sid, tid) => {
                        resolve();
                    });
                });
                await new Promise(r => setTimeout(r, 200));
                // 重新获取 topicId
                let topicId = getCurrentTopic();
                if (!topicId) {
                    // 如果没有议题，创建新议题
                    await createNewTopicAndSend(sessionId, text);
                    input.value = '';
                    return;
                }
            }

            // 2. 结束命令
            // 2. 结束命令
const endKeywords = ['结束当前问题', '此事已解决', '结束讨论'];
if (endKeywords.includes(text)) {
    let topicId = getCurrentTopic();
    
    // ===== 防御性检查：如果 topicId 为空或已关闭，尝试自动查找未关闭的议题 =====
    if (!topicId) {
        const sessionId = getCurrentSession();
        if (sessionId) {
            try {
                const topics = await import('./api.js').then(api => 
                    api.apiFetch(`/sessions/${sessionId}/topics`)
                );
                const sortedTopics = topics.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
                const activeTopic = sortedTopics.find(t => t.status !== 'closed');
                if (activeTopic) {
                    topicId = activeTopic.id;
                    setCurrentTopic(topicId);
                    console.log('[Input] 自动切换到未关闭的议题:', topicId);
                }
            } catch (err) {
                console.warn('[Input] 获取议题列表失败:', err);
            }
        }
    }
    
    if (!topicId) {
        addMessage('system', '⚠️ 当前没有活跃的议题。', '');
        input.value = '';
        return;
    }

    addMessage('user', text);

    try {
        await saveUserMessage(topicId, text);
    } catch (err) {
        console.warn('保存结束消息失败:', err);
    }

    try {
        await closeTopic(topicId);
        addMessage('system', '📌 议题已由主公结束。', '');
    } catch (err) {
        // ===== 如果议题已关闭，显示友好提示 =====
        if (err.message && err.message.includes('议题已关闭')) {
            addMessage('system', '📌 该议题已结束。', '');
        } else {
            addMessage('system', `❌ 结束议题失败：${err.message}`, '');
        }
    }
    
    closeWebSocket();
    setCurrentTopic(null);
    document.getElementById('topicTitle').textContent = '议题已结束，请开始新问题';
    loadSessions();
    input.value = '';
    return;
}

            // 3. 显式开始新问题
            if (text.startsWith('开始新问题')) {
                let question = text.replace(/^开始新问题[：:]\s*/, '').replace(/^开始新问题\s+/, '').trim();
                if (!question) {
                    addMessage('system', '⚠️ 请指定新议题的问题内容', '');
                    input.value = '';
                    return;
                }
                await createNewTopicAndSend(sessionId, question);
                input.value = '';
                return;
            }

            // ===== 4. 普通发言：关键修复 =====
            let topicId = getCurrentTopic();

            // 如果当前没有议题，创建新议题
            if (!topicId) {
                await createNewTopicAndSend(sessionId, text);
                input.value = '';
                return;
            }

            // ===== 有议题：直接发送，不创建新议题 =====
            // 保存用户消息到后端（落盘）
            try {
                await saveUserMessage(topicId, text);
            } catch (err) {
                console.warn('保存用户消息失败:', err);
            }

            const wsState = getWebSocketState();
            if (wsState !== WebSocket.OPEN) {
                await new Promise((resolve, reject) => {
                    connectWebSocket(
                        sessionId,
                        topicId,
                        handleWebSocketMessage,
                        () => {
                            sendWebSocketMessage({ type: 'user_message', content: text, sender: 'client' });
                            addMessage('user', text);
                            resolve();
                        },
                        () => {},
                        (err) => reject(err)
                    );
                });
            } else {
                sendWebSocketMessage({ type: 'user_message', content: text, sender: 'client' });
                addMessage('user', text);
            }

            input.value = '';
        } catch (err) {
            console.error('发送消息异常', err);
            addMessage('system', `❌ 发送失败：${err.message}`, '');
        } finally {
            setTimeout(() => {
                isProcessing = false;
            }, 800);
        }
    }

    sendBtn.addEventListener('click', (e) => {
        e.preventDefault();
        sendMessage();
    });

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.repeat) {
            e.preventDefault();
            sendMessage();
        }
    });
}
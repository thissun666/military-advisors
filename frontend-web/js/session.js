import { getSessions, createSession, deleteSession, createTopic, updateSessionTitle as apiUpdateTitle } from './api.js';
import { closeWebSocket } from './websocket.js';
import { clearMessages, loadHistory } from './chat.js';
import { getTopicHistory } from './api.js';
import { saveCurrentSessionState } from './main.js';

let currentSessionId = null;
let currentTopicId = null;
let isDraftMode = false;
let sessionListData = [];
let editingSessionId = null; // 当前正在编辑的会话 ID

export function initSessionList(onSelect) {
    loadSessions(onSelect);
    document.getElementById('newSessionBtn').addEventListener('click', () => {
        enterDraftMode();
    });

    // 删除弹窗事件绑定
    const modal = document.getElementById('deleteConfirmModal');
    document.getElementById('deleteCancelBtn').addEventListener('click', () => {
        modal.style.display = 'none';
    });
    document.getElementById('deleteConfirmBtn').addEventListener('click', () => {
        const sessionId = parseInt(modal.dataset.sessionId);
        if (sessionId) {
            performDelete(sessionId);
        }
        modal.style.display = 'none';
    });
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });
}

function enterDraftMode() {
    isDraftMode = true;
    currentSessionId = null;
    currentTopicId = null;
    clearMessages();
    document.getElementById('topicTitle').textContent = '新对话';
    const items = document.querySelectorAll('.session-item');
    items.forEach(item => item.classList.remove('active'));
    cancelEditing(); // 取消任何编辑状态
}

// 取消编辑状态
function cancelEditing() {
    if (editingSessionId !== null) {
        const editingItem = document.querySelector(`.session-item[data-id="${editingSessionId}"]`);
        if (editingItem) {
            const input = editingItem.querySelector('.session-name-input');
            const nameSpan = editingItem.querySelector('.session-name');
            if (input && nameSpan) {
                // 恢复显示名称（不保存修改）
                const originalTitle = nameSpan.textContent;
                input.remove();
                nameSpan.style.display = '';
                // 移除 editing 类
                editingItem.classList.remove('editing');
            }
        }
        editingSessionId = null;
    }
}

// 开始内联编辑
function startInlineEdit(sessionId, currentTitle, onSave) {
    // 先取消任何正在进行的编辑
    cancelEditing();

    const item = document.querySelector(`.session-item[data-id="${sessionId}"]`);
    if (!item) return;

    const nameSpan = item.querySelector('.session-name');
    if (!nameSpan) return;

    // 创建输入框
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'session-name-input';
    input.value = currentTitle;
    input.maxLength = 50;

    // 替换 span 为 input
    nameSpan.style.display = 'none';
    nameSpan.parentNode.insertBefore(input, nameSpan);

    // 标记编辑状态
    editingSessionId = sessionId;
    item.classList.add('editing');

    // 聚焦并选中全部文本
    input.focus();
    input.select();

    // 保存函数
    const save = () => {
        const newTitle = input.value.trim();
        if (newTitle && newTitle !== currentTitle) {
            onSave(sessionId, newTitle);
        }
        // 恢复显示（即使没有变化也要恢复）
        finishEditing(sessionId);
    };

    // 取消函数
    const cancel = () => {
        finishEditing(sessionId);
    };

    // 事件绑定
    input.addEventListener('blur', save);
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            input.blur(); // 触发 blur 保存
        } else if (e.key === 'Escape') {
            e.preventDefault();
            cancel();
        }
    });

    // 阻止点击外部关闭（由 blur 处理）
    input.addEventListener('click', (e) => e.stopPropagation());
}

// 完成编辑（恢复显示）
function finishEditing(sessionId) {
    if (editingSessionId !== sessionId) return;

    const item = document.querySelector(`.session-item[data-id="${sessionId}"]`);
    if (item) {
        const input = item.querySelector('.session-name-input');
        const nameSpan = item.querySelector('.session-name');
        if (input && nameSpan) {
            input.remove();
            nameSpan.style.display = '';
        }
        item.classList.remove('editing');
    }
    editingSessionId = null;
}

export async function createRealSessionAndTopic(question) {
    const newSession = await createSession('新会话');
    const sessionId = newSession.id;
    const newTopic = await createTopic(sessionId, question);
    const topicId = newTopic.id;

    currentSessionId = sessionId;
    currentTopicId = topicId;
    isDraftMode = false;

    await loadSessions();
    highlightSession(sessionId);
    document.getElementById('topicTitle').textContent = question;

    await apiUpdateTitle(sessionId, question);
    await loadSessions();
    saveCurrentSessionState();

    return { sessionId, topicId };
}

export function loadSessions(onSelect = null) {
    return getSessions().then(sessions => {
        sessionListData = sessions;
        const list = document.getElementById('sessionList');
        list.innerHTML = '';
        sessions.forEach(s => {
            const li = document.createElement('li');
            li.className = 'session-item' + (s.id === currentSessionId ? ' active' : '');
            li.dataset.id = s.id;

            const nameSpan = document.createElement('span');
            nameSpan.className = 'session-name';
            nameSpan.textContent = s.title || '未命名';

            const actions = document.createElement('div');
            actions.className = 'session-actions';

            // 重命名按钮 - 触发内联编辑
            const renameBtn = document.createElement('button');
            renameBtn.innerHTML = '<i class="fas fa-pen"></i>';
            renameBtn.title = '重命名';
            renameBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                // 如果已经在编辑这个会话，不重复触发
                if (editingSessionId === s.id) return;
                startInlineEdit(s.id, s.title || '未命名', async (id, newTitle) => {
                    try {
                        await apiUpdateTitle(id, newTitle);
                        // 更新数据
                        const session = sessionListData.find(item => item.id === id);
                        if (session) session.title = newTitle;
                        // 更新当前会话标题
                        if (currentSessionId === id) {
                            document.getElementById('topicTitle').textContent = newTitle;
                        }
                        // 刷新列表（保持编辑状态完成）
                        await loadSessions(onSelect);
                        // 重新高亮当前会话
                        if (currentSessionId) {
                            highlightSession(currentSessionId);
                        }
                    } catch (err) {
                        console.error('重命名失败', err);
                        alert('重命名失败，请重试');
                    }
                });
            });

            // 删除按钮 - 显示自定义弹窗
            const delBtn = document.createElement('button');
            delBtn.className = 'delete-btn';
            delBtn.innerHTML = '<i class="fas fa-trash"></i>';
            delBtn.title = '删除';
            delBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                showDeleteConfirm(s.id, s.title || '未命名', onSelect);
            });

            actions.appendChild(renameBtn);
            actions.appendChild(delBtn);
            li.appendChild(nameSpan);
            li.appendChild(actions);

            li.addEventListener('click', () => {
                // 点击会话时，如果有正在编辑的，先取消
                if (editingSessionId !== null) {
                    cancelEditing();
                }
                isDraftMode = false;
                selectSession(s.id, onSelect);
            });

            list.appendChild(li);
        });

        // 如果有正在编辑的会话，恢复其编辑状态
        if (editingSessionId !== null) {
            const session = sessionListData.find(s => s.id === editingSessionId);
            if (session) {
                // 重新触发编辑
                startInlineEdit(editingSessionId, session.title || '未命名', async (id, newTitle) => {
                    // 同上
                    try {
                        await apiUpdateTitle(id, newTitle);
                        const sessionData = sessionListData.find(item => item.id === id);
                        if (sessionData) sessionData.title = newTitle;
                        if (currentSessionId === id) {
                            document.getElementById('topicTitle').textContent = newTitle;
                        }
                        await loadSessions(onSelect);
                        if (currentSessionId) {
                            highlightSession(currentSessionId);
                        }
                    } catch (err) {
                        console.error('重命名失败', err);
                        alert('重命名失败，请重试');
                    }
                });
            } else {
                editingSessionId = null;
            }
        }
    }).catch(console.error);
}

// 显示自定义删除确认弹窗
function showDeleteConfirm(sessionId, sessionTitle, onSelect) {
    const modal = document.getElementById('deleteConfirmModal');
    const messageEl = document.getElementById('deleteModalMessage');
    const titleEl = document.getElementById('deleteModalTitle');

    titleEl.textContent = `删除 "${sessionTitle}"`;
    messageEl.textContent = `确定要删除此会话吗？此操作不可恢复。`;
    modal.dataset.sessionId = sessionId;
    modal.style.display = 'flex';
}

// 执行删除
async function performDelete(sessionId) {
    try {
        await deleteSession(sessionId);
        // 如果删除的是当前会话，进入草稿模式
        if (currentSessionId === sessionId) {
            enterDraftMode();
            closeWebSocket();
        }
        // 刷新侧边栏
        await loadSessions();
        if (currentSessionId) {
            highlightSession(currentSessionId);
        }
    } catch (err) {
        console.error('删除失败', err);
        alert('删除失败，请重试');
    }
}

function highlightSession(sessionId) {
    const items = document.querySelectorAll('.session-item');
    items.forEach(item => {
        if (parseInt(item.dataset.id) === sessionId) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });
}

export function selectSession(id, onSelect) {
    if (isDraftMode) {
        isDraftMode = false;
    }
    currentSessionId = id;
    highlightSession(id);

    import('./api.js').then(api => {
        api.getSessions().then(sessions => {
            const session = sessions.find(s => s.id === id);
            const sessionTitle = session ? session.title : '未命名';

            api.apiFetch(`/sessions/${id}/topics`).then(topics => {
                if (topics.length === 0) {
                    currentTopicId = null;
                    document.getElementById('topicTitle').textContent = '请开始新问题';
                    clearMessages();
                    saveCurrentSessionState();
                    if (onSelect) onSelect(id, null);
                    return;
                }

                // ===== 关键修复：优先选择未关闭的议题 =====
                const sortedTopics = topics.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
                // 1. 优先找状态为 'active' 或 'pending' 的议题（未关闭）
                let activeTopic = sortedTopics.find(t => t.status !== 'closed');
                // 2. 如果没有未关闭的，取最新的（即使是已关闭的）
                const topic = activeTopic || sortedTopics[0];
                
                currentTopicId = topic.id;
                saveCurrentSessionState();

                const displayTitle = topic.question && topic.question.trim() !== ''
                    ? topic.question
                    : sessionTitle;
                document.getElementById('topicTitle').textContent = displayTitle;

                // 更新侧边栏名称
                const items = document.querySelectorAll('.session-item');
                for (let item of items) {
                    if (parseInt(item.dataset.id) === id) {
                        const nameSpan = item.querySelector('.session-name');
                        if (nameSpan && (nameSpan.textContent === '未命名' || nameSpan.textContent === '新会话')) {
                            nameSpan.textContent = displayTitle;
                        }
                        break;
                    }
                }

                getTopicHistory(topic.id).then(data => {
                    if (data.messages && data.messages.length > 0) {
                        loadHistory(data.messages);
                    } else {
                        clearMessages();
                    }
                    if (onSelect) onSelect(id, currentTopicId);
                }).catch(err => {
                    console.error('加载历史失败', err);
                    clearMessages();
                    if (onSelect) onSelect(id, currentTopicId);
                });
            }).catch(err => {
                console.error('获取议题列表失败', err);
                alert('获取议题列表失败，请刷新重试');
            });
        }).catch(err => {
            console.error('获取会话列表失败', err);
        });
    });
}

export function getCurrentSession() {
    return currentSessionId;
}

export function getCurrentTopic() {
    return currentTopicId;
}

export function setCurrentTopic(topicId) {
    currentTopicId = topicId;
}

export function isDraft() {
    return isDraftMode;
}

export async function updateSessionTitle(sessionId, title) {
    try {
        await apiUpdateTitle(sessionId, title);
        const items = document.querySelectorAll('.session-item');
        for (let item of items) {
            if (parseInt(item.dataset.id) === sessionId) {
                const nameSpan = item.querySelector('.session-name');
                if (nameSpan) nameSpan.textContent = title;
                break;
            }
        }
    } catch (e) {
        console.warn('更新会话标题失败', e);
    }
}
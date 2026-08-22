let ws = null;
let reconnectTimer = null;
let reconnectAttempts = 0;
const MAX_RECONNECT = 3;
let isConnecting = false;
let manualClosed = false; // 新增：是否为手动关闭（手动关闭不触发重连）

export function connectWebSocket(sessionId, topicId, onMessage, onOpen, onClose, onError) {
    if (isConnecting) {
        console.log('正在连接中，请勿重复调用');
        return;
    }

    if (ws) {
        // 关键：手动关闭旧连接时，先摘掉回调再 close，
        // 防止异步触发的 onclose 引发意外重连（导致重复发送消息）
        manualClosed = true;
        ws.onopen = null;
        ws.onmessage = null;
        ws.onclose = null;
        ws.onerror = null;
        ws.close();
        ws = null;
    }

    manualClosed = false;
    isConnecting = true;
    reconnectAttempts = 0;

    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = location.host;
    const url = `${protocol}//${host}/ws/${sessionId}/${topicId}`;
    ws = new WebSocket(url);

    ws.onopen = () => {
        console.log('WebSocket 已连接');
        reconnectAttempts = 0;
        isConnecting = false;
        if (onOpen) onOpen();
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (onMessage) onMessage(data);
        } catch (e) {
            console.error('解析消息错误', e);
        }
    };

    ws.onclose = () => {
        console.log('WebSocket 断开');
        isConnecting = false;

        // 手动关闭，不触发重连
        if (manualClosed) return;

        if (onClose) onClose();

        if (reconnectAttempts < MAX_RECONNECT) {
            reconnectAttempts++;
            if (reconnectTimer) clearTimeout(reconnectTimer);
            reconnectTimer = setTimeout(() => {
                // 关键：重连时不传 onOpen，避免重连成功后重复发送消息
                connectWebSocket(sessionId, topicId, onMessage, null, onClose, onError);
            }, 3000);
        } else {
            console.warn('已达到最大重连次数，请刷新页面');
        }
    };

    ws.onerror = (error) => {
        console.error('WebSocket 错误', error);
        if (onError) onError(error);
    };
}

export function sendWebSocketMessage(data) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(data));
    } else {
        console.warn('WebSocket 未连接，无法发送');
    }
}

export function closeWebSocket() {
    manualClosed = true;
    if (ws) {
        // 关键：先摘掉所有回调再 close，
        // 这样即使 onclose 异步触发也不会进入重连逻辑
        ws.onopen = null;
        ws.onmessage = null;
        ws.onclose = null;
        ws.onerror = null;
        ws.close();
        ws = null;
    }
    if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
    }
    reconnectAttempts = 0;
    isConnecting = false;
}

export function getWebSocketState() {
    return ws ? ws.readyState : WebSocket.CLOSED;
}

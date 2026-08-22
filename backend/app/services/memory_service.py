import os
from typing import List, Dict, Any
from ..utils.file_utils import read_json, write_json, ensure_dir
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data", "sessions")

def _get_topic_dir(session_id: int, topic_id: int) -> str:
    dir_path = os.path.join(DATA_DIR, f"session_{session_id}", f"topic_{topic_id}")
    ensure_dir(dir_path)
    return dir_path

def _get_messages_file(session_id: int, topic_id: int) -> str:
    return os.path.join(_get_topic_dir(session_id, topic_id), "all_messages.json")

def save_message(session_id: int, topic_id: int, sender_type: str, content: str, sender_name: str = None) -> None:
    """统一保存消息接口"""
    file_path = _get_messages_file(session_id, topic_id)
    data = read_json(file_path)
    if not isinstance(data, list):
        data = []
    
    msg = {
        "sender_type": sender_type,
        "content": content,
        "timestamp": datetime.now().isoformat()
    }
    if sender_name:
        msg["sender_name"] = sender_name
    
    data.append(msg)
    write_json(file_path, data)
    print(f"[Memory] 保存消息: {sender_type} - {content[:30]}...")

def save_user_message(session_id: int, topic_id: int, content: str) -> None:
    save_message(session_id, topic_id, "user", content)

def save_advisor_message(session_id: int, topic_id: int, advisor_name: str, content: str) -> None:
    save_message(session_id, topic_id, "advisor", content, advisor_name)

def save_system_message(session_id: int, topic_id: int, content: str) -> None:
    """保存系统消息（如结束提示、议题创建等）"""
    save_message(session_id, topic_id, "system", content)

def get_full_conversation(session_id: int, topic_id: int) -> List[Dict[str, Any]]:
    """获取完整对话"""
    file_path = _get_messages_file(session_id, topic_id)
    data = read_json(file_path)
    if not isinstance(data, list):
        return []
    # 兼容旧数据格式
    for msg in data:
        if 'sender_type' not in msg:
            if msg.get('sender') == 'user':
                msg['sender_type'] = 'user'
            else:
                msg['sender_type'] = 'advisor'
        if 'sender_name' not in msg:
            msg['sender_name'] = msg.get('advisorName', None)
    return data

# 兼容旧接口
def save_memory(session_id: int, topic_id: int, advisor_name: str, memory_item: str) -> None:
    save_advisor_message(session_id, topic_id, advisor_name, memory_item)

def load_memory(session_id: int, topic_id: int, advisor_name: str, limit: int = 100) -> List[str]:
    all_msgs = get_full_conversation(session_id, topic_id)
    result = []
    for msg in all_msgs:
        if msg.get("sender_type") == "advisor" and msg.get("sender_name") == advisor_name:
            result.append(msg.get("content", ""))
    return result[-limit:] if len(result) > limit else result

def clear_topic_data(session_id: int, topic_id: int) -> None:
    import shutil
    dir_path = _get_topic_dir(session_id, topic_id)
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)
def save_system_message(session_id: int, topic_id: int, content: str) -> None:
    """保存系统消息（如结束提示、议题创建等）"""
    save_message(session_id, topic_id, "system", content)
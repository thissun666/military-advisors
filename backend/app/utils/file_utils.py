import json
import os
from pathlib import Path
from typing import Any, Dict

def ensure_dir(path: str) -> None:
    """确保目录存在，若不存在则创建"""
    Path(path).mkdir(parents=True, exist_ok=True)

def read_json(file_path: str) -> Dict[str, Any]:
    """读取 JSON 文件，若文件不存在或格式错误则返回空字典"""
    if not os.path.exists(file_path):
        return {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def write_json(file_path: str, data: Dict[str, Any]) -> None:
    """将数据写入 JSON 文件（覆盖写入）"""
    ensure_dir(os.path.dirname(file_path))
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def append_to_json_list(file_path: str, new_item: Any) -> None:
    """向 JSON 数组文件追加一条记录（如果文件不存在则创建数组）"""
    data = read_json(file_path)
    if not isinstance(data, list):
        data = []
    data.append(new_item)
    write_json(file_path, data)
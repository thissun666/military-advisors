from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Optional, List
from datetime import datetime
from pydantic import BaseModel
import os
import shutil

from sqlalchemy.orm import Session
from ..database import SessionLocal, get_db
from .. import models
from ..services.memory_service import get_full_conversation
from ..utils.file_utils import read_json, write_json
from ..config import settings
from ..services.llm_service import get_advisor_model_mapping, save_advisor_model_mapping

router = APIRouter()

# 配置文件路径（基于项目根目录）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_DIR = os.path.join(BASE_DIR, "data", "config")
MODEL_CONFIG_PATH = os.path.join(CONFIG_DIR, "model_config.json")
ADVISOR_BACKEND_PATH = os.path.join(CONFIG_DIR, "advisor_backend.json")

# 军师 ID 与显示名的映射（与 llm_service.py 保持一致）
ADVISOR_DISPLAY_NAMES = {
    "zhuge_liang": "诸葛亮",
    "si_ma_yi": "司马懿",
    "zhou_yu": "周瑜",
    "xun_yu": "荀彧",
}

# ---------- Pydantic 模型 ----------
class ProviderConfig(BaseModel):
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None

class ModelConfigUpdate(BaseModel):
    providers: Dict[str, ProviderConfig]

class AdvisorBackendUpdate(BaseModel):
    mapping: Dict[str, str]

class AdvisorModelMappingUpdate(BaseModel):
    detailed_mapping: Dict[str, str]

class SettingsResponse(BaseModel):
    providers: Dict[str, dict]
    advisor_mapping: Dict[str, str]
    advisor_models: Dict[str, str]

class UserMessageCreate(BaseModel):
    content: str

# ---------- 辅助函数 ----------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_effective_config():
    """读取当前配置，若文件不存在则返回默认配置（从 .env 读取）"""
    config = read_json(MODEL_CONFIG_PATH)
    if not config or "providers" not in config:
        config = {
            "providers": {
                "zhipu": {
                    "api_key": settings.ZHIPU_API_KEY,
                    "base_url": settings.ZHIPU_BASE_URL,
                    "model": settings.DEFAULT_MODEL_ZHIPU
                },
                "siliconflow": {
                    "api_key": settings.SILICONFLOW_API_KEY,
                    "base_url": settings.SILICONFLOW_BASE_URL,
                    "model": settings.DEFAULT_MODEL_SILICON
                },
                "ollama": {
                    "api_key": "",
                    "base_url": settings.OLLAMA_BASE_URL,
                    "model": settings.DEFAULT_MODEL_LOCAL_QWEN
                }
            }
        }
        write_json(MODEL_CONFIG_PATH, config)
    return config

def get_advisor_mapping():
    """读取军师-模型映射，若文件不存在则返回默认映射"""
    mapping = read_json(ADVISOR_BACKEND_PATH)
    if not mapping:
        mapping = {
            "zhuge_liang": "zhipu",
            "si_ma_yi": "siliconflow",
            "zhou_yu": "ollama",
            "xun_yu": "ollama"
        }
        write_json(ADVISOR_BACKEND_PATH, mapping)
    return mapping

# ---------- API 端点 ----------
@router.get("/", response_model=SettingsResponse)
def get_settings():
    """获取当前完整配置（脱敏显示 API Key 前几位）"""
    config = get_effective_config()
    mapping = get_advisor_mapping()
    models = get_advisor_model_mapping()

    providers = config.get("providers", {})
    masked_providers = {}
    for name, cfg in providers.items():
        masked = cfg.copy()
        if cfg.get("api_key") and len(cfg["api_key"]) > 8:
            key = cfg["api_key"]
            masked["api_key"] = key[:4] + "****" + key[-4:]
        masked_providers[name] = masked

    return SettingsResponse(
        providers=masked_providers,
        advisor_mapping=mapping,
        advisor_models=models.detailed_mapping
    )

@router.post("/model")
def update_model_config(data: ModelConfigUpdate):
    """更新模型配置（API Key、Base URL、模型名）"""
    current = get_effective_config()

    for provider_name, new_cfg in data.providers.items():
        if provider_name not in current["providers"]:
            current["providers"][provider_name] = {}

        if new_cfg.api_key is not None:
            current["providers"][provider_name]["api_key"] = new_cfg.api_key
        if new_cfg.base_url is not None:
            current["providers"][provider_name]["base_url"] = new_cfg.base_url
        if new_cfg.model is not None:
            current["providers"][provider_name]["model"] = new_cfg.model

    write_json(MODEL_CONFIG_PATH, current)
    print(f"[Settings] 模型配置已更新: {current['providers'].keys()}")
    return {"detail": "模型配置已更新"}

@router.post("/advisor")
def update_advisor_mapping(data: AdvisorBackendUpdate):
    """更新军师-模型映射"""
    current = get_advisor_mapping()
    for advisor, backend in data.mapping.items():
        if advisor in current:
            current[advisor] = backend
        else:
            current[advisor] = backend
    write_json(ADVISOR_BACKEND_PATH, current)
    print(f"[Settings] 军师映射已更新: {current}")
    return {"detail": "军师映射已更新"}

@router.get("/advisor/available")
def list_available_providers():
    """返回可用的服务商列表（供前端下拉菜单使用）"""
    config = get_effective_config()
    provider_names = list(config.get("providers", {}).keys())
    return {"providers": provider_names}

# ===== 获取军师模型名（供前端聊天区显示）=====
@router.get("/advisor/models")
def get_advisor_models():
    """
    返回格式：
    {
        "advisors": {
            "诸葛亮": "glm-4-flash",
            "司马懿": "Qwen/Qwen2.5-7B-Instruct",
            "周瑜": "deepseek-r1:1.5b",
            "荀彧": "qwen2.5:3b"
        }
    }
    """
    print("[Settings] === 开始获取军师模型名 ===")
    
    config = get_effective_config()
    mapping = get_advisor_mapping()
    models = get_advisor_model_mapping()
    providers = config.get("providers", {})

    print(f"[Settings] advisor_backend.json 映射: {mapping}")
    print(f"[Settings] detailed_mapping: {models.detailed_mapping}")
    print(f"[Settings] model_config.json providers: {list(providers.keys())}")

    result = {}
    for advisor_id, provider_name in mapping.items():
        display_name = ADVISOR_DISPLAY_NAMES.get(advisor_id, advisor_id)
        
        # ===== 关键修复：优先使用 detailed_mapping =====
        model_name = None
        
        # 1. 优先从 detailed_mapping 读取
        if advisor_id in models.detailed_mapping:
            detailed_value = models.detailed_mapping[advisor_id]
            # 格式: "ollama:deepseek-r1:1.5b" 或 "zhipu:glm-4-flash"
            if ':' in detailed_value:
                parts = detailed_value.split(':', 1)
                model_name = parts[1]  # 取冒号后面的模型名
            else:
                model_name = detailed_value
            print(f"[Settings] {display_name} 从 detailed_mapping 读取: {model_name}")
        
        # 2. 如果没有 detailed_mapping，从 provider 配置读取
        if not model_name:
            provider_cfg = providers.get(provider_name, {})
            model_name = provider_cfg.get("model", "") or "未配置"
            print(f"[Settings] {display_name} 从 provider 配置读取: {model_name}")
        
        result[display_name] = model_name

    print(f"[Settings] 返回结果: {result}")
    return {"advisors": result}

# ===== 保存军师模型映射 =====
@router.post("/advisor/model")
def update_advisor_model_mapping(data: AdvisorModelMappingUpdate):
    """更新军师模型映射（支持同一后端不同模型）"""
    print(f"[Settings] 收到更新军师模型映射请求: {data.detailed_mapping}")
    
    current = get_advisor_model_mapping()
    for advisor, backend in data.detailed_mapping.items():
        if advisor in current.detailed_mapping:
            current.detailed_mapping[advisor] = backend
        else:
            current.detailed_mapping[advisor] = backend
    
    save_advisor_model_mapping(current)
    print(f"[Settings] 军师模型映射已保存: {current.detailed_mapping}")
    return {"detail": "军师模型映射已更新"}

@router.post("/{topic_id}/messages")
def save_user_message(topic_id: int, data: UserMessageCreate, db: Session = Depends(get_db)):
    topic = db.query(models.Topic).filter(models.Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="议题不存在")

    from ..services.memory_service import save_message
    save_message(topic.session_id, topic_id, "user", data.content)
    return {"detail": "消息已保存"}

@router.post("/{topic_id}/start")
def start_topic(topic_id: int, db: Session = Depends(get_db)):
    topic = db.query(models.Topic).filter(models.Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="议题不存在")

    if topic.status != "pending":
        raise HTTPException(status_code=400, detail="该议题已处于进行中或已关闭")

    topic.status = "active"
    db.commit()
    return {"detail": "讨论已开启", "topic_id": topic_id}

@router.post("/{topic_id}/close")
def close_topic(topic_id: int, db: Session = Depends(get_db)):
    topic = db.query(models.Topic).filter(models.Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="议题不存在")

    if topic.status == "closed":
        raise HTTPException(status_code=400, detail="议题已关闭")

    topic.status = "closed"
    db.commit()

    try:
        from ..services.memory_service import save_system_message
        save_system_message(topic.session_id, topic_id, "📌 议题已由主公结束。")
        print(f"[Close Topic] 已保存系统消息")
    except Exception as e:
        print(f"[Close Topic] 保存系统消息失败: {e}")

    return {"detail": "议题已关闭", "topic_id": topic_id}
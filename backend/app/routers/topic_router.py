from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from pydantic import BaseModel

from ..database import SessionLocal
from .. import models
from ..services.memory_service import get_full_conversation

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------- Pydantic 模型 ----------
class TopicCreate(BaseModel):
    question: str

class UserMessageCreate(BaseModel):
    content: str

class TopicResponse(BaseModel):
    id: int
    session_id: int
    question: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class TopicHistoryResponse(BaseModel):
    messages: List[dict] = []

# ---------- API 端点 ----------

@router.post("", response_model=TopicResponse)
def create_topic(session_id: int, data: TopicCreate, db: Session = Depends(get_db)):
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    new_topic = models.Topic(
        session_id=session_id,
        question=data.question,
        status="pending"
    )
    db.add(new_topic)
    db.commit()
    db.refresh(new_topic)

    try:
        from ..services.memory_service import save_system_message
        save_system_message(session_id, new_topic.id, f"📌 新议题已创建：{data.question}")
    except Exception as e:
        print(f"[Create Topic] 保存系统消息失败: {e}")

    return new_topic

@router.get("/{topic_id}/history", response_model=TopicHistoryResponse)
def get_topic_history(topic_id: int, db: Session = Depends(get_db)):
    topic = db.query(models.Topic).filter(models.Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="议题不存在")

    messages = get_full_conversation(topic.session_id, topic_id)
    return TopicHistoryResponse(messages=messages)

# ===== 新增：保存用户消息端点（用于结束讨论等场景的消息落盘）=====
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
        # ===== 修改：返回友好信息，而不是抛出 400 =====
        return {"detail": "议题已关闭", "topic_id": topic_id, "already_closed": True}

    topic.status = "closed"
    db.commit()

    try:
        from ..services.memory_service import save_system_message
        save_system_message(topic.session_id, topic_id, "📌 议题已由主公结束。")
        print(f"[Close Topic] 已保存系统消息")
    except Exception as e:
        print(f"[Close Topic] 保存系统消息失败: {e}")

    return {"detail": "议题已关闭", "topic_id": topic_id, "already_closed": False}
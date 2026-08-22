from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from pydantic import BaseModel
import os
import shutil

from ..database import SessionLocal
from .. import models

router = APIRouter()

# ---------- 依赖注入：获取数据库会话 ----------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------- Pydantic 模型 ----------
class SessionCreate(BaseModel):
    title: str = "新会话"

class SessionResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    topic_count: int = 0

    class Config:
        from_attributes = True

class SessionUpdate(BaseModel):
    title: str

# ---------- API 端点 ----------
# 注意：为了兼容前端请求不带尾部斜杠，所有根路径装饰器都使用 "" 而不是 "/"

@router.post("", response_model=SessionResponse)
def create_session(data: SessionCreate, db: Session = Depends(get_db)):
    """新建一个会话（不自动创建默认议题，等用户首次提问时再创建）"""
    new_session = models.Session(title=data.title)
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    # 修复：不再自动创建 question="" 的空议题，
    # 否则前端首次发送消息时会走到"已有议题"分支，导致标题不更新
    return SessionResponse(
        id=new_session.id,
        title=new_session.title,
        created_at=new_session.created_at,
        topic_count=0
    )

@router.get("", response_model=List[SessionResponse])
def list_sessions(db: Session = Depends(get_db)):
    """获取所有会话列表，按创建时间倒序"""
    sessions = db.query(models.Session).order_by(models.Session.created_at.desc()).all()
    result = []
    for s in sessions:
        topic_count = db.query(models.Topic).filter(models.Topic.session_id == s.id).count()
        result.append(SessionResponse(
            id=s.id,
            title=s.title,
            created_at=s.created_at,
            topic_count=topic_count
        ))
    return result

@router.get("/{session_id}", response_model=SessionResponse)
def get_session(session_id: int, db: Session = Depends(get_db)):
    """获取单个会话详情"""
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    topic_count = db.query(models.Topic).filter(models.Topic.session_id == session_id).count()
    return SessionResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        topic_count=topic_count
    )

@router.delete("/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db)):
    """删除会话（级联删除其下的所有议题 + 磁盘数据）"""
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 删除磁盘上的数据目录
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_dir = os.path.join(base_dir, "data", "sessions", f"session_{session_id}")
    if os.path.exists(data_dir):
        shutil.rmtree(data_dir)
        print(f"[Delete Session] 已删除磁盘数据: {data_dir}")

    db.delete(session)
    db.commit()
    return {"detail": "会话已删除", "id": session_id}

@router.get("/{session_id}/topics")
def get_session_topics(session_id: int, db: Session = Depends(get_db)):
    """获取指定会话下的所有议题列表（按创建时间倒序）"""
    topics = db.query(models.Topic).filter(
        models.Topic.session_id == session_id
    ).order_by(models.Topic.created_at.desc()).all()

    return [
        {
            "id": t.id,
            "question": t.question,
            "status": t.status,
            "created_at": t.created_at.isoformat()
        }
        for t in topics
    ]

@router.put("/{session_id}")
def update_session(session_id: int, data: SessionUpdate, db: Session = Depends(get_db)):
    """更新会话标题"""
    session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    session.title = data.title
    db.commit()
    return {"detail": "会话标题已更新", "id": session_id, "title": session.title}

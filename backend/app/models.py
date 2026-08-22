from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, default="新会话")
    created_at = Column(DateTime, default=datetime.utcnow)

    topics = relationship("Topic", back_populates="session", cascade="all, delete-orphan")

class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    question = Column(Text, nullable=False)          # 主公提出的问题
    status = Column(String(20), default="pending")   # pending, active, closed
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("Session", back_populates="topics")
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os
import asyncio
import json
import uuid

from .database import init_db
from . import models
from .routers import session_router, topic_router, settings_router
from .websocket_manager import manager
from .services.scheduler import Scheduler
from .services.memory_service import save_message  # 改用统一存储

app = FastAPI(title="主公的军师团 API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    init_db()

app.include_router(session_router.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(topic_router.router, prefix="/api/topics", tags=["topics"])
app.include_router(settings_router.router, prefix="/api/settings", tags=["settings"])

frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend-web")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")
    @app.get("/")
    async def get_index():
        index_file = os.path.join(frontend_path, "index.html")
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
else:
    print("警告: frontend-web 目录不存在")

schedulers = {}
welcomed = set()

async def start_discussion(session_id: int, topic_id: int, user_question: str):
    print(f"[Main] 启动讨论: {user_question}")
    scheduler = Scheduler(session_id, topic_id)
    scheduler.reset(user_question)
    schedulers[(session_id, topic_id)] = scheduler
    try:
        await scheduler.run()
    except Exception as e:
        print(f"[Main] 讨论异常: {e}")
    finally:
        schedulers.pop((session_id, topic_id), None)
        print("[Main] 讨论结束")

@app.websocket("/ws/{session_id}/{topic_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: int, topic_id: int):
    await manager.connect(websocket, session_id, topic_id)
    key = (session_id, topic_id)
    try:
        if key not in welcomed:
            await manager.send_message(session_id, topic_id, {
                "type": "system",
                "content": "连接已建立，可以开始对话。"
            })
            welcomed.add(key)

        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "user_message":
                user_content = msg.get("content", "")
                sender = msg.get("sender", "client")
                print(f"[Main] 收到消息: {user_content}")
                save_message(session_id, topic_id, "user", user_content, None)
                await manager.send_message(session_id, topic_id, {
                    "type": "user_message",
                    "content": user_content,
                    "sender": sender
                })

                if key in schedulers and schedulers[key].is_active:
                    await manager.send_message(session_id, topic_id, {
                        "type": "system",
                        "content": "主公，请等待当前讨论结束再发言。"
                    })
                else:
                    if key in schedulers:
                        del schedulers[key]
                    asyncio.create_task(start_discussion(session_id, topic_id, user_content))
            else:
                pass
    except WebSocketDisconnect:
        print("[Main] WebSocket 断开")
        if key in schedulers:
            schedulers[key].is_active = False
            del schedulers[key]
        welcomed.discard(key)
        manager.disconnect(websocket, session_id, topic_id)
    except Exception as e:
        print(f"[Main] 异常: {e}")
        if key in schedulers:
            schedulers[key].is_active = False
            del schedulers[key]
        welcomed.discard(key)
        manager.disconnect(websocket, session_id, topic_id)
        try:
            await websocket.close()
        except:
            pass
import sys
import os
import asyncio
import json
import uuid

# ===== 打包后路径处理（必须放在最顶部） =====
def get_base_path():
    """获取可执行文件所在目录"""
    if getattr(sys, 'frozen', False):
        # 打包后运行
        return os.path.dirname(sys.executable)
    else:
        # 开发环境运行，项目根目录
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_PATH = get_base_path()

# ===== 创建完整的目录结构（确保运行时数据目录存在） =====
data_path = os.path.join(BASE_PATH, 'backend', 'data')
sessions_path = os.path.join(data_path, 'sessions')
config_path = os.path.join(data_path, 'config')

for path in [data_path, sessions_path, config_path]:
    os.makedirs(path, exist_ok=True)

print(f"[Main] 数据目录已就绪: {data_path}")

# ===== 将项目根目录添加到 sys.path，使打包后能正确导入模块 =====
if getattr(sys, 'frozen', False):
    sys.path.insert(0, BASE_PATH)

# ===== 导入（使用绝对导入，避免相对导入在打包后失败） =====
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from backend.app.database import init_db
from backend.app import models
from backend.app.routers import session_router, topic_router, settings_router
from backend.app.websocket_manager import manager
from backend.app.services.scheduler import Scheduler
from backend.app.services.memory_service import save_message

# ===== 应用实例 =====
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

# ===== 注册路由 =====
app.include_router(session_router.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(topic_router.router, prefix="/api/topics", tags=["topics"])
app.include_router(settings_router.router, prefix="/api/settings", tags=["settings"])

# ===== 静态文件（使用 BASE_PATH 计算） =====
frontend_path = os.path.join(BASE_PATH, 'frontend-web')

if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")
    
    @app.get("/")
    async def get_index():
        index_file = os.path.join(frontend_path, "index.html")
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
else:
    print(f"警告: frontend-web 目录不存在，请确认路径: {frontend_path}")

# ===== WebSocket 和调度器 =====
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

# ===== 直接运行入口（方便开发调试） =====
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
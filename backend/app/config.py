import os
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

class Settings:
    # 数据库：改为 backend/data/app.db
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./backend/data/app.db")

    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    ZHIPU_API_KEY: str = os.getenv("ZHIPU_API_KEY", "")
    ZHIPU_BASE_URL: str = os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
    DEFAULT_MODEL_ZHIPU: str = os.getenv("DEFAULT_MODEL_ZHIPU", "glm-4-flash")

    SILICONFLOW_API_KEY: str = os.getenv("SILICONFLOW_API_KEY", "")
    SILICONFLOW_BASE_URL: str = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
    DEFAULT_MODEL_SILICON: str = os.getenv("DEFAULT_MODEL_SILICON", "Qwen/Qwen2.5-7B-Instruct")

    DEFAULT_MODEL_LOCAL_QWEN: str = os.getenv("DEFAULT_MODEL_LOCAL_QWEN", "qwen:7b")
    DEFAULT_MODEL_LOCAL_DEEPSEEK: str = os.getenv("DEFAULT_MODEL_LOCAL_DEEPSEEK", "deepseek-r1:7b")

settings = Settings()
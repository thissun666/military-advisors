import os
import json
import time
from typing import Dict, Optional, List, Any
from pydantic import BaseModel, Field
from fastapi import HTTPException
import httpx
import asyncio
from ..utils.file_utils import read_json, write_json
from ..config import settings

# ========== 服务商 → Base URL 映射（硬编码，不依赖配置文件） ==========
PROVIDER_BASE_URLS = {
    "zhipu": "https://open.bigmodel.cn/api/paas/v4",
    "siliconflow": "https://api.siliconflow.cn/v1",
    "ollama": "http://localhost:11434",
    "kimi": "https://api.moonshot.cn/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "volcano": "https://ark.cn-beijing.volces.com/api/v3",
    "qwen": "https://dashscope.aliyuncs.com/api/v1",
}

# ---------- 模型服务基类 ----------
class LLMService:
    def __init__(self, config: Dict):
        self.config = config
        self.client = httpx.AsyncClient(timeout=30.0)

    async def generate(self, prompt: str, **kwargs) -> str:
        raise NotImplementedError

    async def close(self):
        await self.client.aclose()


# ---------- 智谱服务 ----------
class ZhipuService(LLMService):
    async def generate(self, prompt: str, **kwargs) -> str:
        api_key = self.config.get("api_key")
        if not api_key or api_key.startswith("****"):
            raise HTTPException(status_code=401, detail="智谱 API Key 未配置或已脱敏")

        url = f"{PROVIDER_BASE_URLS['zhipu']}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.config.get("model", "glm-4-flash"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "top_p": 0.9
        }

        try:
            response = await self.client.post(url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"智谱调用失败: {str(e)}")


# ---------- 硅基流动服务 ----------
class SiliconFlowService(LLMService):
    async def generate(self, prompt: str, **kwargs) -> str:
        api_key = self.config.get("api_key")
        if not api_key or api_key.startswith("****"):
            raise HTTPException(status_code=401, detail="硅基 API Key 未配置或已脱敏")

        url = f"{PROVIDER_BASE_URLS['siliconflow']}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.config.get("model", "Qwen/Qwen2.5-7B-Instruct"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "top_p": 0.9
        }

        try:
            response = await self.client.post(url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"硅基流动调用失败: {str(e)}")


# ---------- Ollama 服务 ----------
class OllamaService(LLMService):
    async def generate(self, prompt: str, **kwargs) -> str:
        base_url = self.config.get("base_url", PROVIDER_BASE_URLS["ollama"])
        model = self.config.get("model", "qwen2.5:3b")

        url = f"{base_url}/api/generate"
        data = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9
            }
        }

        try:
            response = await self.client.post(url, json=data)
            response.raise_for_status()
            result = response.json()
            return result["response"]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ollama 调用失败: {str(e)}")


# ---------- Kimi 服务（新增） ----------
class KimiService(LLMService):
    async def generate(self, prompt: str, **kwargs) -> str:
        api_key = self.config.get("api_key")
        if not api_key or api_key.startswith("****"):
            raise HTTPException(status_code=401, detail="Kimi API Key 未配置或已脱敏")

        url = f"{PROVIDER_BASE_URLS['kimi']}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.config.get("model", "moonshot-v1-8k"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "top_p": 0.9
        }

        try:
            response = await self.client.post(url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Kimi 调用失败: {str(e)}")


# ---------- 军师模型映射配置 ----------
class AdvisorModelMapping(BaseModel):
    zhuge_liang: str = "zhipu"
    si_ma_yi: str = "siliconflow"
    zhou_yu: str = "ollama"
    xun_yu: str = "ollama"

    detailed_mapping: Dict[str, str] = {
        "zhou_yu": "ollama:deepseek-r1:1.5b",
        "xun_yu": "ollama:qwen2.5:3b"
    }


def get_advisor_model_mapping():
    """读取军师模型映射配置（优先读取运行时配置，不存在则使用默认）"""
    config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "config")
    mapping_path = os.path.join(config_dir, "advisor_model_mapping.json")
    
    try:
        mapping = read_json(mapping_path)
        if mapping and "detailed_mapping" in mapping:
            return AdvisorModelMapping(**mapping)
    except Exception as e:
        print(f"[LLM Service] 读取军师模型映射失败，使用默认: {e}")

    return AdvisorModelMapping(
        detailed_mapping={
            "zhou_yu": "ollama:deepseek-r1:1.5b",
            "xun_yu": "ollama:qwen2.5:3b"
        }
    )


def save_advisor_model_mapping(mapping: AdvisorModelMapping):
    """保存军师模型映射到文件"""
    config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "config")
    mapping_path = os.path.join(config_dir, "advisor_model_mapping.json")
    try:
        write_json(mapping_path, mapping.dict())
    except Exception as e:
        print(f"[LLM Service] 保存军师模型映射失败: {e}")


def get_advisor_model_config(advisor_id: str, mapping: AdvisorModelMapping):
    """根据军师ID获取模型配置（支持同一后端不同模型）"""
    if advisor_id in mapping.detailed_mapping:
        parts = mapping.detailed_mapping[advisor_id].split(':', 2)
        if len(parts) >= 2:
            backend_id = parts[0]
            model_name = parts[1] if len(parts) == 2 else parts[1] + ':' + parts[2]
            return backend_id, model_name

    default_mapping = {
        "zhuge_liang": "zhipu",
        "si_ma_yi": "siliconflow",
        "zhou_yu": "ollama",
        "xun_yu": "ollama"
    }
    backend_id = default_mapping.get(advisor_id, "ollama")
    return backend_id, None


# ---------- 主 LLM 获取函数 ----------
def get_llm(advisor_id: str, config: Dict, mapping: AdvisorModelMapping):
    """
    根据军师ID获取LLM实例（支持同一后端不同模型）
    """
    backend_id, model_name = get_advisor_model_config(advisor_id, mapping)
    
    backend_config = config.get(backend_id)
    if not backend_config:
        raise ValueError(f"未找到后端配置: {backend_id}")

    if model_name:
        backend_config = backend_config.copy()
        backend_config["model"] = model_name

    # 根据服务商创建对应的服务实例
    if backend_id == "zhipu":
        return ZhipuService(backend_config)
    elif backend_id == "siliconflow":
        return SiliconFlowService(backend_config)
    elif backend_id == "ollama":
        return OllamaService(backend_config)
    elif backend_id == "kimi":
        return KimiService(backend_config)
    elif backend_id == "deepseek":
        # DeepSeek 使用 OpenAI 兼容接口，可复用 Zhipu 的逻辑但改 base_url
        # 暂未实现，可以先返回错误
        raise ValueError(f"服务商 {backend_id} 暂未实现")
    else:
        raise ValueError(f"不支持的LLM后端: {backend_id}")


# ---------- 对话历史管理 ----------
class MemoryService:
    def __init__(self, session_id: int, topic_id: int):
        self.session_id = session_id
        self.topic_id = topic_id
        self.base_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "data", "sessions", f"session_{session_id}", f"topic_{topic_id}"
        )
        os.makedirs(self.base_dir, exist_ok=True)

    def save_message(self, role: str, content: str):
        file_path = os.path.join(self.base_dir, "all_messages.json")
        try:
            messages = []
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    messages = json.load(f)
            
            messages.append({
                "role": role,
                "content": content,
                "timestamp": time.time()
            })
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Memory Service] 保存消息失败: {e}")

    def save_system_message(self, content: str):
        self.save_message("system", content)

    def get_full_conversation(self) -> List[Dict]:
        file_path = os.path.join(self.base_dir, "all_messages.json")
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"[Memory Service] 读取对话历史失败: {e}")
        return []


# ========== 对外接口 ==========
def get_llm_instance(advisor_id: str, config: Dict):
    mapping = get_advisor_model_mapping()
    return get_llm(advisor_id, config, mapping)


def get_conversation_history(session_id: int, topic_id: int) -> List[Dict]:
    memory = MemoryService(session_id, topic_id)
    return memory.get_full_conversation()


# ========== 向后兼容：保留 call_model 函数 ==========
async def call_model_async(advisor_id: str, prompt: str) -> str:
    config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "config")
    config_path = os.path.join(config_dir, "model_config.json")
    config = read_json(config_path)
    
    if not config or "providers" not in config:
        config = {
            "providers": {
                "zhipu": {
                    "api_key": settings.ZHIPU_API_KEY,
                    "base_url": PROVIDER_BASE_URLS["zhipu"],
                    "model": settings.DEFAULT_MODEL_ZHIPU
                },
                "siliconflow": {
                    "api_key": settings.SILICONFLOW_API_KEY,
                    "base_url": PROVIDER_BASE_URLS["siliconflow"],
                    "model": settings.DEFAULT_MODEL_SILICON
                },
                "ollama": {
                    "api_key": "",
                    "base_url": PROVIDER_BASE_URLS["ollama"],
                    "model": settings.DEFAULT_MODEL_LOCAL_QWEN
                }
            }
        }
    
    mapping = get_advisor_model_mapping()
    
    try:
        llm = get_llm(advisor_id, config["providers"], mapping)
        response = await llm.generate(prompt)
        return response
    except Exception as e:
        print(f"[call_model] 调用失败: {e}")
        try:
            fallback_config = config["providers"].get("ollama", {
                "base_url": PROVIDER_BASE_URLS["ollama"],
                "model": settings.DEFAULT_MODEL_LOCAL_QWEN
            })
            fallback_llm = OllamaService(fallback_config)
            return await fallback_llm.generate(prompt)
        except Exception as e2:
            print(f"[call_model] 备用调用也失败: {e2}")
            return "主公，我的信号不好，请稍后再问。"


def call_model(advisor_id: str, prompt: str) -> str:
    try:
        loop = asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, call_model_async(advisor_id, prompt))
            return future.result(timeout=60)
    except RuntimeError:
        return asyncio.run(call_model_async(advisor_id, prompt))
    except Exception as e:
        print(f"[call_model] 同步调用失败: {e}")
        return "主公，我的信号不好，请稍后再问。"


def get_llm_instance_sync(advisor_id: str, config: Dict):
    mapping = get_advisor_model_mapping()
    return get_llm(advisor_id, config, mapping)
import json
from typing import List, Dict
from .llm_service import call_model
from .memory_service import load_memory

def generate_summary(session_id: int, topic_id: int, topic_question: str) -> str:
    """
    生成议题的总结报告，包含各方观点和综合建议。
    """
    advisors = ["诸葛亮", "司马懿", "周瑜", "荀彧"]
    advisor_views = {}
    for adv in advisors:
        memories = load_memory(session_id, topic_id, adv, limit=5)
        if memories:
            advisor_views[adv] = "；".join(memories)
        else:
            advisor_views[adv] = "（未发言）"

    # 构建提示词，让模型生成总结
    prompt = f"""请根据以下军师对议题“{topic_question}”的观点，生成一份简洁的总结报告（200字以内），包括：
1. 各方主要观点（简要概括）
2. 共识与分歧
3. 综合建议

各军师观点：
"""
    for adv, view in advisor_views.items():
        prompt += f"{adv}：{view}\n"

    try:
        summary = call_model("zhuge_liang", prompt)  # 用诸葛亮做总结
        # 如果结果过长，截断
        if len(summary) > 500:
            summary = summary[:500] + "..."
        return summary
    except Exception as e:
        # 降级：直接拼接
        fallback = f"议题：{topic_question}\n\n"
        for adv, view in advisor_views.items():
            fallback += f"{adv}：{view}\n"
        fallback += "\n（自动生成总结失败，以上为原始观点）"
        return fallback
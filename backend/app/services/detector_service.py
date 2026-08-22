import json
from .llm_service import call_model

def check_agreement(text1: str, text2: str) -> tuple:
    """
    检测两段发言是否观点对立。
    返回：(是否对立, 理由)
    """
    prompt = f"""请判断以下两段发言的观点是否明显对立（即直接冲突或相反）。只回答"是"或"否"，并给出简要理由。

发言1：{text1}
发言2：{text2}

输出格式（JSON）：
{{"opposed": true/false, "reason": "简要理由"}}"""
    
    try:
        response = call_model("zhou_yu", prompt)  # 使用本地模型
        result = json.loads(response)
        return result.get("opposed", False), result.get("reason", "")
    except:
        return False, "分析失败"

def check_relevance(speech: str, topic: str) -> tuple:
    """
    检测发言是否偏题。
    返回：(是否偏题, 理由)
    """
    prompt = f"""请判断以下发言是否与议题相关。如果发言明显偏离议题，回答"是"，否则"否"，并给出简要理由。

议题：{topic}
发言：{speech}

输出格式（JSON）：
{{"irrelevant": true/false, "reason": "简要理由"}}"""
    try:
        response = call_model("zhou_yu", prompt)
        result = json.loads(response)
        return result.get("irrelevant", False), result.get("reason", "")
    except:
        return False, "分析失败"

def check_convergence(memory_list: list) -> tuple:
    """
    检测观点是否重复（收束检测）。
    输入：某个军师的最近若干条记忆（字符串列表）
    返回：(是否重复, 重复度评分 0-1)
    """
    if len(memory_list) < 2:
        return False, 0.0
    # 使用简单的文本相似度（实际可调用模型判断语义重复）
    # 这里先用 Jaccard 相似度作为快速判断
    from collections import Counter
    def get_keywords(text):
        # 简单分词（中文按字符），去掉停用词
        import re
        words = re.findall(r'[\u4e00-\u9fa5a-zA-Z]+', text)
        # 去除常见停用词
        stopwords = {'的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '来'}
        return [w for w in words if w not in stopwords]
    
    # 取最近两条记忆的关键词
    kw1 = set(get_keywords(memory_list[-2]))
    kw2 = set(get_keywords(memory_list[-1]))
    if not kw1 or not kw2:
        return False, 0.0
    intersection = len(kw1 & kw2)
    union = len(kw1 | kw2)
    similarity = intersection / union if union > 0 else 0.0
    # 如果相似度超过 0.7，认为重复
    return similarity > 0.7, similarity
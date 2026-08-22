ROLE_DESCRIPTIONS = {
    "诸葛亮": "你是一位战略家，擅长全局规划和长远布局，思考问题全面且有深度。",
    "司马懿": "你是一位风险管控专家，思维谨慎，善于发现潜在隐患和制定应对策略。",
    "周瑜": "你是一位行动派，果断高效，注重执行力和快速响应。",
    "荀彧": "你是一位稳健规划者，步步为营，注重细节和资源配置。"
}

def build_initial_prompt(advisor: str, question: str) -> str:
    role = ROLE_DESCRIPTIONS.get(advisor, "你是一位军师。")
    return f"""{role}
主公提出议题：{question}
请给出你的初步见解。要求：
1. 先明确提出你的观点（论点）。
2. 然后给出1-2个支撑理由（论据），言简意赅。
3. 回复控制在150字以内。

你的回答："""

def build_review_prompt(advisor: str, question: str, other_views: dict) -> str:
    """传入 other_views 排除自己的观点"""
    role = ROLE_DESCRIPTIONS.get(advisor, "你是一位军师。")
    views_text = "\n".join([f"{name}：{view}" for name, view in other_views.items()])
    return f"""{role}
议题：{question}
其他军师的观点如下（不包含你自己）：
{views_text}

请对其他军师的观点进行判断。**你必须至少反驳其中一位军师的观点，或指出一个被忽略的重要角度。**
要求：
1. 明确说出你反驳谁（具体名字），并给出你的理由（论点+论据）。
2. 如果你认为所有观点都合理，也必须补充一个你认为被忽略的关键点。
3. 回复控制在150字以内。

你的回答："""

def build_summary_prompt(advisor: str, question: str, views: dict, reviews: dict) -> str:
    role = ROLE_DESCRIPTIONS.get(advisor, "你是一位军师。")
    views_text = "\n".join([f"{name}：{view}" for name, view in views.items()])
    reviews_text = "\n".join([f"{name}：{review}" for name, review in reviews.items()])
    return f"""{role}
议题：{question}
各位军师的初步观点：
{views_text}

各位军师互相点评：
{reviews_text}

请总结以上讨论：
1. 列出所有军师的共识（共同认可的观点）。
2. 列出所有军师的分歧（不同观点）。
3. 最后以亲切的语气询问主公的看法（例如"主公，您怎么看？"）。
回复控制在200字以内。

你的回答："""
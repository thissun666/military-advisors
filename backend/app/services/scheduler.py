import asyncio
from typing import Dict
from .memory_service import save_memory, save_message
from .llm_service import call_model
from ..websocket_manager import manager
from .prompt_builder import build_initial_prompt, build_review_prompt, build_summary_prompt

ADVISOR_DISPLAY = ["诸葛亮", "司马懿", "周瑜", "荀彧"]
ADVISOR_IDS = ["zhuge_liang", "si_ma_yi", "zhou_yu", "xun_yu"]
DISPLAY_TO_ID = dict(zip(ADVISOR_DISPLAY, ADVISOR_IDS))

class Scheduler:
    def __init__(self, session_id: int, topic_id: int):
        self.session_id = session_id
        self.topic_id = topic_id
        self.is_active = False
        self.user_question = ""
        self.round = 0
        self.views = {}
        self.reviews = {}

    def reset(self, user_question: str):
        self.user_question = user_question
        self.round = 0
        self.views = {}
        self.reviews = {}
        self.is_active = True

    async def run(self):
        try:
            while self.is_active:
                print(f"[Scheduler] 当前轮次: {self.round}, views: {len(self.views)}, reviews: {len(self.reviews)}")
                if self.round == 0:
                    await self._phase_initial_views()
                elif self.round == 1:
                    await self._phase_reviews()
                elif self.round == 2:
                    await self._phase_summary_and_ask()
                    break
                else:
                    print("[Scheduler] 未知轮次，结束")
                    break
        except Exception as e:
            print(f"[Scheduler] 运行异常: {e}")
            import traceback
            traceback.print_exc()
            self.is_active = False

    async def _call_model_with_retry(self, advisor_id: str, prompt: str, max_retries: int = 2) -> str:
        for attempt in range(max_retries + 1):
            try:
                reply = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, call_model, advisor_id, prompt),
                    timeout=30  # 增加到30秒，适应本地模型首次加载
                )
                return reply
            except asyncio.TimeoutError:
                print(f"[Scheduler] {advisor_id} 超时 (尝试 {attempt+1}/{max_retries+1})")
                if attempt == max_retries:
                    return "主公，我的信号不好，请稍后再问。"
            except Exception as e:
                print(f"[Scheduler] {advisor_id} 调用失败: {e} (尝试 {attempt+1}/{max_retries+1})")
                if attempt == max_retries:
                    return "主公，我的信号不好，请稍后再问。"
                await asyncio.sleep(1)
        return "主公，我的信号不好，请稍后再问。"

    async def _phase_initial_views(self):
        print("[Scheduler] === 第一阶段：初步观点 ===")
        for display in ADVISOR_DISPLAY:
            if not self.is_active:
                print("[Scheduler] 调度已停止")
                return
            advisor_id = DISPLAY_TO_ID[display]
            prompt = build_initial_prompt(display, self.user_question)
            await manager.send_message(self.session_id, self.topic_id, {
                "type": "advisor_start",
                "advisor_name": display
            })
            print(f"[Scheduler] 调用 {display}...")
            reply = await self._call_model_with_retry(advisor_id, prompt)
            print(f"[Scheduler] {display} 回复: {reply[:30]}...")
            
            is_success = (reply != "主公，我的信号不好，请稍后再问。")
            
            if is_success:
                self.views[display] = reply
                save_message(self.session_id, self.topic_id, "advisor", reply, display)
                print(f"[Scheduler] {display} 观点已保存")
            else:
                save_message(self.session_id, self.topic_id, "advisor", reply, display)
                await manager.send_message(self.session_id, self.topic_id, {
                    "type": "system",
                    "content": f"⚠️ {display} 暂时无法联系，已跳过。"
                })
                print(f"[Scheduler] {display} 失败，已跳过")
            
            await manager.send_message(self.session_id, self.topic_id, {
                "type": "advisor_message",
                "advisor_name": display,
                "content": reply
            })
            await asyncio.sleep(0.5)
        
        if not self.views:
            print("[Scheduler] 所有军师均无法发言，结束讨论")
            await self._close_discussion("所有军师均无法发言，讨论结束。")
            return
        
        self.round = 1
        print(f"[Scheduler] 第一阶段完成，views: {list(self.views.keys())}")

    async def _phase_reviews(self):
        print("[Scheduler] === 第二阶段：互相点评 ===")
        if not self.views:
            print("[Scheduler] 没有观点，跳过点评")
            self.round = 2
            return
        
        if len(self.views) <= 1:
            print("[Scheduler] 只有一位军师有观点，跳过点评")
            self.round = 2
            return
        
        for display in ADVISOR_DISPLAY:
            if not self.is_active:
                print("[Scheduler] 调度已停止")
                return
            advisor_id = DISPLAY_TO_ID[display]
            other_views = {name: view for name, view in self.views.items() if name != display}
            if not other_views:
                continue
            
            print(f"[Scheduler] {display} 点评其他 {len(other_views)} 位军师...")
            prompt = build_review_prompt(display, self.user_question, other_views)
            await manager.send_message(self.session_id, self.topic_id, {
                "type": "advisor_start",
                "advisor_name": display
            })
            reply = await self._call_model_with_retry(advisor_id, prompt)
            
            is_success = (reply != "主公，我的信号不好，请稍后再问。")
            
            if is_success:
                self.reviews[display] = reply
                save_message(self.session_id, self.topic_id, "advisor", reply, display)
                print(f"[Scheduler] {display} 点评已保存")
            else:
                save_message(self.session_id, self.topic_id, "advisor", reply, display)
                await manager.send_message(self.session_id, self.topic_id, {
                    "type": "system",
                    "content": f"⚠️ {display} 暂时无法联系，已跳过。"
                })
                print(f"[Scheduler] {display} 点评失败，已跳过")
            
            await manager.send_message(self.session_id, self.topic_id, {
                "type": "advisor_message",
                "advisor_name": display,
                "content": reply
            })
            await asyncio.sleep(0.5)
        
        self.round = 2
        print(f"[Scheduler] 第二阶段完成，reviews: {list(self.reviews.keys())}")

    async def _phase_summary_and_ask(self):
        print("[Scheduler] === 第三阶段：总结 ===")
        if not self.views:
            await self._close_discussion("由于军师未提供有效观点，讨论结束。")
            return
        
        advisor = "诸葛亮"
        advisor_id = DISPLAY_TO_ID[advisor]
        prompt = build_summary_prompt(advisor, self.user_question, self.views, self.reviews)
        await manager.send_message(self.session_id, self.topic_id, {
            "type": "advisor_start",
            "advisor_name": advisor
        })
        
        print(f"[Scheduler] {advisor} 总结中...")
        reply = await self._call_model_with_retry(advisor_id, prompt)
        save_message(self.session_id, self.topic_id, "advisor", reply, advisor)
        
        if reply == "主公，我的信号不好，请稍后再问。":
            # 降级方案：手动生成总结
            print("[Scheduler] 模型总结失败，使用降级方案")
            fallback_summary = f"议题：{self.user_question}\n\n"
            fallback_summary += "各位军师初步观点：\n"
            for name, view in self.views.items():
                fallback_summary += f"- {name}：{view[:50]}...\n"
            if self.reviews:
                fallback_summary += "\n各位军师互相点评：\n"
                for name, review in self.reviews.items():
                    fallback_summary += f"- {name}：{review[:50]}...\n"
            fallback_summary += "\n主公，您怎么看？"
            reply = fallback_summary
            save_message(self.session_id, self.topic_id, "advisor", reply, advisor)
        
        await manager.send_message(self.session_id, self.topic_id, {
            "type": "advisor_message",
            "advisor_name": advisor,
            "content": reply
        })
        
        await manager.send_message(self.session_id, self.topic_id, {
            "type": "ask_lord",
            "content": "主公，您怎么看？"
        })
        self.is_active = False
        print("[Scheduler] 第三阶段完成，等待主公输入")

    async def _close_discussion(self, reason: str):
        from .summary_service import generate_summary
        summary = generate_summary(self.session_id, self.topic_id, self.user_question)
        full_summary = f"讨论结束。{reason}\n\n{summary}"
        await manager.send_message(self.session_id, self.topic_id, {
            "type": "topic_closed",
            "summary": full_summary
        })
        self.is_active = False
        print(f"[Scheduler] 讨论关闭: {reason}")
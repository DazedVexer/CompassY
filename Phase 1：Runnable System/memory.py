from config import MAX_SHORT_TERM_TURNS

class ShortTermMemory:
    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt
        self.history: list[dict] = []

    def add_user_message(self, content: str):
        self.history.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str):
        self.history.append({"role": "assistant", "content": content})

    def get_messages(self) -> list[dict]:
        # 返回完整 messages 列表，包含 system prompt + 最近 N 轮
        recent = self.history[-(MAX_SHORT_TERM_TURNS * 2):]
        return [{"role": "system", "content": self.system_prompt}] + recent

    def get_summary(self) -> str:
        # 返回当前对话的简要摘要（用于 session 元数据）
        user_msgs = [m["content"] for m in self.history if m["role"] == "user"]
        return " > ".join(user_msgs[-3:])
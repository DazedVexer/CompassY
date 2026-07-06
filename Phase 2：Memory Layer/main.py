from config import validate_config
from prompt_builder import sys_prompt_builder
from llm_client import chat_stream
from session_manger import create_session, save_message
from short_term_memory import ShortTermMemory
from memory_manager import MemoryManager
from long_term_memory import init_db, get_memory_count

def main():
    validate_config()                                           # 验证 .env 配置

    init_db()                                                   # 创建/连接 SQLite 记忆库
    mem_count = get_memory_count()                              # 获取长期记忆条数

    print("[Polaris] 正在加载规则...")
    system_prompt = sys_prompt_builder()                        # 加载规则 Prompt

    memory = ShortTermMemory(system_prompt)                     # 创建短期记忆盒子

    session_file = create_session()                             # 创建 session JSON 文件
    session_id = session_file.stem                              # .stem去掉文件扩展名（后缀），只保留文件名主体            

    mem_mgr = MemoryManager(memory, session_id)                 # 创建记忆管家

    print(f"[Polaris] Session 已创建：{session_file.name}")
    if mem_count > 0:
        print(f"[Polaris] 已加载 {mem_count} 条长期记忆")

    BANNER = r"""
      ┌──────────────────────────────────────┐
      │             Polaris  v2.0            │
      │   Personal AI Executive Assistant    │
      │        Phase 2 · Memory Layer        │
      └──────────────────────────────────────┘
    """
    print("\n" + "=" * 50)
    print(BANNER)
    print("输入 /exit 退出  |  /save 手动存档  |  /help 查看帮助")
    print("=" * 50 + "\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input:
            continue
        if user_input.lower() == "/exit":
            break
        if user_input.lower() == "/save":
            print(f"[Polaris] 当前 session 已自动保存至 {session_file.name}")
            continue

        # 记录用户消息
        memory.add_user_message(user_input)
        save_message(session_file, "user", user_input)

        # 检索并注入长期记忆
        memory_context = mem_mgr.inject_memory_context(user_input)
        temp_extra = []
        if memory_context:
            temp_extra.append({
                "role": "system",
                "content": memory_context,
            })

        # 调用 LLM
        try:
            messages = memory.get_messages()
            full_messages = [messages[0]] + temp_extra + messages[1:]
            print("Polaris: ", end="", flush=True)
            response = chat_stream(full_messages)
        except Exception as e:
            response = f"[错误] LLM 调用失败：{e}"
            print(f"\n{response}")
            save_message(session_file, "system", response)
            memory.add_assistant_message(response)
            save_message(session_file, "assistant", response)
            mem_mgr.maybe_extract()
            mem_mgr.maybe_summarize()
            continue

        # 记录 AI 回复
        memory.add_assistant_message(response)
        save_message(session_file, "assistant", response)

        # 对话后触发记忆提取和总结
        mem_mgr.maybe_extract()
        mem_mgr.maybe_summarize()

    print(f"\n[Polaris] 对话结束。Session 已保存至 sessions/{session_file.name}")
    print(f"[Polaris] 记忆库中共有 {get_memory_count()} 条长期记忆")


if __name__ == "__main__":
    try:
        main()
    except ValueError as e:
        print(e)
    except KeyboardInterrupt:
        print()

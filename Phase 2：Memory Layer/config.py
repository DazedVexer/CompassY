import os            
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).parent                        # 项目根目录
RULES_DIR = BASE_DIR / "rules"                          # Rules 规则文档路径
SESSIONS_DIR = BASE_DIR / "sessions"                    # Session 存档路径

LTM_DB_PATH = BASE_DIR / "polaris_memory.db"            # SQLite 数据库文件路径

load_dotenv(BASE_DIR / ".env", override=True)           # 加载 .env 配置（覆盖系统环境变量）
LLM_CONFIG = {
    "api_key": os.getenv("OPENAI_API_KEY"),
    "base_url": os.getenv("OPENAI_BASE_URL"),
    "model": os.getenv("OPENAI_MODEL"),
    "temperature": 0.7,
    "max_tokens": 2000,
}

def validate_config():                                  # 启动配置校验
    errors = []
    if not LLM_CONFIG["api_key"]:
        errors.append("OPENAI_API_KEY 未设置，请在 .env 中配置")
    if not LLM_CONFIG["base_url"]:
        errors.append("OPENAI_BASE_URL 未设置")
    if not LLM_CONFIG["model"]:
        errors.append("OPENAI_MODEL 未设置")
    if errors:
        raise ValueError("\n".join(["\n❌ 配置错误："] + errors))

STM_WindowSize = 10                                     # 短期记忆最大轮数
STM_SUMMARY_TRIGGER = 18                                # 短期记忆中积累超过此轮数时，触发自动总结

LTM_RETRIEVAL_K = 5                                     # 记忆检索：每次对话最多从 LTM 中取 K 条相关记忆

LLM_MEMORY_EXTRACTION = 5                               # 记忆提取：每 N 轮对话后触发一次 LLM 提取记忆
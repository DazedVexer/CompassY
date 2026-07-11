import os            
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).parent                        # 项目根目录
RULES_DIR = BASE_DIR / "rules"                          # Rules 规则文档路径
SESSIONS_DIR = BASE_DIR / "sessions"                    # Session 存档路径

LTM_DB_PATH = BASE_DIR / "polaris_memory.db"            # SQLite 数据库文件路径

load_dotenv(BASE_DIR / ".env", override=True)           # 加载 .env 配置（覆盖系统环境变量）
LLM_CONFIG = {
    "api_key": os.getenv("OPENAI_API_KEY"),             # OpenAI API 密钥
    "base_url": os.getenv("OPENAI_BASE_URL"),           # OpenAI API 基础 URL
    "model": os.getenv("OPENAI_MODEL"),                 # OpenAI 模型
    "temperature": 0.7,                                 # 温度参数（0~1，0 表示确定性，1 表示随机性）
    "max_tokens": 2000,                                 # 最大生成 token 数
}

def validate_config():                                  # 启动配置校验
    errors = []                                         # 错误信息列表
    if not LLM_CONFIG["api_key"]:
        errors.append("OPENAI_API_KEY 未设置，请在 .env 中配置")
    if not LLM_CONFIG["api_key"]:
        errors.append("OPENAI_API_KEY 未设置，请在 .env 中配置")
    if not LLM_CONFIG["base_url"]:
        errors.append("OPENAI_BASE_URL 未设置")
    if not LLM_CONFIG["model"]:
        errors.append("OPENAI_MODEL 未设置")
    if errors:
        raise ValueError("\n".join(["\n❌ 配置错误："] + errors))  # 抛出配置错误异常

STM_WindowSize = 10                                     # 短期记忆最大轮数 <short_term_memory.py>
STM_SUMMARY_TRIGGER = 18                                # 短期记忆中积累超过此轮数时，触发自动总结 <short_term_memory.py>

LTM_RETRIEVAL_K = 5                                     # 记忆检索：每次对话最多从 LTM 中取 K 条相关记忆 <long_term_memory.py>

LLM_MEMORY_EXTRACTION = 5                               # 记忆提取：每 N 轮对话后触发一次 LLM 提取记忆 <long_term_memory.py>

# ========================
# Phase 3：RAG 知识系统配置
# ========================

# ---- Embedding ----
# 可选值: "openai" 或 "bge"
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "openai")

# OpenAI Embedding 模型（provider=openai 时生效）
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# bge 本地模型名（provider=bge 时生效）
# 可选: "BAAI/bge-small-zh-v1.5" / "BAAI/bge-base-zh-v1.5" / "BAAI/bge-large-zh-v1.5"
BGE_MODEL_NAME = os.getenv("BGE_MODEL_NAME", "BAAI/bge-small-zh-v1.5")

# ---- 向量数据库 ----
# 可选值: "chroma" 或 "faiss"
VECTOR_DB_PROVIDER = os.getenv("VECTOR_DB_PROVIDER", "chroma")

# Chroma 持久化目录
CHROMA_PERSIST_DIR = BASE_DIR / "chroma_db"

# FAISS 索引文件路径
FAISS_INDEX_PATH = BASE_DIR / "faiss_index.bin"
FAISS_META_PATH = BASE_DIR / "faiss_meta.json"

# 向量相似度阈值（0~1，低于此值的结果不返回）
VECTOR_SIMILARITY_THRESHOLD = 0.65

# 记忆检索 TOP_K
MEMORY_RETRIEVAL_TOP_K = 5

# ---- 知识库 ----
# 知识库文档目录（用户把 .md / .pdf 放这里）
KB_DIR = BASE_DIR / "kb"

# 文档分块参数
CHUNK_SIZE = 500          # 每块最多 500 字符
CHUNK_OVERLAP = 50        # 相邻块重叠 50 字符

# 知识库检索 TOP_K
KB_RETRIEVAL_TOP_K = 3

# ========================
# Phase 4：Agent 配置
# ========================

# Agent 最大执行步数（防止无限循环）
AGENT_MAX_STEPS = 10

# 单步超时（秒）
AGENT_STEP_TIMEOUT = 120

# 是否启用反思（Reflection）
AGENT_REFLECTION_ENABLED = True

# 反思最大重试次数
AGENT_MAX_RETRIES = 3

# LLM 温度（规划用低温度确保稳定，执行用中温度保持灵活）
AGENT_PLAN_TEMPERATURE = 0.2
AGENT_EXECUTE_TEMPERATURE = 0.6
AGENT_REFLECT_TEMPERATURE = 0.3

# 最大上下文传递长度（字符，防止步骤间上下文膨胀）
AGENT_MAX_CONTEXT_LENGTH = 3000

# ========================
# Phase 5：工具系统配置
# ========================

# ---- API Keys ----
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# ---- 工具开关 ----
# 可单独禁用某个工具（设 False 则该工具不会注册）
TOOLS_ENABLED = {
    "weather": bool(OPENWEATHER_API_KEY),       # 有 API Key 才启用
    "github": bool(GITHUB_TOKEN),
    "filesystem": True,                          # 本地文件操作默认启用
}

# 文件系统工具的安全根目录（只允许在此目录下操作）
FILESYSTEM_SAFE_ROOT = str(BASE_DIR)

# 文件读取的大小限制（字节）
FILESYSTEM_MAX_READ_SIZE = 100 * 1024  # 100KB

# ========================
# Phase 6：服务器 / Web 配置
# ========================

# FastAPI 服务器配置
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
SERVER_RELOAD = os.getenv("SERVER_RELOAD", "false").lower() == "true"

# CORS 允许的前端地址（开发环境通常是 http://localhost:5173）
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

# API 认证（简单 Token，非生产级）
API_TOKEN = os.getenv("API_TOKEN", "")

# 前端资源目录
WEB_DIR = BASE_DIR / "web" / "dist"

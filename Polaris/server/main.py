"""
Polaris Web Server — FastAPI 入口
启动方式：
  python -m server.main
  或
  uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
"""

import sys
from pathlib import Path

# 确保项目根目录在 Python 路径中
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from config import WEB_DIR, SERVER_HOST, SERVER_PORT

# 导入 API 路由
from server.api.chat import router as chat_router
from server.api.memory import router as memory_router
from server.api.knowledge import router as knowledge_router
from server.api.tools import router as tools_router
from server.middleware import setup_middleware
from server.models import HealthResponse

# 创建 FastAPI 应用
app = FastAPI(
    title="Polaris API",
    description="Personal AI Executive Assistant — API",
    version="6.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 注册中间件
setup_middleware(app)

# 注册路由
app.include_router(chat_router)
app.include_router(memory_router)
app.include_router(knowledge_router)
app.include_router(tools_router)


# ====== 健康检查 ======

@app.get("/health", response_model=HealthResponse)
async def health():
    total_memories = 0
    total_tools = 0
    try:
        from memory.long_term_memory import get_memory_count
        from tools.tool_registry import get_tool_registry
        total_memories = get_memory_count()
        total_tools = len(get_tool_registry().list_tools())
    except Exception:
        pass

    return HealthResponse(
        status="ok",
        version="6.0.0",
        tools_count=total_tools,
        memory_count=total_memories,
    )


# ====== 静态文件（前端） ======

if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="frontend")


# ====== 启动入口 ======

if __name__ == "__main__":
    import uvicorn
    from tools import register_all_tools
    from memory.long_term_memory import init_db

    # 初始化 Phase 2~5 的核心模块
    print("[Polaris Server] 正在初始化...")
    init_db()

    try:
        register_all_tools()
    except Exception as e:
        print(f"[Polaris Server] 工具初始化警告：{e}")

    print(f"[Polaris Server] 启动于 http://{SERVER_HOST}:{SERVER_PORT}")
    print(f"[Polaris Server] API 文档：http://{SERVER_HOST}:{SERVER_PORT}/docs")

    uvicorn.run(
        "server.main:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=True,
        log_level="info",
    )

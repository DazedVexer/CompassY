import sqlite3
from config import LTM_DB_PATH

def _get_connection() -> sqlite3.Connection:
    """获取数据库连接（自动创建文件）"""
    conn = sqlite3.connect(str(LTM_DB_PATH))                            # 连接SQLite数据库文件，如果文件不存在，则创建一个
    conn.row_factory = sqlite3.Row                                      # 让查询结果返回 sqlite3.Row 对象
    return conn

def init_db():
    """初始化数据库表（程序启动时调用一次）—— 升级版"""
    conn = _get_connection()                                            # 获取一个数据库连接
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            content     TEXT    NOT NULL,
            category    TEXT    DEFAULT 'general',
            importance  TEXT    DEFAULT 'medium',
            source      TEXT    DEFAULT 'llm_extracted',
            session_id  TEXT,
            embedding   TEXT,
            created_at  TEXT    DEFAULT (datetime('now', 'localtime'))
        )
    """)                                                                # 列名，数据类型，约束/默认值

    """
        PRIMARY KEY：        主键，唯一标识每一行，不能重复
        AUTOINCREMENT：      自动递增，插入时不用手动填
        DEFAULT 'general'：  如果你插入时不填 category，自动填入 'general'
    """

    # BangBand：情绪时间线表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mood_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            mood         TEXT    NOT NULL,
            intensity    TEXT    DEFAULT 'medium',
            intent       TEXT    DEFAULT 'chatting',
            context      TEXT,
            session_id   TEXT,
            created_at   TEXT    DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # BangBand：用户画像表（支持 UPSERT 的持续更新档案）
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_profile (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            section      TEXT    NOT NULL UNIQUE,
            content      TEXT    NOT NULL,
            updated_at   TEXT    DEFAULT (datetime('now', 'localtime'))
        )
    """)

    conn.commit()                                                       # 提交事务，将所有变更写入数据库
    conn.close()                                                        # 关闭数据库连接，释放资源

    # Phase 3 迁移：确保 embedding 列存在（兼容老数据库）
    _ensure_embedding_column()

def add_memory(content: str, category: str = "general",
               importance: str = "medium", source: str = "llm_extracted",
               session_id: str = None) -> int:
    """插入一条记忆，返回记忆 ID"""
    conn = _get_connection()
    cursor = conn.execute(
        """INSERT INTO memories (content, category, importance, source, session_id)
           VALUES (?, ?, ?, ?, ?)""",
        (content.strip(), category, importance, source, session_id)
    )
    conn.commit()
    memory_id = cursor.lastrowid
    conn.close()
    return memory_id


def search_memories(query: str, limit: int = 5) -> list[dict]:
    """关键词模糊搜索记忆"""
    conn = _get_connection()
    keywords = query.strip().split()
    if not keywords:
        conn.close()
        return []

    conditions = " OR ".join(["content LIKE ?" for _ in keywords])
    params = [f"%{kw}%" for kw in keywords]

    cursor = conn.execute(
        f"""SELECT id, content, category, importance, created_at
            FROM memories
            WHERE {conditions}
            ORDER BY created_at DESC
            LIMIT ?""",
        params + [limit]
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_recent_memories(limit: int = 20) -> list[dict]:
    """获取最近存入的记忆"""
    conn = _get_connection()
    cursor = conn.execute(                                              # 创建游标 cursor 并执行 SQL
        """SELECT id, content, category, importance, created_at
           FROM memories
           ORDER BY created_at DESC
           LIMIT ?""",                                                  # '?'作占位符被(limit,)替代
        (limit,)
    )
    rows = cursor.fetchall()                                            # fetchall()获取所有查询结果
    conn.close()
    return [dict(row) for row in rows]                                  # 将查询结果转换为字典列表，每个字典对应一行数据


def delete_memory(memory_id: int):
    """删除指定记忆"""
    conn = _get_connection()
    conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
    conn.commit()
    conn.close()


def get_memory_count() -> int:
    """返回记忆总数"""
    conn = _get_connection()
    cursor = conn.execute("SELECT COUNT(*) FROM memories")
    count = cursor.fetchone()[0]
    conn.close()
    return count


# ========================
# Phase 3 新增：Embedding 支持
# ========================

def _ensure_embedding_column():
    """确保 memories 表有 embedding 列（从 Phase 2 升级时自动添加）"""
    conn = _get_connection()
    cursor = conn.execute("PRAGMA table_info(memories)")
    columns = [row[1] for row in cursor.fetchall()]
    if "embedding" not in columns:
        conn.execute("ALTER TABLE memories ADD COLUMN embedding TEXT")
        conn.commit()
    conn.close()


def add_memory_with_embedding(
    content: str,
    category: str = "general",
    importance: str = "medium",
    source: str = "llm_extracted",
    session_id: str = None,
) -> int:
    """
    插入一条记忆，同时自动生成 embedding 并存储。
    这是 Phase 3 推荐的记忆写入方式。
    """
    from llm.embedding import embed_single
    import json

    conn = _get_connection()

    # 生成 embedding
    try:
        vec = embed_single(content)
        embedding_json = json.dumps(vec) if vec else None
    except Exception:
        embedding_json = None  # embedding 失败不阻塞记忆写入

    cursor = conn.execute(
        """INSERT INTO memories (content, category, importance, source, session_id, embedding)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (content.strip(), category, importance, source, session_id, embedding_json)
    )
    conn.commit()
    memory_id = cursor.lastrowid
    conn.close()

    # 同步写入向量数据库
    if vec:
        _sync_to_vector_db(memory_id, content, vec, category, importance, source, session_id)

    return memory_id


def _sync_to_vector_db(memory_id: int, content: str, vec: list[float],
                       category: str, importance: str, source: str, session_id: str):
    """将记忆向量同步写入向量数据库"""
    try:
        from retrieval.vector_store import VectorStore
        store = VectorStore("memories")
        store.add(
            ids=[str(memory_id)],
            vectors=[vec],
            metadatas=[{
                "content": content,
                "category": category,
                "importance": importance,
                "source": source,
                "session_id": session_id or "",
                "memory_id": memory_id,
            }],
        )
    except Exception:
        pass  # 向量库写入失败不影响主流程


def search_memories_by_vector(
    query: str,
    top_k: int = 5,
    category_filter: str = None,
) -> list[dict]:
    """
    Phase 3 核心检索方法：用 embedding 做语义搜索。

    参数:
        query: 用户输入的查询文本
        top_k: 返回最多 K 条
        category_filter: 可选，按分类过滤（如 "learning"）

    返回:
        [{"id": 1, "content": "...", "score": 0.93, ...}, ...]
    """
    from llm.embedding import embed_single
    from retrieval.vector_store import VectorStore

    store = VectorStore("memories")

    if store.count() == 0:
        # 向量库为空，fallback 到关键词搜索
        return search_memories(query, limit=top_k)

    # 生成查询 embedding
    query_vec = embed_single(query)
    if not query_vec:
        return search_memories(query, limit=top_k)

    # 向量相似度搜索
    filter_meta = None
    if category_filter:
        filter_meta = {"category": category_filter}

    results = store.search(query_vec, top_k=top_k, filter_meta=filter_meta)

    # 组装返回格式（兼容旧代码）
    output = []
    for r in results:
        meta = r["metadata"]
        output.append({
            "id": meta.get("memory_id", 0),
            "content": meta.get("content", ""),
            "category": meta.get("category", "general"),
            "importance": meta.get("importance", "medium"),
            "score": r["score"],
        })
    return output


def rebuild_embedding_column():
    """
    给所有没有 embedding 的旧记忆批量生成 embedding。
    Phase 2 升级到 Phase 3 时调用一次。
    """
    from llm.embedding import embed

    conn = _get_connection()
    cursor = conn.execute(
        "SELECT id, content FROM memories WHERE embedding IS NULL OR embedding = ''"
    )
    rows = cursor.fetchall()

    if not rows:
        conn.close()
        print("[Polaris] 所有记忆已有 embedding，无需重建。")
        return

    print(f"[Polaris] 正在为 {len(rows)} 条记忆生成 embedding...")

    # 分批处理，每批 20 条（避免一次发太多给 API）
    batch_size = 20
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        texts = [row["content"] for row in batch]
        try:
            vectors = embed(texts)
        except Exception as e:
            print(f"[Polaris] embedding 生成失败（第 {i} 批）: {e}")
            continue

        for row, vec in zip(batch, vectors):
            import json
            vec_json = json.dumps(vec)
            conn.execute(
                "UPDATE memories SET embedding = ? WHERE id = ?",
                (vec_json, row["id"])
            )

        conn.commit()
        print(f"[Polaris] 已完成 {min(i + batch_size, len(rows))}/{len(rows)}")

    conn.close()
    print("[Polaris] embedding 重建完成。")


def sync_all_to_vector_db():
    """
    将 SQLite 中所有有 embedding 的记忆同步到向量数据库。
    适用于首次迁移或向量库损坏后重建。
    """
    import json
    from retrieval.vector_store import VectorStore

    conn = _get_connection()
    cursor = conn.execute(
        """SELECT id, content, category, importance, source, session_id, embedding
           FROM memories WHERE embedding IS NOT NULL AND embedding != ''"""
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("[Polaris] 没有需要同步的记忆。")
        return

    print(f"[Polaris] 正在同步 {len(rows)} 条记忆到向量数据库...")

    store = VectorStore("memories")
    batch_size = 50
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        ids = []
        vectors = []
        metadatas = []
        for row in batch:
            try:
                vec = json.loads(row["embedding"])
            except (json.JSONDecodeError, TypeError):
                continue
            ids.append(str(row["id"]))
            vectors.append(vec)
            metadatas.append({
                "content": row["content"],
                "category": row["category"],
                "importance": row["importance"],
                "source": row["source"],
                "session_id": row["session_id"] or "",
                "memory_id": row["id"],
            })
        if ids:
            store.add(ids=ids, vectors=vectors, metadatas=metadatas)

    print(f"[Polaris] 同步完成，向量库中现有 {store.count()} 条记忆。")


# ========================
# BangBand 新增：情绪追踪 & 用户画像
# ========================

def log_mood(mood: str, intensity: str, intent: str,
             context: str, session_id: str):
    """记录一条情绪日志（静默，不打印）。每轮对话后由 memory_manager 调用。"""
    conn = _get_connection()
    conn.execute(
        """INSERT INTO mood_log (mood, intensity, intent, context, session_id)
           VALUES (?, ?, ?, ?, ?)""",
        (mood, intensity, intent, context[:300] if context else "", session_id)
    )
    conn.commit()
    conn.close()


def upsert_profile(section: str, content: str):
    """
    更新或插入用户画像的某个 section。
    如果该 section 已存在则更新内容，否则插入新行。
    """
    conn = _get_connection()
    conn.execute(
        """INSERT INTO user_profile (section, content, updated_at)
           VALUES (?, ?, datetime('now', 'localtime'))
           ON CONFLICT(section) DO UPDATE SET
               content = excluded.content,
               updated_at = excluded.updated_at""",
        (section, content)
    )
    conn.commit()
    conn.close()


def get_recent_mood(limit: int = 5) -> list[dict]:
    """获取最近的情绪记录，用于注入对话上下文。"""
    conn = _get_connection()
    cursor = conn.execute(
        """SELECT mood, intensity, intent, context, created_at
           FROM mood_log
           ORDER BY created_at DESC
           LIMIT ?""",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows][::-1]  # 反转，按时间正序返回


def get_profile() -> dict:
    """获取完整用户画像，返回 {section: content} 字典。"""
    conn = _get_connection()
    cursor = conn.execute(
        "SELECT section, content FROM user_profile ORDER BY updated_at DESC"
    )
    rows = cursor.fetchall()
    conn.close()
    return {row["section"]: row["content"] for row in rows}


def get_mood_count() -> int:
    """返回情绪日志总数。"""
    conn = _get_connection()
    cursor = conn.execute("SELECT COUNT(*) FROM mood_log")
    count = cursor.fetchone()[0]
    conn.close()
    return count

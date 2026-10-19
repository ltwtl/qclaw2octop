#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
qclaw2octop.py — QClaw Agent 迁移到 Octop 的通用工具（跨机可用）

用法总览：
  python qclaw2octop.py inventory  --qclaw-home ~/.qclaw --agent-id agent-xxxxxxxx
  python qclaw2octop.py copy-configs --package <迁移包目录> --workspace <Octop专家工作区> \
      --path-map "旧工作区路径=新工作区路径" [--path-map ...]
  python qclaw2octop.py import-sessions --octop-home ~/.octop --db <octop.db路径> \
      --sessions-dir <jsonl目录> --agent-id <Octop专家ID> --user-id 1
  python qclaw2octop.py replicate-sidebar --db <octop.db路径> \
      --sessions-json <QClaw sessions.json路径> --agent-id <Octop专家ID> [--keep-prefix]

所有步骤只读 QClaw 源文件；写 Octop 前自动备份数据库。可重复执行（幂等）。
"""
import argparse, json, os, random, re, shutil, sqlite3, sys, time, uuid

# ============================================================ 工具函数
_CROCK = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

def ulid(ts_ms=None):
    ts = int(ts_ms if ts_ms is not None else time.time() * 1000)
    bits = (ts & ((1 << 48) - 1)) << 80 | random.getrandbits(80)
    return "".join(_CROCK[(bits >> (125 - 5 * i)) & 31] for i in range(26))

RE_SENDER = re.compile(r"Sender \(untrusted metadata\):\s*```json\s*.*?```\s*", re.S)
RE_MEM = re.compile(r"<relevant-memories>.*?</relevant-memories>\s*", re.S)
RE_TS = re.compile(r"^\[[A-Za-z]{3} \d{4}-\d{2}-\d{2} \d{2}:\d{2} GMT\+\d+\]\s*")

def clean_user_text(t):
    """剥离 QClaw 注入的元数据头 / 记忆注入块 / 时间戳前缀，保留用户正文。"""
    for _ in range(3):
        t2 = RE_MEM.sub("", t)
        t2 = RE_SENDER.sub("", t2)
        if t2 == t:
            break
        t = t2
    return RE_TS.sub("", t).strip()

def backup_db(db_path):
    bak = f"{db_path}.bak-{time.strftime('%Y%m%d-%H%M%S')}"
    src, dst = sqlite3.connect(db_path), sqlite3.connect(bak)
    src.backup(dst); dst.close(); src.close()
    print(f"[backup] 数据库已备份: {bak}")

# ============================================================ 1) inventory
def cmd_inventory(a):
    ws = os.path.join(a.qclaw_home, f"workspace-{a.agent_id}")
    sess = os.path.join(a.qclaw_home, "agents", a.agent_id, "sessions")
    print(f"== QClaw Agent 资产盘点: {a.agent_id} ==\n")
    core = ["SOUL.md", "USER.md", "IDENTITY.md", "MEMORY.md", "AGENTS.md", "TOOLS.md", "HEARTBEAT.md"]
    print("[工作区配置]")
    for name in core:
        p = os.path.join(ws, name)
        print(f"  {'✓' if os.path.isfile(p) else '✗'} {name}")
    mem = os.path.join(ws, "memory")
    if os.path.isdir(mem):
        print(f"  ✓ memory/ ({len(os.listdir(mem))} 文件)")
    print("\n[会话]")
    if os.path.isdir(sess):
        mains = [f for f in os.listdir(sess)
                 if f.endswith(".jsonl") and ".trajectory" not in f and ".checkpoint." not in f]
        total = sum(os.path.getsize(os.path.join(sess, f)) for f in mains)
        print(f"  主会话 {len(mains)} 个 / {total/1e6:.1f} MB（已排除 trajectory 调试文件与 checkpoint 副本）")
        sj = os.path.join(sess, "sessions.json")
        if os.path.isfile(sj):
            with open(sj, encoding="utf-8") as f:
                meta = json.load(f)
            labeled = [v for v in meta.values() if (v.get("label") or "").strip()]
            print(f"  sessions.json: {len(meta)} 条目，其中正式入口（有标题）{len(labeled)} 个")
    print("\n[技能] 请人工确认专属技能目录（通常在 <qclaw-home>/skills/<技能名>/）")

# ============================================================ 2) copy-configs
VERBATIM = ["SOUL.md", "USER.md", "IDENTITY.md", "MEMORY.md", "HEARTBEAT.md"]

def cmd_copy_configs(a):
    pkg, ws = a.package, a.workspace
    maps = []
    for pm in a.path_map or []:
        old, _, new = pm.partition("=")
        if old and new:
            maps.append((old, new))
    def fix(s):
        for old, new in maps:
            s = s.replace(old, new)
        return s
    cfg = os.path.join(pkg, "01_Agent配置")
    for name in VERBATIM:
        src = os.path.join(cfg, name)
        if os.path.isfile(src):
            with open(src, encoding="utf-8") as f:
                content = fix(f.read())
            with open(os.path.join(ws, name), "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            print(f"  ✓ {name}")
    # AGENTS.md = QClaw 原文 + TOOLS.md 并入 + 目标平台原文
    parts = []
    qa = os.path.join(cfg, "AGENTS.md")
    if os.path.isfile(qa):
        with open(qa, encoding="utf-8") as f:
            parts.append(fix(f.read()).rstrip())
    tl = os.path.join(cfg, "TOOLS.md")
    if os.path.isfile(tl):
        with open(tl, encoding="utf-8") as f:
            parts.append("---\n\n## 工具配置与限制（原 TOOLS.md 逐字并入）\n\n" + fix(f.read()).strip())
    oa = os.path.join(ws, "AGENTS.md")
    if os.path.isfile(oa):
        with open(oa, encoding="utf-8") as f:
            parts.append("---\n\n## 目标平台工作区约定\n\n" + f.read().strip())
    with open(oa, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n\n".join(parts) + "\n")
    print("  ✓ AGENTS.md（QClaw 原文 + TOOLS.md + 平台约定）")
    # 其余目录
    for src_rel, dst_rel in [
        (os.path.join("01_Agent配置", ".learnings"), ".learnings"),
        ("02_记忆与连续性", "memory"),
        ("03_系统配置", os.path.join("archive", "qclaw-系统配置")),
    ]:
        src, dst = os.path.join(pkg, src_rel), os.path.join(ws, dst_rel)
        if not os.path.isdir(src):
            continue
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        # 文本文件做路径替换
        for root, _, fs in os.walk(dst):
            for fn in fs:
                if fn.endswith((".py", ".md", ".json", ".txt")):
                    p = os.path.join(root, fn)
                    with open(p, encoding="utf-8", errors="ignore") as f:
                        s = f.read()
                    s2 = fix(s)
                    if s2 != s:
                        with open(p, "w", encoding="utf-8", newline="\n") as f:
                            f.write(s2)
        n = sum(len(fs) for _, _, fs in os.walk(dst))
        print(f"  ✓ {dst_rel}（{n} 文件）")
    # 专属技能
    sk_src_root = os.path.join(pkg, "04_专属技能")
    if os.path.isdir(sk_src_root):
        for slug in os.listdir(sk_src_root):
            src, dst = os.path.join(sk_src_root, slug), os.path.join(ws, "skills", slug)
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            print(f"  ✓ skills/{slug}")
    print("\n完成。请在 Octop 中重启客户端或执行 agent reload。")

# ============================================================ 3) import-sessions
def extract_messages(path):
    msgs, skipped = [], 0
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("type") != "message":
                continue
            m = d.get("message", {})
            role, ts_ms, content = m.get("role"), m.get("timestamp"), m.get("content")
            if role == "user":
                text = "\n".join(p.get("text", "") for p in content
                                 if isinstance(p, dict) and p.get("type") == "text") if isinstance(content, list) else (content or "")
                text = clean_user_text(text)
                if text:
                    msgs.append(("human", text, ts_ms))
                else:
                    skipped += 1
            elif role == "assistant":
                text = "\n".join(p.get("text", "") for p in content
                                 if isinstance(p, dict) and p.get("type") == "text") if isinstance(content, list) else (content or "")
                text = text.strip()
                if text:
                    msgs.append(("ai", text, ts_ms))
                else:
                    skipped += 1
            else:
                skipped += 1
    return msgs, skipped

def wire(role, text):
    mid = ("lc_run--" if role == "ai" else "") + str(uuid.uuid4())
    data = {"content": text, "additional_kwargs": {}, "response_metadata": {},
            "type": role, "name": None, "id": mid}
    if role == "ai":
        data.update({"tool_calls": [], "invalid_tool_calls": [], "usage_metadata": None})
    return mid, json.dumps({"type": role, "data": data}, ensure_ascii=False)

def cmd_import_sessions(a):
    backup_db(a.db)
    con = sqlite3.connect(a.db, timeout=30)
    con.execute("PRAGMA busy_timeout=30000")
    existing = {r[0] for r in con.execute("SELECT session_key FROM sessions")}
    files = sorted(f for f in os.listdir(a.sessions_dir) if f.endswith(".jsonl"))
    n_thr = n_msg = 0
    for fn in files:
        sess_uuid = fn[:-6]
        skey = f"{a.agent_id}:imported:{sess_uuid}:dm"
        if skey in existing:
            continue
        msgs, _ = extract_messages(os.path.join(a.sessions_dir, fn))
        if not msgs:
            continue
        first_ts = next((m[2] for m in msgs if m[2]), int(time.time() * 1000))
        last_ts = next((m[2] for m in reversed(msgs) if m[2]), first_ts)
        title_src = next((m[1] for m in msgs if m[0] == "human"), msgs[0][1])
        tid = "thr_" + ulid(first_ts)
        con.execute("INSERT INTO threads (thread_id, agent_id, user_id, channel_type, session_key, title, pinned, last_active, created_at) VALUES (?,?,?,?,?,?,0,?,?)",
                    (tid, a.agent_id, a.user_id, "dashboard", skey, "🗂 " + title_src.replace("\n", " ")[:36], last_ts // 1000, first_ts // 1000))
        con.execute("INSERT INTO sessions (session_key, agent_id, user_id, channel_type, chat_type, thread_id, updated_at, unread_count) VALUES (?,?,?,?,?,?,?,0)",
                    (skey, a.agent_id, a.user_id, "dashboard", "dm", tid, last_ts // 1000))
        con.execute("INSERT INTO thread_history_projection (thread_id, status, updated_at) VALUES (?,?,?)",
                    (tid, "ready", first_ts // 1000))
        for seq, (role, text, ts_ms) in enumerate(msgs, 1):
            mid, mj = wire(role, text)
            con.execute("INSERT INTO thread_messages (thread_id, seq, message_id, role, message_json, created_at) VALUES (?,?,?,?,?,?)",
                        (tid, seq, mid, role, mj, (ts_ms or first_ts) // 1000))
        n_thr += 1
        n_msg += len(msgs)
        print(f"  ✓ {sess_uuid[:13]} → {len(msgs)} 条")
    con.commit(); con.close()
    print(f"\n导入完成: {n_thr} 个会话窗口 / {n_msg} 条消息")

# ============================================================ 4) replicate-sidebar
def cmd_replicate_sidebar(a):
    with open(a.sessions_json, encoding="utf-8") as f:
        meta = json.load(f)
    keep = {}
    for v in meta.values():
        sid, label = v.get("sessionId"), (v.get("label") or "").strip()
        label = re.sub(r"\s*\[[a-z0-9]{6}\]\s*$", "", label).strip()
        if sid and label:
            keep[sid] = label
    backup_db(a.db)
    con = sqlite3.connect(a.db, timeout=30)
    con.execute("PRAGMA busy_timeout=30000")
    prefix = "🗂 " if a.keep_prefix else ""
    kept = removed = 0
    for tid, skey in con.execute(
            "SELECT thread_id, session_key FROM threads WHERE session_key LIKE ?",
            (f"{a.agent_id}:imported:%",)).fetchall():
        sess_uuid = skey.split(":")[2]
        if sess_uuid in keep:
            con.execute("UPDATE threads SET title=? WHERE thread_id=?", (prefix + keep[sess_uuid][:60], tid))
            kept += 1
        else:
            for table, col in [("thread_messages", "thread_id"), ("thread_history_projection", "thread_id"),
                               ("threads", "thread_id"), ("sessions", "thread_id")]:
                con.execute(f"DELETE FROM {table} WHERE {col}=?", (tid,))
            removed += 1
    con.commit(); con.close()
    print(f"保留并复名 {kept} 个正式入口，清理 {removed} 个非入口窗口（原文档案不受影响）")

# ============================================================ main
def main():
    p = argparse.ArgumentParser(description="QClaw → Octop 迁移工具")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("inventory", help="盘点 QClaw Agent 资产")
    sp.add_argument("--qclaw-home", required=True)
    sp.add_argument("--agent-id", required=True)
    sp.set_defaults(fn=cmd_inventory)

    sp = sub.add_parser("copy-configs", help="复制配置/记忆/技能到 Octop 专家工作区")
    sp.add_argument("--package", required=True, help="迁移包根目录")
    sp.add_argument("--workspace", required=True, help="Octop 专家工作区（~/.octop/agents/<id>）")
    sp.add_argument("--path-map", action="append", help="路径替换，格式 旧=新，可多次")
    sp.set_defaults(fn=cmd_copy_configs)

    sp = sub.add_parser("import-sessions", help="会话 jsonl 导入 Octop 数据库（恢复会话窗口）")
    sp.add_argument("--db", required=True, help="octop.db 路径")
    sp.add_argument("--sessions-dir", required=True, help="主会话 jsonl 目录（剔除 trajectory/checkpoint）")
    sp.add_argument("--agent-id", required=True)
    sp.add_argument("--user-id", type=int, default=1)
    sp.set_defaults(fn=cmd_import_sessions)

    sp.add_argument and None
    sp = sub.add_parser("replicate-sidebar", help="按 QClaw 侧栏正式入口复刻窗口列表")
    sp.add_argument("--db", required=True)
    sp.add_argument("--sessions-json", required=True, help="QClaw sessions.json 路径")
    sp.add_argument("--agent-id", required=True)
    sp.add_argument("--keep-prefix", action="store_true", help="保留 🗂 导入标记前缀")
    sp.set_defaults(fn=cmd_replicate_sidebar)

    a = p.parse_args()
    a.fn(a)

if __name__ == "__main__":
    main()

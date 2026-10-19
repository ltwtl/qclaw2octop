---
name: qclaw2octop
description: 把 QClaw 上的个人 Agent 完整迁移到 Octop 并完全复刻。触发词：「迁移 QClaw」「QClaw 搬家」「QClaw 转 Octop」「恢复会话窗口」「复刻 Agent」。覆盖：人格配置（SOUL/USER/MEMORY 等 MD 文件逐字复制）、记忆日记、专属技能、会话内容导入 Octop 数据库恢复会话窗口、按 QClaw 侧栏复刻会话入口列表。全程只读源数据、写库前自动备份、幂等可重跑、支持跨机迁移。
---

# QClaw → Octop Agent 迁移技能

把一个 QClaw Agent 完整搬迁到 Octop：人格配置、记忆、技能、**会话窗口级恢复**、侧栏入口复刻。

## 何时使用

用户要把 QClaw 里的某个 Agent 搬到 Octop，或要求恢复/复刻 QClaw 的会话窗口时使用。

## 铁律（不可违反）

1. **只读源数据**：QClaw 的任何文件只做读取和复制，绝不修改删除
2. **写库先备份**：`import-sessions` / `replicate-sidebar` 已内置自动备份，不要绕过脚本直接写 octop.db
3. **决策先问人**：cron 是否重建、调试文件是否迁移、外部数据是否随包走等，先列清单让用户拍板（详见手册第 5 节）
4. **如实告知限制**：恢复的历史窗口能看能续聊，但模型上下文不自动延续（运行断点不可迁移）——必须提前说清楚

## 迁移流水线（六步）

完整细节、排障与原理见 `references/migration-guide.md`。**严格按顺序执行**：

### ① 盘点资产

```bash
python scripts/qclaw2octop.py inventory --qclaw-home "<QClaw数据目录>" --agent-id <源agent-id>
```

确认 7 个配置文件、memory/、专属技能、会话规模，并列出硬编码路径清单。

### ② 在 Octop 建专家

用 `default` 空白模板创建（用户自主设计的 Agent 不套用现成模板），记录返回的 6 位 `agent_id`：

```bash
# 桌面版/便携版（launch.py 等价于 python -m octop）
runtime/python.exe launch.py agent create "<Agent名>" --template default --user <用户名>
```

### ③ 复制配置 / 记忆 / 技能

```bash
python scripts/qclaw2octop.py copy-configs \
  --package "<迁移包目录>" \
  --workspace "<Octop数据目录>/agents/<agent_id>" \
  --path-map "旧工作区路径=<Octop数据目录>/agents/<agent_id>"
```

自动完成：5 个核心 MD 逐字复制 + AGENTS.md 三段合成（QClaw 原文 + TOOLS.md 并入 + 平台约定）+ 记忆/技能/归档脚本就位 + 路径替换。

### ④ 恢复会话窗口

```bash
python scripts/qclaw2octop.py import-sessions \
  --db "<Octop数据目录>/octop.db" \
  --sessions-dir "<主会话jsonl目录>" \
  --agent-id <agent_id> --user-id 1
```

前置：sessions 目录剔除 `*.trajectory.jsonl` 与 `*.checkpoint.*.jsonl`。脚本自动剥离 QClaw 注入的系统元数据。

### ⑤ 复刻侧栏入口

```bash
python scripts/qclaw2octop.py replicate-sidebar \
  --db "<Octop数据目录>/octop.db" \
  --sessions-json "<QClaw数据目录>/agents/<源agent-id>/sessions/sessions.json" \
  --agent-id <agent_id>
```

保留 QClaw 正式入口并恢复官方会话名，清理非入口窗口（原文档案不受影响）。

### ⑥ 验收（四项全过才算完成）

1. 人格：问一个只有该 Agent 才答得对的问题，核对答案与数据来源
2. 技能：说专属技能触发词，确认被调用
3. 窗口：重启客户端，侧栏与 QClaw 一致，历史消息完整可读
4. 续聊：在历史窗口发消息，能正常回复追加

## 交付时必须向用户说明

- 哪些是完全复刻（配置/记忆/技能/窗口内容/侧栏名称）
- 哪些是概念映射（注册条目、cron）
- 唯一的固有限制：历史窗口的上下文不自动延续，Agent 靠 MEMORY.md 与记忆检索了解过去

## 参考

- **完整操作手册**：`references/migration-guide.md`（跨机指南、回滚 SQL、FAQ）
- **核心工具**：`scripts/qclaw2octop.py`（零依赖，Python 3.10+）

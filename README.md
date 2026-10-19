# qclaw2octop — QClaw / OpenClaw → Octop Agent 迁移工具

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](scripts/qclaw2octop.py)
[![Zero Dependencies](https://img.shields.io/badge/Dependencies-Zero-brightgreen.svg)](#)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](#)

**把 QClaw / OpenClaw 上的个人 AI Agent 完整迁移到 Octop**：人格配置、长期记忆、专属技能，以及**会话窗口级恢复**与侧栏入口复刻。

**Migrate personal AI agents from QClaw / OpenClaw to Octop with full fidelity** — persona configs (SOUL/USER/MEMORY markdown), long-term memory, custom skills, plus conversation-window-level restoration and sidebar replication.

![Migration pipeline](docs/migration-pipeline.png)

## 为什么需要它 / Why

[QClaw](https://github.com/TencentCloud)（基于 OpenClaw 引擎）和 [Octop](https://github.com/TencentCloud/Octop) 都采用「每 Agent 一个工作区 + Markdown 人格文件」的架构，但**会话存储完全不同**：QClaw 用 jsonl 文件流，Octop 用 SQLite。本工具补齐了两者之间缺失的迁移桥梁，尤其是官方未提供的**会话历史恢复**能力。

Both QClaw (OpenClaw-based) and Octop use workspace + markdown persona files, but store conversations differently (jsonl files vs SQLite). This toolkit bridges the gap — including conversation history restoration, which no official tool covers.

## 特性 / Features

- ✅ **逐字复刻人格配置**：SOUL / USER / IDENTITY / MEMORY / HEARTBEAT 同名 MD 文件原样迁移
- ✅ **会话窗口复活**：jsonl 会话转换写入 Octop 数据库，历史对话以窗口形式重现
- ✅ **侧栏完全复刻**：按 QClaw `sessions.json` 官方入口与命名还原会话列表
- ✅ **长期记忆与日记**：memory/ 目录文件照搬
- ✅ **专属技能迁移**：skills/ 目录原样复制，触发词机制保持一致
- ✅ **只读源数据**：全程复制，QClaw 侧不动一个字节
- ✅ **安全可重跑**：写库前自动备份，幂等设计，随时可回滚
- ✅ **跨机迁移**：路径参数化，打包材料即可迁到另一台电脑
- ✅ **Agent 可自主执行**：自带 SKILL.md，可作为技能被 AI Agent 加载并自动完成迁移

## 快速开始 / Quick Start

```bash
# ① 盘点源 Agent 资产 / Inventory source agent assets
python scripts/qclaw2octop.py inventory --qclaw-home ~/.qclaw --agent-id agent-xxxxxxxx

# ② 在 Octop 建空白专家（记录返回的 agent_id）/ Create a blank expert in Octop

# ③ 复制配置 / 记忆 / 技能 / Copy configs, memory, skills
python scripts/qclaw2octop.py copy-configs --package <迁移包> --workspace ~/.octop/agents/<agent_id> --path-map "旧路径=新路径"

# ④ 恢复会话窗口 / Restore conversation windows
python scripts/qclaw2octop.py import-sessions --db ~/.octop/octop.db --sessions-dir <jsonl目录> --agent-id <agent_id>

# ⑤ 复刻侧栏入口 / Replicate sidebar entries
python scripts/qclaw2octop.py replicate-sidebar --db ~/.octop/octop.db --sessions-json ~/.qclaw/agents/<源agent-id>/sessions/sessions.json --agent-id <agent_id>
```

## 作为 Agent 技能使用 / Use as an Agent Skill

把本仓库放入 Agent 的技能目录（如 `skills/qclaw2octop/`），Agent 即可按 [SKILL.md](SKILL.md) 自主执行完整迁移流程。兼容 Octop 技能体系及任何支持 SKILL.md 约定的 Agent 平台。

Drop this repo into any agent's `skills/` directory — the agent will follow [SKILL.md](SKILL.md) to run the full migration autonomously.

## 文档 / Documentation

- 📖 [完整操作手册](references/migration-guide.md)：概念映射、决策清单、技术原理与限制、跨机指南、回滚方案、FAQ
- 🗺 [概念映射图](docs/concept-mapping.png)：QClaw 与 Octop 的概念对照

## 已知限制 / Known Limitations

恢复的历史会话窗口**能看、能续聊**，但模型上下文不自动延续（运行断点 checkpoint 不可迁移）。详见[手册](references/migration-guide.md)第 6 节。

Restored conversation windows are viewable and continuable, but the model context does not carry over automatically (runtime checkpoints are not portable).

## 要求 / Requirements

- Python 3.10+（零第三方依赖，仅标准库 / zero third-party dependencies）
- Octop ≥ v1.0.2b7

## License

[MIT](LICENSE) — 欢迎 Fork、二次开发、集成到你自己的 Agent 工具链。

---

**Keywords**: QClaw, OpenClaw, Octop, Tencent Cloud, agent migration, AI agent, personal AI assistant, conversation history restore, session migration, long-term memory, LangChain, SQLite, workspace migration, agent skills, local-first AI, 育儿 Agent, 个人助理迁移, 会话恢复, 智能体迁移

# 轻量化 GitHub 层与漏洞修复：交付报告

日期：2026-10-28。范围：推送到 GitHub 之后的流程（本地日常按 v2：知识库可在本地 `main` 直接 `save`，Issue/PR 可选）。

## 结果

| 项 | 状态 |
|---|---|
| dev `main` | `191275e`（批次 PR #49 合入），CI 绿 |
| vault `main` | `a3e4f03`（PR #25 合入，第一个按新流程直接合入 main 的 PR），CI 绿 |
| 部署 | 6 处副本各 347 个文件，`source_commit` = `191275e`，`--verify-only` 全部一致 |
| pre-push hook | 两仓库重装，调用已部署副本 `~/.agents/skills/research-wiki/wiki.py` 的 guard |
| 完整 pytest（dev main，含 local/r/compose） | 882 passed, 4 skipped |

## 已完成任务

| 任务 | PR | 内容 |
|---|---|---|
| 7 | dev #25 | 测试按 `RWIKI_VAULT_ROOT` → `config.json` → `DEV_ROOT.parent` 找 vault，worktree 中不再失败 |
| 9 | dev #26 | CI 按改动路径用 step 级 `if` 跳过 pytest/前端测试，检查始终上报；每周与手动全量 |
| — | dev #31 | `lint --ci` 对限制性许可模板缺失的 `code/` 报 LOCAL-ONLY（v2 推送后 vault CI 一直失败的原因） |
| — | vault #22 | 重新生成作者块字节基准（v2 未更新） |
| 1 | dev #38 | 运行入口从 `config.json` 的 `env` 段准备环境（代理、gh 路径）并统一 UTF-8；拒绝设置 `RWIKI_AGENT`、`GIT_DIR`、`PATH` 等变量 |
| 8 | dev #39 | pre-push hook 调用已部署副本的 guard，缺失时退回检出并警告 |
| 4 | dev #40 | `gh merge` 收尾中断后可重跑；`git worktree remove` 非交互；残留联接按 reparse 点删除；main 快进改用 `merge --ff-only origin/main` |
| 2 | dev #41 | 门禁接受 skipping；`rwiki/risk.py` 与 `gh tier`：按 base 上的 `.github/risk-tiers.json` 与 `--no-renames` 的改动路径计算 low/normal/high |
| 5 | dev #42 | worktree 中经联接的受限目录不再误报“验收记录已过期”与 spec.entry 越界；主检出快照不变 |
| 3 | dev #44 | 门禁按档判定：low CI 即合；normal 再要针对当前 head 的 pass 评审；high 再要 `owner-approved`（晚于针对 head 的最早评审），可由 base 规则 `high_requires_owner: false` 关闭 |
| 6 | dev #46 | GitHub Flow：`start-batch` 只建 Milestone，任务分支从 `origin/main` 切、PR 直接到 main，`close-batch` 只关 Milestone；`--repo` 与同名检测；“PR 须包含最新 main”门禁；旧批次兼容 |
| 10 | dev #48、vault #25 | 规则文档、两仓库风险规则文件（`high_requires_owner: false`）、AGENTS.md 两份逐字节一致 |
| 11 | — | 遗留 Issue 分诊（作者确认）：dev #8 关闭，dev #10 加 `blocked:v2`，vault #3–#13 加 `blocked:scp-paused`，dev #17 保留 |

每个 PR 都经 CI 与独立评审 agent。评审拦下的阻断问题都已修复后复审通过：改名绕过 high、PR 改/删规则自降档（#41）；`owner-approved` 只信提交者时间、可被旧标签放行（#44）。

## 作者决定

- 分支模型 GitHub Flow；评审按风险分级；CI 路径过滤。
- v2 已由另一会话直接推到两个 main（含 vault 的 `.agents/tasks/` 两份报告与 `.push-guard-allow` 豁免）；作者选择接受现状、不改写远端历史。
- 2026-10-28：高风险 PR 不再逐个征求作者确认 → 两仓库规则 `high_requires_owner: false`；high 仍需独立评审与 CI。

## 实测 CI 耗时（成功运行的中位数）

| 仓库 | 类型 | 次数 | 中位数 |
|---|---|---|---|
| dev | 任务 PR（含 pytest） | 18 | 14.9 分钟 |
| dev | 批次 PR | 3 | 13.8 分钟 |
| dev | push 到 main（路径过滤后只跑轻量） | 5 | 0.5 分钟 |
| vault | PR / push 到 main | 5 | 约 1.9 分钟 |

新流程下一个 dev 代码任务约 1 次全量 PR CI（约 15 分钟）+ 1 次 main 轻量检查（约 0.5 分钟）；纯文档任务（`review/**/*.md`、根目录 `*.md`）为 low 档，CI 只跑轻量、无需评审。原流程为任务 PR、批次 PR、main push 三次全量。

## 环境变更

- Codex 运行时（venv 底座）在 2026-10-28 00:26 自动更新时被删除且重装停在下载阶段。已安装官方 Python 3.12.10 到 `D:\Python312`（签名 Python Software Foundation，按用户安装，未改 PATH），`research-wiki` 与 `bio-python` 两个 venv 的 `pyvenv.cfg` 改指向它；原文件备份为同目录 `pyvenv.cfg.codex-runtime.bak`。

## 遗留与后续

- `owner-approved` 只是约定：单账号下 GitHub 无法区分作者与 agent；当前已由规则关闭。
- “最新 main”门禁只在判定时刻成立；判定与合并之间 main 前进不会被拦（无远端分支保护），由每周全量 CI 兜底。
- `start-batch` 跨仓库同名检测只读本机元数据。
- `lint --ci` 对受限页整页降级，受限模板 spec.json 损坏也会被报为 LOCAL-ONLY；可收窄为只降级涉及缺失目录的消息。
- worktree 联接放行只校验目标位置与页面，未要求目标属于同一仓库（需本机写权限才能利用）。
- `AGENTS.md` 中“三档都要求 PR 包含最新 main”应补“（base 为 main 的 PR）”；`github-workflow.md` 对 CI skipping 的描述可更准确。
- `test_vault_root.py` 用了 pytest 8.3 的 `__wrapped__`，升级 pytest 时复核。
- 本地残留：dev 分支 `task/lite-gh-T2-gate-tier`、`T4-merge-resume`、`T5-acceptance-junction` 与对应空 worktree 目录（以及 `task__v2-sync-dev-T1-v2-merge` 空目录）被已结束会话的终端占用；PR 已合并、Issue 已关闭，占用解除后重跑 `wiki.py gh merge 40/41/42` 补完。
- Codex 自身运行时仍未恢复（不再影响本项目）。

# github-structured-workflow 交付报告

本报告覆盖 spec `.kiro/specs/github-structured-workflow/` 的本地部分（任务 1–14）。网络阶段（任务 15）因本机没有 gh CLI 未执行；任务 16 依赖它，也未执行。

路径约定：`<dev>` = 开发仓库根（`E:\research-wiki\开发`），`<vault>` = 根仓库（`E:\research-wiki`），`<skill>` = `<dev>/staged/research-wiki`。逐步记录见 `E:\research-wiki-env\tmp\gsw\progress.md`。

## 已完成任务

| 任务 | 内容 |
|---|---|
| 1 | V5 基线（111 条未提交改动，blob 按磁盘原字节入对象库）；假 gh 与临时 git 仓库夹具 |
| 2–3 | `rwiki/push_guard.py`（规则分类、推送范围扫描、pre-push、GPL 忽略托管块、作者块字节基准）；`rwiki/writer_lock.py`（按 worktree 的写入锁） |
| 4 | `rwiki/ghflow.py` 封装与纯函数：gh/git 薄封装、私有仓库校验、分支命名、评审标记、Merge_Gate、Issue 正文、迁移标记 |
| 5 | config（push_guard/github、`--wiki-root` 覆盖）、store.save 分支策略与 trailer、cli `gh` 子命令组、`lint --ci`（LOCAL-ONLY） |
| 6 | `tools/deploy.py` 来源门禁、`--verify-only`、manifest `source_commit`/`source_tag` |
| 8 | 两仓库 `.gitattributes`、`.gitignore`、`.push-guard-allow`、CI、PR/Issue 模板；pytest `local` marker；`知识库/.protected-hashes.json` |
| 10 | gh 子命令：preflight、start-batch、start-task（含 `--worktree`）、finish-task、review、merge、close-batch、migrate-legacy、bootstrap、install-hook；历史构造（replay_filtered、snapshot_orphan、switch_to_main） |
| 12 | 规则文档（知识库/AGENTS.md、assets/AGENTS.md、SKILL.md、references/github-workflow.md）、根 README、launcher 传递 `RWIKI_WIKI_ROOT` |
| 13 | V5 分批提交（见下表）；`deploy.py --verify-only` 核对；`review/legacy-map.json` |
| 7/9/11/14 | 各 Checkpoint |

13 的收尾核对：

- 五个主题/misc 提交的文件集合与 v5-plan.json 一致，每个文件的 mode 与 blob 都等于基线；111 条基线条目恰被一个提交覆盖，无遗漏、无重复；`<dev>` 工作区干净。
- `chore(misc-20261023-26)` 含 32 个文件，全部在 `obsidian-neural-view/` 下：`.gitignore`、`LICENSE`、`NOTICE.md`、`PROVENANCE.md`、`README.md`、`licenses/MIT-legacy.txt`、`manifest.json`、`media/`（jellyfish.jpg/.mp4、orb.jpg/.mp4）、`package.json`、`package-lock.json`、`preview/`（index.html、main.jsx）、`scripts/`（build.mjs、preview-server.mjs）、`src/`（adapter.mjs、graph.mjs、main.jsx、native-open.mjs、ui/App.jsx、ui/overrides.css、vendor/ 下 NetworkCanvas.jsx、Scene.jsx、icons.jsx、neural.css、theme.js）、`tests-built/artifacts.test.mjs`、`tests/`（adapter、boundaries、native-open 三个 .test.mjs）。
- guard 干跑：dev master 历史 4 处 abs-path（codex/ 3 个文件、config.json）都在重放时去除，未处理项 0；模拟重放后的 main（14 个提交）0 命中；vault 快照模拟 930 个文件 0 命中。vault master 历史的 2466 处命中不进入推送范围，因为 vault 首推用无父快照，不推历史。
- `deploy.py --verify-only`：5 处副本 missing 34、different 11，全部是本特性文件，部署后会消失；另有 4 处副本残留 `references/tag-taxonomy.md`、`rwiki/categories.py`，这是本特性之前就有的旧文件。
- `review/legacy-map.json`：T1–T7、P1、P2、M1–M3、R1 共 13 项，remaining-gaps.md 缺口 12 项（11 个归 vault、1 个归 dev）；28 条证据的 sha256 与磁盘一致。
- 规格留档 `<vault>/文档/github-structured-workflow/` 三份与 `.kiro/specs` 逐字节相同（只在 vault 工作区，未提交）。

## 测试结果（Checkpoint 14，全部提交之后）

| 命令 | 结果 |
|---|---|
| `<skill>` 完整 `pytest`（含 local、r、compose） | 742 passed, 3 skipped, 1 warning（既有 starlette 弃用警告），1545 s |
| `<vault>/tools/tests` `pytest` | 3 passed |
| `wiki.py lint` | OK（仅既有 WARN） |
| `wiki.py gh preflight` | 未找到 gh CLI，按设计报错并提示安装页与 `gh auth login` |

## V5 提交（`<dev>` master，未推送）

| sha | 说明 | 文件数 |
|---|---|---|
| `26a8cc799b7ce38bd530c2416135782b5a2db149` | feat(方法族): 方法家族、实现清单与 LLM-Wiki 模式 | 46 |
| `f14ad0a7b221e0216da0687b9deb60b789f3746b` | feat(taxonomy/输入绑定): 方法分类与灵活输入绑定 | 14 |
| `72ce040fc02464cc01e4d82b4a334be9979cd321` | feat(最小运行闭包): 最小依赖独立模块与运行契约 | 3 |
| `90f4745f4a4b2d2c065c1587d237439f7e54ab8f` | feat(课题状态层): 跨领域课题复用闭环与课题状态层 | 16 |
| `9cf3f6e1dd6eef0f24c524433bb26bec95baee09` | chore(misc-20261023-26): Obsidian 神经图谱插件 | 32 |
| `7b7bd393d887c37ee8c91b95e6ebc9ae7c9817f0` | feat(github-workflow): GitHub 结构化工作流 | 45 |
| `ec7f210e4cc279102bd7059061398d8e73010729` | chore(repo): 仓库文件、CI 与模板，停止跟踪本机配置与 codex 记录 | 33 |
| `cfaa2357f670a6b0ec0063847251a55ae764dfc3` | chore(repo): .push-guard-allow 逐条登记历史中的测试/QA 文件绝对路径 | 1 |

本报告另以 `docs(review): github-structured-workflow 交付报告` 提交，位于上表之后。

## 网络阶段未执行的原因

`wiki.py gh preflight` 在本机找不到 gh CLI。按约束不自动安装依赖，所以任务 15（bootstrap、migrate-legacy、首个真实 PR、从 main 部署）全部没有执行。两仓库仍在 `master`，没有 remote，没有 pre-push hook，没有任何网络写。

## 用户后续步骤

以下命令中 `wiki.py` 指 `<skill>/wiki.py`，用平时的解释器运行。

1. 安装并登录 gh：`winget install GitHub.cli`，重开终端后 `gh auth login`。
2. `wiki.py gh preflight`：确认账号、owner、两仓库不存在或为 PRIVATE、待推送范围与 guard 结果无阻断；把账号与 owner 写进本机 `config.json` 的 `github` 段。
3. `wiki.py gh bootstrap`（不带 `--confirm`）：只读输出授权摘要（账号/组织、仓库名、private、待推送提交范围），核对无误后再决定授权。
4. `wiki.py gh bootstrap --confirm`：master 改名 `legacy/master`、构造并切到 `main`、装 pre-push hook、建私有仓库、推送、Label、deploy key 与 secret、分支保护探测。完成后核对两仓库可见性为 PRIVATE、主检出在 `main`、`画廊/`、`维护记录/`、`config.json`、`codex/` 仍在磁盘。
5. `wiki.py gh migrate-legacy --map <dev>/review/legacy-map.json --dry-run` 核对计划，再去掉 `--dry-run` 正式执行；重跑一次确认没有重复 Issue。
6. 首个 PR：dev 用 `start-batch`/`start-task` 提交迁移标记，vault 同样流程把 README 的远程地址与保护模式填实；两边都走 `finish-task` → CI → `review` → `merge` → `close-batch`。
7. 在 `<dev>` 检出已推送的 `main`，运行 `python tools/deploy.py <record> "<note>"`，确认来源门禁通过、manifest 有 `source_commit`、5 处副本哈希一致。

## 未执行项

- 任务 15.1–15.6（含可选的 15.5 CI 拦截验证 PR）。
- 任务 16：两仓库 `main` 上的 CI 绿检查、最终 `deploy.py --verify-only`。
- 独立代码审查尚未进行，需要另行安排。

## 剩余风险

- `RWIKI_BOOTSTRAP=1` 会放行本地门禁对 `main`/`project/*`/`ingest/*` 的直接推送限制（guard 内容扫描仍然生效）。GitHub 侧拿不到分支保护（403 → local 模式）时，只要设置这个变量就能绕过本地门禁。
- pre-push hook 调用的是当前检出中的 `wiki.py`。在旧分支或改坏的检出上推送时，hook 运行的就是那份代码。
- CI 跑在 `windows-latest`，中文路径（`知识库/`、`开发/` 等）在 runner 上的检出与 pytest 还没有真实验证过，首个 PR 时需要观察。
- vault 侧改动（`.gitignore`、`.gitattributes`、`.push-guard-allow`、`.github/`、`知识库/.gitignore` GPL 托管块、`.protected-hashes.json`、规则文档、README、launcher、`tools/deploy.py` 与测试、规格留档）都还在工作区，没有提交；bootstrap 的快照会把它们带进 vault 的 `main`，在此之前请勿丢弃。
- `cfaa2357` 这个 chore(repo) 提交在本地 amend 过一次。它从未推送，所以没有影响远端历史；之后的修改一律用新提交。

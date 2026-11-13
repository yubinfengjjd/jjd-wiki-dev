# github-structured-workflow 交付报告

本报告覆盖 spec `.kiro/specs/github-structured-workflow/` 的全部任务（1–16）。任务 1–14 为本地部分；任务 15–16（网络阶段与最终检查）已于 2026-10-27 完成，见“网络阶段”。

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

## 网络阶段（任务 15–16）

仓库：`yubinfengjjd/jjd-wiki-dev`（dev）、`yubinfengjjd/jjd-wiki`（vault），均为 PRIVATE，默认分支 `main`。免费私有仓库的分支保护 API 返回 403，两者均为本地门禁模式（`protection: local`），pre-push hook 已安装。

| 任务 | 结果 |
|---|---|
| 15.1 preflight | gh 2.103 已认证；发现两处不兼容（空列表输出、`deploy-key add` 不再有 `--read-only`），经 dev PR #2 修复 |
| 15.2 bootstrap | 两仓库已建并首推；dev 为过滤重放历史，vault 为单次快照 |
| 15.3 migrate-legacy | dry-run 25 项；正式执行建 dev Issue #4–#17、vault Issue #3–#13，T5、T7 与 12 个缺口保持打开；14 个任务书文件加迁移标记（dev PR #18）；重跑 25 项均为 none，无重复 |
| 15.4 首个真实 PR | dev：PR #2、#18 → 批次 PR #19 合入 `main`（`d7c9a7d`）；vault：PR #2（改名同步）→ 批次 PR #14 合入 `main`（`f99bab2`）。每个 PR 都走 CI → 独立评审回帖 → `gh merge`。CI 实际检查项：dev `test`（约 13 分钟），vault `check`（约 2 分钟） |
| 15.5 CI 拦截验证（可选） | 未执行 |
| 15.6 从 main 部署 | 来源门禁通过，manifest `source_commit` = `d7c9a7d`；5 处各 330 个文件哈希一致。部署前把 5 处 `config.json` 同步为 staged 版本（新增 `push_guard`、`github` 两段），原文件备份在维护记录 `2026-10-27-GitHub接入收尾/config-before/` |
| 16 | 完整 pytest 746 passed、3 skipped；两仓库 `main` CI 为绿；`--verify-only` 仅余下述旧残留 |

## 遗留与后续

- `deploy.py` 不删除 `app/` 之外的旧文件：4 处副本仍残留 `references/tag-taxonomy.md`、`rwiki/categories.py`（本特性之前就有），需要时手工删除。
- 在 `start-task --worktree` 建的 worktree 中，`lint` 对带 `source/` 联接的 ready 方法页报“入库验收记录已过期”：`rwiki/acceptance.py` 的 `snapshot()` 用 `resolve()` 判断文件是否在资产目录内，联接解析到主检出后文件全部被排除。主检出无此问题。
- `tests/test_rule_docs.py::test_vault_rule_docs` 以 `DEV_ROOT.parent` 作为 vault 根，在 dev worktree 中失败；在主检出通过。
- `start-batch` 不拒绝与另一仓库已有批次同名的名称，而 `find_batch` 先查 vault：同名时 `start-task` 会建到 vault。本次误建的 vault Issue #17 已关闭（not planned），对应的空 worktree 与分支已移除，dev 侧同名空批次（分支与 Milestone）已删除，改用 `gsw-delivery-report`。
- `gh merge` 在 worktree 已被删除但 git 仍登记时（`git worktree remove` 中断）重跑会因 `rev-parse` 失败退出；本次手工补完分支删除与元数据。
- 剩余风险中的 `RWIKI_BOOTSTRAP=1` 与 hook 使用当前检出代码两条仍然成立。

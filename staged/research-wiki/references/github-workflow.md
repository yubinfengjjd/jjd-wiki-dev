# GitHub 流程（可选）

v2（2026-10-27）起，Issue / PR / 他人评审是可选流程：知识库可在本地 `main` 直接 `save` 提交，开发仓库也可在本地 `main` 提交，推送由作者决定。开发代码大改、需要 CI 与第二个 agent 评审时，再用本页的任务分支流程。

所有操作经 `wiki.py gh <子命令>`，它是 git 与 gh CLI 的薄封装；失败时报错并退出 1，修正后可原样重跑（每步先查后建，不重复建 Issue/PR）。

## 适用范围：项目自带，与宿主无关

- 流程是本项目自带的：`wiki.py gh` 子命令、仓库内 `.github/`（PR/Issue 模板、CI）、`.push-guard-allow`、`知识库/.protected-hashes.json` 与 pre-push hook。Codex、Claude、Devin、Kiro 等任何 agent 都用同一套命令，不依赖 Kiro 或任何宿主的私有配置、钩子或权限文件。
- pre-push hook 写在 `.git/hooks/`，不入库。新克隆或新机器先运行 `wiki.py gh install-hook --repo dev|vault`（每个仓库一次，可重复运行）重新安装。
- 两个仓库：`jjd-wiki-dev`（`开发/`）与 `jjd-wiki`（项目根，含 `知识库/`、`文档/`、`tools/`），默认分支 `main`。仓库名、owner、`dev_root`、`vault_root`、`worktree_root` 写在本机 `config.json` 的 `github` 段（示例见 `config.example.json`，`config.json` 不入库）。
- 两者都是免费账号下的私有仓库，没有远端分支保护（保护 API 返回 403），bootstrap 记为 `protection: local`。v2 起 pre-push 不再据此拒绝 `main`、`project/*`、`ingest/*`，只拒绝 `legacy/*`；内容扫描照常。

## v2 放开了什么

| 2026-10-27 之前 | v2 |
|---|---|
| `main` 与长期分支上拒绝 `save` 和网页写入，写入前先开任务分支 | 本地 `main` 与批次分支直接 `save`；`task/*` 仍需写入锁 |
| 每个任务都走 Issue → PR → codex-review → `gh merge` | 可选；本地提交即可。走 PR 时 `gh merge` 仍按门禁合并并收尾 |
| pre-push 拒绝直接推送主分支与长期分支 | 只拒绝 `legacy/*`；画廊、课题数据、限制性许可源码、超限文件、本机绝对路径的扫描保留 |
| 部署只认 `origin/main` 或已推送 tag | 本地 `main`、`origin/main` 或已推送 tag；部署 6 个技能目录（新增 `.kiro`） |

## 什么时候用

- 开发仓库代码大改，想留下 CI 结果与评审记录。
- 多个 agent 并行写同一个知识库：`task/*` 分支加写入锁（`start-task --worktree`）避免互相覆盖。
- 日常收录、按批次入库、规则与文档修改：在本地 `main` 提交即可，不需要本流程。

## 角色分工（走 PR 时）

- **编码 agent**：`start-task` → 写入（`save` 或普通 git 提交）→ `finish-task`；按评审意见修改后再推送。
- **评审 agent（Codex 角色）**：由非编码 agent 读 PR diff 与 CI 结果，把问题逐行写进文件，用 `wiki.py gh review <pr> --verdict pass|changes --findings <文件>` 回帖。编码 agent 不评审自己的 PR。
- **合并**：`wiki.py gh merge <pr>`。门禁通过才合并，并负责关闭 Issue、释放写入锁、清理联接与 worktree；在网页上点合并或直接 `gh pr merge` 会跳过这些收尾，需要手工补。

## 命名

- 长期分支：`project/<课题>`、`ingest/<批次>`，与 Milestone 同名。
- 任务分支：`task/<批次>-<阶段>-<主题>`，阶段为 `P0`–`P5` 或 `T<数字>`，批次与主题为小写 slug（`[a-z0-9]+(-[a-z0-9]+)*`，≤ 40 字符），如 `task/scp-wave3-P2-harmony`。中文名称写进 `--title`。
- 遗留迁移的 Milestone：`legacy/<来源目录名>`。
- Label：`type:project|ingest|code|legacy`、`stage:P0`…`stage:P5`、`stage:T1`…`stage:T9`、`stage:legacy`、`status:进行中|待评审|需修改|已验收`、`blocked:用户决定|本地验证|外部依赖|CI`、`risk:low|normal|high`（`finish-task` 写入，只供查看）、`owner-approved`（只由作者在网页上添加）。

## 子命令

除 `guard`、`protect-baseline`、`install-hook`、`tier` 外，每个子命令先检查 gh 已安装且已登录（`gh auth status`）；不满足时报出安装页与 `gh auth login`，不自动安装。

| 子命令 | 参数 | 用途 | 前置条件 |
|---|---|---|---|
| `preflight` | — | 只读输出 JSON：gh 路径/版本、账号、owner、两仓库存在性与可见性、分支保护探测（403 → `local`）、本地分支与未提交数、待推送范围、guard 干跑、`DEV_DEPLOY_KEY` 是否已设；有阻断项退出 1 | gh 可用 |
| `bootstrap` | `[--confirm]` | 首推。无 `--confirm` 只输出授权摘要、不做网络写；`--confirm` 时 `master` 改名 `legacy/master`、构造 `main`（dev 过滤重放、vault 快照）、只移动 HEAD 与索引切到 `main`、安装 hook、建私有仓库并推送、建 Label、deploy key 与 secret、探测/配置分支保护 | preflight 无阻断；`--confirm` 需用户一次性明确授权 |
| `install-hook` | `[--repo dev\|vault]` | 写 pre-push hook（调用 `gh guard --pre-push`）：优先调用部署副本 `~/.agents/skills/research-wiki/` 的 `wiki.py` 与 `config.json`，不随主检出切分支或改坏而变；副本缺失时退回当前检出并警告（先运行 `tools/deploy.py`）；输出含所用 `wiki_py` 与 `source`；缺省为当前目录所在仓库；已有非本工具 hook 时拒绝覆盖 | 无（不需要 gh） |
| `start-batch` | `<project\|ingest> <名称> --title <中文标题> --repo dev\|vault` | 从 `origin/main` 建长期分支、同名 Milestone，经 guard 推送 | 已 bootstrap |
| `start-task` | `<批次> <阶段> <主题> --title <Issue 标题> [--worktree]` | 建 Issue（`rwiki-task` 标记、Milestone、`type:*`/`stage:*`/`status:进行中`），创建任务分支并取得写入锁；`--worktree` 在 `worktree_root` 下建独立检出并输出 `RWIKI_WIKI_ROOT` | 批次存在；已设 `RWIKI_AGENT` |
| `finish-task` | `[--local-report <文件>]` | 经 guard 推送任务分支，开 PR 到所属长期分支，正文按 PR 模板填 `Refs #n`、本地专属验证、受保护字节核验；按 base 上的规则算风险档，打 `risk:low\|normal\|high` 标签（移除另两个），“改动摘要”首行写 `风险档：<档>（前 3 条命中原因）`；重跑时更新标签与该行；Issue 改 `status:待评审` | 在 task 分支；无未提交的已跟踪改动 |
| `review` | `<pr> --verdict pass\|changes --findings <文件>` | 针对 PR 当前 head 以 COMMENT 类型 review 回帖 codex-review 标记，更新状态标签 | PR 存在；由非编码 agent 执行 |
| `merge` | `<pr> [--plan <文本>]` | 按风险档做 Merge_Gate 判定（档位在合并时重算，不信 `risk:*` 标签；见下文）；输出 JSON 含 `tier`；通过则 `--match-head-commit` 合并并收尾，不通过则回帖阻断原因与计划并退出 1；PR 已合并时只做收尾 | — |
| `close-batch` | `<批次>` | Milestone 内 Issue 全部关闭后开长期分支到 `main` 的 PR（再经 `review`/`merge`）；有未关闭 Issue 时拒绝并列出 | Milestone 内 Issue 全部关闭 |
| `migrate-legacy` | `--map <legacy-map.json> [--dry-run]` | 按映射把旧任务书与 `remaining-gaps.md` 缺口迁为 Issue（`rwiki-legacy` 标记去重），非 dry-run 时在原文件顶部加迁移标记 | 首次推送完成 |
| `guard` | `[--range <rev-range>] [--pre-push <remote> <url>] [--sync-ignore]` | 推送防泄漏扫描：画廊、限制性许可源码（路径与 GPL 文件头）、课题数据 `wiki-use/_project/`、超限文件、本机绝对路径；`--sync-ignore` 重写 `知识库/.gitignore` 的托管块；不带 `--range` 时扫描尚未推送的提交 | 无（纯本地，不需要 gh） |
| `protect-baseline` | `[--check]` | 生成或核验 `知识库/.protected-hashes.json`（每个 user 块的 SHA-256，含行尾）；`--check` 输出为空表示通过 | 无（纯本地，不需要 gh） |
| `tier` | `--range <rev-range>` | 按 `git diff --name-only <range>` 的改动路径与仓库内 `.github/risk-tiers.json`（`{"high": [glob], "low": [glob], "high_requires_owner": true\|false}`，最后一项可选、缺省 true、必须是布尔；`*` 不跨 `/`，`**` 匹配零到多级目录，不带 `/` 的模式只匹配根目录）输出 JSON `{"tier", "reasons", "paths"}`：任一路径命中 high 为 `high`，全部命中 low 为 `low`，其余（含无改动、无规则文件）为 `normal` | 无（纯本地，不需要 gh） |

全局参数 `--wiki-root <目录>` 覆盖 `config.json` 的 `wiki_root`，优先级：`--wiki-root` > 环境变量 `RWIKI_WIKI_ROOT` > 配置文件。

## 一次任务的完整流程

```powershell
$env:RWIKI_AGENT = 'codex'                         # 执行写入的 agent 名
& $rw -X utf8 $wiki gh start-batch ingest scp-wave3 --title 'SCP 第三批' --repo vault   # 每批一次
& $rw -X utf8 $wiki gh start-task scp-wave3 P2 harmony --title 'Harmony 整合入库' --worktree
# 按输出设置 RWIKI_WIKI_ROOT，在该检出中工作；知识库写入用 save，文档/tools 用普通 git 提交
& $rw -X utf8 $wiki save 'ingest harmony'
& $rw -X utf8 $wiki gh finish-task --local-report <报告文件>
# 评审 agent（非编码 agent）：
& $rw -X utf8 $wiki gh review 52 --verdict pass --findings <问题文件>
& $rw -X utf8 $wiki gh merge 52
& $rw -X utf8 $wiki gh close-batch scp-wave3      # 批次全部 Issue 关闭后
```

- 主检出模式（不带 `--worktree`）用 `git switch -c`，只允许 `知识库/` 内的未提交改动随行；`知识库/` 之外有已跟踪改动时拒绝并列出。并行任务或作者正在用 Obsidian 时用 `--worktree`。
- 写入锁按检出：`<git-dir>/rwiki-writer.lock`，由 `start-task` 取得、task PR 合并后由 `merge` 释放。他人持有时 save 报出持有者与分支；遗留锁由用户手工删除。
- 有 `RWIKI_AGENT` 或在 task 分支上时，`save` 的提交附 trailer：`Issue: #n`（仅 task 分支）、`Agent: <RWIKI_AGENT>`、`Pages: …`（超过 20 个页面写前 20 个与余数）。

## save 与网页写入

- `task/*` 分支上的 `save` 需要当前检出的写入锁与分支元数据，否则报错；`main`、`project/*`、`ingest/*` 与其他分支直接提交。
- 网页（`server.py`）的写入端点也调用 save：主检出在 `main` 时网页写入直接提交到 `main`。要让网页写入落到任务分支，先 `gh start-task … --worktree`，按输出设置环境变量后启动 launcher：

  ```powershell
  $env:RWIKI_WIKI_ROOT = '<worktree_root>\task__scp-wave3-P2-harmony\知识库'
  & 'tools\launcher.ps1'      # launcher 把 RWIKI_WIKI_ROOT 以 --wiki-root 传给 server
  ```

  launcher 复用已在运行的 server 时不会改变它的 wiki_root；先关掉旧 server 再启动。也可以直接 `wiki.py --wiki-root <检出>\知识库 serve`。

## worktree 与限制性许可目录联接

- 限制性许可源码目录（GPL 方法的 `code/`、`source/`，限制性许可配方的 `source/`，此类模板的 `code/`、`example/`）写在 `知识库/.gitignore` 的 `# >>> push-guard gpl` 托管块中，不入库；`save` 在暂存前自动同步该块。块的内容与许可判定见 sources-and-recipes.md。
- `start-task --worktree` 在 `worktree_root/<分支名把 / 换成 __>` 建 worktree，并为托管块中每个目录建 `mklink /J` 目录联接指回主检出，使 worktree 内渲染、运行、完整 lint 与方法复核可用；联接不进 git。
- `merge` 收尾时先逐个 `rmdir` 联接本身（确认是 reparse 点，不带 `/s`），再 `git worktree remove`（不加 `--force`）。不要手工 `rmdir /s` 或强制删除 worktree：这些源码不在远端，误删只能从来源快照 `restore`（配方）或无法恢复（本地方法源码）。

## lint --ci 与 LOCAL-ONLY

GitHub 上的 vault 不含限制性许可源码目录、`画廊/` 与 `维护记录/`。CI 运行 `lint --ci`：被 vault 忽略（`git check-ignore` 命中）而缺失的引用报 `LOCAL-ONLY`，不计入错误；未被忽略的缺失仍是 `ERROR`。`LOCAL-ONLY` 表示“这项只能在本机核对”，不是通过。完整 `lint` 与方法复核只在主检出或带联接的 worktree 中运行。

## 仅本地运行的检查与 --local-report

CI 运行 `pytest -m "not r and not compose and not local"`、前端 `npm test`、`lint`（vault 为 `lint --ci`）、`gh guard --range` 与 `gh protect-baseline --check`。下列检查只能在本机运行；PR 涉及这些范围时，编码 agent 本地运行并把命令、结果与未运行原因写进报告文件，再用 `finish-task --local-report <文件>` 填进 PR 的“本地专属验证”：

| 检查 | 原因 |
|---|---|
| `verify-template` / `verify-layout` / `render`（`pytest -m r`） | 需本机 Rscript 与 R 包 |
| 配方 `run`、`deps`、`restore` | 需本机 Rscript、Wiki 专用 R 库与来源快照 |
| panel 合成（`pytest -m compose`） | 需 sci-figure-replica 环境 |
| `pytest -m local`、方法复核回执重放、`check-entry` 涉及 runtime | 依赖本机数据、真实画廊与被忽略的限制性许可源码 |
| 真实画廊读取（`ingest-figure`、`test-gallery*`） | 画廊受版权保护，不入库 |
| `frontend/tests/real-taxonomy.ts` | 读本机 taxonomy |
| `tools/deploy.py` 部署与 `--verify-only` | 操作本机 6 个技能目录 |
| 浏览器检查（`qa/cdp.mjs`） | 需本机浏览器与运行中的 server |
| 完整 `lint`（非 `--ci`） | 需限制性许可源码、画廊与维护记录 |

报告里只写相对路径与 sha256，不写本机绝对路径（guard 会拦截）。

## Merge_Gate 与评审标记（走 PR 时）

- 评审回帖首行：`<!-- codex-review: verdict=pass|changes sha=<40 位 head SHA> -->`，随后为结论、问题列表与所评审的 SHA。
- 风险档在 `merge` 时重算，不信 PR 上的 `risk:*` 标签：规则读 PR base 分支当前提交（`origin/<base>`，先 fetch）上的 `.github/risk-tiers.json`，改动范围为 `origin/<base>...<headRefOid>`（merge-base 语义，与 GitHub PR diff 一致；head 本地没有时先按分支、再按 sha 取回）。PR 自己改规则（改松 glob、删文件、把 `high_requires_owner` 改成 false）都不影响本 PR 的档位与要求。不提供改规则来源的参数。
- CI 条件（三档相同）：`gh pr checks` 至少一项 pass，其余为 pass 或 skipping（全部 skipping 视为没有 CI 结果）；pending、fail、cancel 阻断。
- `low`：CI 通过即可合并，不需要 codex-review。
- `normal`：CI 通过，且 reviews 与 comments 中按时间最新的 codex-review 标记为 `pass`、sha 等于 PR 当前 head。PR 之后再有提交，旧评审失效，需要重新评审。
- `high`：`normal` 的全部要求；base 规则的 `high_requires_owner` 为 true（缺省）时还要作者确认：PR 上有 `owner-approved` 标签，且它最近一次 labeled 事件（PR timeline）晚于当前 head 的推送时间。推送时间取 timeline 中 `head_ref_force_pushed` 与 `committed` 事件时间的最晚值，timeline 没有 head 的 committed 事件时用 head 提交的 committer date（近似）。标签早于最新提交即失效，需作者移除后重新添加。
- 开发仓库 `.github/risk-tiers.json` 设为 `"high_requires_owner": false`：作者 2026-10-28 明确放弃逐个确认高风险 PR；high 仍需独立评审与 CI。
- 不通过：回帖 `<!-- rwiki-gate: blocked sha=<head> -->`、原因列表（第一条为档位与前 3 条命中规则）与 `### 修复计划`（`--plan`，缺省“待补”），PR 保持未合并，退出 1。
- 通过：`gh pr merge --merge --match-head-commit <head> --delete-branch`；task PR 合并后关闭 Issue（附 PR 与合并 SHA）、标 `status:已验收`、释放锁、清理联接与 worktree、删本地分支，主检出模式切回 `main` 并 `pull --ff-only`；长期分支 PR 合并后关闭 Milestone 并删除长期分支。

## 推送边界与部署来源

- 不推送：`画廊/`、`维护记录/`、限制性许可源码目录、课题数据（`wiki-use/_project/`）、`config.json`、`codex/`、`*.lnk`、`Rplots.pdf`、超过阈值（默认 5 MB）的文件、本机绝对路径。`.push-guard-allow` 只能豁免 `abs-path` 与 `size`，每条须写理由。
- 每次推送都经 `gh guard`（wrapper 与 hook 各查一次）；hook 拒绝推送任何 `legacy/*`，其余分支（含 `main`）只做内容扫描。
- `tools/deploy.py <record> "<note>" [--sync-config]` 只在 `开发` 工作区干净、HEAD 等于本地 `main`、`origin/main` 或恰为已推送 tag 时部署 6 个技能目录（`.agents`、`.codex`、`.claude`、`.cc-switch`、`.config/opencode`、`.kiro`），manifest 记 `source_commit`、`source_ref` 与 `source_tag`；`--sync-config` 先备份再用 staged `config.json` 覆盖各处；`deploy.py --verify-only` 只核对 6 处副本与 staged 的哈希，不写入。

## 不要在主检出检出 legacy/master

bootstrap 切到 `main` 时只移动 HEAD 与索引（`git symbolic-ref` + `git read-tree`），因为旧 `master` 跟踪了 `画廊/`、`维护记录/`（vault）与 `config.json`、`codex/`（dev），而新 `main` 不跟踪它们。在主检出上 `git switch`/`checkout` 到 `legacy/master` 再切回，会把这些文件从磁盘删除，远端没有副本。需要查看旧历史时用 `git log legacy/master`、`git show legacy/master:<路径>`，或在 `worktree_root` 下另建 worktree。

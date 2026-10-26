# GitHub 结构化工作流

任务、评审、验收从文件任务书迁到 GitHub 私有仓库的 Milestone / Issue / PR。所有操作经 `wiki.py gh <子命令>`，它是 git 与 gh CLI 的薄封装；失败时报错并退出 1，可在修正后原样重跑（每步先查后建，不重复建 Issue/PR）。

## 适用范围：项目自带，与宿主无关

- 流程是本项目自带的：`wiki.py gh` 子命令、仓库内 `.github/`（PR/Issue 模板、CI）、`.push-guard-allow`、`知识库/.protected-hashes.json` 与 pre-push hook。Codex、Claude、Devin、Kiro 等任何 agent 都通过 `wiki.py gh` 遵守同一套规则，不依赖 Kiro 或任何宿主的私有配置、钩子或权限文件。
- pre-push hook 写在 `.git/hooks/`，不入库。新克隆或新机器先运行 `wiki.py gh install-hook --repo dev|vault`（每个仓库一次，可重复运行）重新安装。
- 两个仓库：`research-wiki-dev`（`开发/`）与 `research-wiki-vault`（项目根，含 `知识库/`、`文档/`、`tools/`），默认分支 `main`。仓库名、owner、`dev_root`、`vault_root`、`worktree_root` 写在本机 `config.json` 的 `github` 段（示例见 `config.example.json`，`config.json` 不入库）。

## 角色分工

- **编码 agent**：`start-task` → 写入（`save` 或普通 git 提交）→ `finish-task`；按评审意见修改后再推送。
- **评审 agent（Codex 角色）**：必须是非编码 agent。读 PR diff 与 CI 结果，把问题逐行写进文件，用 `wiki.py gh review <pr> --verdict pass|changes --findings <文件>` 回帖。编码 agent 不评审自己的 PR。
- **合并**：任一 agent 运行 `wiki.py gh merge <pr>`；门禁不通过就不合并。免费私有仓库没有远端分支保护（保护 API 返回 403 → 本地门禁模式）时，合并只能经 `wiki.py gh merge`，不在网页上点合并，也不直接运行 `gh pr merge`，同样不直接推送 `main` 或长期分支。

## 命名

- 长期分支：`project/<课题>`、`ingest/<批次>`，与 Milestone 同名。
- 任务分支：`task/<批次>-<阶段>-<主题>`，阶段为 `P0`–`P5` 或 `T<数字>`，批次与主题为小写 slug（`[a-z0-9]+(-[a-z0-9]+)*`，≤ 40 字符），如 `task/scp-wave3-P2-harmony`。中文名称写进 `--title`。
- 遗留迁移的 Milestone：`legacy/<来源目录名>`。
- Label：`type:project|ingest|code|legacy`、`stage:P0`…`stage:P5`、`stage:T1`…`stage:T9`、`stage:legacy`、`status:进行中|待评审|需修改|已验收`、`blocked:用户决定|本地验证|外部依赖|CI`。

## 子命令

除 `guard`、`protect-baseline`、`install-hook` 外，每个子命令先检查 gh 已安装且已登录（`gh auth status`）；不满足时报出安装页与 `gh auth login`，不自动安装。

| 子命令 | 参数 | 用途 | 前置条件 |
|---|---|---|---|
| `preflight` | — | 只读输出 JSON：gh 路径/版本、账号、owner、两仓库存在性与可见性、分支保护探测（403 → `local`）、本地分支与未提交数、待推送范围、guard 干跑、`DEV_DEPLOY_KEY` 是否已设；有阻断项退出 1 | gh 可用 |
| `bootstrap` | `[--confirm]` | 首推。无 `--confirm` 只输出授权摘要、不做网络写；`--confirm` 时 `master` 改名 `legacy/master`、构造 `main`（dev 过滤重放、vault 快照）、只移动 HEAD 与索引切到 `main`、安装 hook、建私有仓库并推送、建 Label、deploy key 与 secret、探测/配置分支保护 | preflight 无阻断；`--confirm` 需用户一次性明确授权 |
| `install-hook` | `[--repo dev\|vault]` | 写 pre-push hook（调用 `gh guard --pre-push`）；缺省为当前目录所在仓库；已有非本工具 hook 时拒绝覆盖 | 无（不需要 gh） |
| `start-batch` | `<project\|ingest> <名称> --title <中文标题> --repo dev\|vault` | 从 `origin/main` 建长期分支、同名 Milestone，经 guard 推送 | 已 bootstrap |
| `start-task` | `<批次> <阶段> <主题> --title <Issue 标题> [--worktree]` | 建 Issue（`rwiki-task` 标记、Milestone、`type:*`/`stage:*`/`status:进行中`），创建任务分支并取得写入锁；`--worktree` 在 `worktree_root` 下建独立检出并输出 `RWIKI_WIKI_ROOT` | 批次存在；已设 `RWIKI_AGENT` |
| `finish-task` | `[--local-report <文件>]` | 经 guard 推送任务分支，开 PR 到所属长期分支，正文按 PR 模板填 `Refs #n`、本地专属验证、受保护字节核验；Issue 改 `status:待评审` | 在 task 分支；无未提交的已跟踪改动 |
| `review` | `<pr> --verdict pass\|changes --findings <文件>` | 针对 PR 当前 head 以 COMMENT 类型 review 回帖 codex-review 标记，更新状态标签 | PR 存在；由非编码 agent 执行 |
| `merge` | `<pr> [--plan <文本>]` | Merge_Gate 判定；通过则 `--match-head-commit` 合并并收尾，不通过则回帖阻断原因与计划并退出 1；PR 已合并时只做收尾 | — |
| `close-batch` | `<批次>` | Milestone 内 Issue 全部关闭后开长期分支到 `main` 的 PR（再经 `review`/`merge`）；有未关闭 Issue 时拒绝并列出 | Milestone 内 Issue 全部关闭 |
| `migrate-legacy` | `--map <legacy-map.json> [--dry-run]` | 按映射把旧任务书与 `remaining-gaps.md` 缺口迁为 Issue（`rwiki-legacy` 标记去重），非 dry-run 时在原文件顶部加迁移标记 | 首次推送完成 |
| `guard` | `[--range <rev-range>] [--pre-push <remote> <url>] [--sync-ignore]` | 推送防泄漏扫描：画廊、GPL 源码（路径与文件头）、课题数据 `wiki-use/_project/`、超限文件、本机绝对路径；`--sync-ignore` 重写 `知识库/.gitignore` 的 GPL 托管块；不带 `--range` 时扫描尚未推送的提交 | 无（纯本地，不需要 gh） |
| `protect-baseline` | `[--check]` | 生成或核验 `知识库/.protected-hashes.json`（每个 user 块的 SHA-256，含行尾）；`--check` 输出为空表示通过 | 无（纯本地，不需要 gh） |

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
- `save` 的提交附 trailer：`Issue: #n`、`Agent: <RWIKI_AGENT>`、`Pages: …`（超过 20 个页面写前 20 个与余数）。

## save 与前端写入在 main 上被拒

- `main`、`project/*`、`ingest/*` 上 `wiki.py save` 在写 `log.md` 与暂存之前即报错，提示先 `gh start-task`。网页（`server.py`）的写入端点也调用 save，同样被拒，页面改动由服务端还原，网页显示“请先 start-task”。
- 主检出平时停在 `main`，只作阅读检出。要在网页里编辑：先 `gh start-task … --worktree`，按输出设置环境变量后启动 launcher：

  ```powershell
  $env:RWIKI_WIKI_ROOT = '<worktree_root>\task__scp-wave3-P2-harmony\知识库'
  & 'tools\launcher.ps1'      # launcher 把 RWIKI_WIKI_ROOT 以 --wiki-root 传给 server
  ```

  launcher 复用已在运行的 server 时不会改变它的 wiki_root；先关掉旧 server 再启动。也可以直接 `wiki.py --wiki-root <检出>\知识库 serve`。

## worktree 与 GPL 目录联接

- GPL 源码目录（GPL 方法页的 `methods/<id>/code/`、`source/`）写在 `知识库/.gitignore` 的 `# >>> push-guard gpl` 托管块中，不入库；`save` 在暂存前自动同步该块。
- `start-task --worktree` 在 `worktree_root/<分支名把 / 换成 __>` 建 worktree，并为托管块中每个目录建 `mklink /J` 目录联接指回主检出，使 worktree 内渲染、完整 lint 与方法复核可用；联接不进 git。
- `merge` 收尾时先逐个 `rmdir` 联接本身（确认是 reparse 点，不带 `/s`），再 `git worktree remove`（不加 `--force`）。不要手工 `rmdir /s` 或强制删除 worktree：GPL 源码不在远端，误删不可恢复。

## lint --ci 与 LOCAL-ONLY

GitHub 上的 vault 不含 GPL 源码目录、`画廊/` 与 `维护记录/`。CI 运行 `lint --ci`：被 vault 忽略（`git check-ignore` 命中）而缺失的引用报 `LOCAL-ONLY`，不计入错误；未被忽略的缺失仍是 `ERROR`。`LOCAL-ONLY` 表示“这项只能在本机核对”，不是通过。完整 `lint` 与方法复核只在主检出或带联接的 worktree 中运行。

## 仅本地运行的检查与 --local-report

CI 运行 `pytest -m "not r and not compose and not local"`、前端 `npm test`、`lint`（vault 为 `lint --ci`）、`gh guard --range` 与 `gh protect-baseline --check`。下列检查只能在本机运行；PR 涉及这些范围时，编码 agent 本地运行并把命令、结果与未运行原因写进报告文件，再用 `finish-task --local-report <文件>` 填进 PR 的“本地专属验证”：

| 检查 | 原因 |
|---|---|
| `verify-template` / `verify-layout` / `render`（`pytest -m r`） | 需本机 Rscript 与 R 包 |
| panel 合成（`pytest -m compose`） | 需 sci-figure-replica 环境 |
| `pytest -m local`、方法复核回执重放、`check-entry` 涉及 runtime | 依赖本机数据、真实画廊与被忽略的 GPL 源码 |
| 真实画廊读取（`ingest-figure`、`test-gallery*`） | 画廊受版权保护，不入库 |
| `frontend/tests/real-taxonomy.ts` | 读本机 taxonomy |
| `tools/deploy.py` 部署与 `--verify-only` | 操作本机 5 处技能目录 |
| 浏览器检查（`qa/cdp.mjs`） | 需本机浏览器与运行中的 server |
| 完整 `lint`（非 `--ci`） | 需 GPL 源码、画廊与维护记录 |

报告里只写相对路径与 sha256，不写本机绝对路径（guard 会拦截）。

## Merge_Gate 与评审标记

- 评审回帖首行：`<!-- codex-review: verdict=pass|changes sha=<40 位 head SHA> -->`，随后为结论、问题列表与所评审的 SHA。
- 通过条件：`gh pr checks` 非空且全部 pass；reviews 与 comments 中按时间最新的 codex-review 标记为 `pass`，且 sha 等于 PR 当前 head。PR 之后再有提交，旧评审失效，需要重新评审。
- 不通过：回帖 `<!-- rwiki-gate: blocked sha=<head> -->`、原因列表与 `### 修复计划`（`--plan`，缺省“待补”），PR 保持未合并，退出 1。
- 通过：`gh pr merge --merge --match-head-commit <head> --delete-branch`；task PR 合并后关闭 Issue（附 PR 与合并 SHA）、标 `status:已验收`、释放锁、清理联接与 worktree、删本地分支，主检出模式切回 `main` 并 `pull --ff-only`；长期分支 PR 合并后关闭 Milestone 并删除长期分支。

## 推送边界与部署来源

- 不推送：`画廊/`、`维护记录/`、GPL 源码目录、课题数据（`wiki-use/_project/`）、`config.json`、`codex/`、`*.lnk`、`Rplots.pdf`、超过阈值（默认 5 MB）的文件、本机绝对路径。`.push-guard-allow` 只能豁免 `abs-path` 与 `size`，每条须写理由。
- 每次推送都经 `gh guard`（wrapper 与 hook 各查一次）；hook 拒绝推送任何 `legacy/*`，本地门禁模式下还拒绝直接更新 `main`、`project/*`、`ingest/*`。
- `tools/deploy.py <record> "<note>"` 只在 `开发` 工作区干净、HEAD 等于 `origin/main` 或恰为已推送 tag 时部署，manifest 记 `source_commit` 与 `source_tag`；`deploy.py --verify-only` 只核对 5 处副本与 staged 的哈希，不写入。

## 不要在主检出检出 legacy/master

bootstrap 切到 `main` 时只移动 HEAD 与索引（`git symbolic-ref` + `git read-tree`），因为旧 `master` 跟踪了 `画廊/`、`维护记录/`（vault）与 `config.json`、`codex/`（dev），而新 `main` 不跟踪它们。在主检出上 `git switch`/`checkout` 到 `legacy/master` 再切回，会把这些文件从磁盘删除，远端没有副本。需要查看旧历史时用 `git log legacy/master`、`git show legacy/master:<路径>`，或在 `worktree_root` 下另建 worktree。

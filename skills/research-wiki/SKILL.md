---
name: research-wiki
description: Use when the author wants a template, figure or analysis method from their 科研知识库 (LLM Wiki), such as 找模板、按场景推荐、出图、换数据套用、找分析方法、课题还能做什么分析; when ingesting open-source code libraries (开源库入库, e.g. FigureYa) or replicated figures (复刻图入库); for 处理待办 and 知识库体检 (lint). Also use it when sci-figure-replica finishes a replication (ingest-figure) and when medfig-render or medpaper-pipeline reach a drawing step (查模板 before drawing). Any agent (Claude Code, Codex, Kiro, opencode) calls it through rwiki find / show / use; the optional GitHub Issue/PR flow is wiki.py gh.
---

# 科研知识库（research-wiki）

作者的 LLM Wiki：配方、图模板、方法笔记与数据接口，按等级区分。L0 = 来源目录项（未建页），L1 = 原样运行通过的整模块配方，L2 = 函数化、可换数据的模板/方法。你只用命令操作，不必读 `rwiki/` 源码。

## 怎么调用

- `rwiki` 在 PATH 上时直接 `rwiki <命令>`（PowerShell 用 `rwiki.cmd`，Git Bash 用 `rwiki`）。不在 PATH 时用专用解释器：

  ```powershell
  $env:TEMP=$env:TMP='E:\research-wiki-env\tmp'; $env:MPLCONFIGDIR='E:\research-wiki-env\tmp\mpl'
  $rw = 'C:\Users\86186\.codex\venvs\research-wiki\Scripts\python.exe'
  & $rw -X utf8 '<本技能目录>\wiki.py' <命令> …
  ```

- 参数以 `rwiki <命令> --help` 为准；命令输出里的 `wiki.py …` 换成 `rwiki …` 即可。
- 写页面、收录或改状态前读总库 `AGENTS.md`（路径 = 本技能 config.json 的 `wiki_root`），底线以它为准。

## 日常：找到并调用（find → show → use）

1. `rwiki find <场景/图型/分析名…> [--kind recipe|template|method|scenario|item] [--runnable]`：读 `catalog.jsonl`，场景首选排前，每条带下一步命令。
2. `rwiki show <id>`：用途、适用/不适用、输入、许可、最近运行。读完再给作者 1–3 个候选与差异，等作者选；已有选择就复用。
3. `rwiki use <id> --project <课题目录>`：代码复制到 `<课题>\wiki-use\<名>\`，不改 Wiki。L0 条目要求来源 trusted。
4. 按副本里的 `RWIKI-USE.md` 换数据：配方替换同名输入文件、保持列格式；模板把 `bindings.draft.json` 改成 `bindings.json`（内部字段 → 作者列）。含义、单位、粒度不清先问。
5. 运行：配方副本 `rwiki run --dir <副本>`；模板 `rwiki render <id> --data <目录> --out <目录> --bindings <bindings.json>`；方法在课题环境调用 `code\` 入口。
6. 打开图看一眼；没有看图能力就把目视检查写成待办。数据、脚本、成图都留在课题目录。
7. 任务授权包含正式 Wiki 写入时才回写：`rwiki record-use <模板 id> --project <slug> --title … --output <png>`；只做了分析用 `record-method-use`。只记路径与判断。

medfig-render、medpaper-pipeline 出图前先 `rwiki find`：有可用模板或通过的配方就给作者候选，没有就照常出图。按列名或研究问题初筛也可用 `suggest` / `suggest-methods` / `suggest-pipeline` / `discover-methods`；课题状态与证据用 `project …`（只写 `<课题>\wiki-use\_project\`）。见 references/project-reuse.md、references/project-state.md。

## 入库：开源库与复刻图（画廊是来源之一）

1. 登记来源（作者同意收这个库）：`rwiki source add <id> --title … --url … --license <SPDX> --adapter figureya [--trusted] [--cite …]` → `rwiki source fetch <id>` → `rwiki source scan <id>`（生成 L0 目录）。
2. 按主题挑条目：`rwiki promote <来源> <条目…> --curation <json>`（中文标题、图型、受控 tags、用途/适用/不适用）。
3. `rwiki deps <配方…>` 列缺包，整理成一批清单交作者；作者按批次批准后 `rwiki deps <配方…> --install`（只装进 Wiki 专用 R 库）。
4. `rwiki run <配方…> [--jobs N]` 原样运行；看收据与 preview.png，补页面判断。缺包写 not_run，不伪造。
5. 作者确认一批：`rwiki mark-ready <id…>`（任一不通过则全部不改）。
6. 默认同步整理代码复用层（成熟依赖优先复用既有闭包/原生调用适配，避免重复建模板）；确需单 panel 模板时：`rwiki scaffold-template <配方 id> --from-recipe --chart-type <slug> --title …` → 写 `code\`、`example\` 与 spec → `rwiki verify-template <模板 id>` → `rwiki mark-ready <模板 id>`。复刻图：sci-figure-replica 复刻后 `rwiki ingest-figure <画廊条目>` → `rwiki scaffold-template <版式 id> --chart-type … --panels …`（相同画法用 `attach-template`）→ `verify-template` → `mark-ready`。
7. 方法：按 AGENTS.md 的四步（读目的与输入 → 查库语义去重 → 提炼与验证 → 知识整合与确认），骨架用 `rwiki scaffold-method`。

细节见 references/sources-and-recipes.md 与 references/method-families.md。

## 默认双层入库与前端同步（2026-11-02）

作者要求：每次入库默认交付代码复用层与方法理论层，并实际同步前端展示。方法理论含目的、输入单位、假设/统计边界和输出含义；代码保留原语言、原字节来源与显式可复制入口、最小闭包、runtime.json、当前逐分支收据。缺包或未运行如实写 not_run；只有理论来源时标明代码缺口，不虚构实现。

继续遵循方法语义去重：analysis 为规范理论家族，workflow/technical 资料关联既有家族。irGSEA/SCP 等原生绘图与自定义函数分开，优先复用，不为展示凑模板。方法页 `code_roles: [visualization]` 显式进入图库“绘图代码”；`theory_methods` 仅指向理论资料，不授予接口直连或科学验证。

收尾顺序：逐页 check-entry → save → lint → 核对实际 API/前端显示与代码查看/下载。改前端时构建并通过 tools/deploy.py 同步安装副本；浏览器实际核对方法库检索、图库对应入口、详情分支/缺包标识。只报告本地提交不算完成前端同步，未操作界面时不得声称已展示。

## 待办、体检与 Git

- “处理待办”：`rwiki pending --json` 列出 agent 动作与待作者确认项；继续已有草稿，不重复新建。确认前 `rwiki check-entry <id>` 查缺项。
- `rwiki lint` 只查结构。写操作最后 `rwiki save "<说明>"`（多数命令自带）；本地 main 可直接 save。
- GitHub Issue/PR/评审是可选流程，推送 GitHub 时用：`gh start-task --worktree`（从 `origin/main` 切）→ `gh finish-task`（PR 到 `main`）→ 非编码 agent `gh review` → `gh merge`；批次只是 Milestone。`gh tier --range origin/main...HEAD` 自查风险档：`risk:low` CI 即合，`risk:normal` 再要 pass 评审，`risk:high` 同 normal，`high_requires_owner` 为 true 时再要 `owner-approved`（只由作者在网页添加，agent 禁止添加）。全部子命令、门禁与 `--repo` 见 references/github-workflow.md。
- `config.json` 的 `env` 段给出代理与 gh 路径（`vars`、`path_prepend`），`wiki.py` 启动时自动设置；`install-hook` 的 hook 调用已部署副本，guard 改动部署后才生效。

## 常见错误

- 用 config 里的 `python_exe` 跑 wiki.py：报 `No module named 'yaml'`（那是模板出图用的解释器）。
- 没 `show` 就推荐，或推荐后不等作者选就开始做。
- 按列名相似猜列，或在 bindings 里补值、换算、聚合；改统计逻辑、分组含义前不先问。
- 往课题环境装包，或未经作者按批次批准就 `deps --install`。
- 把课题数据、脚本、成图写进知识库目录。
- 手改 `<!-- user:start -->` 区块、facts 区块或 frontmatter 的 status/favorite。
- 遗漏知识代码或泄漏敏感信息：作者 2026-11-02 要求所有知识默认保存 Git（包括 GPL/CC 源码、复用代码、公开示例、模板资源和验证材料）；私有数据、密码、私钥不进 Git。保留原许可证与来源；save 清理旧许可排除块。
- 在主检出检出 `legacy/master`（会删掉本地画廊与维护记录）。
- 临时文件、缓存写到 C 盘。

## references（按需读）

- references/sources-and-recipes.md：来源、L0/L1、运行器、收据、use 副本、装包审批、restore、许可、catalog 字段、画廊来源、确认与待办
- references/input-binding.md：bindings 与长宽整理
- references/adaptive-sizing.md：模板组数与尺寸适配
- references/minimal-runtime.md：`runtime.json` 与独立性证据
- references/method-families.md、references/knowledge-linking.md：方法家族、验证收据、`figure_relations`
- references/code-assets.md：原生代码与网页查看代码
- references/project-reuse.md、references/project-state.md：课题推荐、适配与课题状态层
- references/llm-wiki-mode.md：LLM Wiki 模式、网页删除与预览、Obsidian
- references/github-workflow.md：GitHub Flow、gh 子命令、风险档与门禁、env 段、CI 跳过范围

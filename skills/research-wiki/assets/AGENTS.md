# 科研知识库 · agent 维护规则（v2，2026-10-27）

这是作者的个人科研 LLM Wiki：互链的 Markdown 页面，加上可直接调用的配方、图模板与方法代码。agent 收录、编译和维护页面；作者阅读、确认、写备注。
任何 agent（Claude Code、Codex、Kiro、opencode）都用同一套命令 `rwiki <命令>`，即 research-wiki 技能的 `wiki.py <命令>`，参数相同；命令输出里的 `wiki.py …` 可直接换成 `rwiki …`，参数以 `--help` 为准。
本文件只写底线与页面分工，实现细节在技能目录的 `references/`（见文末）。改页面前读完本文件。

## 三层与目录

- 原始层（只读）：上游来源快照（`config.sources_root`，不在 Wiki 内）、画廊（`config.gallery_root`，sci-figure-replica 的复刻产物）、配方与方法的 `source/` 原字节。
- Wiki 层：本目录，agent 编译的页面。
- 规则层：本文件，加技能的 `SKILL.md` 与 `references/`。

| 位置 | type | 内容 |
|---|---|---|
| `sources/<id>.md`、`sources/<id>/items.jsonl` | source | 来源登记（URL、commit、许可证、适配器、trusted）与 L0 目录 |
| `recipes/<id>.md`、`recipes/<id>/` | recipe | L1 配方：上游整模块原字节 `source/`、`source.json` 哈希、运行收据 `runs/`、`preview.png` |
| `templates/<id>.md`、`templates/<id>/` | template | L2 图模板：`spec.json`、`code/`、`example/`、回放 `verify/` |
| `methods/<id>.md`、`methods/<id>/` | method | L2 方法：笔记，可选 `source/`、`code/`、`runtime.json`、`verification/` |
| `scenarios/<id>.md` | scenario | 场景导航：`picks: [{id, note}]` 首选组合 |
| `interfaces/<slug>.md` | interface | 数据接口：列、必需/可选与“含义” |
| `chart-types/<slug>.md` | chart-type | 图型概念页 |
| `layouts/<id>.md`、`layouts/<id>/` | layout | 画廊复刻图样的来源记录 |
| `projects/<slug>.md` | project | 课题用过什么、怎么适配；只由 `record-use` / `record-method-use` 生成 |
| `index.md`、`catalog.jsonl`、`log.md` | — | 前两个由 `save` 重建，`log.md` 只追加；都不手改 |

## 等级与状态

- L0：来源目录项（`items.jsonl` 一行，未建页）；能被 `find` 检索，来源 trusted 时可直接 `use`。
- L1：配方；当前原字节有 pass 的原样运行收据才算可运行。
- L2：模板/方法；函数化、可换数据。模板经 `verify-template` 回放，方法每个实现分支有 `verification/*.json`。
- recipe、template、method 的状态统一 draft / ready / archived，ready = 作者已确认。layout 只来自画廊（`ingest-figure`），它的 pending_signoff / pending_template 是历史状态，只读保留；开源库与配方不建 layout。
- 能否执行看等级与收据，不看 status：配方 ready 但当前原字节没有 pass 收据，不能当可运行；方法 ready 不等于有已验证实现。
- 单 panel 只约束 L2 模板：一个模板 = 一个逻辑 panel（inset、色标、边缘分布随主 panel）。L1 配方保留上游整模块，可含多张图。

## 收录流程

画廊是来源之一，不是必经入口。按批次推进，作者按批次确认。

1. 来源：`source add <id> --title … --url … --license <SPDX> --adapter <名> [--trusted]` 登记（作者同意收这个库后登记；trusted = 白名单，之后按需获取不再逐次询问；非白名单来源获取代码前先问作者）→ `source fetch <id>`（固定 commit 的稀疏快照）→ `source scan <id>`（生成 L0 目录）。
2. L0 → L1：按主题挑值得收的条目，`promote <来源> <条目…> --curation <json>`（中文标题、图型、受控 tags、用途/适用/不适用）→ `deps <配方…>` 列缺包 → 作者按批次批准后 `deps <配方…> --install` → `run <配方…>` → 看收据与预览图，补写页面判断。
3. 确认：作者看过一批后 `mark-ready <id…>`；多个 id 时先全部核对，任一不通过则全部不改。
4. L2 在课题用到时再做：`scaffold-template <配方> --from-recipe --chart-type <slug> --title …`，函数化后 `verify-template`；画廊复刻图走 `ingest-figure` → `scaffold-template` / `attach-template`。不为“以后可能有用”预先批量做 L2。
5. 方法家族收录四步：
   1. 读目的与输入：分析目的、输入语义、行/样本单位、估计目标、输出对象与本次范围；复用作者已确认的答案。
   2. 查库语义去重：按研究问题、输入、单位、估计目标、算法假设比对已有家族、实现、流程与接口，不只比标题、函数名或包名。同一实现补来源；新算法加分支；多个方法串联写 `workflow`；源码/环境适配写 `technical`；只有新的分析目的才建新家族。
   3. 提炼与验证：原代码以原语言、原字节进 `source/`；`code/` 显式参数化；写 `runtime.json`；逐分支实际调用并写收据，缺包或失败写精确 not_run。
   4. 知识整合与确认：更新相关方法、图、接口与“知识关联检查”，`check-entry <id>` 无缺项后交作者确认（可按批次）。
6. 常规单次检验（t 检验、Wilcoxon、卡方等）写进所属方法或图注，不单独成页。

## 默认入库交付（作者 2026-11-02 修订）

每次入库默认同时整理 **代码复用层 + 方法理论层**，并同步前端展示；不能只归档源文件或只写理论页就宣称入库全部完成。本条取代此前“代码等课题用到再整理”的默认口径，原始层只读、语义去重、作者确认和装包审批继续有效。

- 方法理论层：明确研究问题、输入对象与行单位、估计目标、假设、适用/不适用、算法与统计边界、输出含义；相同目的合并到既有分析家族，组合流程与源码适配保留 workflow/technical 分类及互链。
- 代码复用层：有源码时同步保留原字节来源，提炼原语言、显式参数的可复制入口、最小依赖闭包、runtime.json 与逐分支收据；做原版对照、真实合法数据调用和异目录新进程验证。缺代码、缺数据、缺依赖或未跑的分支写精确缺口/not_run，不编造实现或通过证据。
- 成熟依赖（如 irGSEA、SCP、Seurat）原生图与项目自定义计算/绘图分开登记；优先复用既有闭包或薄调用适配，不因项目、文件名或 PDF 不同重复建模板。绘图代码在方法页显式登记 `code_roles: [visualization]`，其理论关联用 `theory_methods: [规范方法id]` 表达；这些只是发现入口，不是科学直连或可执行授权。
- 前端验收：save 重建索引后，检查实际服务读取正式 Wiki；方法库可按标题、ID、函数/依赖和关键词找到理论、流程与代码资料，图库的模板与绘图代码入口分别可见。打开详情核对入口、依赖、当前逐分支验证范围和代码查看/下载，缺包状态不得继承其他分支的通过结果。
- 修改前端/技能源码时，完成构建、部署副本哈希核对及实际浏览器检查；已打开页面可用“同步知识库”刷新数据。只完成提交、save 或 lint 不等于已同步前端。

## 检索与调用

- find → show → use → run 或 render。`find <关键词…>` 读 `catalog.jsonl`，场景首选排在前面，每条给出下一步命令；`show <id>` 看用途、适用/不适用、输入、许可与最近运行；`use <id> --project <课题>` 把代码复制到 `<课题>/wiki-use/<名>/`，附 `RWIKI-USE.md`（换数据说明），模板另附 `bindings.draft.json`。`use` 不写 Wiki。
- 换数据后运行：配方副本 `run --dir <副本>`（收据写在副本 `rwiki-runs/`）；模板 `render <id> --data … --out … --bindings …`；方法在课题环境调用 `code/` 入口。
- 推荐前读候选页的“适用 / 不适用 / 输入”；列名相同不证明适用，列名不同也不排除。给作者 1–3 个候选与差异，等作者选；已有选择就复用。
- 课题数据、脚本、成图留在课题目录，不进 Wiki。只有任务授权包含正式 Wiki 写入时才 `record-use`（配图）或 `record-method-use`（只做分析），只记路径与判断。
- 课题证据与经验草稿用 `project …` 写在 `<课题>/wiki-use/_project/`，不进 save 链。

## 环境与依赖

- `wiki.py` 只用 research-wiki 专用 Python；临时文件与缓存写 E 盘（TEMP/TMP/MPLCONFIGDIR）。
- 配方 `run`、`run --dir` 与 R 模板 `render` 使用 Wiki 专用 R 库（`config.r_libs`）。运行时不联网装包：`install_dependencies.R` 换成只检查不安装的桩。
- 装包只经 `deps --install`：先 `deps` 列出一批缺包清单，作者按批次批准后执行，只装进 `r_libs` 的第一个目录；不往课题环境或系统库装包。
- 缺包写 not_run，上游报错写 fail，都保留精确原因；不伪造通过，不用近似实现顶替。
- 课题自己的 Python/R 环境由作者管理：缺包时列出包名问作者。

## 收据

- 配方：`recipes/<id>/runs/<run_id>.json`（schema_version 2，scope = as-is / new-data / other-dir，state = pass / fail / not_run，本机路径脱敏）；`run --dir` 的收据留在课题副本。
- 模板：`verify/` 回放回执，绑定 code、spec、示例数据、接口与输出哈希。方法：`verification/*.json` 逐分支；独立迁移证据随 `runtime.json`。
- 代码或输入变了，旧收据就不再代表当前版本。收据只证明“在记录的环境里跑通”，不证明统计或科学有效。
- 检查项与检查者如实写；没有看图能力时，把目视检查写成待办并写明由谁核查。

## 底线（不能破）

1. 来源快照与原始层只读：保留原字节、哈希、许可证；配方 `source/`、方法 `source/`、画廊不改。
2. `<!-- user:start -->` 与 `<!-- user:end -->` 之间是作者内容，agent 一字不改、不移动；`<!-- facts:start -->`…`<!-- facts:end -->` 只由脚本生成；frontmatter 的 `status`、`favorite`、`archived_from` 只经 `wiki.py` 或网页改。
3. 不编造数据、文献、收据或适用结论；没跑写“未跑”，不确定写“待作者确认”。
4. 改变统计逻辑、补缺失算法、改分组含义，或缺原始数据需要估读、合成时，先问作者。
5. 列映射显式写（内部字段 → 作者列）；不猜列、不补值、不换算单位、不聚合。
6. 知识库的所有知识默认保存 Git，包括方法理论、源码、复用代码、公开示例、画廊知识、模板资源与验证材料。私有数据、密码和私钥不进 Git、不推送；保留原许可证、署名、来源与用途限制，不因保存 Git 改变许可。
7. 网页服务只接受本机访问，不为外部访问放开。

## 页面写什么

- 判断优先：下一个 agent 读完会不会做出不同动作？会就写进页面；只是“知道有这回事”就链接到来源。不复制原始层大段内容。
- 配方、模板、方法都写清“适用 / 不适用 / 输入含义 / 知识关联检查”。配方正文节为用途、适用、不适用、输入、怎么用、输出、知识关联检查、使用记录；限制性许可的配方页顶部保留许可提示。
- 场景页：`picks: [{id, note}]`，id 为页面 id 或 `来源:条目`；正文节为什么时候用、首选组合、注意。
- 接口页“含义”：一行代表什么、单位/编码、最容易出错的前提、与相近接口的区别；模板不重算的统计写“上游给定”。
- 图型页五节：回答什么问题、什么时候选它、什么时候不要用、与相近图型怎么区分、常见误用。
- 方法—图关系只在方法侧 `figure_relations` 维护（direct / adaptable / candidate），反向自动派生；接口结构匹配不等于可直接接。
- `tags` 只用受控词表（`config.taxonomy` 的规范键或中文 label）；别名、数据集、软件、模型名进 `keywords`。非法或重复 tags 为 ERROR，空列表仍可读。`purposes` 只用于 analysis 方法。
- 命名：id 冻结，是文件名和引用键；title 写中文内容名，约 8–20 字，不拼来源、版本、图型前缀或项目名。
- 链接用相对 Wiki 根的双链，如 `[[recipes/<id>|显示名]]`；frontmatter 列表存值，不存链接。

## Git

- 知识库写操作的最后一步是 `save "<说明>"`（多数命令自带）：重建 facts、`index.md`、`catalog.jsonl`，追加 `log.md`，只提交 Wiki 子树。本地 `main` 与批次分支可直接 save；`task/*` 分支需要写入锁（`gh start-task` 建）。
- 本地日常不需要 Issue / PR；推送由作者决定。要推送 GitHub 或开发代码大改时走 GitHub Flow：`gh start-task … --worktree`（从 `origin/main` 切）→ 提交 → `gh finish-task`（PR 到 `main`）→ 非编码 agent `gh review` → 只经 `gh merge` 合并。批次只是 Milestone（`gh start-batch` / `gh close-batch`）。细节与全部 `gh` 子命令见 `references/github-workflow.md`。
- 风险档按 base 上的 `.github/risk-tiers.json` 算，可先 `gh tier --range origin/main...HEAD` 自查：`risk:low` CI 通过即合；`risk:normal` 再要针对当前 head 的 pass 评审；`risk:high` 同 normal，`high_requires_owner` 为 true 时再要 `owner-approved`（当前为 false）。三档都要求 PR 已包含最新 main。
- `owner-approved` 只由作者在网页上添加，agent 禁止添加；单账号下 GitHub 分不出是谁加的，这是约定。
- pre-push 只拒绝 `legacy/*`，并扫描私有数据、课题数据、密码/令牌/私钥、超限文件与本机绝对路径。
- 作者 2026-11-02 修订：知识默认入 Git，取消按 GPL/CC 许可排除源码的旧规则；save 移除旧 `push-guard gpl` 托管块。仅敏感内容与非知识运行产物（环境、缓存、浏览器会话、重复备份）排除；大文件按内容核查后用 Git LFS 或精确 size 豁免保存，不能只留页面而漏掉代码。`restore` 仍可修复缺失或损坏的来源原字节。
- 不要在主检出检出 `legacy/master`：它跟踪过画廊与维护记录，切过去再切回会把这些文件从磁盘删除，远端没有副本。看旧历史用 `git log legacy/master` 或另建 worktree。

## 体检

`lint` 只查结构：frontmatter、断链、状态、收据结构、必需节是否空白、`index.md` 与 `catalog.jsonl` 是否过期。lint 通过不代表语义正确，跨来源同义与科学适用性由 agent 审查；逐条修复后 `save`。处理待办用 `pending --json`，确认前用 `check-entry <id>` 查缺项。

## 细则（research-wiki 技能目录 references/）

| 文件 | 什么时候读 |
|---|---|
| `sources-and-recipes.md` | 来源登记、适配器、L0 目录、配方与运行器、收据、use 副本、装包审批、restore、许可托管块、catalog 字段、画廊来源、确认与待办 |
| `input-binding.md` | 写 bindings、长宽整理 |
| `adaptive-sizing.md` | 做 L2 模板的组数与尺寸适配 |
| `minimal-runtime.md` | 写 `runtime.json`、独立性证据、R 模块封装与环境恢复 |
| `method-families.md` | 方法家族、实现、验证收据、函数契约 |
| `knowledge-linking.md` | `figure_relations`、一方法多图与一图多方法 |
| `code-assets.md` | 原生代码与网页“查看代码” |
| `project-reuse.md`、`project-state.md` | 在课题里选方法/图、适配、课题状态层 |
| `llm-wiki-mode.md` | 三层与 ingest/query/lint、网页删除与预览、Obsidian |
| `github-workflow.md` | GitHub Flow、全部 `gh` 子命令、风险档与门禁、`config.json` 的 env 段、CI 跳过范围 |

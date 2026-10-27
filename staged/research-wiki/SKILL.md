---
name: research-wiki
description: Use when the author wants a figure or an analysis for a research project and may already have a reusable figure template or analysis method in their 科研知识库 (LLM Wiki), such as 出图前查模板、推荐图、换数据套用、SHAP/差异分析等可复用方法、分析→出图、处理待办、收录复刻图或方法、知识库体检; also when sci-figure-replica, medfig-render or medpaper-pipeline reach a drawing step; and for the project's GitHub workflow on the research-wiki repos (开任务分支、提 PR、Codex 评审、合并、首推/迁移, via wiki.py gh).
---

# 科研知识库（research-wiki）

作者的知识库是一个 LLM Wiki，写给你读的说明书：

- **图模板**：带可运行代码，换上作者的数据就能出图（`render`）。
- **方法笔记**：先写用途、输入/输出、适用边界和依据，可附有来源的函数；没有可执行代码也能成为有用笔记。开发期可对显式函数入口做隔离调用并写验证收据，但知识库/网页不替你运行课题分析，代码存在或一个分支通过不等于科学有效。
- **数据接口**：描述数据含义和执行入口的表格契约。发现阶段不要求列名完全相同；执行前在课题副本用显式 bindings 映射，或写成标准内部表。`<接口>.csv` 是执行约定，不是作者的命名要求。

你通过本技能目录下的 `wiki.py` 操作知识库，不读 `rwiki/` 源码也能完成全部工作。

## 先做两件事

1. **用对解释器。** `wiki.py` 只能用 research-wiki 自己的 Python 运行；配置里的 `python_exe` 是模板出图用的，由 wiki.py 自己调用：

   ```powershell
   $env:TEMP=$env:TMP='E:\research-wiki-env\tmp'; $env:MPLCONFIGDIR='E:\research-wiki-env\tmp\mpl'
   $rw = 'C:\Users\86186\.codex\venvs\research-wiki\Scripts\python.exe'
   & $rw -X utf8 '<本技能目录>\wiki.py' <命令> …     # 默认读本技能目录的 config.json
   ```

2. **读总库根目录的 `AGENTS.md`**（路径 = config.json 的 `wiki_root`）。页面类型、谁能改什么、收录与推荐的规则都在那里，以它为准。

## GitHub 结构化工作流（2026-10-27）

知识库与开发代码分属两个 GitHub 私有仓库（`jjd-wiki`、`jjd-wiki-dev`，默认分支 `main`），任务、评审、验收用 Milestone / Issue / PR 管理，文件任务书已停用（旧任务书经 `gh migrate-legacy` 迁为 Issue）。完整的子命令参数、前置条件、仅本地运行的检查清单与 `--local-report` 用法见 [GitHub 工作流](references/github-workflow.md)。

- **项目自带、与宿主无关**：规则由 `wiki.py gh` 子命令、仓库内 `.github/` 模板与 CI、pre-push hook 实现；Codex、Claude、Devin、Kiro 等任何 agent 都通过 `wiki.py gh` 遵守，不依赖 Kiro 或宿主配置。
- **写入前先开任务分支**：`main`、`project/*`、`ingest/*` 上 `save` 与网页写入都被拒；先 `gh start-batch`（每批一次）再 `gh start-task <批次> <阶段> <主题> --title … [--worktree]`（需设 `RWIKI_AGENT`）。网页编辑用 `--worktree`，按输出设置 `RWIKI_WIKI_ROOT` 后运行 launcher。
- **一次任务**：`start-task` → `save`/普通提交 → `finish-task [--local-report <文件>]` → CI → `review` → `merge` → 批次收尾 `close-batch`。
- **分工**：评审须由非编码 agent（Codex 角色）执行并以 `wiki.py gh review <pr> --verdict pass|changes --findings <文件>` 回帖；编码 agent 不评审自己的 PR。
- **合并只经 `wiki.py gh merge`**：两仓库都是免费私有仓库、无远端分支保护（保护 API 403），已处于本地门禁模式（`protection: local`），这是唯一合并入口，不在网页上点合并，也不直接运行 `gh pr merge`；门禁要求 CI 全部 pass 且最新 codex-review 为 pass、sha 等于 PR 当前 head。
- **hook 不入库**：新克隆或新机器运行 `wiki.py gh install-hook --repo dev|vault` 重新安装 pre-push hook。`gh guard`、`gh protect-baseline` 不需要 gh。
- **不要在主检出检出 `legacy/master`**：会把画廊、维护记录等未进 `main` 的文件从磁盘删除。

| 子命令 | 用途 |
|---|---|
| `gh preflight` | 只读检查 gh、账号、仓库可见性、分支保护与待推送范围 |
| `gh bootstrap [--confirm]` | 首推；无 `--confirm` 只输出授权摘要 |
| `gh install-hook [--repo dev\|vault]` | 安装 pre-push hook |
| `gh start-batch` / `gh start-task` | 建长期分支 + Milestone / 任务 Issue + 任务分支 |
| `gh finish-task [--local-report <文件>]` | 推送任务分支并开 PR |
| `gh review` / `gh merge [--plan]` | Codex 评审回帖 / 门禁合并 |
| `gh close-batch` | 批次全部 Issue 关闭后开到 `main` 的 PR |
| `gh migrate-legacy [--dry-run]` | 旧任务书与遗留缺口迁为 Issue |
| `gh guard` / `gh protect-baseline` | 推送防泄漏检查 / 作者块字节基准（纯本地） |

## 作者要出图或做分析

| 作者的话 | 命令 |
|---|---|
| 数据已经是整理好的表，要出图 | `suggest --columns a,b,c --q …` → `contact-sheet <模板 id，1–3 个> --out <课题>\candidates.png` |
| 课题还能做什么分析 | `suggest-methods --q …`，先读课题必要计划、代码、结果和数据说明 |
| 查看含未验证分支的机会清单 | `discover-methods [--q … --limit n]`（只读；executable 仅为 ready_for_use 真值，机会不等于推荐） |
| 要先做分析再出图 | `suggest-pipeline [--figure <模板 id>] --q …` |
| 课题状态/证据/运行记录 | `project init/status/check/impact/record-run/add-*/evaluate/recover/add-lesson/lesson-review --root <课题>`（只写 `wiki-use/_project/`，不写 Wiki；见 [课题状态层](references/project-state.md)） |

两种入口先读 [课题推荐与适配流程](references/project-reuse.md)。优先当前可做项，再列少量补材料候选，说明用途、依据、前提、缺口和代码状态。含义明确可在课题副本映射列名/整理长宽表，含义不清或缺关键数据先问；不自动聚合、填补、换算单位或改变统计逻辑。项目适配先留项目，有通用价值时经作者再次确认才回存。

`suggest` 只是初筛：读候选页面的“适用/不适用”，按数据和接口判断，不按标签或图长得像就断言方法适用。只推荐 `ready` 的模板和方法，说明候选的用途、数据要求和差异，等作者选。已有明确选择与计划则复用，不重复询问。

输入是文章、图或代码时，先让 agent 读图，列去重后的样式卡（代表裁图、来源/重复位置、编码、附属结构、已有模板和不确定点），再确认样式、数据、保真重点、代码与交付计划。每个选定样式只做一个代表单 panel；inset、色标、边缘分布属于该 panel，模型/指标/颜色变化不自动新增模板，实质结构差异保留变体。完整整图仅作只读溯源，不复刻整组或收录整图条目。缺原始数据须说明缺口并询问本次用估读还是合成；未回答不是同意。方法联想限定为有依据的方法家族推广（如 XGBoost＋SHAP → 满足条件的机器学习模型＋SHAP）：保留原实现，说明适用范围、前提、限制与未实现/未验证分支；不从画法通用性推导宽泛新分析方法。先写文字，有来源代码可按函数契约融入，不自动补算法。渲染和正式收录在关键选择与计划明确后进行，详见总库 AGENTS.md。

作者选定后连续执行，全部产出放课题目录：

1. 读方法笔记的输入、输出、适用边界和代码状态。有代码则复制所需模块到 `<课题>\scripts\`，在显式参数中传数据/列映射/该方法所需参数；记录代码来源是 Wiki 分支还是课题自有——用课题自有代码运行、或仅整理/格式化既有结果，都不能记成"运行了 Wiki 实现"。真正的实现复用是：选科学兼容的已验证分支、按其 `runtime.json` 复制声明的文件/资源、在新进程用显式输入/参数调用所复制入口并保留范围与诊断；受托管的 render 或课题内准备脚本本身不证明该分支运行过，绑定与收据必须对应实际调用的代码。没有代码可继续咨询或写文字笔记，缺分析算法时先提出具体方案询问，不自动补实现。
2. 在课题自己的 Python / R 环境里运行。缺包时列出包名问作者，不要擅自装，也不要改用知识库的解释器。
3. 按方法笔记检查数据前提和必要诊断，不满足时说明影响；代码能运行不等于统计或科学有效。
4. 分析函数返回结构化结果（表、模型、矩阵、原生对象均可，诊断随结果保留）；绘图函数只物化该图实际接受的表，可独立调用或串联，不要求每个分析都出 CSV。先核对语义、粒度、量纲与配对关系；原表不改。外部表在显式调用层用 `--bindings` 映射到接口字段（写清内部字段→作者列），或写成 `<课题>\analysis\<接口 slug>.csv` 标准表。不做隐式聚合、补值、单位换算或统计；映射报告留在课题输出。
5. 每张图：`render <模板 id> --data <课题>\analysis --out <课题>\figures\<名>`；外部命名/列名用 `--bindings <课题>\bindings.json`。打开 PNG 看一眼——检查项与检查者如实写入收据；没有图像读取能力时把目视检查标为待办并写明由谁核查，不在收据记未做过的目视确认。
6. 正式回写（**仅当任务授权明确包含正式 Wiki 写入时**）：`record-use <模板 id> --project <课题 slug> --title "<课题名>" --output <png 路径> --method <方法 id>`（配图）；只做了分析没出图用 `record-method-use --method <方法 id> --project <slug> --title "…" --project-root <课题> --run <已完成 run_id>`（核实收据结构+产物/输入指纹现行才登记，不配图不写图页）。两者都是正式 Wiki 写并可能提交 Git，与只写课题目录的 `project record-run` 完全不同：授权只含隔离实验或明确禁止正式写时**不要调用**，证据留在课题状态层与 lesson 草稿；图完成或运行登记本身不构成回写授权，明确任务边界优先于通用流程步骤。

报错、方法前提不满足或结果异常（输出为空、数值离谱、图上文字被裁切）时保存现场并说明；需要改变统计逻辑或补分析算法时先询问。给作者的消息里写关键数字和改过的参数。

## 课题本地状态与机会发现（2026-10-24）

- 课题证据层：`<课题>/wiki-use/_project/` 保存实体/原生对象/观察/主线/授权/任务/产物/运行收据/经验草稿，`project` 子命令维护；单写者锁 + revision，已测写失败边界保持权威文件与已发布视图一致（不声称跨文件崩溃原子性），绝不调用 Wiki `save`。中断后用 `project recover` 先只读核查（锁/活性/孤儿收据），修复动作显式隔离到 `_quarantine/` 不删证据。旧 `wiki-use/<标识>/` context 仅作引用兼容。
- 判断轴分开：basis（verified/author_stated/unknown）、工作状态、产物新鲜度、Wiki 实现验证、科学解释互不授予；`record-run` 的 completed 要实际命令+存在输出+检查项，退出码/布尔不授予验证；复用已验证运行须 `--code` 登记实际代码来源（implementation_id 只是分支名）。
- 任务家族/实现绑定按实际执行的操作、输入输出、单位与算法判定：消费既有标签/预测/结果文件不等于执行产生它们的算法（评估既有预测≠训练、绘制构象≠对接、汇总既有标签≠聚类）；无匹配规范家族/分支时用未绑定的课题内任务加显式来源登记，库内缺口如实保留，不为通过核查新建正式家族。
- `discover-methods` 与 `GET /api/discover-methods`：只读列出规范 analysis 笔记、未验证分支与缺口；`suggest-methods`/`ready_for_use` 语义不变，workflow/technical/归档页与库外缺口永不升为可执行。
- 领域前提：`rwiki/domain_profiles.yaml` 声明式配置覆盖生信/深度学习/影像组学/药设/网药毒理/蛋白组/代谢组；`project evaluate [--subject object:…]` 逐项给 satisfied/unsatisfied/unknown/conflicted/not_applicable：同层正负观察冲突不报满足，关于其他对象的观察不作全局证明，材料缺失/指纹变化的登记项不再满足前提，条件前提（`when`/`unless`）不适用时报 not_applicable；阶段证据按任务/观察的 `stage` 声明+现行证据判 declared/recorded/not_recorded——阶段名是声明不是完成证据，未知保持未知。
- `runtime.json` v2 兼容扩展：`entry_kind`（function/script/external_program）、`tools`、`external_resources`、`hardware`、`invocation`；空/缺席仍是旧指纹，实质条件进 v2 指纹并使旧收据过期。只声明不安装。详见 [最小运行清单](references/minimal-runtime.md)。

## 其他操作

| 场景 | 命令 |
|---|---|
| sci-figure-replica 复刻完一张图 | `ingest-figure <画廊条目 id>`，再按 AGENTS.md“收录”补适用说明 |
| 作者说“处理待办” | `pending`，按实际剩余工作继续已有草稿或补齐模板；不按状态盲目重建 |
| 收录一段分析代码或写方法笔记 | AGENTS.md“收录方法”（`scaffold-method` → 写笔记 → 作者确认） |
| 体检 | `lint`（CI 用 `lint --ci`：被忽略而缺失的 GPL 源码、画廊、维护记录报 `LOCAL-ONLY`） |
| 网页 | `serve`（作者在网页签核、确认方法、改标签；主检出在 `main` 时写入被拒，经 `RWIKI_WIKI_ROOT` / `--wiki-root` 指向任务分支检出） |
| 开任务、提 PR、评审、合并 | `gh start-task` / `gh finish-task` / `gh review` / `gh merge`，见上节与 [GitHub 工作流](references/github-workflow.md) |

作者源码函数化保留原语言、源字节/哈希与修改副本，记录输入/输出、依赖、随机性和限制；比较原版与封装版数值等价，再在不同工作目录/换数据检查可移植性。函数不硬编码课题/知识库路径，使用课题环境；绘图对象按语言返回，多个 axes 仍可构成一个 panel。保留现有 `draw(fig, rect, tables, style)`/render 入口并共用绘图核心。统计逻辑改变或补缺失分析算法前询问作者；不为收录而制作公共 pip/R 包。详细契约见总库 AGENTS.md。

函数化也要验证改变组数/类别数/行列后能套用，不能只封装固定规模。 n为实际数据中的任意合法数量，由课题agent识别并编排，不为固定几个n另写分支/模板；尺寸默认系数可按课题覆盖。按数据结构配置尺寸增长，默认保持单panel与间距并继续加宽/增高；只在作者明确设置上限时协商其他布局。新Python模板使用可复制的 `code/sizing.py` 和 `spec.style.sizing`，独立函数与render共用核心；复刻比例与换数据自适应分开验收。实现、配置和迁移边界见 [尺寸适配契约](references/adaptive-sizing.md)。

Wiki 写操作最后都是 `save "<说明>"`（多数命令已自带），只在 `task/*` 任务分支上提交并附 `Issue`/`Agent`/`Pages` trailer；`project` 课题状态命令只写课题 `wiki-use/_project/`，不进 save 链。完整参数：`wiki.py <命令> --help`。

## 方法家族与入库八步（2026-10-23）

方法页用 `method_kind: analysis|workflow|technical` 区分分析家族、组合流程和技术资料；只有 `analysis` + 作者 ready + 笔记完整 + 至少一个当前 `verified` 实现才进入可执行分析推荐。实现写在 `implementations`，每个分支独立 `verification/*.json`；缺依赖写精确 `not_run`，不安装、不伪造。旧 SCP/课题实现页保留旧 id、`source/` 和作者备注，改为技术/流程资料并链接真正家族，不再保留主 `figure_relations`。

新资料入库必须先走完八步，不能直接 `scaffold-method`：

1. **读输入与目的**：目的、输入语义、输出对象、统计单位、估计目标、提炼范围，以及研究领域与候选用途；复用作者已确认答案。
2. **查库与语义去重**：查现有家族、实现、流程、接口；按研究问题/输入/单位/估计目标/假设判断，不只比标题/函数名/关键词/文件或列名。
3. **分类判定**：同一实现补来源/修订；新算法/实现加分支；多个方法串联 → `workflow`；源码/环境/绘图适配 → `technical`；只有新分析目的才提议新家族。参数变化是配置。`analysis` 按正文依据补受控 `purposes`，不为填满分类夸大范围。
4. **具体收录方案**：页面、增量、函数入口、验证、材料缺口、输入语义、内部接口、可选表/列依据、bindings 与关键选择；关键选择明确后执行；缺数据/改统计/补算法先问。
5. **提炼**：原始代码原语言/原字节；提炼版独立，显式数据/参数/结果/诊断和复制依赖；只在现有环境验证。先读语义再绑定，外部表只在映射层整理。确定最小调用闭包、算法包、转换层、局部资源和可选分支，写 `runtime.json`；拆不开就标 `bundle`/`unknown`，不能让整库加载器冒充独立实现。
6. **验证**：逐实现实际调用、原版/提炼版、异目录复制、换合法数据、输入不变；失败/缺依赖/未运行写精确 `not_run`；一个分支通过不批准整个家族。改变 bindings 时另做原输入/绑定输入的表图对照。独立迁移须只复制清单文件和资源到异目录，不提供来源库路径，在新进程实际调用并记录命令/环境/闭包哈希；source、文件存在或整库收据都不算。
7. **知识整合**：更新实现选择、适用边界、相关方法/流程/接口/图样；冲突记录并修订旧判断，不做一来源一条目。
8. **验收与确认**：查重复/断链/冗余/证据；更新带摘要索引和只追加日志；知识整理与实现验证分开显示；按作者正常确认流程交付。

跨来源去重：青光眼与 SCP 同义分析汇入同一规范家族；同一算法不同包装是实现差异；不同算法同家族要比较，不抹平输入/假设/单位/结果。自动 `lint` 只检查结构/标题/收据/断链，语义同义性由 agent 审查。每次实质入库交付“旧页/来源→规范家族→具体实现→原始来源”对照表。

## 最小运行闭包与独立性（2026-10-23）

- 每个实现/模板在资产根写 `runtime.json`，声明入口、`runtime_mode`（standalone/bundle/unknown）、复制文件、资源、必要/可选包与来源映射；后端 `rwiki/runtime_contract.py` 唯一解析，API、lint、代码查看器与前端共用。
- 独立迁移证据与算法验证分开：`portability` 的 verified/declared/not_run/stale/invalid 只描述能否脱离来源库运行；算法 `verified` 仍只由 `verification/*.json` 的实际调用决定。二者互不授予。
- 复制到课题时只带清单文件和资源；成熟包的传递依赖保留，可选包按功能延迟检查。缺包写精确 `not_run`，不安装、不换环境、不用近似实现顶替原生图。
- 旧入口可接受 `bundle` 参数但不得读取整库；无法兼容时保留旧分支并新增独立入口。接口、helper、资源或依赖声明变化使独立性证据过期；旧证据保留。
- 命令、字段、状态派生与验收示例见 [最小运行清单](references/minimal-runtime.md)。

## 领域→用途浏览与灵活输入（2026-10-23）

- 方法库按 `tags`（研究领域）→ `purposes`（分析用途）两级浏览。用途只接受后端单一词表（`rwiki/method_taxonomy.py`），`GET /api/method-taxonomy` 与 `lint` 同源；前端不另造词表。一页可多领域/多用途，所有入口仍是同一 `id` 与规范页，计数为去重页数。分类只用于发现，不是科学适用性或可执行推荐门槛。
- 缺用途的旧 `analysis` 页可读并提示；非法/重复用途是 ERROR；分类变化不使实现收据失效，笔记验收变化时重录。
- 输入分三层：语义要求（对象/行单位/配对/单位/前提）、实现真实接受的对象与参数、内部表格式。外部数据用显式 `--bindings`：`columns` 方向为内部字段→作者列，`file` 相对 `--data`；缺必需项/未知表字段/重复映射/重复表头/非法数值在运行前失败。
- 只做无聚合 melt/pivot（显式 id/变量/值列）；pivot 重复键拒绝，index 按原值身份保留（空字符串、缺失值、嵌入分隔符不改写），空/缺失 pivot 类别显式拒绝。不改原表、不猜列、不补值、不换算、不做统计；映射报告放课题输出。
- 完整有效映射（显式+同名回退）中同一作者列只能消费一次；冲突报具体字段。写前预检全部来源/输出，输出不得覆盖源（含其他表输入与链接别名）；源哈希写前采集，staging 全部成功后才替换，失败不留部分结果。
- 可复制核心：`rwiki/input_binding.py`（Python）与 `assets/input_binding.R`（R）。完整格式、示例与验证边界见 [灵活输入契约](references/input-binding.md)。

来源 panel 存储：来源 panel、完整原图、`original_code/` 只放画廊；Markdown 只存路径/哈希/bbox/证据，不复制同字节图片。模板/方法资产可存代码、示例和真实回放；无回放时显示来源图并标“来源参考图／尚无回放”。

LLM Wiki 的三层、ingest/query/lint、更新而非按来源堆叠、矛盾/未知记录、index 摘要与只追加 log，见 [方法家族契约](references/method-families.md) 和 [LLM Wiki 模式](references/llm-wiki-mode.md)。正式规则以总库 `AGENTS.md` 为准。

单 panel 模板经 `verify-template` 和作者确认后可 `mark-ready`、独立 `render`，不要求 `verify-layout`；来源 layout 可仍为 `pending_template`。若还要将该 layout 标为 ready，则做只覆盖已选 panel 的布局/preview 并 `verify-layout`（单 panel 可为 1×1），再由作者确认；不包含未选 panel。

## 常见错误

- 用 `python_exe` 跑 wiki.py：报 `No module named 'yaml'`。
- 先 `scaffold-method` 再查重，或按来源/软件包新建同义分析家族；先走入库八步。
- 只凭标题、函数名、关键词或图型相似判断同一家族；跨来源要比较研究问题、输入、单位、估计目标和假设。
- 把源码/绘图接口/流程资料写成 `analysis`，或把未验证分支写成可执行推荐。
- 只凭 `runtime.json` 声明、source 成功、文件存在或旧整库收据就说“独立迁移已验证”；独立迁移必须在异目录、新进程、不提供来源库路径下实际调用。
- 把多个模块的 engine/helper 放成共享全局名，或用最外层课题 driver 的 `ofile` 定位模块；每个入口须私有闭包，路径取当前 source 文件。
- 调用后不恢复 `search()`/options、detach 用户原有包，或 diagnostics 在未恢复时写“none”；成功与异常路径都要验证。
- `resources` 不列入 `files`/不核对 sha256，或页面 entrypoint 与清单入口/函数不一致仍沿用 verified；算法 `passed` 由硬编码配方而非实际比较产物产生。
- 把纯绘图/辅助函数写进 `analysis` 的 `implementations` 或计入 verified；运行函数不等于分析实现，绘图不得批准轨迹分析可用。
- 前端另写一套领域/用途词表或把分类计数相加当方法总数；分类不是推荐或执行门槛。
- 按文件名/列名相似自动认领外部列，或把 `--bindings` 当成隐式改表、补值、单位换算、统计步骤。
- 推荐后不等作者选就开始做。
- 分析脚本、数据、成图写进知识库目录；知识库只通过 `record-use` 记录路径。
- 手改 `<!-- facts -->` 区块、frontmatter 的 `status`，或 `<!-- user -->` 区块。
- 临时文件、缓存写 C 盘：先设 TEMP/TMP/MPLCONFIGDIR 到 E 盘。

## 每次收录的知识关联与代码

新增或实质更新知识时双向检查“一方法多图／一图多方法”，包括不同来源。核对目的、行单位、语义、量纲、前提和代码能力；有依据在方法侧唯一维护 figure_relations，反向图页和图谱自动派生。分别标“直接可接／需要适配／待核实”及独立验证范围，接口结构匹配不自动等于直接可接。检查记录与未关联原因写正文；不为连通网络硬连。见 [方法家族与关系契约](references/knowledge-linking.md)。

原生代码和复用版附在对应方法/单 panel，保留原语言和源字节，不覆盖原件。网页卡片“查看代码”可在 Wiki 内按版本/文件查看、复制、下载，只读不执行；存在文件不证明可运行或已验证。见 [代码资产](references/code-assets.md)。

## 页面写什么：编译后的判断（2026-10-22）

Wiki 的价值在编译后的理解，不在文件清单。一次收录或实质更新，除 layout/template 外至少检查并更新：

- **接口页“含义”**：一行代表什么（行单位/粒度）、单位或编码（0–1 与 0–100、log 尺度、缺失含义）、准备数据时最容易出错的前提、与相近接口的区别。模板不重算的统计写“上游给定/模板不重算”。`lint` 对含义为空报 WARN。
- **图型页**：统一五节 `回答什么问题`、`什么时候选它`、`什么时候不要用`、`与相近图型怎么区分`、`常见误用`；有模板时列“本库模板”链接，暂无模板时明确写“本库暂无模板”。`suggest` 仍读模板/方法页的“适用/不适用”，不读图型页正文。
- **项目与使用记录**：课题中的适配、失败模式与判断回填到 `projects/<slug>.md` 或相关页面“使用记录”，不留在对话里；只回填判断，不复制课题数据与成图。
- **原始层不复制**：来源 panel、整图、缩略图与哈希留在画廊；Wiki 只存路径、哈希和证据指针。模板无回放时前端 preview 从画廊读取来源 panel；`layouts/<id>/thumb.png` 是复刻缩略图，不冒充来源图。

判据：下一个 agent 读完这页，是否会做出不同动作？会则写入；只是“知道有这回事”就链接到源。


待办按后端只读 `workflow` 派生，CLI与前端统一：无成功回放的模板归agent，成功回放草稿归作者确认；同一工作转到模板后来源不重复计数，选定panel已由ready模板完整覆盖则来源退出待办。`pending`只列仍需agent处理的来源ID，先读其现有模板与工作说明，不重复scaffold；为空不等于所有来源做过可选的layout回放。归档/删除导致有效覆盖缺失时重新列出，恢复后重算。保留来源签核、模板确认和运行证据各自含义，不为清零而改状态。


### 页面命名（2026-10-22）

- `id` 是业务键、文件名和引用键，现有 id 冻结；新增模板仍用 `<layout-id>--<chart-type>`。
- `title` 是内容名，中文为主，保留 UMAP/SHAP/marker 等术语，约 8–20 字；不写 `单panel：`、`图表复刻`、项目名/GSE 号、来源/版本、`示例数据`、`图型`。
- layout title 写图样名（必要时加来源限定）；template title 写可复用功能名，`scaffold-template --title` 显式传入；method title 写对象 + 核心操作，来源留在 `source`/facts。
- 图型、项目/来源、panel 分别放在 `chart_types`、facts/keywords、`panels`，同一信息不重复。
- 改标题只改 frontmatter `title` 与 H1；不改 id、路径、spec/code；`save` 重建 facts/index，受影响页重录 acceptance。

## 入库验收

按正式Wiki AGENTS.md“入库与展示验收”逐项核查：来源/单panel范围、明示覆盖关系下的配图去重、两栏数量口径、方法家族边界、多对多关系与适配、代码资产、前端实查和队列交接。图样栏按逻辑样式浏览，包含已有单panel函数模板；模板栏按函数入口浏览，同一记录可在两栏出现。按明示来源覆盖去重，不能用存储页面类型排除模板；历史整图归档不隐藏已拆出的单panel图样，不为补展示而重新入库或新增待办。方法页优先用途、输入/输出、去重配图与适配要求，完整证据可展开；不照抄示例的图数或direct能力，不改完整Markdown事实/作者备注。未完成验收项如实记录，不补算法或凑来源。


## 当前版本的验收与待办

处理待办用 `pending --json` 查看所有 agent 动作（含方法/独立模板）；默认 `pending` 只列来源 ID。草稿方法必须填完必要说明和“知识关联检查”后才交作者确认；文字笔记可无代码，无关联时说明检查范围和原因，不补算法。`check-entry <id>` 查询缺项，核对后 `check-entry <id> --record` 记录验收；确认入口共用检查并自动记录。

来源签核绑定已签版本，重复 ingest 不批准新版本。回放绑定 code/spec/example/接口与三个输出的哈希；改变输入或失败重跑后重新 verify，不能只凭 preview 标 ready。旧回放先以原代码/示例刷新执行证据，不改历史作者确认或宣称任意 n 迁移。验收指纹变化会提示核查，不能为清零伪造证据。

图库与方法页按同一个明示覆盖规则去重，多个来源完整复用同一模板时保留所有来源链接。通用表格检查只保证文件/必需列，类型、缺失、单位、配对与科学前提另由课题 agent/具体方法核对。完整规则见总库 AGENTS.md“入库验收的执行入口”。

### 方法关系与有效状态（2026-10-22）

模板 ready 后，方法 `figure_relations` 的主记录指向模板；来源 layout 只作 evidence。方法仍指向 layout 而该 layout 有 ready 覆盖模板时 `lint` 报错。方法声明输出与模板输入不一致时标 `adaptable`，方法页另列“语义关联的模板（需适配）”并写适配动作；结构匹配栏只显示真正消费输出的模板。关系卡的可用状态取目标页的有效 workflow（如“模板已就绪”），不把来源 `pending_template` 显示成未完成。

### 链条完整性与读取接口（2026-10-22）

方法页必须显示结构匹配模板和需适配模板；每个模板标出读取接口；适配关系在正文写实际 `render-*` 等接口与准备步骤。结构匹配为空时不能只留“暂无”。`lint` 对未说明读取接口的 adaptable 关系报 WARN；结构匹配不是语义直连。

### 接口含义与图型判断（2026-10-22）

接口页必须写“含义”：行单位、单位/编码、准备前提、与相近接口区别；`lint` 对空含义报 WARN。图型页按概念页写选择与对比判断，不只有标题。模板无回放时 preview 从画廊 `files.source_image` 只读展示来源 panel，`layouts/<id>/thumb.png` 标为复刻缩略图。接口页 facts 增加“经模板关联的方法”（adaptable/candidate，经读取该接口的模板），不再只显示“产出/读取方法：无”。

### Obsidian 辅助窗口（2026-10-22）

作者可将 `E:\research-wiki\知识库` 作为 Obsidian vault 阅读与编辑 user 区块；不把项目根/画廊联接进 vault，不改名、移动或删除正式条目。facts/frontmatter/正文分工按正式 AGENTS.md；签核、待办、确认、状态与删除仍走同一网页/CLI workflow。`.obsidian/` 不入 Git，verify 证据仍入 Git。神经图谱仅为只读视觉浏览，不从连线推断语义兼容、有效状态或科学验证，不加入新的编辑/运行/联网功能。

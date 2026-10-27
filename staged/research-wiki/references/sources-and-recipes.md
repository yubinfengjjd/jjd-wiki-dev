# 来源、配方与检索目录（v2 契约，2026-10-27）

本页是开源库入库、L1 配方运行和 `find / show / use` 的实现契约。底线与页面分工见总库 `AGENTS.md`；命令参数以 `wiki.py <命令> --help` 为准（`rwiki <命令>` 等价）。

| 等级 | 存放 | 含义 |
|---|---|---|
| L0 | `sources/<来源>/items.jsonl` 一行一项 | 上游目录项：用途、输入、依赖、许可；可检索、可 `use`（来源 trusted），未在 Wiki 运行 |
| L1 | `recipes/<id>.md` + `recipes/<id>/` | 上游整模块原字节 + 原样运行收据 |
| L2 | `templates/`、`methods/` | 函数化、可换数据；回放与验证收据另见 method-families.md、minimal-runtime.md |

## 配置键

| 键 | 含义 |
|---|---|
| `sources_root` | 上游快照目录（不在 Wiki 内，不进 Git） |
| `work_root` | 配方运行副本、装包日志与临时 R 脚本目录 |
| `r_libs` | Wiki 专用 R 库列表；运行时全部加入 `R_LIBS`，`deps --install` 只装进第一个目录 |
| `cran_mirror` | `deps --install` 用的 CRAN 镜像，缺省 `https://cloud.r-project.org/` |

## 来源页 `sources/<id>.md`

- 由 `source add <id> --title … --url … --license <SPDX> --adapter <名> [--trusted] [--cite …] [--notice …]` 生成并 save；id 用小写字母、数字与连字符。
- frontmatter：`type: source`、`id`、`title`、`url`、`commit`（fetch 后写入）、`license`、`license_notice`、`cite`、`adapter`、`trusted`（布尔）、`snapshot`（快照目录名，缺省等于 id）、`tags`、`keywords`、`summary`。
- 正文：这是什么 / 怎么用 / 许可与引用 / 知识关联检查，加 facts 区块与 user 区块。facts 显示上游 URL 与 commit、白名单状态、快照位置 `<sources_root>/<snapshot>`、L0 项数与自动领域分布、已有 L1 配方。
- 同意边界：登记一个库前确认作者要收它。`trusted: true` 表示作者把该来源列入白名单，`use <来源:条目>` 与 `promote` 按需获取代码不再逐次询问；`trusted: false` 时，`source fetch` 与 `promote` 前先问作者，`use <来源:条目>` 直接拒绝。

## 适配器

- 注册在 `rwiki/adapters.py` 的 `ADAPTERS`；适配器只读快照，不执行上游代码。接口：`BASE_PATTERNS`（首次检出的元数据路径）、`item_patterns(item)`、`scan(...)`、`parse_item(...)`、`main_rmd(...)`、`recipe_id(item)`。新增来源类型要在开发仓库加适配器与测试。
- 目前只有 `figureya`（ying-ge/FigureYa）：每个 `FigureYa*` 目录一个 R Markdown 模块（主 Rmd、`install_dependencies.R`、`easy_input_*`）。基础检出 `/*/*.Rmd`、`/*/install_dependencies.R`、`/gallery_compress/`、`/README.md`、`/LICENSE*`；条目检出整个目录但排除 `*.html` 报告。
- 配方 id 由条目名派生：`FigureYa59volcanoV2` → `figureya-59volcanov2`；扫描时 id 冲突直接报错。

## 快照与稀疏检出

- `source fetch <id> [条目…] [--update]`：首次在 `<sources_root>/<snapshot>` 部分克隆（`--filter=blob:none --depth 1 --no-checkout`）并按 `BASE_PATTERNS` 稀疏检出；给出条目时追加条目目录。来源页记录 HEAD commit（有变化才 save）。
- `fetch` 不主动拉取上游新提交。快照 commit 与来源页记录不同时拒绝；确认要改记录时加 `--update`。已有配方仍指向自己记录的 commit，`restore` 需要同一 commit 的快照。
- `source scan <id>` 从快照重建 L0 目录并 save；已升级为配方的条目在 catalog 里由配方代替。

## L0 目录 `items.jsonl`

一行一个 JSON，按 `item` 排序。字段：

- 身份：`id`（`<来源>:<条目>`）、`source`、`item`、`commit`、`title`、`rmd`（主 Rmd 相对路径）、`recipe`（升级后的配方 id）。
- 说明：`requirement` / `requirement_en`（上游“需求描述”）、`scenario` / `scenario_en`（“应用场景”），各截至约 280 字。
- 输入输出：`inputs`（`[{file, note}]`，至多 12 个）、`outputs`（至多 20 个）。
- 依赖：`packages`（`cran`、`bioc`、`github`、`library`）、`requires`（运行需要的包名，去掉 base R）。
- 发现：`tags`（自动规则，至多 3 个，`tags_auto: true`）、`chart_hints`、`keywords`、`refs`、`thumb_url`、`language`。

自动 tags 只用于检索；配方页的 tags 由 curation 给出。

## 配方 `recipes/<id>.md` 与目录

- `promote <来源> <条目…> [--curation <file.json>]`：先 fetch 条目，再把上游目录原字节复制到 `recipes/<id>/source/`（`.html` 报告除外，记入 `excluded`），写 `source.json`，建 draft 配方页并补齐图型页。全部成功才 save；任一失败就删掉本次新建的页面与图型页，不提交。
- curation 是 `{条目: {…}}`，字段：`title`、`chart_types`、`tags`、`keywords`、`use`、`fit`、`unfit`、`inputs_note`、`runtime_note`；另接受 `inputs_ok`、`heavy`、`note` 作批次整理备注（不写入页面）；其他字段报错。没有 curation 时，用途/适用取上游需求描述/应用场景，不适用留“待补充”，`check-entry` 会拦下。
- frontmatter：`type: recipe`、`id`、`title`、`status`（draft / ready / archived）、`source`（`id`、`item`、`commit`、`url`）、`license`、`cite`、`language`、`runner: rmd-knit`、`entry`（`source/<主 Rmd>`）、`inputs`、`outputs`、`packages`、`tags`、`keywords`、`chart_types`、`summary`、`favorite`。
- 正文：顶部许可提示，facts 区块，然后用途 / 适用 / 不适用 / 输入 / 怎么用 / 输出 / 知识关联检查 / 使用记录（user 区块在“使用记录”里）。facts 列来源与 commit、许可与引用、依赖、最近运行、派生的 L2 模板与运行预览。
- “知识关联检查”初稿列出同图型模板，不建立 `figure_relations`；关系在升级为 L2 时再核对。
- 目录：`source/`（上游原字节）、`source.json`（`schema_version: 1`、`source`、`item`、`url`、`commit`、`license`、`files`{相对路径: sha256}、`excluded`、`copied_at`）、`runs/<run_id>.json`、`preview.png`、`acceptance.json`。

## 运行器

`run <配方 id…> [--timeout 秒] [--jobs N]`（缺省 1200 秒、1 个并行）：

1. 核对 `source/` 与 `source.json` 哈希一致，把 `source/` 复制到 `<work_root>/runs/<id>/<时间>/`。
2. `install_dependencies.R` 换成检查桩：只检查声明的 CRAN/Bioconductor/GitHub 包是否已装，缺包时报 `rwiki: missing packages: …` 并停止。
3. 运行 `Rscript --vanilla _rwiki_knit.R <主 Rmd> rwiki-knit.md`：`R_LIBS` = 存在的 `r_libs` 目录，`R_LIBS_USER` 指向 `work_root` 下的空目录；knitr 直接 knit（不需要 pandoc），读 Rmd 头部 `params`；`install.packages` 被替换为报错，CRAN/Bioc 镜像指向不可达地址，运行中不会联网装包；图存 `rwiki-figure/`（png）；写 `rwiki-session.json`（R 版本与已加载包版本）。
4. 判定：退出码 0 且 knit 成功为 pass；检出缺包为 not_run（列出 `missing_packages`）；其他错误或超时为 fail。
5. 收据写 `recipes/<id>/runs/<run_id>.json`，每个配方保留最近 10 份（更早的仍在 Git 历史里）；pass 且有图时把最后一张图存为 `preview.png`。一批运行一次 save；有任何不是 pass 的条目，命令退出码为 1。

`run --dir <use 副本>`：在课题副本原地运行，原 `install_dependencies.R` 先备份为 `install_dependencies.R.rwiki-orig`。与 `rwiki-origin.json` 相比输入文件有变（不算输出与图、报告类文件）时 scope 为 new-data，否则为 other-dir；收据写副本 `rwiki-runs/`，不写 Wiki。

## 运行收据（schema_version 2）

| 字段 | 内容 |
|---|---|
| `schema_version`、`kind`、`id`、`run_id` | `2`、`run`、配方 id、开始时间（UTC，`YYYYMMDDTHHMMSSZ`） |
| `scope` | `as-is`（Wiki 内原样）/ `new-data`（课题副本换了输入）/ `other-dir`（课题副本未换输入） |
| `state` | `pass` / `fail` / `not_run` |
| `runner`、`command`、`runner_sha256` | `rmd-knit`、实际命令、运行器脚本哈希 |
| `started_at`、`duration_s`、`exit_code` | 超时时退出码为 null |
| `environment` | `r_version`、`lib_paths`（标签）、`packages`（已加载包版本） |
| `code`、`outputs` | 运行时代码文件哈希、本次新增或改变的输出哈希 |
| `expected_outputs`、`missing_outputs`、`figures` | 页面声明的输出、缺失的输出、捕获的图 |
| `missing_packages`、`error`、`checks` | 精确缺包、错误摘要、实际做过的检查 |
| `workdir`、`changed_inputs`、`scope_note` | 运行目录标签；`run --dir` 时变更的输入；范围说明 |

- 收据会提交，本机路径一律换成标签：`<wiki>`、`<work_root>`、`<sources_root>`、`<r_lib0>`…、`<R_HOME>`、`<home>`、`<workdir>` / `<copy>`，其余绝对路径为 `<abs>`。
- “当前收据”是 `code` 与当前 `source/` 哈希相同的最近一份；source 字节一变，旧收据不再代表当前版本。
- 收据只证明“在记录的环境里跑通”，不证明统计或科学有效。

## use 副本

`use <id | 来源:条目> --project <课题> [--name <名>]` 复制到 `<课题>/wiki-use/<名>/`：课题目录必须存在且不在 Wiki 内，目标目录不能已存在（换 `--name`）。

| 条目 | 复制内容 | 另写 |
|---|---|---|
| L0（`来源:条目`） | 先 fetch 条目，复制上游目录（不含 `.html`）；来源须 trusted | — |
| L1 配方 | `source/`（哈希不符时先 `restore`） | — |
| L2 模板 | `code/`、`example/`、`spec.json`、`runtime.json` | `bindings.draft.json`：每张表 `file = <接口>.csv`，列为同名映射 |
| L2 方法 | `code/`、`runtime.json`（没有 `code/` 的文字笔记拒绝） | — |

- 每个副本都写 `rwiki-origin.json`（`id`、`kind`、`level`、`entry`、`packages`、`outputs`、`license`、上游或页面、`commit`、`copied_at`、`files`{路径: sha256}）与 `RWIKI-USE.md`（许可提示、来源、运行命令、输入文件表与示例表头，模板另有列映射说明）。
- 命令输出含 `missing_packages_in_wiki_r`：Wiki 专用 R 库里还缺的包。
- `use` 不提交 Wiki；课题里的数据、改动与成图留在副本。

## 依赖与装包审批

- `deps <配方 id | 来源:条目…>`：汇总 `cran` + `bioc` + `library()` + GitHub 包名（去掉 base R），用 Wiki 专用 R 库检查缺哪些，按条目列出并给并集与 GitHub 仓库。只读，不装包。
- 审批：agent 把一批缺包清单（条目、包名、来源 CRAN/Bioconductor/GitHub、已知的重依赖）交作者；作者按批次批准一次后才执行 `deps <同一批…> --install`。批准范围写进批次记录。
- `--install` 用 BiocManager（缺时先装）按 `cran_mirror` 装进 `r_libs` 第一个目录；`--github` 另用 remotes 装声明的 GitHub 仓库（单个失败只记日志）。日志在 `<work_root>/deps-install-<时间>.log`，结果列 `installed` 与 `still_missing`。
- 不往课题环境、系统库或 `r_libs` 的其他目录装包。目前 `deps` 只读配方与 L0 条目的依赖声明；方法与模板的依赖写在 `runtime.json`，缺包写 not_run 并列进批次清单交作者。

## restore

`restore <配方 id…>`：限制性许可配方的 `source/` 不进 Git，新检出里没有。restore 要求来源页 commit 与 `source.json` 的 commit 相同，从快照取回条目，先放进暂存目录核对全部哈希，一致才替换 `source/`；不一致时什么都不替换。

## 许可与 .gitignore 托管块

- 限制性许可：GPL 系（GPL、AGPL、LGPL）与 CC-BY-*-NC/SA/ND（如 FigureYa 的 `CC-BY-NC-SA-4.0`）。
- 托管块在知识库 `.gitignore` 的 `# >>> push-guard gpl` 与 `# <<< push-guard gpl` 之间，save 与 `gh guard --sync-ignore` 重写，块外字节不动：
  - GPL 系方法：`methods/<id>/code/`、`methods/<id>/source/`；
  - 限制性许可配方：`recipes/<id>/source/`；
  - 限制性许可模板（含从这类配方派生的模板，`license` 随 `scaffold-template --from-recipe` 继承）：`templates/<id>/code/`、`templates/<id>/example/`。
- 这些目录不进 Git、不推送；`source.json`、`runs/`、`preview.png` 与页面照常提交。pre-push 的 `gh guard` 另按路径与许可头拦截。
- 许可提示：`CC-BY-NC-SA-4.0` 有内置提示（仅限非商业、署名并引用、改编须相同方式共享、源码与派生代码不进 Git）；其他许可用 `--notice` 或通用提示。提示写在配方页顶部和 `RWIKI-USE.md`。

## catalog.jsonl 与 find

- save 重建 `catalog.jsonl`：一行一条，按场景、模板、配方、方法、L0 目录项排序；归档页不收，已升级的 L0 项由配方代替。缺文件时 `find` 现场计算；与页面不一致时 lint 报 WARN。
- 公共字段：`id`、`kind`（scenario / template / recipe / method / item）、`level`、`title`、`summary`、`chart_types`、`tags`、`keywords`、`page`、`use`（下一步命令）。
- 按类型另有：模板 `status`、`usable`、`not_for`、`inputs`（接口）、`language`、`license`；配方 `status`、`usable`、`run`（最近当前收据的 state 或 none）、`missing_packages`、`scenario`、`not_for`、`inputs`（文件）、`requires`、`language`、`license`、`source`；方法 `status`、`usable`、`method_kind`、`purposes`、`not_for`、`inputs`、`outputs`、`license`（`level` 在方法可用时为 L2，否则为 note）；场景 `picks`（`level` 为 `-`）；L0 项 `status: catalog`、`run: none`、`scenario`、`inputs`、`requires`、`language`、`license`、`source`、`thumb`。
- `usable` 与“可用”同义：ready、验收记录未过期、当前收据通过（配方 pass，模板有当前回放，分析方法有已验证实现）。
- 排序：关键词命中标题/id 3 分、用途/场景 2 分、关键词/输入/依赖/图型/用途分类 1 分；三字以上中文词按二字片段部分匹配；图型别名与受控领域词扩展各自加分；查询命中某个场景时，它的 `picks` 中本身也命中查询的条目再加 3 分（“场景首选”）；usable 或运行 pass 再加分。`--kind`、`--level`、`--runnable`（只留可用模板/方法与运行 pass 的配方）过滤，`--limit` 缺省 8。
- `show <id>` 给出用途、适用/不适用、输入（模板列出每张表的接口列与必需/可选）、许可提示、最近运行与下一步命令；L0 项写成 `来源:条目`。

## 场景页 `scenarios/<id>.md`

- frontmatter：`type: scenario`、`id`、`title`、`picks`（`[{id, note}]`，id 为 `templates/<id>`、`recipes/<id>` 等页面路径、页面 id，或 `来源:条目`）、`tags`、`keywords`、`summary`。
- 正文：什么时候用 / 首选组合 / 注意，加 facts 区块（首选表：级别、状态、说明）与 user 区块。
- 首选条目不存在或已归档时 lint 报 ERROR。查询命中场景标题、摘要、关键词或领域时，其首选在 `find` 里排前。

## 画廊来源（sci-figure-replica 复刻）

画廊是来源之一：

- 画廊条目由 sci-figure-replica 复刻产生。复刻前先读图列去重样式卡（代表裁图、来源位置、视觉编码、附属结构、已有模板与差异、不确定点），每个选定样式只做一个代表单 panel；缺原始数据先说明缺口，问作者本次用估读还是合成。
- `ingest-figure <条目>` 建或更新 layout 页（待签核，作者在网页签核）：画廊 `scenarios.primary/secondary` 的受控标签进 `tags`，`scenarios.free` 进 `keywords`；补写适用/不适用。
- 模板化：`scaffold-template <版式 id> --chart-type … --panels …`；相同画法用 `attach-template` 复用，模型/指标/颜色变化是参数，不新建模板。`verify-template` 后作者确认 `mark-ready <模板 id>`，不要求 `verify-layout`。只有要把 layout 本身标为 ready 时，才为已选 panel 做布局与 preview（单 panel 用 1×1）并 `verify-layout`。
- 来源 panel、整图、`original_code/` 留在画廊；Markdown 只存路径、哈希、bbox 与证据（见 method-families.md“来源 panel 存储”）。图库保留“单 panel 图样 / 可调用模板”两个可重叠视图，按明示覆盖去重。

## 确认、验收与待办

- `check-entry <id> [--record]`：查必需节是否空白或仍是占位（如“待补充”）与 frontmatter；配方另查原字节一致且当前收据 pass，模板另查当前回放，方法另查 `figure_relations` 结构与引用的接口。`--record` 保存 `acceptance.json`。只核对结构与证据，不替代科学审查。
- `mark-ready <id…>`：单个 id 走各类型的确认检查；多个 id 只用于配方、模板与方法（layout 逐个确认），先全部核对，任一不通过则全部不改，一次 save。网页确认配方用同一检查。
- 模板确认要求当前版本的完整成功回放（绑定 code、spec、示例数据、接口列与 PNG/PDF/SVG 输出哈希），只有 preview 不行；`verify/` 回放证据进 Git。
- 模板必须记录来源：`layouts`（画廊版式）或 `sources`（如 `recipes/<id>`），缺来源 lint 报 ERROR。归档来源若是某个未归档模板的唯一出处，删除被拒绝。
- `pending --json`：与网页共用 workflow，列出 agent 动作与待作者确认项。配方：“待装包”（最近运行 not_run，装包须作者按批次批准）、“待补齐”（缺收据、运行失败或页面缺项）、“待你确认”（draft 且运行通过）；模板与方法按回放、验证与笔记完整性派生。ready 条目验收记录过期时重新列出。不为清零伪造证据或改状态。

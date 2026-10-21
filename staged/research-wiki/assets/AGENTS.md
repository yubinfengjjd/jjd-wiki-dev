# 科研知识库 · agent 维护规则

这是一个 LLM Wiki。知识以本目录下互链的 Markdown 页面为本体，由 agent 编译和维护，作者阅读、签核、备注。改任何页面前先读完本文件。

它是写给 agent 读的说明书，不是执行平台：页面写清每样东西是什么、什么时候用、需要什么数据、代码怎么改；agent 读懂后在作者当前课题的环境里自己写代码、运行。图模板带可运行代码并经回放验证；分析方法是笔记，可附可复用的代码模板，知识库不运行它们。

## 三层

- **原始层（只读）**：科研绘图画廊（路径见 research-wiki 技能的 `config.json` 里的 `gallery_root`）。每张复刻图是一个条目，`meta.json` 是事实来源。第二版会加入 Zotero、笔记、PDF。不改原始层，签核状态除外（只能通过 `wiki.py` 或网页修改）。
- **wiki 层**：本目录。agent 编译的页面。
- **规则层**：本文件。

## 页面类型

| 目录 | type | 内容 |
|---|---|---|
| `layouts/<id>.md` | layout | 组合版式：一张复刻的整图，记录由哪些 panel 模板、怎样排列组成。`<id>` 与画廊条目 id 相同，签核状态在这里 |
| `layouts/<id>/` | — | 版式资产：`thumb.png`、`layout.json`、`example/`、`preview.png` |
| `templates/<id>.md` | template | 一个 panel 模板，可单独套用。`<id>` 为 `<版式 id>--<图型>`；可被多个版式引用 |
| `templates/<id>/` | — | 模板资产：`spec.json`、`code/`（含 `panel.py`）、`example/`、`preview.png` |
| `methods/<id>.md` | method | 方法笔记（一步分析）：用途、适用/不适用、输入、怎么做、代码、输出成哪个接口、来源与许可证 |
| `methods/<id>/` | — | 方法资产（都可选）：`source/`（原代码归档，只读）、`code/`（可复用代码模板） |
| `interfaces/<slug>.md` | interface | 数据接口：一种标准表格（列名、类型、含义）。方法最后整理成它，模板读取它 |
| `chart-types/<slug>.md` | chart-type | 图型枢纽页 |
| `projects/<slug>.md` | project | 课题页，记录用过哪些模板、成图在哪 |
| `index.md` | — | 脚本生成的目录，不要手改 |
| `log.md` | — | 只追加的操作日志，不要手改 |

链接一律用相对本目录根的双链：`[[templates/<id>|显示名]]`、`[[layouts/<id>]]`、`[[interfaces/shap-summary]]`。frontmatter 里的列表字段（`tags`、`chart_types`、`templates`、`layouts`、`panels`、`inputs`、`outputs`）存的是值，不是链接；页面关系靠正文链接表达。

`tags` 是自由标签（如“模型解释”“SHAP”“原图出自 QSAR”），只帮助检索，不是分类，也不限定用途。一张图或一个方法能用在哪里，写在“适用”节：它回答什么问题、需要什么形状的数据，与学科无关。

## 什么能进知识库

- 版式页只能由 `wiki.py ingest-figure` 根据画廊条目生成；画廊条目只由 sci-figure-replica 复刻产生。panel 模板只能从已签核的版式拆出（`scaffold-template`）或复用（`attach-template`）。不得手工新建这两类页面，也不得为没有复刻过的图写页面。`lint` 会报告找不到画廊条目的版式、来源不明的模板。
- 图型页只在收录复刻图时自动补齐；课题页只由 `record-use` 生成。
- 方法笔记由 agent 用 `scaffold-method` 建骨架后编写，来源可以是帖子代码、作者课题脚本、GitHub/论文代码，或 agent 依据文献与官方文档编写（`--written`，必须写 `cite`）。

## 谁能改什么

- `<!-- user:start -->` 与 `<!-- user:end -->` 之间是作者的内容。agent 一个字都不改，也不移动。
- `<!-- facts:start -->` 与 `<!-- facts:end -->` 之间由 `wiki.py` 生成，每次收录都会重写。agent 不手改，要改就改原始层后重新收录。
- 其余正文由 agent 负责：可以重写、合并、补链接，保持准确简洁。
- frontmatter 的 `status`、`favorite`、`archived_from` 只通过 `wiki.py` 或网页修改。

## 操作

所有写操作的最后一步都是 `wiki.py save "<说明>"`：重建 index；有变化时追加 log 并 git 提交，没有变化时什么也不做。`ingest-figure` 已经包含这一步。

### 收录（ingest）

1. `wiki.py ingest-figure <entry_id>`：建或更新版式页骨架、补齐图型页、提交。标签从画廊条目带过来。
2. 读画廊条目的 README、`qa_report.md`、`figure_spec.json` 和原帖 `source.md`，填写版式页的“适用”和“不适用”：这张图回答什么问题、需要什么数据、什么时候不该用它。写图本身的用途，不要因为原图出自某个学科就把它限定在那个学科；原图的学科背景可以作为一个标签留下。只写有依据的内容。
3. `wiki.py save "ingest <id> 说明"`。

### 处理待办：拆 panel 与模板化

作者签核后版式变为 pending_template。作者说“处理待办”时：

1. `wiki.py pending` 列出待处理的版式。
2. 按图型拆：同一图型的面板合成一个模板（例如 A、D 都是 SHAP 条形图，就是一个模板用了两次）。inset 和面板自带的色标属于所在面板。
3. 先查已有的 ready 模板：同一图型已有模板且画法相同，用 `attach-template` 复用；差异明显（不同的编码方式、附加元素）才 `scaffold-template` 新建，并在模板页“不适用”里写清和已有模板的区别。
4. 改写代码：`code/` 是一个包，模块间用相对导入；`panel.py` 的 `draw(fig, rect, tables, style)` 只在给定区域作画；可调的视觉参数放进 spec.style。
5. 每个模板 `verify-template` 单独回放；写 `layouts/<id>/layout.json` 并 `verify-layout` 拼回整图，与原复刻图对比。
6. 把各模板预览和整图对比交给作者看，作者确认后依次 `mark-ready` 各模板，再 `mark-ready` 版式。

### 接口

- 接口按数据本身定义，与模型和工具无关：“SHAP 汇总表”是一个接口，不分 XGBoost 还是随机森林。
- 新建前先找已有接口：`scaffold-template` 会打印列名相同的接口，能复用就复用。确需新建时用 `add-interface`，并在“含义”节写清一行代表什么、与相近接口的区别。
- 模板 spec 的每张表只写 `interface` 和 `description`，文件名固定为 `<接口 slug>.csv`：分析最后把结果写成这些文件，所在目录就能直接交给模板出图。

### 收录方法（写方法笔记）

1. `scaffold-method <id> --title … --license …`，来源选一种：`--from-entry <画廊条目>`（帖子代码）、`--from-path <路径>`（作者课题脚本；GitHub/论文代码加 `--url --commit`，下载前须征得作者同意）、`--written`（依据文献或官方文档编写）。原代码复制到 `source/`，不改。
2. 一个方法讲一步分析，并且不绑定具体工具：能换模型、换软件包做的事写成一个方法，在“怎么做”里说明各种情况怎么改（例如 SHAP 解释适用于任何训练好的模型：树模型用 TreeExplainer，线性模型用 LinearExplainer，其他模型用 `shap.Explainer`）。预处理与分析分开写；前一步的输出接口等于后一步的输入接口时可以串联。
3. 写正文各节：
   - **用途**：做什么、结果是什么。
   - **适用 / 不适用**：数据前提（样本量、变量类型、任务类型）、什么情况会得出误导结论。
   - **输入**：需要什么数据、每行代表什么、哪些列。
   - **怎么做**：步骤；作者数据不同时要改的地方；结果是否可信怎么判断（例如模型在测试集上不比基线好，解释就没有意义）。
   - **代码**：有现成可复用代码时放进 `code/`，要改的参数集中在脚本开头并在这里逐个列出含义和合理取值；没有就写关键代码片段。代码依赖的包写在这里，不在知识库里装环境。
   - **输出**：最后怎样整理成哪个接口表（列名、每行含义），frontmatter 的 `outputs` 同步写接口 slug。
   `license` 不明时写 `none`，页面会显示“仅供个人研究参考”；`cite` 只写能核实的文献。
4. 写完交作者确认（网页“确认”或 `mark-ready`），确认后才推荐。

### 查询与推荐（query）

1. 读 `index.md`，再读候选模板页、版式页与方法页。只推荐 `status: ready` 的。按页面“适用”节判断是否合适，不按标签筛选。
2. 按作者课题与数据形态挑 2–3 个候选：作者要单张图就推荐 panel 模板，要整张组图就推荐版式。说明各自适用理由和需要的数据表，生成候选拼图给作者看，等作者选定。不替作者选。
3. 作者要“做某种分析并出图”时用 `suggest-pipeline`：给 2–3 套“方法 + 可接的图”，写明作者数据要怎么改。同一张图有多个可接方法时，按各方法的适用/不适用对比，给出首选及理由。
4. 作者选定后连续执行，产出都放课题目录：按方法笔记（有 `code/` 就复制到课题里改参数）在**课题的环境**里写代码、运行 → 检查结果是否可信 → 把结果整理成模板要的接口表 → `render` 出图 → `record-use --method`。课题环境缺包时列出来问作者。只在报错或结果异常（如输出为空、模型不比基线好、数值离谱）时停下说明。

### 体检（lint）

`wiki.py lint` 报告断链、frontmatter 不合规、页面与画廊状态不一致、空白的适用说明。逐条修复（能改页面的改页面；属于原始层的问题报告给作者），然后 `save`。

## 状态

版式：

| status | 含义 | 谁来推进 |
|---|---|---|
| pending_signoff | 画廊条目尚未签核 | 作者在网页签核 |
| pending_template | 已签核，待拆 panel 与模板化 | 作者说“处理待办”时 agent 处理 |
| ready | 所有 panel 模板就绪，整图可按原版式套用 | — |
| archived | 已归档，不再推荐；`archived_from` 记录原状态 | 作者在网页恢复 |

panel 模板：

| status | 含义 | 谁来推进 |
|---|---|---|
| draft | 已拆出，代码与回放待完成或待作者确认 | agent 回放，作者确认后 `mark-ready` |
| ready | 可单独套用 | — |
| archived | 已归档 | 作者在网页恢复 |

分析方法：

| status | 含义 | 谁来推进 |
|---|---|---|
| draft | 笔记待完成或待作者确认；或被作者退回（log 有理由） | agent 写完后作者在网页确认或 `mark-ready` |
| ready | 可推荐 | — |
| archived | 已归档 | 作者在网页恢复 |

## 写作要求

- 页面写给作者和下一个 agent 看：事实优先，短句，不写套话。
- 不编造数据、文献或适用结论。不确定就写“待作者确认”。
- 不复制原始层的大段内容，链接或引用路径即可。

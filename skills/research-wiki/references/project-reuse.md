# 在课题中查方法、选图与适配

本流程由当前课题中的 agent（Claude Code、Codex、Kiro、opencode 等）执行。Wiki 提供知识与代码，不扫描课题磁盘、不判断科学适用性，也不在网页运行分析。

## 课题本地状态（2026-10-24 新增）

课题证据、前提、主线、授权、任务与运行收据写在 `<课题>/wiki-use/_project/`（`wiki.py project …`），只写课题目录、不调用 Wiki `save`。登记原生对象（`add-object`，无需转 CSV/统一列；`--inspected --adapter` 标记实际解析过的对象，接受文件名不等于已解析语义）、观察与依据（`add-observation`，verified/author_stated/unknown 分开，verified 观察需可检查证据文件才算高层依据）、主线（`add-route`）、执行约定与预算（`add-authorization`）、候选任务（`add-task`）与实际运行（`record-run`，completed 须有实际命令+存在的输出+检查项；输入缺省沿用任务声明依赖）。`check` 做结构/路径/指纹核查并把 stale/unknown 沿依赖传到下游任务，`impact` 按已登记依赖与 file/object/artifact 路径别名分析变更影响，`evaluate` 按声明式领域配置评估前提（同层冲突报 conflicted，材料过期不满足，`--subject` 限定一致上下文，未知保持 unknown）。复制/移动的课题先 `project relocate`。完整命令与写语义见 [课题状态与证据层](project-state.md)。

发现候选分析时分两类：`suggest-methods` 仍只返回当前可执行（ready_for_use）的家族；`discover-methods` 是只读机会清单，额外列出规范 analysis 笔记的未验证分支与缺口，`executable` 仅当页面 ready_for_use 才为真——机会不是推荐，workflow/technical 资料和归档页永不升为候选，库外缺口只留课题候选。执行前仍逐项核查前提、分支收据与课题环境。

## 两个入口

“课题还能做什么分析”：先读当前课题已有计划、数据说明、代码入口、必要结果表头和运行日志。明确研究问题、当前阶段、样本/行单位、验证设计、已完成工作及证据、现有材料和未知条件。代码文件存在不证明运行完成；缺研究目的或关键前提时先问作者。

“已经跑完，选适当的可视化”：先查实际结果的含义、每行单位、量纲、配对/重复层级和摘要定义，再查图样。无需为了选图而新增一个方法页。

用 `rwiki`，或 research-wiki 技能专用的 Wiki 解释器调用该技能目录的 wiki.py（路径见该技能 SKILL.md/config.json）：

```text
wiki.py find 研究场景 图型 分析名 [--runnable]       # 读 catalog.jsonl：L0–L2 条目与场景首选
wiki.py show <id>                                    # 用途、适用/不适用、输入、许可、最近运行
wiki.py suggest-methods --q "当前研究问题和可用材料" --limit 5
wiki.py suggest --q "实际结果含义和想表达的问题" --columns 实际列名 --limit 5
wiki.py suggest-pipeline --q "分析目的"
```

命令提供检索线索。列名/接口不同不能排除语义上合适的方法；同名也不证明兼容。读候选正文、接口含义和明确记录的 figure_relations，再做判断。正式推荐（可直接执行）限于可用条目：`find --runnable` 只列可用的模板/方法与原样运行通过的配方。L0 目录项与 draft 条目可以列为候选，但要标明“未在 Wiki 运行”或“未经作者确认”；图样参考需明确待模板化。归档条目不再推荐。选定后用 `wiki.py use <id> --project <课题>` 把代码复制到 `<课题>/wiki-use/<名>/`，按副本里的 `RWIKI-USE.md` 换数据。

## 给作者的候选

优先给少量“当前可做项”，再列少量有明确价值的“补材料后可做项”。逐项写：要回答的问题、为何适合当前课题、项目证据、Wiki 页面、已有材料、缺口/适配、代码实际状态（具体到 `verified`/`not_run` 分支）、可配图样、下一步。待核实不能当作可执行方案。没有合适库存就如实说明。

页面 ready、语义关系直接可接、代码有文件、示例已跑、某分支 `verified`、`portability=verified`、真实课题已验证是不同事实。不能用任一项替代其他项；只复述收据中列明的分支与范围。先让作者选定方案；已有明确选择与计划则不重复咨询。

复制实现到课题时，按该方法/模板的 `runtime.json` 只带 `files` 和 `resources`，不复制完整来源库，也不把知识库环境当课题环境。清单标 `bundle`/`unknown` 的条目不能宣称为独立模块；缺 `required_packages` 时先在课题环境确认，缺包列出包名问作者，不往课题环境装包。登记运行/使用时写清代码来源是 Wiki 分支还是课题自有：真正的实现复用是选科学兼容的已验证分支、复制其声明文件/资源、在新进程用显式输入/参数调用所复制入口并保留范围与诊断；受托管 render 或课题内准备脚本不构成实现运行证据，绑定与收据须对应实际调用的代码。

## 选定后的适配边界

含义清楚且不改变分析逻辑时，可在课题副本中重命名列、调整列顺序、整理文件名、长宽表转换。优先用显式 `render --bindings` 完成列/文件映射，保留原表；也可写成标准 `<接口>.csv`。在项目环境复制所需代码并运行，继续通过 render 的必需文件/必需列检查，并由课题 agent 和具体函数核对类型、缺失、单位、实体/配对与方法前提；表头通过不是科学有效性证明。不关闭结构检查以获得兼容。

### 显式 bindings

`bindings.json` 由 spec 的表键定位；`columns` 方向是“内部字段 → 作者列”，`file` 相对 `--data`：

```json
{"tables": {"dotplot": {"file": "my_results.csv", "columns": {
  "group": "cell_type", "feature": "gene_symbol",
  "avg_expression": "mean_expr", "pct_expressed": "positive_percent"}}}}
```

- 缺必需表/列、未知表或字段、重复映射、重复源表头、越界/网络/隐藏路径、非法数值都在执行前失败；不按相似度猜列。
- 只允许无聚合 melt/pivot，显式 id/变量/值列；pivot 重复键拒绝，不自动求均值或补格。额外原始列保留（除非 reshape 明确未 carry，报告会列出）。
- 映射报告写在输出目录 `bindings-report.json`：源路径/哈希、映射、缺失可选项、观测范围、检查、警告。原表不改。
- 字段名吻合不证明单位、粒度或配对；0–1/0–100 只提示，不换算。标准输入的 verify 收据不扩大为外部文件已验证。
- 可复制实现：`rwiki/input_binding.py`（Python，stdlib）与 `assets/input_binding.R`（R）；见 [灵活输入契约](input-binding.md)。

例如 observed/predicted → y_true/y_pred，只有在结局定义、量纲、验证来源和每行身份一致时才是格式映射。model_A/model_B 宽表转 model/value 长表须保留案例键、模型名、缺失值和全部数值。不要仅因名字相似就建立通用别名。

以下不属于格式适配：聚合、删行、缺失值填补、补样本、重算统计量、单位换算、阈值/验证划分/估计量改变。含义不明、重复样本身份不清或缺关键数据时，说明具体缺口并问作者；涉及统计逻辑改变或补分析算法也先问。

核查源文件哈希未变、列映射无冲突、关键值/实体/单位保持、排序显式。长宽转换按主键和值检查可还原，不能要求前后总行数相同。报错保留现场；缺包列出包名问作者，不往课题环境装包。L1 配方副本可用 `run --dir <副本>` 在 Wiki 专用 R 库原地运行，收据留在副本 `rwiki-runs/`，不写 Wiki；Wiki 专用库要装包时，按批次经作者批准后 `deps --install`。

## 记录与回存

复用项目已有等效记录；无约定时在 `<课题>/wiki-use/<本次标识>/` 写：

- `context.json`：研究问题、阶段、行单位、验证设计、材料/已完成工作的证据路径、未知项。
- `recommendations.md`：当前可做/需补材料、候选理由、Wiki 引用、关系兼容与代码验证范围、作者选择。
- `mapping.json` 和必要的适配脚本：源/目标路径及哈希、列映射/表形状、保留键、检查结果、使用的代码版本与调用环境。
- 运行和使用记录：实际命令、结果路径及检查——检查项与检查者如实记录；无图像读取能力时目视检查标待办并写明由谁核查，不在收据记未做过的目视确认。
- 任务登记家族/实现按实际执行的操作、输入输出、单位与算法绑定：消费既有标签/预测/结果文件不等于执行产生它们的算法（评估既有预测≠训练、绘制构象≠对接、汇总既有标签≠聚类）；无匹配规范家族时用未绑定的课题内任务加显式来源，库内缺口如实保留，不为通过核查新建正式家族。
- 正式回写（仅当任务授权明确包含正式 Wiki 写入时）：出图后 `record-use` 引用课题产物。
- 只复用了方法、未出图（同样在正式写入授权内）：`record-method-use --method <方法 id> --project <课题 slug> --title "<课题名>" --project-root <课题> --run <run_id>`——把一个 `completed` 且收据结构完整、产物指纹现行、输入指纹未变的课题运行登记到项目页"使用的方法"与方法页"使用记录"。失败/未完成/产物 stale 或指纹不符的运行一律拒登；不产生图、不写图页，区别于 `record-use`。
- `record-use`/`record-method-use` 是正式 Wiki 写并可能提交 Git，与只写课题目录的 `project record-run` 完全不同：授权只含隔离实验或明确禁止正式写时不要调用，证据留在课题状态层与 lesson 草稿；图完成或运行登记本身不构成回写授权，明确任务边界优先于通用步骤。

不复制课题原始数据进 Wiki。本次映射先留项目；有通用价值时提出拟回存内容、适用条件、证据与拟改文件，作者再次确认后才回存。不能自动覆盖原生源码或把一次课题列名变为全库要求。

课题中形成的选择规则、失败模式与适配教训，先登记为课题状态层的 lesson 草稿（`project add-lesson`，`--evidence` 证据引用与 `--applies-to` 适用范围均必填；同命题同范围同链接自动合并，无界命题不收）；经 `project lesson-review` 由署名评审处置（accepted 须附已登记的 `decision:` 作者决策）后，仍走正式 Wiki 评审回填到 `projects/<slug>.md` 或相关图型/接口页正文——accepted 草稿只是候选提案，不是已入库知识；deferred/rejected 永不进正式推荐。只回填判断，不复制数据与成图。不要只留在 `wiki-use/` 或对话里。

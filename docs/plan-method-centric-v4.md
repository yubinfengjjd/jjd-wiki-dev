# Research Wiki v4 架构重构与实施计划（双模型审查修订版 v4.1）

> **状态**：**v4.1（已吸收 Codex `gpt-6.2-sol` + Antigravity 独立只读审查意见修订）**，待用户最终确认后施工（**尚未改动任何业务代码**）。
> **需求基线**：基于 `socratic-project-manager` Q001–Q009 访谈裁决。
> **规范文件路径说明**：文中后端模块位于 `开发/skills/research-wiki/rwiki/`，MCP 服务位于 `开发/skills/research-wiki/mcp_server.py`，前端位于 `开发/apps/web/`，知识库位于 `wiki/`。

---

## 一、 核心定位与用户裁决基线（Q001–Q009）

| 编号 | 核心维度 | 用户明确裁决 | 架构落地准则 |
|---|---|---|---|
| **Q001** | **前端核心定位** | **A. 方法导航为主，图在方法页内展示；保留本机试跑接口但退居次席** | 主链路：**按数据类型找方法 → 看输入/输出对象契约 → 在方法页内看配套可视化模板与参考配方 → 看下一步多重可选分支 → 复制/派发代码（试跑退居次席抽屉）**。 |
| **Q002** | **方法分类导航轴** | **B. 一级按数据类型（组学域），二级按研究目的（Purpose）** | 参考光热生信的科研直觉分类（不复刻零代码在线跑大队列），顶部一级先选**数据类型域**，域内按**研究目的**分组展示方法。 |
| **Q003** | **模板命名简化** | **A. 改为简短语义化 slug + 旧 ID 别名兼容迁移** | 31 个现存模板统一迁移为短 slug，旧 ID 存入 `aliases`，通过全入口解析器兼容历史引用并同步迁移收据与保护基线。 |
| **Q004** | **Agent 下一步多路推荐** | **C. 混合机制（精选分支 + 对象推导候选），CLI / HTTP / MCP 统一** | 拒绝死板单链，增量扩展 `suggest_next_steps`：保留旧字段兼容性，同时返回 `curated_branches` + `object_compatible_candidates` + `attached_visualizations`。 |
| **Q005** | **可视化与方法的关系** | **C. 混合挂载（主归属 + 对象兼容 + 通用绘图独立成类）** | 模板通过 `primary_method` 明确主展示归属（不伪造验证结论），通过严格语义接口匹配 + 显式提取转换映射呈现对象兼容图样，通用统计图归入「通用绘图与统计」。 |
| **Q006** | **重构边界** | **A. 重写前端视图与信息架构，保留 React+Vite 与 Python 后端（按需扩展接口）** | 保留 Python 校验/收据/Git 底座；重构前端视图及后端 `hub`/`aliases`/`next` 接口。 |
| **Q007** | **一级数据类型分类（7 大类）** | **A. 7 大独立数据类型域** | `single-cell`、`spatial-omics`、`bulk-transcriptomics`、`genomics-epigenomics`、`clinical-prognosis`、`multi-omics`、`general-viz-stats`。 |
| **Q008** | **配方与技术/流程页归置** | **A. 配方挂方法下作参考实现；technical/workflow 收进二级「资料与检索」区** | 146 配方按多对多方法归属挂入方法页折叠栏（保留未匹配清单）；22 `technical` + 6 `workflow` + 35 `interface` + `sources` 迁入资料区。 |
| **Q009** | **计划审查机制** | **A. Orca Codex (GPT-6.2) + Antigravity 只读审查并汇总** | 已完成双模型交叉审查并吸收所有高危阻塞点（详见第七节审查汇总与修订清单）。 |

---

## 二、 知识模型与分类体系（双层正交分类 + 不破坏 `tags` 词表约束）

### 2.1 一级「7 大数据类型域 (`data_domains`)」与二级「12 类研究目的 (`PURPOSES`)」

针对审查指出的 `config.json` 外部 `scenario_taxonomy.yaml` 优先级与 `tags.py` 严格检验陷阱，采用**解耦而不破坏兼容**的设计：
1. **保留现有 `tags` 与 `开发/docs/scenario_taxonomy.yaml` 完全兼容**：
   - 不删除或修改现有 `scenarios` 键名与旧中文 `label`（保证 `test_controlled_tags.py`、`tag_errors` 与外部 `config.taxonomy` 继续 100% 合法，已有 `proteomics`、`metabolomics`、`computational-drug-design`、`imaging-radiomics` 等内容不丢失、仍可检索）。
2. **引入独立受控字段 `data_domains`（7 大规范域）与统一归一化函数 `domains_for(meta)`**（存于 `开发/skills/research-wiki/rwiki/method_taxonomy.py`）：
   - 7 大规范域 Slug 与中文展示名：
     1. `single-cell`：单细胞转录组
     2. `spatial-omics`：空间转录组
     3. `bulk-transcriptomics`：Bulk 转录组
     4. `genomics-epigenomics`：基因组与表观遗传
     5. `clinical-prognosis`：临床与预后建模
     6. `multi-omics`：多组学整合与泛癌
     7. `general-viz-stats`：通用绘图与统计
   - **显式标注优先 + 保守历史映射**：在全部 21 个 `analysis` 方法页显式写入 `data_domains: [...]`（**绝不**把跨单细胞与 Bulk 的 `differential-expression`、`gene-set-scoring` 盲目全猜为 `bulk-transcriptomics`，而应按实际适用范围标为 `["single-cell", "bulk-transcriptomics"]`；`shap-explanation` 标为 `["clinical-prognosis", "general-viz-stats"]` 等）。无 `data_domains` 的历史页面由 `domains_for(meta)` 做保守映射，未命中者归入可检索兜底视图；所有统计计数**按 canonical 页面严格去重**，空域计数显式为 `0`。
   - `/api/method-taxonomy` **保留原有顶层字段**（`total`、`domains`、`purposes`、`unclassified`），并**增量新增** `data_domains`（按 7 大域聚合、按页面去重）供新前端使用。
3. **扩展 `PURPOSES`（8 → 12 个受控值）**：
   - 保留原有 8 个：
     `预处理与质量控制`、`整合与批次校正`、`降维与聚类`、`注释与参考映射`、`差异与功能分析`、`轨迹与动态分析`、`模型评价`、`模型解释`
   - 新增 4 个：
     `细胞通讯与微环境`、`变异与表观调控`、`生存与预后建模`、`集合与通用统计`
   - 同步更新 `开发/skills/research-wiki/tests/test_method_taxonomy.py` 中硬编码 `len(PURPOSES) == 8` 的断言。

### 2.2 补齐 6 个核心 `analysis` 方法锚点页（按科学目的严格去重，不虚构已验证实现）
1. `cell-cell-communication`（细胞通讯与配受体网络分析）— `data_domains: [single-cell, spatial-omics]`，`purposes: [细胞通讯与微环境]`，`inputs: [scrna-annotated-cells]`，`outputs: [cellchat-lr-table, celltype-gene-expression]`。
2. `cell-proportion-composition`（细胞亚群组成比例与流向分析）— `data_domains: [single-cell]`，`purposes: [注释与参考映射, 细胞通讯与微环境]`，`inputs: [scrna-annotated-cells]`，`outputs: [cell-proportion-stats]`。
3. `survival-prognosis-analysis`（生存分析与临床预后建模）— `data_domains: [clinical-prognosis, bulk-transcriptomics]`，`purposes: [生存与预后建模]`，`inputs: [survival-time-event-group]`，`outputs: [subgroup-effect-table, candidate-biomarker-list]`。
4. `immune-infiltration-tme`（肿瘤微环境与免疫浸润评估）— `data_domains: [bulk-transcriptomics, multi-omics]`，`purposes: [细胞通讯与微环境]`，`inputs: [bulk-de-table]`，`outputs: [pathway-score-table]`。
5. `genomic-epigenomic-landscape`（基因组突变、CNV 与表观遗传图谱）— `data_domains: [genomics-epigenomics]`，`purposes: [变异与表观调控]`，`inputs: []`，`outputs: []`。
6. `set-intersection-and-group-stats`（集合交集与通用组间统计分析）— `data_domains: [general-viz-stats]`，`purposes: [集合与通用统计]`，`inputs: []`，`outputs: []`。

> **关键约束**：上述新建或尚未独立跑通可复现分析实现的锚点页，其代码分支或可视化关系均严格诚实标注 `not_run` / `参考配方`，**绝不**因模板 `ready` 或配方 `pass` 而把分析方法误报为「已验证分析实现」。

---

## 三、 模板短名简化（31 项映射）与无损迁移闭环

### 3.1 31 个模板简短 slug 映射表与主归属方法

| 序号 | 原模板 ID（冗长） | 新短 Slug | 中文标题 | `primary_method` |
|---|---|---|---|---|
| 1 | `2026-08-17-shap-feature-mechanism__fig01-shap-a-f--bar` | `shap-importance-bar` | SHAP 特征重要性条形图（含环形 inset） | `shap-explanation` |
| 2 | `2026-08-17-shap-feature-mechanism__fig01-shap-a-f--beeswarm` | `shap-beeswarm` | SHAP 蜂群分布图 | `shap-explanation` |
| 3 | `2026-08-17-shap-feature-mechanism__fig01-shap-a-f--radial-bar` | `shap-radial-bar` | SHAP 环形贡献图 | `shap-explanation` |
| 4 | `2026-10-19-regression-stability__fig03-density-panel--density-scatter` | `pred-density-scatter` | 预测值密度散点与边缘分布图 | `regression-resampling-evaluation` |
| 5 | `2026-10-19-regression-stability__fig04-boxplot-panel--boxplot` | `resampling-metric-box` | 交叉验证指标箱线散点图 | `regression-resampling-evaluation` |
| 6 | `2026-10-22-glaucoma-scrna__fig01-cns-umap--umap` | `scrna-celltype-umap` | 单细胞分群 UMAP 图 | `dimensionality-reduction` |
| 7 | `2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap` | `scrna-feature-umap-grid` | Marker 特征表达 UMAP 小多图 | `cell-type-annotation` |
| 8 | `2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot` | `marker-bubble-dotplot` | 细胞类型 × Marker 基因气泡点图 | `cell-type-annotation` |
| 9 | `2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow` | `cell-prop-flow-bar` | 细胞比例堆叠流带柱图 | `cell-proportion-composition` |
| 10 | `2026-10-22-glaucoma-scrna__fig06-pathway-violin--violin` | `pathway-stat-violin` | 通路评分分组小提琴图（含统计标注） | `gene-set-scoring` |
| 11 | `2026-10-22-scp-example__fig01-volcano--volcano` | `scp-de-volcano` | 单细胞差异表达火山图 | `differential-expression` |
| 12 | `2026-10-22-scp-example__fig02-ring--ring` | `scp-comp-ring` | 细胞构成同心环图 | `cell-proportion-composition` |
| 13 | `2026-10-22-scp-example__fig03-pie--pie` | `scp-comp-pie` | 细胞构成饼图 | `cell-proportion-composition` |
| 14 | `2026-10-22-scp-example__fig04-rose--rose` | `scp-comp-rose` | 细胞构成玫瑰图 | `cell-proportion-composition` |
| 15 | `2026-10-22-scp-example__fig05-trend--trend` | `scp-comp-trend` | 细胞构成趋势连线图 | `cell-proportion-composition` |
| 16 | `2026-10-22-scp-example__fig06-area--area` | `scp-comp-area` | 细胞构成堆积面积图 | `cell-proportion-composition` |
| 17 | `2026-10-22-scp-example__fig07-dot--dot` | `scp-comp-dot` | 细胞构成比例点图 | `cell-proportion-composition` |
| 18 | `2026-10-22-scp-example__fig08-group-heatmap--heatmap` | `scp-group-heatmap` | 多分组注释表达热图 | `differential-expression` |
| 19 | `2026-10-22-scp-example__fig09-bar--bar` | `scp-count-bar` | 细胞分组计数柱图 | `cell-proportion-composition` |
| 20 | `2026-10-22-scp-example__fig10-sankey--sankey` | `scp-flow-sankey` | 细胞分组流向桑基图 | `cell-proportion-composition` |
| 21 | `2026-10-22-scp-example__fig11-chord--chord` | `scp-flow-chord` | 细胞分组流向和弦图 | `cell-proportion-composition` |
| 22 | `2026-10-22-scp-example__fig12-venn--venn` | `set-venn` | 多集合交集维恩图 | `set-intersection-and-group-stats` |
| 23 | `2026-10-22-scp-example__fig13-upset--upset` | `set-upset` | 多集合交集 UpSet 图 | `set-intersection-and-group-stats` |
| 24 | `2026-10-22-scp-example__fig14-feature-heatmap--heatmap` | `scp-feature-heatmap` | 拟时序/特征连续表达热图 | `dynamic-feature-analysis` |
| 25 | `2026-10-22-scp-example__fig15-cell-cor-heatmap--heatmap` | `scp-cell-cor-heatmap` | 细胞群相关性聚类热图 | `set-intersection-and-group-stats` |
| 26 | `2026-10-22-scp-example__fig16-cell-density--ridge` | `scp-expr-ridge` | 分组基因表达山脊密度图 | `gene-set-scoring` |
| 27 | `2026-10-22-scp-example__fig17-group-heatmap-dot--heatmap` | `scp-group-dot-heatmap` | 分组表达点阵复合热图 | `differential-expression` |
| 28 | `figureya-1survivalcurve-update--km-curve` | `km-survival-curve` | KM 生存曲线与风险表 | `survival-prognosis-analysis` |
| 29 | `figureya-59volcanov2--volcano` | `bulk-de-volcano` | Bulk 差异表达分级着色火山图 | `differential-expression` |
| 30 | `figureya-6rhrsv2--forest` | `subgroup-hazard-forest` | 预后与亚组分析风险比森林图 | `survival-prognosis-analysis` |
| 31 | `ks-cellchat-circos-multi--circos` | `cellchat-circos-multi` | 细胞通讯多轨环形图（配受体+热图+柱状轨） | `cell-cell-communication` |

### 3.2 双审暴露出的必改迁移清单（修正旧版遗漏）
1. **`spec.json` 不含 `id` 字段，切勿写入**：31 份现存 `spec.json` 均无 `id`，迁移时保持原字节不变，避免无谓破坏 `spec.json` 哈希。
2. **`runtime.json` 与 `verify/runtime-portability.json`（仅 21/20 个模板拥有）**：
   - 将 `runtime.json` 中 `"id"` 改为新短 slug，保留原 `source`、`commit`、`license`、`files`、`resources` 相对路径不变。
   - 对 20 份 `verify/runtime-portability.json`：更新 `implementation` 为新短 slug，真实重算受 `runtime.json` 字节变化（及 `scp-group-dot-heatmap` 等声明了 `spec.json` 的闭包）影响的 `closure_hash`（保留原始 `command`/`environment`/`executed_at` 历史执行事实并在迁移记录中写明为纯 ID/路径变更迁移，不伪造未执行的新运行时间；可提供 dry-run 迁移校验并按需要抽样/全量重跑 `verify-template` 验证输出一致性）。
3. **`verify/verify.json`（全 31 个模板）与 `code-manifest.json`（5 个模板）**：
   - `verification.py` 按 Wiki 根相对路径生成 `inputs` 字典键（如 `templates/<old>/spec.json` → `templates/<new>/spec.json`）。迁移时重写键名前缀并保留 `interfaces/<slug>#columns` 与真实输出 `png/pdf/svg` SHA-256，或对可迅速重跑的模板实跑 `verify-template`。
   - 同步更新 5 个模板下的 `code-manifest.json` 的 `evidence` 路径。
4. **`wiki/layouts/` 不止 `.md`，还包含 `layout.json`**：
   - 迁移 `wiki/layouts/*.md` 的 `templates` 与 `template_panels`（严格保留面板字母覆盖完整度，供 `relations.py:_ready_covering_template` 与 `lint.py` 检查），同时迁移 `wiki/layouts/2026-08-17-shap-feature-mechanism__fig01-shap-a-f/layout.json` 中 6 处 `panels[*].template` 旧 ID（并按版式校验更新其对应回放引用）。
   - 同步迁移 `wiki/methods/*.md`（`figure_relations`、`next_steps`、正文）、`wiki/scenarios/*.md`（`picks`、`steps`）、`wiki/projects/*.md`（`templates:`）、`wiki/chart-types/*.md`（22 份）、`wiki/interfaces/*.md`（经 `save` 重建 `facts`）、`wiki/recipes/*.md`（仅历史备注/引用中的旧 ID 链接，**不动 `source/` 原字节与用户 `<!-- user:start -->` 块**）。
5. **统一类型感知 Canonical ID / Alias Resolver**：
   - 在新建 `rwiki/aliases.py`（共享解析器）中实现严格类型感知映射：拒绝重复别名、跨实体歧义、环路与路径穿越；统一接入 `links.py:resolve()`（含资产子路径如 `templates/<old>/preview.png`）、`pages.py:visual_path()`、`finder.py:_page()`、`suggest.py:_locate_node()`、`template_spec.py:load_unified_spec()`、`relations.py:_target()`、`templates.py`、`asset_checkout.py`、`deletion.py` 与 `server.py`（`/api/page`、`/files/wiki`、`/api/templates/...`）。
   - 返回结果保留 `requested_id` 与规范 `id`，前端按 `(type, id)` 去重；在 `lint.py` 新增 `aliases` 校验（非空字符串列表、禁止重复、禁止与现存页面 `id` 或其他页 `aliases` 冲突）。
6. **`acceptance.json` 与 `wiki/.protected-hashes.json` 更新顺序**：
   - **重要**：先完成 Phase 1 改名 + Phase 2 写入 `primary_method`/`data_domains`/`purposes`/`aliases`，待 frontmatter 与正文全部稳定后，统一重新执行 `check-entry <id> --record` 更新全部变动页的 `<entry>/acceptance.json`（不中途重签两次），随后运行 `wiki.py save` 重建 `facts`/`index.md`/`catalog.jsonl`，最后执行 `gh protect-baseline` 刷新 `wiki/.protected-hashes.json`（确保 CI `test_repo_files.py:42` 通过 `gh protect-baseline --check`），并以 `wiki.py lint` 核查 0 ERROR 与各 `runtime` WARN。

---

## 四、 混合可视化挂载与 `render-*` 接口语义隔离规范

### 4.1 严格纠正：`render-*` 接口绝不混入 `method.outputs`
两份审查均指出：24 个模板读取的是 `render-*` 绘图专用中间表（如 `render-de-results`、`render-dotplot-long`、`render-cell-metadata`、`render-cell-proportions`），而分析方法实际产出的是科学分析对象（如 `scrna-annotated-cells`、`deg-result-table`）。**绝不允许**为了自动匹配而把 `render-*` 直接写入分析方法的 `outputs` 导致 `direct` 与真实验证语义混乱！

修正后的**三层混合挂载聚合模型**（新建后端共享聚合模块 `开发/skills/research-wiki/rwiki/method_hub.py`）：
1. **第一层：主归属与审定关系（`curated_visualizations`）**
   - 模板通过 `primary_method: <method_id>` 声明其在 UI 中默认归属的方法（决定展示位次），**不代表 `direct` 或已验证**；
   - 人工语义兼容等级与验证范围**唯一以方法侧 `figure_relations` 为准**（保留 `direct` / `adaptable` / `candidate`、`adaptation` 与 `verification.scope`，无 `figure_relations` 的新锚点或主归属标为 `未审定 / candidate` 或显示自身模板回放范围，**决不**虚标为 `已核实`）。
2. **第二层：结果对象匹配（区分 `full_match` / `partial_match` / `render_adapter`）**
   - **`full_match`**：模板所有 `required: true` 输入表接口 `<= set(method.outputs)`（如 `survival-time-event-group` / `shap-summary` + `shap-samples` / `cellchat-lr-table`）。
   - **`partial_match`**：仅命中部分必需表（明确返回 `matched_interfaces` 与 `missing_required_interfaces`，供用户或 Agent 决定是否补齐第二张表）。
   - **`render_adapter`（对象抽取转换桥接）**：在方法页元数据声明可选字段 `render_bridges: [{interface, from_output, extractor_note, unit}]`（例如 `cell-type-annotation` 说明如何从 `scrna-annotated-cells` 提取平均表达长表 `render-dotplot-long` 或坐标表 `render-umap-groups`；`cell-proportion-composition` 分别桥接 `render-cell-proportions` 与 `render-cell-metadata`/`render-cell-linkage`），使 **24 个 `render-*` 模板全部能严谨地按对象转换路径挂到对应方法下**，且清晰展示需要经过的提取步骤而不伪造 `direct`！
3. **第三层：参考源码配方（`reference_recipes`，多对多映射）**
   - 在 `recipes/*.md`（或受控外部映射 `wiki/recipes/method-map.json` + 允许 `acceptance.py` 忽略纯分类扩展或统一重录 `acceptance.json`）支持 `method_ids: [...]` 多对多关联（因为一个 FigureYa 综合配方常同时涉及差异分析 + 富集 + 生存建模）。
   - 同时保留“待归类配方”视图（如蛋白组/网络药理/药敏等暂未建专项分析方法页的条目），确保 `SourcesView` / `SearchView` 与 L0 目录检索不遗漏任何一条配方。

---

## 五、 Agent 动态多路决策协议（增量兼容版 `next` Schema）

升级 `开发/skills/research-wiki/rwiki/suggest.py`（同时服务 `wiki.py next --json`、`/api/next/<id>` 与 MCP `rwiki_next`），采用**增量兼容（Additive Schema）**：
1. **100% 保留既有契约字段**（确保 `tests/test_studio.py` 与旧客户端零破坏）：
   - `node_id`、`kind`、`title`、`page`、`outputs`、`next_steps`、`structural_matches`（保留 `--q` 过滤逻辑、scenario `steps` fallback，并在 `structural_matches` 严格排除 `technical`/`workflow`/`archived`/隐藏页，同时按 `required <= outputs` 区分 `full_match` 与 `partial_match`）。
2. **新增面向通用 Agent（Codex / Claude Code）的多路决策结构**：
   - `schema_version: 2`
   - `current_node`: `{id, type, title, data_domains, purposes, inputs, outputs}`
   - `decision_mode: "multi_branch_optional"` + `agent_guidance`（明确声明：*静态接口推导与预设条件仅作决策参考，Agent 须结合当前课题样本设计、实际产出的 RDS/CSV 对象与初步观察结果自主选择一条或多条路径，可并行或跳跃推进，不得生搬硬套*）
   - `curated_branches`: 保留 `branch_id`、`direction`、`when`、`hypothesis`、`required_object`、`produced_interface`、`next_methods`、`reference_recipes`（将混在旧 `analysis_templates` 中的 `recipes/*` 分离出来，同时向旧 `analysis_templates` 投影保证兼容）、`viz_templates`
   - `object_compatible_candidates`: 每个候选方法与模板均携带 `source: "object_inferred"`、`match_type: "full" | "partial" | "via_render_bridge"`、`shared_interfaces`、`missing_required_interfaces`、`downstream_viz`
   - `attached_visualizations`: `{curated: [...], object_compatible: [...], render_bridged: [...]}`
3. **新增统一方法工作站 API（`开发/skills/research-wiki/rwiki/server.py`）**：
   - `GET /api/method-hubs?domain=&purpose=&q=`：返回 7 大域 × 12 目的计数矩阵与完整 `analysis` 方法摘要卡片列表（含输入/输出对象、缩略图带、分支数、参考配方数）。
   - `GET /api/methods/{method_id}/hub`：单方法深度工作站聚合接口（详情页直接按需拉取，不依赖全库 `loadLibrary()` 完整图谱水合，保留首屏分阶段轻量加载机制）。

---

## 六、 全新前端架构与测试迁移计划（Method-Centric Web UI）

### 6.1 信息架构与路由契约（保留向后兼容）
- **默认入口**：`route.ts` 中空 hash `""` / `"#/"` 与损坏 `%` 编码统一落地到 `'methods'`（`分析方法库`）；品牌 Logo 链接指向 `#/methods`。
- **顶栏 4 大一级入口**：
  1. **`分析方法库` (`#/methods`)**：顶部 **7 大数据类型域切换栏**（含方法数/缺口提示） → 左侧 **12 类研究目的筛选栏** → 右侧 **方法-对象-图样融合卡片（`MethodHubCard`）**（直接预览配套模板图带 + 输入/输出对象流 + 可选下一步分支数）。
  2. **`多路决策沙盘` (`#/next` & 兼容 `#/playbooks`)**：交互式查看任一方法的上游来源、产出对象、多种条件分支（`curated_branches`）及自动对象推导候选（`object_compatible_candidates`），并突出 Agent CLI/MCP 提示与观察触发条件。
  3. **`课题记录` (`#/projects`)**：保留课题步进时间线与追加记录功能。
  4. **`资料与检索` (`#/resources` & `#/search`)**：分 Tab 清晰收纳 `technical` 技术资料、`workflow` 流程、`interfaces` 数据契约字典、`sources` 来源库（含 L0 目录）、`scenarios` 与全文搜索。
- **兼容性深链保留**：
  - `#/page/methods/<id>.md`：全新升级为**方法工作站视图**（数据对象契约栏 → 配套可视化画廊[含首选 + 对象兼容 + 转换桥接，每张卡片支持复制 CLI/派发到课题/打开内联参数试跑抽屉] → 多重可选下游分支 → 方法深度正文与分支验证证据 → 参考源码配方折叠区）。
  - 保留 `#/page/templates/<id>.md`（支持旧长名 `aliases` 自动规范化跳转提示）、`#/studio?id=...`（可从方法页内联抽屉或独立窗口打开本机试跑/参数调优）、`#/gallery`（作为完整图型辅助索引或视图兼容保留，不再占领默认首页）。

### 6.2 明确的前端测试调整与新增验证范围
不掩盖既有测试影响，明确按以下清单随重构一并更新/补充测试：
- **更新既有断言以对齐新架构**：
  - `开发/apps/web/tests/methods.test.tsx`：更新默认导航视图、7 大域 × 12 目的 `taxonomy` / `data_domains` 结构、新版模板短 ID（同时保留一条旧长名 alias 测试）、新版 `MethodHubCard` 卡片选择器；**严格保留**分支独立 `verified/not_run/stale/invalid` 状态展示、`图模板可用` 与 `分析未验证` 语义隔离、语义输入优先、折叠证据与代码下载按钮等科学防误导核心测试！
  - `开发/apps/web/tests/v2-pages.test.tsx`：按新组件架构迁移 `PlaybooksView`/`NextView`、`Studio` 抽屉、`Recipes` 展示及 `PageView` 语义关系断言，保留许可证徽章、Wikitext 转义、来源不可替代执行等核心保护断言。
  - `开发/apps/web/tests/discovery-loading.test.tsx`：同步补充 `/api/method-hubs` 与 `/api/methods/*/hub` 的模拟加载断言，确保 `hydrateLibrary=false`（如全局搜索）不被多余请求拖慢、旧加载不覆盖新快照。
  - `开发/apps/web/tests/figure-models.mjs` & `global-search.test.tsx`：保留去重规则、`effectiveStatus`、`safeUrl`、`sectionTargets('用途')` 等核心不变量测试。
- **新增专项回归测试**：
  - 空 hash `/`、坏 `%` hash、未知 route、`#/next` vs `#/playbooks`、`#/gallery`、`#/studio?id=<旧长名>`、`#/page/templates/<旧长名>.md` 与旧 `/files/wiki/templates/<旧长名>/preview.png` 路由与解析测试。
  - 后端 pytest：`test_aliases_migration.py`（所有入口解析旧别名、碰撞拒绝、路径穿越拒绝、CLI/HTTP/MCP `next` 输出一致性、7×12 分类统计、多表 `full/partial` 匹配）。

---

## 七、 双模型独立审查结论汇总（Codex GPT-6.2 + Antigravity）

两位审查员（**Orca Codex `gpt-6.2-sol`** 与 **Antigravity 只读审查子代理**）均对原计划给出了 **「核心方向完全正确，须先补齐迁徙与契约细节后施工（Conditional Pass / Changes Required）」** 的一致结论，具体收敛如下：

| 审查发现项 | Antigravity 审查意见 | Codex GPT-6.2 审查意见 | v4.1 计划采纳修正 |
|---|---|---|---|
| **`spec.json` 含 `id` 误判** | 全 31 个 `spec.json` 均无 `id`，写入会打破 `verify.json` 哈希 | 同左：不得无故写入 `spec.id` | 已移除 `spec.json` 修改，保持原字节 |
| **`runtime.json` 与 `runtime-portability.json` 闭环** | 21/20 个模板存在闭环哈希依赖，`id` 修改必须同步 `closure_hash` 与 `implementation` | 同左：强调不得伪造历史运行时间/环境字段，且 `scp-group-dot-heatmap` 闭包内含 `spec.json` | 仅更新 ID 与真实闭包哈希，保留历史运行字段与来源信息 |
| **`verify.json`、`layout.json`、`code-manifest.json` 漏项** | `verify.json` `inputs` 键带 `templates/<old>/` 前缀；遗漏 `shap` 版式的 `layout.json`、5 个 `code-manifest.json`、22 `chart-types`、88 `recipes` | 同左，并逐一核对全 31 份现有哈希与引用位置 | 全部纳入 Phase 1 迁移脚本干跑清单与前后校验 |
| **`wiki/.protected-hashes.json` CI 阻塞** | 指出 30 个模板受 `push_guard.py` + `test_repo_files.py:42` 保护，重命名必须更新 `gh protect-baseline` | 强调不可随意修改只读来源与作者 `user` 块 | 明确最后一步执行 `gh protect-baseline` 并验证 `--check` |
| **`aliases` 解析覆盖面** | 指出 `relations.py:_target`、`pages.py`、`finder.py`、`suggest.py`、`template_spec.py`、`server.py` 均硬编码路径 | 补充 `templates.py`、`asset_checkout.py`、`deletion.py` 及 `/files/wiki` 资产 URL | 抽取统一类型感知 `rwiki/aliases.py`，覆盖全入口 |
| **外部 `scenario_taxonomy.yaml` 优先级与旧标签分类** | 指出 `tags.py` 优先读取 `config.taxonomy` 且 8→12 会打断 `test_method_taxonomy.py` | **进一步发现 `config.json` 当前指向外部 `.claude/skills/...` 文件**，且不能把 `transcriptomics` 盲猜为 `bulk` | 将 7 大域独立为 `data_domains`（含显式 `domains_for` 映射），不改外部词表路径约束，保留旧标签安全 |
| **`render-*` 与 `method.outputs` 语义冲突** | 严正指出 `render-*` 不能写入 `method.outputs`，否则违反 `relations.py` `direct` 约束并造成虚假直连 | **进一步区分 `full_match` vs `partial_match`（多必需表缺失）与 `render_bridge` 显式抽取说明**，`primary_method` 只控归属排序不代表已核实 | 完全采纳：保留 `outputs` 纯净语义，新增 `render_bridges` 与多表完整性区分 |
| **`next` 协议 & 前端测试迁移清单** | 指出替换旧键会破坏 `test_studio.py`，并逐行列出 `methods.test.tsx`/`v2-pages.test.tsx`/`discovery-loading.test.tsx` 影响点 | 补充 `/api/method-hubs` 与 `/api/methods/{id}/hub` 双契约冻结、`recipe` 多对多关联及单次终态 `acceptance` 重录 | 全部并入 Phase 2–4；`acceptance.json` 统一延后至元数据完全稳定后单次重录 |

*(注：两位审查者意见完全收敛，**无原则性技术分歧**；仅细节聚焦侧重互补，已全数吸收至本 v4.1 方案。)*

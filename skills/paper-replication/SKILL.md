---
name: paper-replication
description: Use when the author gives a WeChat post, link, DOI, PMID, or paper PDF and asks to replicate the original paper's computational/bioinformatics methods and publication figures (excluding wet-lab, schematic diagrams, and raw microscopy imaging), using small-scale data, subagent dispatch, and Coordinator self-review into Research Wiki.
---

# 文献生信方法与可视化复刻（paper-replication）

本技能把“二手推文 / 文献线索 → 原文献与附加材料归档 → 正文/附加材料步骤对齐与非计算面板剥离 → 小规模复刻计划 → 子代理分步执行 → 主协调者自审验收 → 本地与 Wiki 双份固化”收口成一条可审计闭环。**动物实验、细胞培养/转染、WB/流式等湿实验（`excluded_wet_lab`）、非计算研究设计/机制模式示意图（`excluded_schematic`）与纯显微/IHC/mIF 影像（`excluded_imaging`）明确剔除，不纳入复刻或通用模板范围。**

## 底线与停机条件

1. **禁止降级猜全文**：只准依据原文献全文 PDF + 附加材料（Supplementary Materials）+ 作者开源仓库做复刻；若 OA 链路失败、遇到付费墙或人机验证拦截，立即停机并请作者提供本地 HTML / PDF / 附加材料（`rwiki paper fetch <id> --pdf <路径> --supp <路径>`），禁止跳过原文仅凭推文脑补步骤。
2. **禁止隐式改算法**：所有统计检验、阈值、归一化和参数默认严格忠于原文 Methods、Supplementary Methods 或作者开源仓库；确实因小规模数据不可行或需更换近似算法时，先说明差异并询问作者。
3. **作者开源仓库优先核对（只读起手）**：解析时自动追踪 `Data/Code Availability` 中的 GitHub/GitLab/Zenodo 仓库；先只读检查 `README`、许可证、依赖清单与脚本对应关系，再按 `research-wiki` 契约函数化提取，不直接盲跑未审阅的整库脚本。
4. **先查重再建项**：每条分析步骤与每张目标图面板必须先过 `rwiki find` 与 `rwiki check-dup`；共同分析归并进既有 26 个规范方法家族或补其分支，不另立重复方法或重复单图模板。
5. **严禁散落临时代码与产物**：所有本地工程脚本必须按编号写入 `<sources_root>/papers/<paper_id>/src/`，严禁把临时调试脚本（如 `chk.R`、`a.py`）留在仓库根目录或桌面；每次任务收口运行 `rwiki clean` 核查。
6. **1:1 视觉忠实度硬边界（严禁“出图就算”）**：
   - **配色精确锁定**：出图前必须从 `upstream_repo/` 源码与原图 PNG（`sample_palette.py` / 像素采样）提取精确 Hex 色值与渐近色标，**严禁**凭空套用无关默认色盘（如随手用 `Set2`/`Dark 3`）。
   - **整图与面板比例 1:1 锁定**：先量取原图宽高比与各 Panel (`A/B/C/...`) 栅格面积占比，精确匹配 `patchwork` `widths`/`heights`、图例停靠位置与边距（整图尺寸偏差控制在 `±5%` 内）。
   - **图元与流形真实感一致**：相关性矩阵必须与原图一致（如 `corrplot` 全矩阵 + 聚类黑框，不能简化成单列条）；降维散点必须呈现连续密集细胞云团（禁止生成彼此孤立的散点团块）；图框、箭头坐标轴与字号对齐原图。
   - **一步一跑 + 逐图打回制**：低配置机器必须**单进程串行渲染**（每次只跑 1 个脚本并即时 `gc()` 释放内存）；每张图完成后立刻目视核查 `side_by_side.png`（原图 vs 复刻图并排），**有一项不像立即打回重修，全部 1:1 过关后方能入库**。
7. **禁止复刻非计算示意图/纯显微影像（`excluded_schematic` / `excluded_imaging`）**：
   - 凡属研究设计流程图、机制通路卡通图（如 Fig. 1A 队列流程示意）一律标注 `excluded_schematic`，纯显微/IHC/mIF 影像一律标注 `excluded_imaging`，与湿实验（`excluded_wet_lab`）并列排除，严禁硬画矢量示意图或为其新建通用绘图模板。
8. **真实数据 `example/`、Schema v2 硬门禁与 Output Slot 3 条硬门禁（v5.6+）**：
   - **真实数据 `example/`**：从复刻论文提炼的 `wiki/templates/<slug>/`，其 `example/*.csv` 与 `code/render.*` 必须直接来自该论文对应 Panel 的真实分析/补表数据与精调绘图代码（单文件 `<= 500 KB`，严禁用随机高斯团块或假 H&E 方块应付 `verify-template`）。
   - **Output Slot 3 条硬门禁（`rwiki lint` 强制校验）**：同一篇论文内部视觉同质的多个 Panel 归并提炼为 **1 套**代表性画风模板，挂入对应的输出槽位 `(primary_method, chart_types[0])`。对包含至少 1 个声明了 `style_tier` 或 `journal_style` 的活跃槽位，必须同时满足：① **禁止孤立 `variant`**（槽位仅有 1 个活跃模板时不得标 `variant`，必须标 `default`）；② **多模板槽位完整性**（槽位有 `>= 2` 个活跃模板时，必须有且仅有 1 个 `default`，且全员均须声明非空 `journal_style` 与合法 `style_tier`）；③ **同槽位主标签对齐**（若 `default` 声明了非空 `tags`，同槽位每个 `variant` 的 `tags` 必须包含 `default.tags[0]`，防止筛选时变体隐身）。
   - **Schema v2 `panel-manifest.yaml` 硬门禁**：每篇复刻论文必须在 `methods/<workflow-id>/` 下产出 `schema_version: 2` 原子级 `panel-manifest.yaml`（`figXX/A`、`sfig03/B` 键）、`code/panels/` 逐计算 Panel 独立可运行 CLI 脚本及 `panel-receipts.json`。对**每一条非排除（`not excluded_*`）计算面板**强制执行：
     - `script_path` 必须非空且在 `methods/<workflow-id>/` 目录内真实存在；
     - 必须声明 `template_disposition`（三选一）：
       - `paper_variant`：`template_id` 必须非空且指向已存在模板，该模板必须满足 `status: ready`、非空 `primary_method`、`style_tier in ("default", "variant")` 与非空 `journal_style`；
       - `reuse_identical`：`template_id` 必须非空且指向已存在模板，且必须声明非空 `disposition_note` 说明为何与旧模板视觉一致无需新建变体；
       - `paper_specific_only`：`template_id` 必须为 `null`（`None`），且必须声明非空 `disposition_note` 说明为何属强论文特异/单用途不进通用模板库。
9. **分析方法入库硬门禁（`method-manifest.yaml` + `verify-method` + 多实现槽位铁律，v5.7+）**：
   - **强制配套 `method-manifest.yaml`**：凡工作流声明了 `schema_version >= 2` 的 `panel-manifest.yaml`，必须在 `methods/<workflow-id>/` 下同步交付 `method-manifest.yaml`（含 `schema_version >= 1`、`paper_id`、`workflow_id`、`steps[]`），缺则 `rwiki lint` 直接 `ERROR` 拦死。
   - **逐计算步骤 `method_disposition` 校验**：每条 `steps[]` 必须具备唯一安全 `step_id`、非空 `title`、工作流目录内真实存在的 `script_path` 及三选一 `method_disposition`：
     - `method_impl`：必须声明存在的活跃 `method_kind: analysis` `method_id` 与 `implementation_id`，该实现须具备合法 `impl_tier`（`default` / `variant`）与非空 `modality`，且必须经 `rwiki verify-method <method_id> --impl <impl_id>` 实跑通过达到 `verified`（严禁 `not_run`/`stale`/`invalid`）；
     - `reuse_impl`：必须声明存在的 `method_id`、`implementation_id`（实测状态须为 `verified`）及非空 `disposition_note`；
     - `paper_specific_only`：`method_id` 与 `implementation_id` 必须为 `null`（`None`），且必须声明非空 `disposition_note`。
   - **多实现槽位 3 条铁律**：同一 `analysis` 方法下可并存多模态/多语言实现分支（通过 `runtime.json` 独立声明 `files` 闭包隔离各实现 SHA256 收据）；凡至少 1 个实现声明了 `impl_tier` 或 `modality`，① 仅 1 个实现时禁止标为 `impl_tier: variant`（须为 `default`）；② `>= 2` 个实现时必须有且仅有 1 个 `default`、其余全部 `variant`；③ 全员必须声明非空 `modality` 与 `language`。
   - **`verify-method` 实跑收据**：新增或修改实现后必须编写 `methods/<method_id>/example/verify_<impl_id>.py`（或 `.R`）并运行 `rwiki verify-method <method_id> --impl <impl_id>`，在隔离临时目录执行并生成不含绝对盘符路径的 `verification/<impl_id>.json`。

## 本地与 Wiki 双份项目目录规范

```text
<sources_root>/papers/<paper_id>/         # 本机完整复刻工程（非 Git）
├── paper.json                            # 元数据、DOI/PMID、数据编号、步骤↔附件↔图映射状态机
├── plan.md                               # 复刻计划：湿实验剔除、降维边界、查重映射、全图清单
├── intake/                               # 只读入口资料：post.html/txt、paper.pdf、supp/*、manifest.json
├── extracted/                            # 解析产物：full_text.md、methods_computational.md、excluded_wet_lab.md、
│                                         #   supp_index.md、supp_full_text.md、step_supp_map.json、captions.json、pages/
├── upstream_repo/<repo_name>/            # 作者开源代码稀疏浅克隆（含 LICENSE 与 commit）
├── src/                                  # ★ 本机复现源码固定目录
│   ├── README.md                         #   脚本顺序、与 upstream_repo 差异说明
│   ├── runtime.json                      #   最小依赖闭包声明
│   ├── 00_sample_data.R / .py            #   小规模抽样脚本（固定 seed = 42）
│   ├── 01_<step_slug>.R / .py …          #   按编号排序的分步生信分析脚本
│   └── figures/                          #   单面板复刻（figXX_panelY.*）与整图拼图（compose_figXX.*）
├── data_small/                           # 抽样后的小规模验证数据（不存 GB 级原库）
├── runs/                                 # 运行日志、中间表（RDS/CSV）与耗时收据
└── review/                               # 主协调者自审：side_by_side.png、参数核查表、QA 报告
```

- **Wiki 正式存档**：`wiki/methods/<workflow-id>.md`（`method_kind: workflow`）下固定保存两套可读源码：`methods/<workflow-id>/source/`（作者原版核心脚本快照 + `source-manifest.json`，单文件 `< 4.5 MB`）与 `methods/<workflow-id>/code/`（同步自 `<paper_id>/src/` 的分步复刻源码 + `runtime.json`），`verification/` 存小规模运行收据；所有可复用可视化代码统一入 `wiki/templates/<short-slug>/`（**一类图允许多套不同顶刊风格模板并存，供真实课题按需切换**）；整图拼图归 `gallery/`。

## 五阶段工作流

### 阶段 1：溯源与文献归档（Trace & Fetch）

1. 运行 `rwiki paper trace [--post-file <md/html> | --doi <doi> | --pmid <pmid> | --query "<标题>"] [--repo <url>] --json` 定位规范原文献元数据、OA 全文链接、数据编号（GEO/TCGA/GSA/Zenodo）与作者开源代码仓库，自动初始化标准本地目录骨架。
2. 运行 `rwiki paper fetch <paper_id> [--pdf <本地PDF>] [--supp <附加材料路径或目录> ...]`：获取全文 PDF 与全部附加材料至 `intake/`；若有开源代码仓库，浅克隆至 `upstream_repo/` 并生成 `.manifest.json`。

### 阶段 2：正文 + 附加材料精读与湿实验剥离（Parse）

1. 运行 `rwiki paper parse <paper_id>`，全量扫描正文全部页数（无 25 页截断）与 `intake/supp/` 下全部附加材料（PDF/DOCX/XLSX/CSV），生成 `extracted/methods_computational.md`、`extracted/excluded_wet_lab.md`、`extracted/supp_index.md`、`extracted/captions.json`、`extracted/step_supp_map.json` 及 `extracted/pages/` 渲染图。
2. 主代理对照正文与附加材料，**捋顺「正文步骤 ↔ 附加材料（Supp Methods/Tables/Figs）↔ 作者代码 ↔ 正文/附图面板」关系**，剔除全部动物/细胞湿实验及 WB/IHC/镜检面板，列出尽量覆盖全量可复刻 Main + Supplementary Figures 的面板清单。

### 阶段 3：小规模降维与全图复刻计划（Plan）

1. 按 [小规模降维规范](references/scale-down-policy.md) 制定本机可运行抽样策略（单细胞 `1,500–2,500` cells、队列 `<= 120` 样本、空间 ROI `<= 2,000` spots、固定种子 `42`）；无公开数据时暂停请作者拍板同类公开小样本或合成结构数据。
2. 运行 `rwiki paper plan <paper_id>`（默认已纳管 Main + Supplementary 生信图，仅显式传 `--main-only` 时排除附图），生成含对照矩阵、本地 `src/` 任务分配与 `check-dup` 复用建议的 `plan.md` 交作者确认。

### 阶段 4：子代理分步执行 + 主协调者审查（Dispatch & Self-Review）

按 [子代理分工与自审契约](references/subagent-orchestration.md) 拆分任务卡分发：

- **Analysis Subagent**：把分步脚本写入 `<paper_id>/src/01_...` 等编号文件，输出真实运行日志至 `runs/`、导出供绘图消费的标准中间表，严禁篡改参数或漏报缺包；需新装包时只收集清单交作者按批批准。
- **Figure Subagent**：调用 `sci-figure-replica` 对全量选定 Main + Supplementary 数据图的每个可复刻 Panel 做 1:1 复刻，开发源码放在 `src/figures/`；优先 `rwiki check-dup` 复用已有 `templates/`，对缺口图型或不同顶刊风格通过 `rwiki scaffold-template <短slug> --native --primary-method <规范方法id>` 建成独立绘图模板（`verify-template` 实跑通过），并用 `patchwork`/`matplotlib` 生成整图拼图与对比图。
- **Coordinator 自审门禁（发布前必过）**：
  1. 对照正文 + 附加材料核查参数、随机种子、`scale_down_boundary` 声明与 `step_supp_map.json`；
  2. 亲自看图审查每张 `side_by_side.png` 与整图拼图对比图；
  3. 运行 `rwiki check-dup`、`rwiki check-entry <id>`、`rwiki lint`（必须 0 ERROR）及 `rwiki clean` 清理临时残留。

### 阶段 5：知识库全闭环沉淀（Publish + Templates + Method Relations + Composable Decision Tree）

1. **统一模板体系 + Schema v2 `panel-manifest.yaml` 与 Output Slot 硬门禁**：不再区分 L1 配方与 L2 模板，所有新增绘图模板一律归入 `wiki/templates/<short-slug>/`（`recipes/` 为历史只读归档，不再新建）。同论文内视觉同质的多个 Panel 归并提炼为 **1 套**代表性画风模板，挂入对应 `(primary_method, chart_types[0])` 槽位并遵守 Output Slot 3 条硬门禁（禁止孤立 `variant`；多模板槽位有且仅有 1 个 `default` 且全员含非空 `journal_style` + `style_tier`；`variant.tags` 必须包含 `default.tags[0]`）；每篇复刻论文在 `methods/<workflow-id>/` 下交付 `schema_version: 2` 原子级 `panel-manifest.yaml`（非排除计算面板必须有真实落盘 `script_path` 与合法 `template_disposition`: `paper_variant` | `reuse_identical` | `paper_specific_only` 及对应 `template_id` / `disposition_note`；`excluded_schematic` / `excluded_imaging` / `excluded_wet_lab` 不要求 `template_id`、`template_disposition` 与 `script_path`）、`code/panels/` 逐计算 Panel 独立可运行 CLI 脚本与 `panel-receipts.json`；所有模板的 `example/*.csv` 与 `code/render.*` 必须来自该论文真实数据与精调绘图代码。
2. **方法 ↔ 多风格可切换模板语义关系入库**：按研究推进顺序，将每个规范方法页的 `figure_relations`（列明一方法对应的多套可选顶刊风格 `templates/`）与 `next_steps` 补全，并运行 `rwiki map-method` 同步，确保方法页与模板页形成清晰互链，不残留“暂无已记录关系”。
3. **构建可组合生信思路分支树（主干 + 专题子树 + 课题实录卡）**：
   - 生信思路分支树 = 主干决策树 + 专题子树（`scenarios/`）+ 节点方法配图关系（`methods/` `figure_relations`/`next_steps`）+ 课题走线实录卡（`projects/`）；
   - 新建或扩展 `wiki/scenarios/<domain>-playbook.md`（结构化 `steps:` DAG 决策树，逐阶段写清 `when`、`method_id`、多套可选 `templates`、`next_steps`，并从主干 Playbook 挂载分支）；
   - 新建 `wiki/projects/<paper_id>.md`（本课题完整步进思路卡，按研究主线逐阶段记录「科学假设 → 所用方法与可选模板 → 关键生物学发现与排坑 → 触发下一研究分支」）。
4. **双份源码与流程页发布**：运行 `rwiki paper publish <paper_id> --id <workflow-slug> --title "<简明中文论文流程名>" --derived-methods ... --derived-templates ...`，同步 `source/`、`code/`、`verification/`，并挂链全部画廊对比图、模板、Playbook 与课题思路卡；通过 `rwiki lint`（0 `ERROR`）、`rwiki gh guard`（`OK`）与 `rwiki clean` 后交作者终审 `mark-ready`。

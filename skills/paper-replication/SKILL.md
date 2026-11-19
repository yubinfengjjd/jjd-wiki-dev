---
name: paper-replication
description: Use when the author gives a WeChat post, link, DOI, PMID, or paper PDF and asks to replicate the original paper's computational/bioinformatics methods and publication figures (excluding animal/wet-lab experiments), using small-scale data, subagent dispatch, and Coordinator self-review into Research Wiki.
---

# 文献生信方法与可视化复刻（paper-replication）

本技能把“二手推文 / 文献线索 → 原文献与附加材料归档 → 正文/附加材料步骤对齐与湿实验剥离 → 小规模复刻计划 → 子代理分步执行 → 主协调者自审验收 → 本地与 Wiki 双份固化”收口成一条可审计闭环。**动物实验、细胞培养/转染、WB/IHC/免疫荧光/CCK-8 等湿实验明确剔除，不纳入复刻范围。**

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

- **Wiki 正式存档**：`wiki/methods/<workflow-id>.md`（`method_kind: workflow`）下固定保存两套可读源码：`methods/<workflow-id>/source/`（作者原版核心脚本快照 + `source-manifest.json`，单文件 `< 4.5 MB`）与 `methods/<workflow-id>/code/`（同步自 `<paper_id>/src/` 的分步复刻源码 + `runtime.json`），`verification/` 存小规模运行收据；可复用单面板图模板入 `templates/<short-slug>/`；整图拼图归 `gallery/`。

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
- **Figure Subagent**：调用 `sci-figure-replica` 对全量选定 Main + Supplementary 数据图的每个可复刻 Panel 做 1:1 复刻，开发源码放在 `src/figures/`；通过 `rwiki scaffold-template <短slug> --native --primary-method <规范方法id>` 建成单 panel 原生模板（`verify-template` 实跑通过），并用 `patchwork`/`matplotlib` 生成整图拼图与对比图。
- **Coordinator 自审门禁（发布前必过）**：
  1. 对照正文 + 附加材料核查参数、随机种子、`scale_down_boundary` 声明与 `step_supp_map.json`；
  2. 亲自看图审查每张 `side_by_side.png` 与整图拼图对比图；
  3. 运行 `rwiki check-dup`、`rwiki check-entry <id>`、`rwiki lint`（必须 0 ERROR）及 `rwiki clean` 清理临时残留。

### 阶段 5：知识库全闭环沉淀（Publish + Templates + Method Relations + Research Playbook）

1. **全图型 100% 模板覆盖（不区分 L1/L2，一律归入 `templates/`）**：逐张盘点所有 Main + Supp Figure 的全部独立面板图型——先 `rwiki check-dup` 复用库内既有 `templates/`，凡尚无对应模板的缺口图型必须全部新建至 `wiki/templates/<short-slug>/`（不再新建 `recipes/`，也不区分 L1/L2）。
2. **按研究思路绑定方法 ↔ 可视化语义关系**：将全篇所用规范方法与全部复用/新建模板逐一写入规范方法页 `figure_relations`（语义审查）与 `next_steps`，并运行 `rwiki map-method` 同步 `method-map.json`，确保方法页与模板页均不残留“暂无已记录关系”。
3. **沉淀课题完整研究思路（Playbook + Project Card）**：
   - 新建或扩展 `wiki/scenarios/<domain>-playbook.md`（结构化 `steps:` DAG 决策树，逐阶段写清 `when`、`method_id`、`templates`、`next_steps`）；
   - 新建 `wiki/projects/<paper_id>.md`（本课题完整步进思路卡，按研究主线逐阶段记录「科学假设 → 分析方法 + 可视化模板 → 生物学发现与排坑 → 触发下一步分叉」）。
4. **双份源码与流程页发布**：运行 `rwiki paper publish <paper_id> --id <workflow-slug> --title "<简明中文论文流程名>" --derived-methods ... --derived-templates ...`，同步 `source/`、`code/`、`verification/`，并挂链全部画廊对比图、模板、Playbook 与课题思路卡；通过 `rwiki lint`（0 `ERROR`）、`rwiki gh guard`（`OK`）与 `rwiki clean` 后交作者终审 `mark-ready`。

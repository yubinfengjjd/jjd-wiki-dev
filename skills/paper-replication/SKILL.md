---
name: paper-replication
description: Use when the author gives a WeChat post, link, DOI, PMID, or paper PDF and asks to replicate the original paper's computational/bioinformatics methods and publication figures (excluding animal/wet-lab experiments), using small-scale data, subagent dispatch, and Coordinator self-review into Research Wiki.
---

# 文献生信方法与可视化复刻（paper-replication）

本技能把“二手推文 / 文献线索 → 原文献追踪下载 → Methods 精读剥离 → 小规模复刻计划 → 子代理分步执行 → 主协调者自审验收 → 入库知识库与画廊”收口成一条可审计闭环。**动物实验、细胞培养/转染、WB/IHC/CCK-8 等湿实验明确剔除，不纳入复刻范围。**

## 底线与停机条件

1. **禁止降级猜全文**：只准依据原文献全文 PDF + 公开/作者确认的补充材料做复刻；若 OA 链路失败、遇到付费墙或人机验证拦截，立即停机并请作者提供本地 PDF（`rwiki paper fetch <id> --pdf <路径>`），禁止跳过原文仅凭推文脑补步骤。
2. **禁止隐式改算法**：所有统计检验、阈值、归一化和参数默认严格忠于原文 Methods 或作者开源仓库；确实因小规模数据不可行或需更换近似算法时，先说明差异并询问作者。
3. **作者开源仓库优先核对（只读起手）**：解析时自动追踪 `Data/Code Availability` 中的 GitHub/GitLab/Zenodo 仓库；先只读检查 `README`、许可证、依赖清单与脚本对应关系，再按 `research-wiki` 契约函数化提取，不直接盲跑未审阅的整库脚本。
4. **先查重再建项**：每条分析步骤与每张目标图面板必须先过 `rwiki find` 与 `rwiki check-dup`；共同分析归并进现有 26 个规范方法家族或补其分支，不另立重复方法或重复单图模板。

## 五阶段工作流

### 阶段 1：溯源与文献归档（Trace & Fetch）

1. 运行 `rwiki paper trace [--post-file <md/html> | --doi <doi> | --pmid <pmid> | --query "<标题>"] [--repo <url>] --json` 定位规范原文献元数据、OA 全文链接、数据编号（GEO/TCGA 等）与作者开源代码仓库。
2. 运行 `rwiki paper fetch <paper_id>`（遇付费墙则请作者提供本地 PDF 后加 `--pdf <本地PDF>`）；如原文献公开了 GitHub/GitLab 仓库，同时浅克隆到受控只读工作区。
3. 大 PDF 与克隆源码留在 `<sources_root>/papers/<paper_id>/`，不直接压入 Wiki 数据仓 Git。

### 阶段 2：Methods 精读与湿实验剥离（Parse）

1. 运行 `rwiki paper parse <paper_id>`，通过 PyMuPDF 提取全文、Methods、图注（`captions.json`）及含图页面预览（`extracted/pages/page_*.png`）。
2. 主代理对照 `extracted/methods_computational.md`、`extracted/excluded_wet_lab.md` 与 `repo/` 脚本：
   - 剔除全部动物/细胞湿实验及显微/WB 影像面板；
   - 列明每一步计算分析的输入、核心包、关键参数与统计假设；
   - 按 `Figure × Panel` 拆出可复刻的数据可视化面板清单（Main Figures 优先，附图按作者要求纳管）。

### 阶段 3：小规模降维与复刻计划（Plan）

1. 按 [小规模降维规范](references/scale-down-policy.md) 生成可在本机跑通的降维策略，优先从原文公开 GEO/Zenodo 抽样小规模真实子集（单细胞默认 `1,500–2,500` cells 分层抽样、队列默认 `<= 120` 样本、固定随机种子 `42`）；无公开数据时暂停询问作者选同类公开小样本还是合成近似数据。
2. 运行 `rwiki paper plan <paper_id>` 生成 `plan.md` 与内置 `check-dup` 复用建议，整理好后交作者确认再派发子代理执行。

### 阶段 4：子代理分步执行 + 主协调者审查（Dispatch & Self-Review）

按 [子代理分工与自审契约](references/subagent-orchestration.md) 拆分任务卡分发：

- **Analysis Subagent**：复现指定计算步骤脚本，输出真实运行收据、数值对照（若有作者开源基准）及标准输入表，严禁篡改参数或漏报缺包；需新装包时只收集清单交作者按批批准。
- **Figure Subagent**：调用 `sci-figure-replica` 对每张选定数据图的每个核心 Panel 做 1:1 复刻（`replica.R/py`、`side_by_side.png`、`qa_report.md`），并以 `rwiki scaffold-template <短slug> --native --primary-method <规范方法id>` 建成单 panel 原生模板（`verify-template` 实跑通过），再用 `patchwork`/`matplotlib` 生成整张 Figure 的拼图脚本与对比图。
- **Coordinator 自审门禁（发布前必过）**：
  1. 对照原文 Methods 逐条核查参数、随机种子、抽样边界说明；
  2. 亲自调用看图能力审查每张 `side_by_side.png` 与拼图对比图；
  3. 逐项运行 `rwiki check-dup`、`rwiki check-entry <id>`、`rwiki lint`（必须 0 ERROR）。

### 阶段 5：知识库沉淀（Publish）

1. 将复刻通过的各单 panel 模板挂入所属 `analysis` 方法（`primary_method` / 规范短 slug）；
2. 运行 `rwiki paper publish <paper_id> --id <workflow-slug> --title "<简明中文论文流程名>" --derived-methods ... --derived-templates ...` 生成串联 `method_kind: workflow` 页面，完整记录文献引用、开源仓库来源、剔除的湿实验范围与小规模算力边界；
3. 汇总所有对比图、验证收据与新模板清单交作者终审后批量 `mark-ready`。

# Research Wiki AI Company · 运行章程 v0.1

> 本文是 Grok Bot 公司化研发的提案，**不表示已经创建任何 Bot、周期任务或入库流水线**。正式知识库为 `yubinfengjjd/jjd-wiki`，开发仓库为 `yubinfengjjd/jjd-wiki-dev`。

## 定位

CEO（作者）仅做研究方向与关键决策；Bot 执行情报发现、科学策划、代码复刻、独立测试、知识入库及报告。产品为可检索、可复用、有真实运行证据的科研知识，不以图漂亮或每日条目数为目标。

## 六个核心 Bot（初创阶段）

| Bot | 部门 | 责任 | 交付 |
| --- | --- | --- | --- |
| COS | 总裁办 | COO / 协调、分工、预算、日报、异常升级 | Daily brief + 任务看板 |
| Scout | 科研情报部 | 文献 API / 合法公众号链接 / 开源项目发现与去重 | 可核验 URL、DOI、日期和来源的候选 |
| Curator | 科学策展部 | 研究问题、可视化证据链、统计用途与 Wiki 语义去重 | 至多 2 个值得复刻的科学任务/日 |
| Builder | 工程研发部 | R/Python 原样复现、参数化、示例与隔离分支 | 实际代码、测试样例、依赖与运行记录 |
| QA | 科学质量部 | 独立验证统计逻辑、版权、环境及可移植性 | pass/fail/not_run 收据和 PR 评审 |
| Librarian | 知识产品部 | 以原有 rwiki CLI 把理论 + 代码 + 运行证据整合，验收前端 | 可检索的正式 Wiki 草稿 |

拓展岗位：Infra（算力、CI 与安全）、Product（网站和用户体验）。起步不创建闲置职位以免消耗配额。

## 正式生产链

`公开元数据/API 与合规微信来源 → Scout 候选 → Curator 科学/视觉评价 → CEO 来源批次授权 → Builder 分支与隔离环境开发 → QA 独立运行证据 → Librarian 现有 L0/L1/L2 入库草案 → CEO 审核 → PR 合并与前端验收`

任何 Bot 必须首先读取 `jjd-wiki/知识库/AGENTS.md` 和 `jjd-wiki-dev/staged/research-wiki/SKILL.md`。沿用 existing `rwiki find/show/use`、`source add/fetch/scan`、`promote`、`verify-template`、`check-entry`、`lint`、`save`。不得重新实现一套平行 Wiki。

## 科研严谨性与权限底线

- 每次入库交付**方法理论层 + 可复用代码层 + 前端实际验收**，准确区分 L0、L1、L2。
- 没跑过就写 `not_run`，不要以样式相似冒充统计科学正确；不编造文献、数据、实验收据。
- 微信公众号默认只收集用户授权的标题、URL、日期等元数据；未经许可不大规模转载全文、图片、闭源图代码或绕过登录/反爬限制。
- 公共仓库不能存密钥、患者隐私、受限研究数据。对来源代码运行前确认许可证与安全性。
- 不修改 `user` 保护块或手写生成索引；Bot 不擅自把条目标为 `ready`。
- 安装包、收费算力、新统计定义、公开发布、`main` 合并须经过 CEO 批准。
- GitHub Actions 轻量测试不等于 GPU/HPC；大型单细胞/空间组学另配可控 runner 和预算。

## 首轮验证标准

1. 公开 API 的论文 DOI、标题、日期和原文链接人工抽查十条可核验；源异常不吞错。
2. 对公众号内容的采集不违反来源授权，识别转载及广告，明确“仅风格参考”与可复用方法的区别。
3. 首个可合法复用图形案例，经原版/新数据/异目录三项真实运行测试并记录环境。
4. 作者能通过 `rwiki find/show/use` 找到模板、复用代码、理论边界，且在前端打开实际验收。
5. 先手动演练，再允许每日 Routine；首次合并前保持所有 Bot 对 `main` 的写入审批。

## 仓库分工

- `jjd-wiki-dev`：Bot 章程、自动化采集器、独立测试、PR 和开发。
- `jjd-wiki`：正式知识库与知识资产，所有变更遵守原有规则。
- 现有 `jjd-wiki` 在 GitHub 实际为**公开**仓库，README 中“两个仓库均私有”的叙述已经过时；权限模型必须按 GitHub 实际可见性而不是旧文档假设。

## 对应工程包

初版工具文件：`operations/ai-company/scout.py`、`sources.json`、`test_scout.py`、`bot-prompts.md`、`.github/workflows/research-scout-manual.yml`。先以独立试点包验证，合入开发仓库前再经 PR 审核。

## 推荐运行时段（待 CEO 决定）

北京时间 08:35 扫描 → 09:00 评审 → 午后研发/QA → 18:00 COO 日报。每日可采集，但不要强制每日复刻、运行与合并。

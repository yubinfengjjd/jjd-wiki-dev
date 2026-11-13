# Research Wiki AI Company · 运行章程 v0.2

> 本文是 Grok Bot 公司化研发的运行文档，**不表示已经创建任何 Bot、周期任务或入库流水线**。正式知识库为 `yubinfengjjd/jjd-wiki`，开发仓库为 `yubinfengjjd/jjd-wiki-dev`。
>
> **2026-11-12 CEO（jb）决定：** 公司默认不主动检索文献。复刻只处理 jb 发来的材料（论文或微信公众号文章）。Scout 默认暂停、空闲。Curator 的每日提案和每周命中率统计暂停。

## 定位

CEO（jb，作者）只做研究方向、来料与关键决策。Bot 在 jb 交来的材料上阅读、分诊、复刻、独立测试、知识入库及报告。没有来料就不发现、不提案、不复刻。产品为可检索、可复用、有真实运行证据的科研知识，不以图漂亮或每日条目数为目标。

## 六个核心 Bot（初创阶段）

| Bot | 部门 | 责任 | 交付 |
| --- | --- | --- | --- |
| COS | 总裁办 | COO / 协调、分工、预算、异常升级。隔离测试放在 COS 测试机。不做文献扫描日报。 | 有来料才更新的任务看板 |
| Scout | 科研情报部 | **默认暂停、空闲。** 不主动扫文献 API、微信公众号或开源项目，不做每日候选。只有 jb 明确恢复主动检索后才工作。 | 暂停期间无候选 |
| Curator | 科学策展部 | **每日提案与每周命中率统计暂停。** jb 发来材料后：通读全文（不以摘要代替），按质量条分诊，列出可选数据图，等 jb 选定。 | 来料分诊：全文已读、候选图、不收录理由 |
| Builder | 工程研发部 | 只复刻 jb 选定的图。使用 sci-figure-replica 技能（源：`github.com/yubinfengjjd/research-jjd/tree/main/sci-figure-replica`）。在 COS 测试机的隔离环境里做 R/Python 复刻、参数化、示例与隔离分支。 | 实际代码、测试样例、依赖、运行记录，以及给 jb 的内嵌截图 PDF |
| QA | 科学质量部 | 在 COS 测试机隔离环境独立重跑；核统计逻辑、版权、环境及可移植性。最终对照 jb 的 Windows、R 4.5.1。 | pass/fail/not_run 收据、重跑记录和 PR 评审 |
| Librarian | 知识产品部 | 以原有 rwiki CLI 把理论 + 代码 + 运行证据整合，验收前端。 | 可检索的正式 Wiki 草稿；未经 jb 不得 ready |

拓展岗位：Infra（算力、CI 与安全）、Product（网站和用户体验）。起步不创建闲置职位以免消耗配额。

## 正式生产链

无来料时链路停在起点：Scout 空闲，Curator 不提案、不统计每周命中率，Builder 不复刻。

有来料时：

`jb 发送论文或微信公众号文章 → Curator 通读全文（非摘要）并按质量条分诊 → jb 选定图 → Builder 用 sci-figure-replica 复刻 → QA 在 COS 测试机隔离环境重跑 → jb 目视签收 → Librarian 按现有 L0/L1/L2 起草 → 仍须 jb 批准才可 ready、合并或发布`

未经 jb，不得 `ready`、合并或发布。

任何 Bot 必须首先读取 `jjd-wiki/知识库/AGENTS.md` 和 `jjd-wiki-dev/staged/research-wiki/SKILL.md`。沿用 existing `rwiki find/show/use`、`source add/fetch/scan`、`promote`、`verify-template`、`check-entry`、`lint`、`save`。不得重新实现一套平行 Wiki。

## 质量条（2026-11-12）

只复刻数据图，例如 ROC、UMAP、heatmap、volcano、forest、KM（Kaplan–Meier）。不复刻流程图、示意图、CONSORT。

论文须在分诊当日往前 2 年内发表；预印本按公开日期计入。超出窗口的材料只回报“不在窗口内”，不进入复刻。

强顶刊图风只按下面 5 条判断：

1. 各 panel 共用一套配色。
2. 主图，加上与主图相连的子 panel。
3. 用与数据同色的引导线直接标注。
4. 高信息密度，背景弱化。
5. 真实数据。

含原始图像的医学影像图只作版式参考，不当作数据图复刻。

## 交付物

交给 jb 的交付物是 **PDF，截图嵌在 PDF 里**。不以外链、仓库路径或“见终端”代替 jb 要看的图。截图来自实际复刻或 QA 重跑，不编造。PDF 是交给 jb 的阅件，不代替代码、理论层和运行证据。

## 环境

- 隔离测试在 **COS 测试机**：conda 环境 `rwiki-r`（R 4.5.1）与 `rwiki-py`。
- 最终验收在 **jb 的 Windows、R 4.5.1**。COS 测试机通过不等于 jb 已签收。
- GitHub Actions 轻量测试不等于上述环境，也不等于 GPU/HPC；大型单细胞/空间组学另配可控 runner 和预算。

## 科研严谨性与权限底线

- 每次入库交付**方法理论层 + 可复用代码层 + 前端实际验收**，准确区分 L0、L1、L2。
- 没跑过就写 `not_run`，不要以样式相似冒充统计科学正确；不编造文献、数据、实验收据。
- 微信公众号默认不主动采集。通读的是 jb 已经发来的全文，不是 Bot 自行抓取。未经许可不大规模转载全文、图片、闭源图代码，不绕过登录或反爬。
- 公共仓库不能存密钥、患者隐私、受限研究数据。对来源代码运行前确认许可证与安全性。
- 不修改 `user` 保护块或手写生成索引；Bot 不擅自把条目标为 `ready`。
- 安装包、收费算力、新统计定义、公开发布、`main` 合并须经过 jb 批准。
- `ready`、合并、发布都要 jb。QA 通过或 PDF 交齐都不代替 jb 的目视签收。

## 首轮验证标准

1. **暂停。** 不以公开 API 抽查 DOI、每日扫描或 Europe PMC 核对作为现行验收。Scout 保持空闲，直到 jb 明确恢复主动检索。
2. jb 发来的公众号文章不违反来源授权；识别转载及广告。含原始图像的医学影像图只作版式参考，并写明“仅版式参考”与可复用数据图的区别。
3. 第一个复刻案例必须是 jb 选定的数据图，来自近 2 年论文（预印本计入），满足质量条 5 条。Builder 用 sci-figure-replica 复刻；QA 在 COS 测试机 `rwiki-r` / `rwiki-py` 重跑；jb 在 Windows R 4.5.1 上目视签收。原样运行、新数据、异目录三项真实运行仍要记录环境。
4. 作者能通过 `rwiki find/show/use` 找到模板、复用代码、理论边界，且在前端打开实际验收。
5. 不启用每日主动检索 Routine。Curator 每日提案与每周命中率统计保持暂停。ready、合并、发布在 jb 签收前保持关闭。

## 仓库分工

- `jjd-wiki-dev`：Bot 章程、独立测试、PR 和开发。主动检索采集器默认不接入。
- `jjd-wiki`：正式知识库与知识资产，所有变更遵守原有规则。
- 现有 `jjd-wiki` 在 GitHub 实际为**公开**仓库，README 中“两个仓库均私有”的叙述已经过时；权限模型必须按 GitHub 实际可见性而不是旧文档假设。

## 对应工程包

主动检索试点包（`operations/ai-company/scout.py`、`sources.json`、`test_scout.py`、`bot-prompts.md`、`.github/workflows/research-scout-manual.yml`）**暂停**。这些文件尚未进入本仓库；默认不导入、不手动触发、不设 Routine。

现行复刻入口是 sci-figure-replica 技能，源码在 `github.com/yubinfengjjd/research-jjd/tree/main/sci-figure-replica`。

## 运行时段

**2026-11-12 已决定：** 取消默认的北京时间 08:35 文献扫描和 09:00 候选评审。Scout 空闲；Curator 不做每日提案。工作从 jb 发来材料开始。不强制每日复刻、运行与合并，也不做每周命中率统计。

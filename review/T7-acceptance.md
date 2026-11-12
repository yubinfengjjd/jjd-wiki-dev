<!-- rwiki-migrated: issue=https://github.com/yubinfengjjd/jjd-wiki-dev/issues/10 -->
> 已迁移，停止维护：https://github.com/yubinfengjjd/jjd-wiki-dev/issues/10
>
> 2026-11-12：[#10](https://github.com/yubinfengjjd/jjd-wiki-dev/issues/10) 按 v2 重定验收。上面这句迁移标记保留。2026-10-21 正文保留为当时收据，不再作为现行步骤。现行结论在文末「v2 重定验收」。

# T7 真实验收 · 进度

日期：2026-10-21。作者对 V1–V4 回复“确认”；V3 选 ST06 + ST07（表只在开发快照 `supp-table-trim-dev-20261017\T2_candidate_20261017\before\02_figures\out\tables\`，正式课题目录无此表）；V2 帖子作者稍后提供。

## 已完成

| 步骤 | 结果 |
|---|---|
| V4 安装 | 改前备份三个技能的 SKILL.md 到 `E:\research-wiki-env\skill-backup\20261021\`。research-wiki 技能装到 Claude 与 Codex 两侧（各 8.2 MB）。sci-figure-replica（只装在 Claude 侧）加第 10 步“收录进知识库”，标题改“十步流程”，第 4 步要求记录 `figure.panel_map`，schema 增加该字段；同步回其开发目录 staged 源并更新安装清单哈希，其测试 105 passed。medfig-render、medpaper-pipeline 两侧加入查模板步骤，两侧文件哈希一致 |
| 正式总库 | `wiki.py init` 建 `E:\桌面\科研知识库`（作者账户，git 正常） |
| post01 收录 | 画廊条目缺 `figure.panel_map`（设计中由 sci-figure-replica 记录，此前只在测试副本手补）。按 P2 已核对的字母→图型写入真实 meta.json；`ingest-figure` 成功；写版式页适用/不适用 |
| V1 签核 | 经网页同一接口签核：画廊 status review → approved，版式 pending_template |
| 处理待办 | 2 个接口、3 个单图模板（代码与示例取自测试库已审查版本）；三个模板预览与测试库逐字节相同；`verify-layout` 与真实画廊 replica.png 平均像素差 0 |
| 方法 | 只收录 XGBoost + SHAP（来源真实：post01 原帖代码）；verify-method 56 s，report.json 与开发时一致，状态 pending_confirm。随机森林 + SHAP 是 M2 时 Codex 写的测试脚本，不以“作者课题脚本”名义进正式库 |
| 检查 | lint OK；真实画廊只有 post01 meta.json 变化（panel_map、status、updated_at），其他 78 个文件不变 |

## 作者确认（2026-10-21）

- 作者在网页点“确认可用”：XGBoost 方法 ready（提交 `confirm xgboost-shap-regression`，A 网页写入经 git 验证）。
- 作者回复“模板可用”：三个单图模板与整图版式 mark-ready，lint OK。

## R1 方向调整后的正式库状态（2026-10-21 晚）

- 正式库已迁移到“方法笔记 + 自由标签”（先 `R1-migrate.py`、再 `init`；顺序不能反：init 的 save 需要新 schema 的 tags）。
- 删除开发期的 `xgboost-shap-regression` 与 `rf-shap-regression`；新建通用方法 `shap-explanation`（draft，待作者确认），带 `code/shap_explain.py` 可换模型模板，已实测 XGBoost 回归、随机森林/逻辑回归/SVM 二分类。
- 用该模板在糖尿病数据上产出两张接口表，三张模板重新出图成功（`E:\research-wiki-env\tmp\r1-method\figures\`）。
- 版式与三个模板 ready 状态不变；接口页不变。

## 等作者

下列两项是 2026-10-21 的待办原文。2026-11-12 起不按此执行，见文末「v2 重定验收」。

1. 确认 `shap-explanation` 方法（网页“确认可用”）。
2. V2 帖子 → 复刻森林图 / 热图 → 收录 → 拆模板 → 用 ST06 / ST07 套用（A4 验收）。

# v2 重定验收（2026-11-12）

执行细则只采用 jjd-wiki `main` `065bb0d14609cc4995137fb1f518f514e3caedc7`（2026-11-12T08:45:08Z）上的这三份文件：

- [`知识库/AGENTS.md`](https://github.com/yubinfengjjd/jjd-wiki/blob/065bb0d14609cc4995137fb1f518f514e3caedc7/知识库/AGENTS.md)（blob `e97c5c7e645775946935ab5dd36b9be3ace8c904`）
- [`文档/当前要求与同步核查.md`](https://github.com/yubinfengjjd/jjd-wiki/blob/065bb0d14609cc4995137fb1f518f514e3caedc7/文档/当前要求与同步核查.md)（blob `9edfc5bc68f252dad8e7a6c5ce538ce21afa0af4`）
- [`文档/决策记录.md`](https://github.com/yubinfengjjd/jjd-wiki/blob/065bb0d14609cc4995137fb1f518f514e3caedc7/文档/决策记录.md)（blob `de6e40088749dd4f03a88bf290239505db5da36b`）

jjd-wiki 本次只读：GitHub Contents API 取页面与收据，另以 `--filter=blob:none` 稀疏检出全部 750 个 Markdown 后检索。没有向该仓库提交、推送或改文件。核对程序用的是本仓库 `main` `cf8787c` 的 `staged/research-wiki`：`acceptance.snapshot`、`acceptance.acceptance_stale`、`verification.replay_available`、`method_implementations.implementation_status`。为导入 `verification.py` 安装了 `pillow==11.1.0`。没有执行三个模板的 `render.py`，没有执行 `explain_model`，也没有重跑收据里的 Windows 命令。

## 作废的旧步骤

这些步骤不再作为 T7 的交付路径。上文对应段落保留，当作 2026-10-21 的历史收据。

| 旧步骤 | 处置 | 依据 |
|---|---|---|
| 画廊必经；新图必须先签核再收录 | 作废 | `AGENTS.md`「收录流程」：画廊是来源之一，不是必经入口。`决策记录.md` 2026-10-20（D022）行：开源库走 `source add/fetch/scan`，开源库与配方不建 layout。`当前要求与同步核查.md`「v2（2026-10-27）修订」同句 |
| 从已签核版式拆模板，并为开源库或配方建 layout | 作废 | 同上 D022 行。layout 的 `pending_signoff` / `pending_template` 只读保留，不驱动新条目 |
| 整图作为 Wiki 条目，或用整图做 A4 验收 | 作废 | `当前要求与同步核查.md`「当前范围修订」（2026-10-21）：只收录代表单 panel，整图不再作为 Wiki 条目或交付目标。`AGENTS.md`：单 panel 只约束 L2 模板 |
| 「V2 帖子 → 收录 → 拆模板 → 用 ST06 / ST07 套用（A4 验收）」这条路径 | 作废 | 上三行，加上 [#10](https://github.com/yubinfengjjd/jjd-wiki-dev/issues/10) 正文：画廊签核、版式拆模板、整图/A4 套用已被 v2 取代 |
| 逐条网页确认才算入库 | 作废为唯一入口 | `决策记录.md` 2026-10-22 行：`mark-ready` 可按批次确认。ready 仍表示作者已确认；本次没有调用 `mark-ready` |

已经发生的 V1 签核、V4 安装、post01 收录和三个单图模板不从本文件删掉。`review/legacy-map.json` 里的 T7 证据哈希 `01549d186d4975825d4fb7e52f431714bc1d9e5d119c1d4ec127e549c2bee96c` 对应提交 `f415a2b` 的迁移前文件，本次不改那份映射。

## 已有条目：只核对，不重建

`知识库/catalog.jsonl`（blob `ad778d1b955eac55b40df9a6d5918a62821571e9`）与页面 frontmatter 一致。四条都是 L2、`status: ready`、`usable: true`。

| 条目 | catalog 行 | 标题 | 页面 blob | 本次字节核对 |
|---|---|---|---|---|
| `shap-explanation` | 207 | 基于 SHAP 的模型解释 | `bb96d41128c75c932c72eebb4bc70dc959c58c1c` | `acceptance.json`（`checked_at` 2026-11-02T05:44:57Z，snapshot `5b6ff039dc6510ca458e14480f8d8991a0c7e15b9bcb85926a0b8ee38b691015`）与当前页面重算结果相同，`acceptance_stale` 为 false。实现 `shap-explain-model` 的 `implementation_status` 为 `verified` |
| `…fig01-shap-a-f--bar` | 8 | SHAP 条形图（含环形 inset） | `ff17ce6dcbc0d1b85cd4319e03bd4a9fcab8e560` | acceptance snapshot `e3332dc2ff31a1c2a77ecba5b903c849d4acfbc9f927a6e62103963734a2dc79` 仍匹配。`replay_available` 为 true |
| `…fig01-shap-a-f--beeswarm` | 9 | SHAP 蜂群图 | `740cb6df22a2bac94f161aa48a44fbec29644f95` | acceptance snapshot `fff552d039f500b33e4125231ce34d3b941b8f0488d6bc8592d0893a50920b83` 仍匹配。`replay_available` 为 true |
| `…fig01-shap-a-f--radial-bar` | 10 | SHAP 环形贡献图 | `7a31935550ee4e3779b14572957f8b68779abd71` | acceptance snapshot `10a27771fb92c010ab09a8fbcbc97844d9e23788117d6c7219320660f11b9580` 仍匹配。`replay_available` 为 true |

三个模板 id 的共同前缀是 `2026-08-17-shap-feature-mechanism__`。`replay_available` 为 true 的含义是：`verify/verify.json` 为 schema 2、`exit_code` 0，其 `inputs` 与当前 `spec.json`、`code/`、示例 CSV、接口列契约的哈希一致，`verify/figure.png|pdf|svg` 与收据 `outputs` 一致，且 `preview.png` 与 png 输出一致。三条收据的时间都是 2026-11-04T04:20:44Z，环境是 Windows 上的 `<ENV_ROOT>/ml-python`（控制器 Python 3.12.7，Anaconda）。这是已存储收据与当前 Git 字节仍绑定，不是本环境重新出图。

方法收据 `verification/shap-explain-model.json`（blob `afab12695dc2614d00f7bc2b5f7af42293aff449`）`state` 为 `passed`。范围是解析线性模型的 SHAP 精确解：summary/samples 表、百分比、输入与模型未变、特征顺序保护。收据内的代码指纹与当前文件一致：`code/explain_model.py` `83d40595be743f045d92a7bf7c363eed3e05107b16807950f4ff7676ff013fbc`，`code/shap_explain.py` `4cc9395490a619ea3a9a0c290575f75d59be3cf6ae0c8b538484026642c36b16`。页面写明树解释器、通用解释器和真实模型/课题未运行。三条 `figure_relations` 的 `verification.state` 都是 `not_run`，范围是「本轮仅核对知识含义与现存契约，未做实际课题分析→出图联调」。

同时看到、且按「不重复建设」留在原处的缺口：

- 方法目录没有 `runtime.json`（Contents API 404）。`implementation_status` 因此给出 `declared: false`、`mode: unknown`、`portability: unknown`。收据正文里的异目录移植描述仍是 2026-10-23 的 Windows 记录，不能当成当前 runtime 契约已声明。
- `code-manifest.json` 仍指向 `source/code_block_01.py` 等四个原文件，并把 `code/shap_explain.py` 标为 `not_run`。方法目录下没有 `source/`（Contents API 404）。页面写明原字节在画廊 `2026-08-17-shap-feature-mechanism/figures/fig01-shap-a-f/original_code/`，历史脚本未提升为已验证实现。
- `当前要求与同步核查.md` 写明三个 SHAP 历史模板没有声明新 sizing 策略，不能当成已完成任意 n 适配。方法页的关系前提写的是同一句话。`文档/任务清单.md` 第 5 节把 sizing 迁移列在「以后」，不属于本次 T7 重建。
- catalog 的 `not_for` 写明模板只绘图；条形/环形示例数值是不确定转录，蜂群是合成近似，不能据此作科学验证。回放收据的 scope 也写明不证明科学有效或任意数据适用。

正式前端在作者本机（`当前要求与同步核查.md`：正式服务端口 8765，读 E 盘知识库）。本次没有该服务，没有做浏览器检索或详情验收，也不把 catalog 行当成前端通过。

## 「V2 帖子」复刻：not_run

状态：`not_run`。没有新增页面、代码、示例或收据。

`文档/handoff.md` 的 V2 定义是：作者提供 1–2 篇简单图帖子（推荐森林图、热图或分组柱），再用 sci-figure-replica 复刻。2026-10-21 的进度写成「V2 帖子作者稍后提供」，并接上已作废的收录、拆模板、ST06/ST07、A4 路径。在 `065bb0d` 的全部 750 个 Markdown 里，「V2 帖子」只出现在 `文档/session.md` 与一份 2026-10-21 维护记录副本，两处都是「稍后提供」。没有 URL、账号、发布日期、选定 panel 或来源 id。

ST06 / ST07 是 ANCHOR-OCT 开发快照里的表（`文档/session.md`：ST07 为 AUROC 矩阵，ST06 为 estimate/lo/hi），路径在作者本机开发快照，正式课题目录当时没有这张表。两份 Git 仓库都没有这些表。`AGENTS.md` 底线第 3、4 条：不编造数据或收据；缺原始数据需要估读或合成时先问作者。因此不能开工。

同库已有的 `templates/figureya-6rhrsv2--forest` 与 `recipes/figureya-90subgroup` 来自 FigureYa 计划（`文档/v2精简与FigureYa入库/计划.md` 的 L2 示范），不是这篇未提供的帖子，本次没有拿它们代替。

作者若以后给出帖子与允许使用的数据，v2 下的做法是：选定一个逻辑 panel，做方法理论层、可复用代码、真实运行收据，再对正式前端做检索和详情验收。不为它新建 layout，也不做整图 A4 验收。在来源和数据到达之前，这一项保持 `not_run`。

## 本次之后仍缺

- 「V2 帖子」的来源（URL 或来源快照，以及选定的单个 panel）和允许使用的数据。ST06/ST07 不能从本仓库取出。
- 上节四条已有 SHAP 条目的前端实机检索/详情。本次只核对了已提交的 catalog、页面和收据字节。
- 方法页已经写明的分析→出图 `not_run`、缺 `runtime.json`、以及三个历史模板的 sizing。这些不是本次要重建的交付。

## 作者决定与本次收尾（2026-11-12）

作者在本次维护会话明确选择「按 v2 新规则取消这项旧任务，保留历史记录」。据此取消上文「V2 帖子」复刻，不再等待帖子、ST06/ST07 或选定 panel；上文 `not_run` 是取消之前的历史事实，保留不改。将来另有来源和实际课题需求时，按当时规则另立任务。

T7 本次范围为 v2 规则替换说明、四个已 ready SHAP 条目的现有状态核对和旧复刻任务取消；没有新建、重建或重新确认任何条目。上文已存收据、方法各分支范围、runtime 与 sizing 的限制继续有效，不随旧任务取消升级为已验证。

本机尝试启动只读服务后做浏览器复核：浏览器连接主机不可用；原生 Firefox 被 Computer Use 工具以「当前 Windows 浏览器不支持 URL 策略执行」停止访问。因此没有完成浏览器检索/详情验收，不把 API、catalog、构建或单测当作浏览器实测。本次没有新增条目，该缺口不构成本次取消旧复刻任务的验收证据，也不改变四条已有页面的状态。

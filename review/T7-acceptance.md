<!-- rwiki-migrated: issue=https://github.com/yubinfengjjd/jjd-wiki-dev/issues/10 -->
> 已迁移，停止维护：https://github.com/yubinfengjjd/jjd-wiki-dev/issues/10

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

1. 确认 `shap-explanation` 方法（网页“确认可用”）。
2. V2 帖子 → 复刻森林图 / 热图 → 收录 → 拆模板 → 用 ST06 / ST07 套用（A4 验收）。

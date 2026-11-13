<!-- rwiki-migrated: issue=https://github.com/yubinfengjjd/jjd-wiki-dev/issues/14 -->
> 已迁移，停止维护：https://github.com/yubinfengjjd/jjd-wiki-dev/issues/14

# M2 审查

日期：2026-10-21。结论：**通过**。审查中改 1 处文字。

## 独立复核

- 全套 pytest 在普通 shell 重跑（含 R 与 bio）：`295 passed in 189s`；TEMP 与 basetemp 均在 E 盘，C 盘可用空间运行前后未减少。
- 真实画廊 79 个文件与 `codex/real-gallery-before.json` 逐一比对哈希：0 变化。
- lint：OK。

## 代码

- `spec.py`：表只接受 `{interface, description}`，文件名 `<interface>.csv`，列从接口页取。校验发生在读取作者/agent 写的 JSON 的边界上，属必要校验。
- 两个 `run.py` 各自自包含（方法目录按约定自包含，后半段 30 行重复可以接受）。`percent` 以筛选前全部特征为分母，与接口定义一致；筛选顺序阈值 → top_n，两张表只含保留特征。`np.divide(where=…)` 处理常数列（测试集里真实可能出现），不算防御性代码。
- `test_m2_bio.py`：真实 bio 环境、100 行、网格单点；验证表头、排序、percent 之和、逐样本均值与汇总一致、着色 0–1、top_n、阈值、空输出报错且无图。测试有实际约束力。

## 方法页

- XGBoost 页如实写明：原帖代码是通用示例、不是该图的生成代码、xlsx 未公开；示例数据为 sklearn 糖尿病数据并给出处。cite 只有指定两条。
- 适用/不适用写得克制，两个方法互相对照并互链，没有编造“谁更准”。
- **改**：随机森林 params.yaml 的 `n_jobs` 说明照抄了“XGBoost 中也用于网格搜索”，改为“随机森林训练的并行任务数”。在 test-wiki-m3（作者账户副本）save 提交。

## 出图目视（codex/M2-renders）

Friedman1 的真实结构是 x0–x4 有效、x5–x9 为噪声。三张图都把 x3、x1、x0、x4、x2 排在前面，x5–x9 接近 0；蜂群图中 x2 两端取值都推高预测（U 形，符合 (x2−0.5)² 项）。分析 → 接口 → 模板整条链路结果正确。

视觉问题（不阻塞，记入后续）：
1. 蜂群图单独出图时画布左侧约三分之一空白（继承自整图中该面板的版心）。单独 render 时应收紧画布，在 T7 前由模板 render.py 处理。
2. 环形图最细的几个扇区上的数值标签与描边重叠、读不清（原图设计如此）。

## 其他发现

- 两个方法的 `scenarios` 都为空，`suggest-pipeline --scenario` 找不到它们。M3 端到端测试中用网页“场景标签”补上 `model-explanation-shap`，同时验证方法页的标签编辑接口。
- test-wiki-m2 由 Codex 沙箱账户创建，作者账户的 git 拒绝操作（已知问题）。前端与后续验收改用作者账户复制的 `test-wiki-m3`（`codex/m3-config.json`）。
- 以后派发 Codex 一律加 `--add-dir E:\research-wiki-env`（第一次派发因此停下）。

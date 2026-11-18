# 子代理分工任务卡与主协调者自审契约

## 1. Analysis Subagent（分析步骤复现子代理）

每个 Analysis Subagent 只负责 1–2 个连续计算步骤（或 1 个开源仓库核心脚本的拆解），写入计划指定的独立工作目录，禁止直接修改 Wiki 主仓已确认页。

- **输入卡片**：
  - `paper_id`、目标步骤 `Methods` 原文摘录、关联作者代码路径（如有）
  - 批准后的小规模验证数据路径与分层抽样脚本（固定种子 `42`）
  - 既有库内 `check-dup` 命中候选（优先补充已有家族分支而非重复建方法页）
- **交付物**：
  - 显式参数化、独立可运行脚本（`.R` / `.py`）+ `runtime.json` 依赖声明
  - 真实运行日志与中间结构表（导出为下步绘图模板可直接消费的 CSV/RDS）
  - 实测耗时、峰值内存估算与小规模缩放边界说明（`scale_down_boundary`）

## 2. Figure Subagent（1:1 面板复刻与原生模板子代理）

每个 Figure Subagent 负责原文中的一张目标 Figure（或其中一组明确指定的面板）：

- **执行顺序**：
  1. 先从 `extracted/pages/` 确认原图各子面板坐标与图注，按 `sci-figure-replica` 规范裁剪单 panel 并在画廊建档（保留完整原图作只读溯源）；
  2. 若作者开源代码仓库已含该图脚本，先核对许可与绘图代码结构（标注 `adapted` 或 `reconstructed`），再按 `rwiki` 原生模板规范改造：
     - 禁硬编码固定样本数/模块数（`n` 必须自适应）
     - ID 严格使用短 slug（`rwiki scaffold-template <slug> --native --primary-method <方法id>`，禁带 `fy-` / `v2` / `--` 拼接）
     - 去水印、修补原图局部重叠瑕疵并保留可编辑 PDF
  3. 对单 panel 运行 `qa_check.py` 与 `rwiki verify-template`，同时输出整张 Figure 的 `patchwork` / `matplotlib` 拼图脚本及 `composite_side_by_side.png`。

## 3. Coordinator 独立审查清单（Reviewer Gate）

子代理回报完成后，主代理在提交 `publish` 与交作者终审前**必须逐项独立复核**：

1. **科学忠诚度复核**：核对子代理脚本参数（如 `min.pct`、`logfc.threshold`、`resolution`、`softPower`、生存截断、交叉验证折数）是否与原文献 Methods 或 `repo/` 一致；任何因小规模数据调整的参数是否已在页面与 `plan.md` 如实注明。
2. **数据边界核查**：确认没有把抽样子集或合成数据的结果宣称为原论文全队列统计复现。
3. **视觉 1:1 实看核对**：主代理亲自查看每张 `side_by_side.png` 与 `composite_side_by_side.png`（不单靠退出码），确认图元类型、配色语义、图例、轴刻度、字体及无遮挡要求达标。
4. **知识库治理门禁**：运行 `rwiki check-dup`、`rwiki check-entry <id>` 与 `rwiki lint`，确保 0 `ERROR`、命名整洁且与所属 `analysis` 方法双向对齐。

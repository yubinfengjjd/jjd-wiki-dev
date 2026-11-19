# 子代理分工任务卡与主协调者自审契约

## 1. Analysis Subagent（分析步骤复现子代理）

每个 Analysis Subagent 只负责 1–2 个连续计算步骤（或 1 个开源仓库核心脚本的拆解），源码**必须**写入 `<sources_root>/papers/<paper_id>/src/` 下编号脚本（如 `00_sample_data.R`、`01_qc_harmony.R`），日志与中间输出写入 `runs/stepXX_*/`，禁止留在仓库根目录或 `tmp/`，也禁止直接修改 Wiki 主仓已确认页。

- **输入卡片**：
  - `paper_id`、目标步骤 `Methods` 与 `Supplementary Methods` 原文摘录、`step_supp_map.json` 映射、`upstream_repo/` 关联脚本路径（如有）
  - 批准后的 `data_small/` 小规模验证数据路径与分层抽样脚本（固定种子 `42`）
  - 既有库内 `check-dup` 命中候选（优先补充已有家族分支而非重复建方法页）
- **交付物**：
  - 写入 `<paper_id>/src/XX_<step>.R|.py` 的显式参数化、独立可运行脚本 + 更新 `src/runtime.json` 依赖声明与 `src/README.md` 差异说明
  - `runs/` 下真实运行日志与中间结构表（导出为下步绘图模板可直接消费的 CSV/RDS）
  - 实测耗时、峰值内存估算与小规模缩放边界说明（`scale_down_boundary`）

## 2. Figure Subagent（1:1 面板复刻与原生模板子代理）

每个 Figure Subagent 负责原文中的一张目标 Figure（含 Main Figure 与可复刻的生信 Supplementary Figure）：

- **执行顺序**：
  1. 先从 `extracted/pages/` 确认原图各子面板坐标与 `captions.json` 图注，排除湿实验面板后，按 `sci-figure-replica` 规范裁剪全部可复刻单 panel 并在画廊建档（保留完整原图作只读溯源）；
  2. 本地调试绘图脚本固定放入 `<paper_id>/src/figures/figXX_panelY.*` 与 `compose_figXX.*`；若 `upstream_repo/` 已含该图脚本，先核对许可与绘图代码结构（标注 `adapted` 或 `reconstructed`），再统一按 `rwiki` 原生绘图模板规范（`wiki/templates/<slug>/`，不再区分 L1 配方与 L2 模板）改造：
     - 禁硬编码固定样本数/模块数（`n` 必须自适应）
     - 一类图允许多套不同顶刊风格的模板并存（如不同布局/多轨组合风），先查重可复用模板，缺失风格或图型再新建短 slug 原生模板（`rwiki scaffold-template <slug> --native --primary-method <方法id>`，禁带 `fy-` / `v2` / `--` 拼接）
     - 去水印、修补原图局部重叠瑕疵并保留可编辑 PDF
  3. 对单 panel 运行 `qa_check.py` 与 `rwiki verify-template`，同时输出整张 Figure 的 `patchwork` / `matplotlib` 拼图脚本及 `composite_side_by_side.png`（汇总图副本放入 `<paper_id>/review/`）。

## 3. Coordinator 独立审查清单（Reviewer Gate）

子代理回报完成后，主代理在提交 `publish` 与交作者终审前**必须逐项独立复核**：

1. **科学忠诚度与附加材料对齐核查**：对照正文 Methods、Supplementary Materials 与 `upstream_repo/` 核对子代理脚本参数（如 `min.pct`、`logfc.threshold`、`resolution`、`softPower`、反卷积/拟时序参数）；任何因小规模数据调整的参数是否已在页面与 `plan.md` 如实注明。
2. **1:1 视觉风格与比例硬门禁（不达标立即打回）**：
   - 核对是否提取并锁定了 `upstream_repo/` 与原图采样的精确 Hex 配色（逐面板核查主色、连续色标与分组色）；
   - 核对整图宽高比及每个 Panel 的 `widths`/`heights` 占比、图例位置与方向、轴样式（无轴箭头 / 方框热图 / 聚类黑框）是否与原图 **1:1** 一致；
   - 严禁“只要不报错出图就过关”：凡外观差距明显、散点孤立、字体裁切或比例失真，**必须当场打回重画该图**，禁止带病入库。
3. **单进程防爆内存与源码目录整洁核查**：严格执行“一步一跑”串行推进（不在低配机器并发多 R 进程）；确认 `<paper_id>/src/` 编号清晰、无散落 `chk.R`/`a.py` 等探针文件；在 `publish` 阶段同步至 `wiki/methods/<workflow-id>/{source,code,verification}/`（Wiki 正文仅写 `<sources_root>/papers/<paper_id>/` 逻辑路径）。
4. **数据边界核查**：确认没有把抽样子集或合成数据的结果宣称为原论文全队列统计复现。
5. **知识库治理与环境清理门禁**：运行 `rwiki check-dup`、`rwiki check-entry <id>`、`rwiki lint`（0 `ERROR`），并运行 `rwiki clean` 确认无临时垃圾残留后交作者终审签核。

## 4. 外部执行代理（Codex 等）调度与 1:1 审查打回协议

当由总调度（Coordinator）将复刻执行委派给外部编码执行代理（如 `codex exec`）时，严格执行「规则锁定 → 串行出图 → 逐图盲审 → 书面修改规则 → 返工复审」闭环：

1. **派单前规则与资产锁定**：总调度先落盘并提交规范文档、提供原图 PNG 清单（含像素尺寸与宽高比）、作者源码路径、精确 Hex 调色板配置文件与已生成的中间分析 CSV，并明示排除的湿实验面板清单与“单进程串行、一次只跑 1 张图”约束。
2. **执行代理交付要求（一步一跑）**：
   - 每完成 1 张 Figure，必须同时产出 `<paper_id>/review/<fig>_replica.png`（及 `.pdf`）与原图并排对比图 `<paper_id>/review/compare/<fig>_side_by_side.png`（高度 ≤ 1400 px、单文件 < 5 MB）；
   - 执行代理在宣告某张图完成前，必须自检其 `side_by_side.png` 是否已对齐配色、整图比例与子图布局。
3. **总调度 6 维 1:1 视觉审查表（逐图打分，任一项 FAIL 即打回）**：
   - **D1 精确配色**：主色、分组色、连续渐近色标（low/mid/high）与作者源码及原图采样 Hex 一致，无擅自替换调色板；
   - **D2 整图高宽比与 Panel 面积占比**：整图宽高比误差 ≤ ±5%，各 Panel（A/B/C…）栅格行列位置、`widths`/`heights` 面积比与原图 1:1 对应；
   - **D3 图元结构忠实度**：矩阵维度（如全对称聚类相关性矩阵 + 对角聚类黑框）、坐标形式（无轴 L 箭头 UMAP、带黑框气泡矩阵、边际柱状图、虚线分组椭圆等）与原图完全一致；
   - **D4 生物流形与视觉密度**：UMAP/DiffusionMap/空间切片呈现连续密集点云与平滑空间边界，禁止孤立针孔散点团块或稀疏空洞；
   - **D5 排版字号与零裁切**：Panel 字母标注（粗体左上角）、轴标签、色条标题、图例停靠位置一致，无重叠、无截断、无乱码；
   - **D6 科学忠实度与排除边界**：湿实验面板已剔除且注明，无把小规模数据夸大为原论文全队列结果。
4. **书面修改规则与返工闭环**：
   - 凡任意 Figure 在 D1–D6 存在缺陷，总调度必须落盘 `<paper_id>/review/revision_rules_round<N>.md`，逐图逐 Panel 写清：① 具体缺陷描述；② 目标修改参数（确切 Hex、行高列宽比、图元改法、字号与图例位置）；③ 验收判定条件；
   - 将修改规则精准回派执行代理定向修复**未通过的图**（已通过的图锁定不动），完成后总调度重新目视审查，直至全部 Figure 100% PASS 方可进入画廊归档与 `rwiki paper publish`。

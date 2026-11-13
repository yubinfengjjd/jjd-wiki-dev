# img07 v2.2 QA 摘要（Builder 自查）
- 以收据 `runs/v2.2_20261112T174749+0800.json` 为准（下游重跑，修了条带检测器）。完整数据运行是 `runs/v2.2_20261112T173942+0800.json`，那份里的 ΔE 作废（检测器误把一个条形当成标题条）。
- 长宽比 0.0000%；全图色板 ΔE00 中位数 7.32（加权 7.08）；标题条 0.00（14 对）；条形填充 1.99（补充）。判定：通过。
- 口径变化：原图按内嵌 Display P3 ICC 转 sRGB 后再算。v2 成图在新口径下是：全图 5.15，标题条 3.00，条形 2.92（`qa/v2replica_icc_metrics.json`）；旧口径复算是 6.47 / 0.00 / 1.85（`qa/v2replica_old_noicc_metrics.json`）。
- qa_check（用这次运行重建的 `gallery_local/`）：17 项过 16 项，FAIL 的是 `data/estimated_data.csv`（不适用）。副本：`qa/qa_check_mechanical.md`。
- 网络模块内边占比 82.2%（4,675/5,685），与 v2 相同。
- 对比图：`compare/side_by_side.png`、`compare/triptych_original_v1_v2.png`（原图都先转成 sRGB 再拼：`compare/original_srgb.png`）。
- 未找到 `v2/qa/QA_REPORT_QA.md`。

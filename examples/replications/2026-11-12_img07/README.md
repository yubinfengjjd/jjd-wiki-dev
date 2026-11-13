# 复刻任务卡 #1 — img07（hdWGCNA hub 网络 + 每模块 GO 富集条形图）

状态：**review** — 等 QA 独立复跑（原数据 / 新数据 / 换目录）和 jb 目视签字。不 ready、不合并 main、不公开发布。
负责人：Builder · 研发。流程：`/workspace/skills-sync/sci-figure-replica-github/`（research-jjd@f6995b5）十步流程。

| 路径 | 内容 |
|---|---|
| `METHOD.md` | 方法原理（hdWGCNA、TOM、kME、网络布局、GO 富集参数）、与原图的数据差异、验收口径、迭代记录、未决问题 |
| `code/01_prepare_network_go.R` | 读 hdWGCNA 对象 + TOM → hub 节点/TOM 边表 + clusterProfiler GO 富集 TSV |
| `code/02_plot_network_go.R` | 只读上一步的表 → PNG/PDF/SVG |
| `code/03_qa_metrics.py` | 宽高比 + CIEDE2000（标题条色板 / 全图色板 / 条形填充） |
| `code/04_receipt.py`, `code/run_all.sh` | 一键运行 + 写收据 `runs/<时间戳>.json` |
| `code/palette_img07.tsv`, `code/argparse_lite.R` | 色板、参数解析（无新依赖） |
| `data/` | `go_enrichment_all.tsv`（全部 GO 结果）、`go_top_terms.tsv`（每模块 top5）、`hub_nodes.tsv`、`hub_edges_tom.tsv`、`module_map.tsv`、`module_genes_kME.tsv` |
| `output/replica.{png,pdf,svg}` | 成图（PNG 3216×2160 @300 dpi） |
| `compare/side_by_side.png`, `compare/overlay.png` | 与原图等高并排、50% 叠加（叠加只辅助定位） |
| `qa/metrics_<ts>.json`, `qa/qa_report.md`, `qa/relocation_check.md` | 指标、人工十项 QA、换目录自测 |
| `runs/<ts>.json` | 运行收据（命令、输入/输出/代码 sha256、R 与包版本、耗时、退出码、验收值） |
| `gallery_local/` | 按 skill 画廊布局建的本地测试条目（不是正式画廊、不入知识库） |
| `source/full_original.png` | 原图只读副本 |
| `scratch/` | 调试中间件（布局比较图、早期指标），不属于交付 |

复跑：
```bash
bash code/run_all.sh --obj /workspace/envtest/hdwgcna/hdWGCNA_object.rds \
  --tom /workspace/envtest/hdwgcna/TOM/INH_TOM.rda --outroot <新目录>
```
conda env `rwiki-r`（R 4.5.1）；01 脚本 R 进程 RSS 实测峰值约 3.7 GB（每秒采样，出现在 GO 富集阶段；TOM 只抽 hub 子块，不展开 13k×13k 全矩阵）；整套约 5.5 分钟，其中 GO 富集约 5 分钟。

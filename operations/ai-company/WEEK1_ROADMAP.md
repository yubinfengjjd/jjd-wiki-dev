# AI Company · 第一周交付与验收清单

> 2026-11-12 修订。CEO（jb）决定：默认不主动检索文献；复刻只处理 jb 发来的论文或微信公众号文章。标为暂停的项不要做。章程见 `COMPANY_CHARTER.md` v0.2。

- [ ] **CEO（jb）**：确认两个 GitHub 仓库及该提案，不在审核前合并到 main。
- [ ] **COS**：在 Grok Bot 创建第一个 CEO Office COO Bot，设置长期规则与权限边界。隔离测试放在 COS 测试机：conda `rwiki-r`（R 4.5.1）与 `rwiki-py`。
- **暂停 · Scout**：默认空闲。不做文献 API 的只读扫描，不手动核对 Europe PMC 或 DOI，不产生每日候选。只有 jb 明确恢复主动检索后才重新打开。
- **暂停 · Curator 每日提案与每周命中率**：暂停。不对公开候选按研究目的、适用场景或许可证做每日评分，也不出每周命中率。jb 发来材料后，才通读全文（非摘要）、按质量条分诊，并等 jb 选图。核对现有 Wiki 的 `catalog.jsonl` 只用于这次来料去重，不作为每日作业。
- **暂停 · Scout 试点包**：不下载、不离线跑、不手动触发 Scout 工作流，也不为确认文献 API 去发主动请求。`scout.py`、`sources.json`、`test_scout.py`、`bot-prompts.md`、`research-scout-manual.yml` 默认不导入。
- [ ] **来料**：只处理 jb 发送的论文或微信公众号文章。通读全文，分诊，由 jb 选定要复刻的图。
- [ ] **质量条**：只要数据图（ROC、UMAP、heatmap、volcano、forest、KM 等）。不要流程图、示意图、CONSORT。论文为近 2 年（预印本计入）。强顶刊图风按 5 条判断：各 panel 一套配色；主图加相连子 panel；同色引导线直接标注；高密度且背景弱化；真实数据。含原始图像的医学影像图只作版式参考。
- [ ] **Builder**：在 COS 测试机隔离环境中，用 sci-figure-replica（`github.com/yubinfengjjd/research-jjd/tree/main/sci-figure-replica`）复刻 jb 选定的图。留原样运行、新数据、异目录验证证据。
- [ ] **QA**：在 COS 测试机 `rwiki-r` / `rwiki-py` 独立重跑；fail/not_run 精确记录。最终验收在 jb 的 Windows、R 4.5.1。
- [ ] **交付**：交给 jb 的是内嵌截图的 PDF。PDF 不代替代码、理论层和运行证据。
- [ ] **Librarian**：遵循 L0/L1/L2 和公司原有知识结构生成待确认 Wiki 条目，不自动 ready。
- [ ] **CEO（jb）**：目视签收。未经 jb，不得 ready、合并或发布。不启用每日主动检索，不恢复 Curator 每日提案或每周命中率统计。

**失败定义**：只读摘要就复刻、主动检索来的文献、流程图/示意图/CONSORT、超出近 2 年窗口的论文、把含原始图像的医学影像图当数据图复刻、仅收论文截图、未经授权转载原图、编造复现结果、没有代码/理论双层产物、只提交 GitHub 未核验前端、交给 jb 的阅件不是内嵌截图的 PDF、未经 jb 就 ready/合并/发布，都不算正式入库。

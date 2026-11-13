<!-- rwiki-migrated: issue=https://github.com/yubinfengjjd/jjd-wiki-dev/issues/16 -->
> 已迁移，停止维护：https://github.com/yubinfengjjd/jjd-wiki-dev/issues/16

# R1 审查 · 方法改笔记、场景改自由标签

日期：2026-10-21。结论：**通过**。

## 独立复核

- 全套 pytest 普通 shell 重跑（含 R）：263 passed，1 条既有第三方弃用警告。
- test-wiki-r1 迁移后 lint OK；三模板、整图回放 0 像素差（Codex 报告，Claude 抽看预览与迁移提交一致）。
- 包内 Python 5446 → 4883 行，`rwiki/methods.py` 312 → 69 行；`verify-method`、`run-method`、method.json、params.yaml、report.json、bio 环境配置与 bio 测试全部删除，没有留兼容层。

## 代码

- `methods.py`：只剩 `scaffold_method`（三种来源互斥、repo 需 url+commit、复制 `source/`）与 `confirm_method`（draft→ready）。校验都发生在写盘前，必要。
- `server.py`：`/api/{kind}/{id}/tags` 去空白、去重保序；方法 confirm 只接受 draft、return 只接受 ready。
- facts 的代码文件链接使用 `/files/wiki/<根相对路径>`，测试按 href 实际 GET 核对原始字节 —— 避免了点击代码链接进入 SPA 外壳的问题。
- `suggest` 关键词只搜标题、tags 与“适用”节，不再搜作者备注（符合“推荐按适用判断”）。

## 前端配套（Claude）

- 数据模型改为 `tags`、方法状态 draft/ready、`inputs/outputs` 进 frontmatter；删场景筛选与 `/api/taxonomy`，图型枢纽成为网络里的绿色大节点。
- 页面用“标签”编辑器替代场景编辑；方法页新增“代码模板”节，文件名取自 facts 的 `/files/wiki/...` 链接（也兼容手写 wikilink）。
- 正文里指向 .py/.R/.csv/.json/.yaml 等文件的 wikilink 改为直接打开原始文件，不再进入空白页面。
- `tsc` 与 `vite build` 通过；1440 与 390 宽截图检查方法库、方法页、知识网络、待办。

## 遗留

- test-wiki-r1 的 AGENTS.md 仍是迁移前的旧规则（迁移脚本不动规则文件）；正式库迁移时先 `init` 覆盖规则再迁移。

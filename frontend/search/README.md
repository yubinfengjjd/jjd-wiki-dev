# 条目检索（静态）

按 **图型**（`chart_types`）、**领域**（`tags`，按 `spec/scenario_taxonomy.yaml` 受控词表规范到键）、**R 包**（R 条目的 `requires`，去掉 knitr/rmarkdown）分面筛选，加关键词搜索。纯 HTML/CSS/JS，无 CDN、无服务端依赖、无 npm 包；生成脚本只用 Python 标准库。

## 生成索引（只读 catalog）

```bash
python3 frontend/search/build_index.py --wiki <jjd-wiki>/知识库 [--rev <jjd-wiki 提交号>]
# 默认 --taxonomy spec/scenario_taxonomy.yaml，--out frontend/search/search-index.json
```

- 条目数从 `catalog.jsonl` 实读，不写死；Wiki 增删条目后重跑即可。
- 缺字段、类型不对时降级为空值；不是 JSON 对象的行跳过并记入 `stats.skipped_lines`。
- 不在词表里的 tag 不丢弃，记入 `unknown_tags` 并在页面标红；不在 `chart-types/*.md` 的图型记入 `unknown_charts`。
- `search-index.json` 是生成物，已 gitignore。

## 预览

```bash
cd frontend/search && python3 -m http.server 8766 --bind 127.0.0.1
# 打开 http://127.0.0.1:8766/index.html，默认结果标题打开 GitHub 源文件
# 若 rwiki serve 正在 8765 端口运行：
# http://127.0.0.1:8766/index.html?app=http%3A%2F%2F127.0.0.1%3A8765%2F
```

URL 参数：`?index=` 索引地址；`?app=` 可选的 rwiki 应用根（需运行服务，条目链到 `<app>#/page/<page>`）；`?src=` 源文件前缀（默认 GitHub jjd-wiki main 的 `知识库/`）。不提供 app 时标题打开源文件。链接仅允许 HTTP(S) 或相对地址。筛选状态写在 hash 里，可直接分享，例如 `#charts=heatmap&domains=single-cell`。

分面规则：同一分面内多选为“或”，不同分面之间及与关键词为“且”；分面计数按“其余条件都满足”实时计算。

## 测试

```bash
cd frontend/search
python3 -m unittest -v test_build_index
node --test search-core.test.mjs
```

CI 在前端检查启用时运行 Python 索引测试；`frontend/npm test` 同时运行搜索 Node 测试。

## 全库正文与本地应用一致

原有目录分面保留。切换“全库正文”后，使用引擎导出的分节正文、词频、别名和 BM25 参数排序；索引不包含用户备注、运行日志或数据。无需服务器即可在浏览器计算相关性。

```powershell
D:\anaconda\python.exe -X utf8 frontend/search/export_full_index.py --config staged/research-wiki/config.json
# 布局迁移后：D:\anaconda\python.exe -X utf8 apps/web/search/export_full_index.py --config skills/research-wiki/config.json
```

导出程序自动寻找引擎，也可指定 `--engine <rwiki包所在目录>`；`--out` 默认同目录 `full-search-index.json`。页面 `?fullindex=<URL>` 可覆盖索引地址。hash 中 `mode=full&q=差异表达&scope=knowledge&runnable=true` 可分享全文查询。

静态索引中的运行证据是带导出时间的快照，使用前应在本地应用重新核对。静态导出不复制来源代码，来源全文只在本地 API/CLI 搜索本机已下载文件。静态页面不会下载资源；本地应用只有点击“下载资料”才发起下载。

`full-search.js` 与 Python `rank_export` 的排名、分数、摘要和筛选通过 `parity.test.mjs` 对同一固定语料核对；`search-core.test.mjs` 继续检查原分面逻辑。

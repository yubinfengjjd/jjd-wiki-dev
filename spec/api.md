# 本地服务接口约定（M1：分析方法与数据接口）

全部 JSON，UTF-8。页面路径 `path` 一律是相对 wiki 根、用 `/` 的字符串，如 `layouts/<id>.md`、`templates/<id>.md`。出错返回 `{"detail": "<说明>"}` 与 4xx/500。

## 读

| 方法 | 路径 | 返回 |
|---|---|---|
| GET | `/api/pages` | `[{path, meta}]`，meta 为 frontmatter；含全部页面类型（layout、template、method、interface、scenario、chart-type、project），不含 index.md / log.md / AGENTS.md / CLAUDE.md |
| GET | `/api/page?path=<path>` | `{path, meta, body, backlinks: [{path, title, type}], gallery}`；`gallery` 只有版式页才有，为画廊条目 meta.json 原样内容，其余为 null |
| GET | `/api/graph` | `{nodes: [{id: path, type, title, status}], links: [{source, target, kind}]}`；`kind=feeds` 为有向数据流：方法→输出接口、接口→读取它的方法、接口→使用它的模板，从 method.json 与 spec.json 声明生成；`kind=link` 为其余正文双链，无向去重，去自链接与图片嵌入。同一对节点存在 feeds 时只保留 feeds（双向数据流可各有一条），不重复输出 link |
| GET | `/api/log` | `[{time, message}]`，新的在前 |
| GET | `/api/taxonomy` | 场景词表 `{<key>: {label, aliases}}` |
| GET | `/files/wiki/<path>`、`/files/gallery/<path>` | 根目录内文件，越界 404 |

## 写

每个写接口：改文件 → `save("<动作> <id>")` → 返回与 `GET /api/page` 相同结构的最新页面。`<kind>` 为 `layouts`、`templates` 或 `methods`。save 先统一重建模板、方法、接口三类页面的 facts，再重建 index 并保存；版式 facts 仍按画廊 meta 在相应操作中更新。方法与接口页的 gallery 为 null。

| 路径 | 适用 | 请求体 | 行为 |
|---|---|---|---|
| `POST /api/layouts/<id>/signoff` | 版式 | — | 画廊 status=approved，updated_at 更新；版式 status=pending_template。版式不是 pending_signoff 时 409 |
| `POST /api/layouts/<id>/reject` | 版式 | `{reason}` | 只允许 pending_signoff、pending_template，否则 409；画廊 status=draft；版式 status=pending_signoff；log 消息含理由 |
| `POST /api/methods/<id>/confirm` | 方法 | — | 仅 pending_confirm → ready，否则 409；同 CLI mark-ready，校验 method.json、params.yaml 与 example/output 中各输出接口 CSV 的存在、表头与非空数据行 |
| `POST /api/methods/<id>/return` | 方法 | `{reason}` | 仅 pending_confirm 或 ready → draft，否则 409；reason 为非空白字符串，否则 422；log 消息含理由 |
| `POST /api/<kind>/<id>/scenarios` | 版式、模板、方法 | `{primary, free}` | primary 1–2 个且在词表中，否则 422；更新 frontmatter，由 save 重建方法/模板 facts；版式 facts 单独更新 |
| `POST /api/<kind>/<id>/favorite` | 版式、模板、方法 | `{value: bool}` | 设置 favorite |
| `POST /api/<kind>/<id>/note` | 版式、模板、方法 | `{text}` | 替换 user 区块 |
| `POST /api/<kind>/<id>/archive` | 版式、模板、方法 | — | archived_from=原 status，status=archived；已归档 409 |
| `POST /api/<kind>/<id>/restore` | 版式、模板、方法 | — | 恢复 archived_from；未归档 409 |

## 其它

- 只监听 `127.0.0.1`；无登录。
- 非 `/api`、`/files` 路径返回前端构建产物（hash 路由回退到 `app/index.html`）。

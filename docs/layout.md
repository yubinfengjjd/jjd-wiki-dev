# 开发布局迁移

| 旧路径 | 当前路径 |
|---|---|
| `staged/research-wiki/` | `skills/research-wiki/` |
| `frontend/` | `apps/web/` |
| `obsidian-neural-view/` | `plugins/obsidian-neural-view/` |
| `review/` | `archive/review/` |
| `operations/` | `archive/operations/` |
| `spec/api.md` | `docs/api.md` |
| `spec/scenario_taxonomy.yaml` | `docs/scenario_taxonomy.yaml` |
| `spec/2026-10-22-obsidian-neural-view-plan.md` | `archive/spec/2026-10-22-obsidian-neural-view-plan.md` |
| `qa/` | `tests/e2e/` |
| `replications/` | `examples/replications/` |

本机保留内容仓库下的独立 `开发/` 检出；新克隆可采用同级 `jjd-wiki-dev/`。路径发现优先 canonical 布局，同时兼容旧版 nested 与 sibling 检出。新的 CI 与构建应直接使用当前路径，不能依靠本机 junction。

从内容仓库运行 `tools/migrate-layout.py --check --repo both`，确认相关路径干净后以 `--apply --record <全新本机记录目录>` 执行。`--rollback <记录目录>` 先核验逐文件哈希与本机配置；新改动或目标冲突会使回滚停止。记录包含 Git 元数据审计备份，但回滚不会恢复 index、HEAD 或重写提交。源代码、公开输入、许可证与历史收据只移动，不批量替换其中的旧路径。

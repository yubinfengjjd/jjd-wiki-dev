# Research Wiki 开发与完整技能包

完整技能位于 `skills/research-wiki/`，包含 `SKILL.md`、后端、脚本、参考资料、测试、配置示例和已构建的 `app/`。前端源码与锁文件位于 `apps/web/`；字体许可随构建产物保留在技能的 `app/licenses/`。知识与来源材料保存在 [jjd-wiki](https://github.com/yubinfengjjd/jjd-wiki)。第三方许可证按来源保留，不以本仓库名义重新授权。

| 路径 | 用途 |
|---|---|
| `skills/research-wiki/` | 可安装、可测试的完整技能 |
| `apps/web/` | 网页应用源码、构建与前端测试 |
| `docs/` | 当前 API、场景分类与布局说明 |
| `tests/e2e/` | 浏览器端检查脚本与步骤夹具 |
| `plugins/obsidian-neural-view/` | Obsidian 插件 |
| `examples/replications/` | 有出处的公开复现示例、输入与收据 |
| `archive/` | 历史 review、operations 与设计计划，保持原始记录 |

将完整技能目录复制到宿主技能根，按 `config.example.json` 配置本机被忽略的 `config.json`。依赖清单为 `requirements.lock.txt`；安装依赖前需作者确认。本机配置、虚拟环境、缓存与私有课题数据不分发。

已有依赖环境下，在技能目录运行 `python -X utf8 -m pytest -m "not r and not compose and not local"`；前端在 `apps/web/` 运行 `npm test` 和 `npm run build`，提交重建的技能 `app/`。本机 Windows 的 Python 脚本使用 `D:\anaconda\python.exe -X utf8`。GitHub 同步不会更新已安装技能副本，部署仍由内容仓库 `tools/deploy.py` 经过来源门禁后执行。

旧布局迁移映射与回滚边界见 [布局说明](docs/layout.md)。

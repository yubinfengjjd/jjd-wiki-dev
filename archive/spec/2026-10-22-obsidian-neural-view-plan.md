# Obsidian 科研神经图谱接入计划

**Goal:** 将作者指定的视频同源视觉接入 `E:\research-wiki\知识库` 的 Obsidian 辅助窗口。

**Architecture:** 独立本地 Obsidian 插件，只读读取 Markdown 与资源并打开原生笔记。保留发光光球、水母、扇形展开和详情侧栏；按图样、模板、方法、接口、课题分组。网页与 CLI 仍是签核、状态、待办、确认、删除的入口。页面、文件名、业务字段不迁移、不重写；不使用原项目的示例内容、创作流程与 localStorage 编辑功能。

**Tech Stack:** Obsidian ItemView、React、Canvas，复用指定上游的视觉代码与本地素材，esbuild 打包。

**Spec:** 本次用户消息明确批准 Obsidian 内前端接入及其阅读/作者备注边界。

## Global Constraints

- Vault 仅为 `E:\research-wiki\知识库`；不索引项目根，不引入画廊目录联接。
- 插件不写业务 Markdown、frontmatter、facts、状态，不运行分析或远程请求，不复制业务 workflow。
- 关系只表达已有页面引用/明示关系；普通引用不标成方法可直接接用。
- Obsidian 允许作者在 user 标记之间写备注；不重命名、移动、删除正式条目。
- `.obsidian/` 排除 Git；链接根目录绝对路径，关闭自动更新链接，属性用源码显示。
- 回放证据 verify/ 继续随 Wiki Git 记录；Obsidian 检索排除不等于 Git 排除。
- 保存上游版本、许可及 NOTICE；开发目录已有未提交工作不得覆盖或提交。
- 规则同步正式 Wiki、staged 规则源和三处已安装 research-wiki 技能；末尾通过 wiki.py save 提交本次 Wiki 规则变更。

## Tasks

- [ ] 1. 独立插件：在 `开发/obsidian-neural-view` 保存上游版本并实现只读数据适配、原版视觉与原生笔记打开；验证无写权限路径、无示例注入、无虚构业务状态。插件停用/视图关闭时清理动画与订阅。
- [ ] 2. Vault 配置：备份相关现有配置；为正式知识库建立 `.obsidian` 设置与插件安装，保留原 vault。设置内部链接、属性与检索排除，记录维护边界并同步安装规则。
- [ ] 3. 接入验收：构建与边界测试，核对条目哈希未变、Git 忽略、同步规则一致与 Wiki lint；真实 Obsidian 检查光球/五模块、展开、详情、打开笔记、返回/刷新。
- [ ] 4. 独立审查与修复，保存截图/检查回执；如受本机运行条件阻碍，明确报告已验证范围。

## Rulings

- 用户已明确选择 Obsidian 内部与辅助使用边界；按该设计直接执行，不另建业务平台或重复询问实施方式。
- 本次插件源与运行产物放独立目录，避开现有前端及后端未提交改动。

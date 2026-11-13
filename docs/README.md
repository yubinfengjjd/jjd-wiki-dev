# 当前开发指南

- [API](api.md)：现有接口与正式写入边界。
- [目录与兼容](layout.md)：完整技能、自包含源码、旧布局及双仓库路径发现。
- [场景分类](scenario_taxonomy.yaml)：受控分类原件，不是检索词语的白名单。
- [技能检索与轻量获取](../skills/research-wiki/references/search-and-checkout.md)：CLI、网页、静态快照及资产状态。
- [检索验收](../archive/review/search-benchmark/README.md)：冻结问题、基线与剩余误差。

Python 后端与测试只维护 `skills/research-wiki/` 一份。前端在 `apps/web/` 构建，产物写入技能 `app/`；保持字体与来源许可。不能将构建通过替代浏览器验收，也不能把结构测试通过记作科学验证。

本机脚本用 `D:\anaconda\python.exe -X utf8`。新增或升级依赖必须先列用途并得到作者确认。本轮使用既有依赖，没有安装或升级包。完整版本才用于正式知识维护；light 用于发现、明确获取与课题复用。

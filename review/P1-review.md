<!-- rwiki-migrated: issue=https://github.com/yubinfengjjd/jjd-wiki-dev/issues/11 -->
> 已迁移，停止维护：https://github.com/yubinfengjjd/jjd-wiki-dev/issues/11

# P1 审查

结论：**通过**（审查中改了 2 处）。

## 独立核实

- 普通 shell 全套：183 passed（含 R、compose），之后补加 1 条 lint 测试，lint/panels/templates 三个文件 74 passed。总计 184 项。
- 真实画廊 79 个文件与 `codex/real-gallery-before.json` 逐一比对，0 处变化；正式总库未创建。
- 按任务书逐项核对：版式页必需键、panel_map 缺失报错、scaffold 的状态/字母/图型/重复覆盖检查、attach 复用、verify-template 不再比对整图、load_layout 的各类错误、compose_runner 不导入 rwiki、同名辅助模块不冲突、版式 mark-ready 门槛、render-layout 的 style 校验在启动子进程之前、suggest 的 kind、服务端签核移到版式、lint 的双向引用规则。
- 旧的整图模板代码已删，没有兼容读取或迁移脚本。

## 偏离裁定

- **版式增加 `template_panels`**（模板 id → 它在本版式覆盖的字母）：接受。任务书只让模板记来源版式的字母，attach 到别的版式时字母可能不同，原设计确实存不下。
- suggest 中版式的 tables 键用 `<模板 id>/<表名>`：接受，防止同名表互相覆盖。
- 比对逻辑抽到 `verification.py`：接受，避免两套度量。

## 审查中修改

1. `lint.py`：layout.json 不合法时原来直接抛错中止，前面积累的诊断都不打印。改为把错误作为一条 ERROR 报出，与其他诊断一起输出；补测试 `test_lint_reports_bad_layout_json_alongside_other_findings`。
2. `templates.py` 的 `mark_ready`：原来用三次 `if meta["type"] == "template"` 分段判断，`spec` 是条件赋值，版式还重复检查了一遍 preview。改为版式、模板两个分支各自完整。

## 记录（不阻塞）

- `ingest_entry` 里拼 facts 的三行和 `layout_facts` 重复（只是少读一次画廊 meta）。小，不改。
- 每个测试都会复制一份 20 MB 的测试画廊，一次全套约 2 GB 临时文件。审查时 C 盘被历次审查的临时目录占满，已清理；以后固定用同一个 basetemp 名，pytest 运行前会清空它。
- layout.json 的 labels 只有 text/x/y/size，post01 原图的字母是粗体、底对齐。P2 需要补 `weight`，见 P2 任务书。

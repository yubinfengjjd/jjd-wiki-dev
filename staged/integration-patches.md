# T6 集成补丁（待作者确认后在 T7 安装）

这些改动写在已装技能里，影响作者的其他工作，而且技能目录在 C 盘。按作者“C 盘不要动”和“改前备份、两侧同步”的约定，T6 只准备补丁文本并测试 research-wiki 技能本身；安装与修改在 T7 由作者确认后执行。

## 0. 安装 research-wiki 技能

- 技能目录 = `staged\research-wiki` 的全部内容（`SKILL.md`、`wiki.py`、`rwiki\`、`assets\`、`app\`、`config.json`、`requirements*.txt`），不含 `tests\`。
- 两侧各一份：`C:\Users\86186\.claude\skills\research-wiki\`、`C:\Users\86186\.codex\skills\research-wiki\`（约 2 MB，主要是前端构建产物）。
- `config.json` 的 `wiki_root` 改为 `E:\桌面\科研知识库`，`gallery_root` 为 `E:\桌面\科研绘图画廊`。
- `SKILL.md` 中的 `<本技能目录>` 两侧分别替换成实际路径。

## 1. sci-figure-replica（两侧）

在“九步流程”第 9 步之后加：

```markdown
10. **收录进知识库**：装有 research-wiki 技能时，按它的 SKILL.md 运行 `wiki.py ingest-figure <条目 id>`，并按总库 AGENTS.md“收录”填写版式页的适用与不适用。帖子带分析代码（`example_not_target` 也算）时，问作者是否抽成方法；同意则 `scaffold-method --from-entry <条目 id>`，进入待办。
```

## 2. medfig-render（两侧）

在“§1 什么时候用哪个技能”的表格后加：

```markdown
动手写脚本前，装有 research-wiki 技能时先按它的 SKILL.md 运行 `suggest`（图型、场景、数据列）。有 ready 模板时，把 1–2 个列给作者作为候选，并说明差别：模板出自复刻图、换数据直接出图，不经 figkit 的 `export.save` 与本技能的影像和统计红线，用于论文前需按 §10 自查。作者选用才走模板；没有匹配或作者不选，照常按本技能画。
```

## 3. medpaper-pipeline（两侧）

在“规则”末尾加：

```markdown
- 第 3 阶段出图前，装有 research-wiki 技能时，提醒被调用的 medfig 技能先查知识库模板（medfig-render 已含此步）；本技能不自己查、不自己画。
```

## 安装步骤（T7）

1. 备份三个技能两侧的 `SKILL.md` 到 `E:\research-wiki-env\skill-backup\<日期>\`。
2. 复制 research-wiki 技能到两侧，改 config 与路径。
3. 按上面 1–3 插入文本，两侧逐字相同。
4. 新开会话验收：说“复刻完 post01 后收录”“给这份数据推荐 SHAP 图”，看 agent 是否按技能走。

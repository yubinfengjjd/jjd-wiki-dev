---
name: research-wiki
description: Use when the author wants a figure or an analysis for a research project and may already have a reusable figure template or analysis method in their 科研知识库 (LLM Wiki), such as 出图前查模板、推荐图、换数据套用、SHAP/差异分析等可复用方法、分析→出图、处理待办、收录复刻图或方法、知识库体检; also when sci-figure-replica, medfig-render or medpaper-pipeline reach a drawing step.
---

# 科研知识库（research-wiki）

作者的知识库是一个 LLM Wiki，写给你读的说明书：

- **图模板**：带可运行代码，换上作者的数据就能出图（`render`）。
- **方法笔记**：写清一步分析怎么做，有的附可复用的代码模板。你在作者课题的环境里写代码、运行，知识库不替你跑。
- **数据接口**：方法最后要整理成的表格格式，也就是模板读取的表。

你通过本技能目录下的 `wiki.py` 操作知识库，不读 `rwiki/` 源码也能完成全部工作。

## 先做两件事

1. **用对解释器。** `wiki.py` 只能用 research-wiki 自己的 Python 运行；配置里的 `python_exe` 是模板出图用的，由 wiki.py 自己调用：

   ```powershell
   $env:TEMP=$env:TMP='E:\research-wiki-env\tmp'; $env:MPLCONFIGDIR='E:\research-wiki-env\tmp\mpl'
   $rw = 'C:\Users\86186\.codex\venvs\research-wiki\Scripts\python.exe'
   & $rw -X utf8 '<本技能目录>\wiki.py' <命令> …     # 默认读本技能目录的 config.json
   ```

2. **读总库根目录的 `AGENTS.md`**（路径 = config.json 的 `wiki_root`）。页面类型、谁能改什么、收录与推荐的规则都在那里，以它为准。

## 作者要出图或做分析

| 作者的话 | 命令 |
|---|---|
| 数据已经是整理好的表，要出图 | `suggest --columns a,b,c --q …` → `contact-sheet <模板 id，1–3 个> --out <课题>\candidates.png` |
| 要先做分析再出图 | `suggest-pipeline [--figure <模板 id>] --q …` |

`suggest` 只是初筛：读候选页面的“适用/不适用”，按作者课题和数据的实际情况判断，不按标签判断。只推荐 `ready` 的模板和方法。给 2–3 套候选（方法 + 可接的图），写明适用理由和作者数据要怎么改。同一张图有多个方法时按“适用/不适用”对比，给首选和理由。**然后停下等作者选。** 作者已经点名了方法和图（且都是 ready）时，不再推荐，直接执行下面的步骤。

作者选定后连续执行，全部产出放课题目录：

1. 读方法笔记的“输入”“怎么做”“代码”。方法有 `code/` 时复制到 `<课题>\scripts\`，改脚本开头的参数；没有就按笔记写脚本。
2. 在课题自己的 Python / R 环境里运行。缺包时列出包名问作者，不要擅自装，也不要改用知识库的解释器。
3. 检查结果是否可信（笔记“怎么做”写了判断方法，例如模型在测试集上不比基线好时解释没有意义），不可信就停下告诉作者。
4. 把结果整理成模板要的接口表：`<课题>\analysis\<接口 slug>.csv`，列名与接口页一致。
5. 每张图：`render <模板 id> --data <课题>\analysis --out <课题>\figures\<名>`（整张组图用 `render-layout`）。打开 PNG 看一眼。
6. 每张图：`record-use <模板 id> --project <课题 slug> --title "<课题名>" --output <png 路径> --method <方法 id>`

只在报错或结果异常（输出为空、模型不比基线好、数值离谱、图上文字被裁切）时停下说明。给作者的消息里写关键数字和你改过的参数。

## 其他操作

| 场景 | 命令 |
|---|---|
| sci-figure-replica 复刻完一张图 | `ingest-figure <画廊条目 id>`，再按 AGENTS.md“收录”补适用说明 |
| 作者说“处理待办” | `pending`，按 AGENTS.md“处理待办”拆模板 |
| 收录一段分析代码或写方法笔记 | AGENTS.md“收录方法”（`scaffold-method` → 写笔记 → 作者确认） |
| 体检 | `lint` |
| 网页 | `serve`（作者在网页签核、确认方法、改标签） |

所有写操作最后都是 `save "<说明>"`（多数命令已自带）。完整参数：`wiki.py <命令> --help`。

## 常见错误

- 用 `python_exe` 跑 wiki.py：报 `No module named 'yaml'`。
- 推荐后不等作者选就开始做。
- 分析脚本、数据、成图写进知识库目录；知识库只通过 `record-use` 记录路径。
- 手改 `<!-- facts -->` 区块、frontmatter 的 `status`，或 `<!-- user -->` 区块。
- 临时文件、缓存写 C 盘：先设 TEMP/TMP/MPLCONFIGDIR 到 E 盘。

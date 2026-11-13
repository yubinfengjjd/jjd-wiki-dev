<!-- rwiki-migrated: issue=https://github.com/yubinfengjjd/jjd-wiki-dev/issues/4 -->
> 已迁移，停止维护：https://github.com/yubinfengjjd/jjd-wiki-dev/issues/4

# T1 审查

结论：**通过**，3 处小修并入 T2 任务书第 0 节。

## 独立验证（Claude，普通 shell）

- `pytest staged\research-wiki\tests`：52 passed（24.05s），basetemp 放在 %TEMP%，不复用 Codex 的产物。
- `wiki.py --config codex\t1-config.json lint`：`OK`，退出码 0。
- 真实画廊 `E:\桌面\科研绘图画廊`：79 个文件，与开工前的哈希清单（codex/real-gallery-before.json）逐一比对，0 处变化。
- `E:\桌面\科研知识库` 不存在（未越界）。
- 测试中没有 mock 或 monkeypatch；文件系统和 git 都是真实操作。

## 代码审查

符合要求：
- 10 个模块各管一件事，最长的 ingest.py 119 行；只有 `Config`、`WikiError` 两个类。
- 只在 `cli.main` 捕获 `WikiError`；`JSONDecodeError`、`YAMLError` 在解析边界转成带路径的 `WikiError`。没有宽泛 except，没有吞掉的异常。
- 没有 T2–T4 的桩或预留参数。
- `parse_page` 返回错误值而不抛异常，是为了让 lint 能累积诊断；`read_page` 在其上抛异常。这样分工合理，不算防御性代码。
- 两处偏离（`render_facts` 增加 taxonomy 参数、3.5.4 的字段划分）判断正确，予以接受。

需要修改：
1. **null 来源字段写成 "None"**（已复现）。画廊 schema 允许 post 的 title/account/publish_date/url 为 null，`render_facts` 会输出 `- URL：None`。帖子标题为 null 时，`new_page` 的标题会变成 `Fig. 4 None`。
2. **多余的 history 判断**：`ingest_figure` 里的 glob `*/figures/*/meta.json` 只匹配第三层，不可能命中 `history/` 下的文件，`"history" not in parts` 永远为真，应删除。现有的 history 测试删掉这行后仍应通过。
3. **`links.resolve` 重复拆分**：`extract_links` 已经去掉了 `|label` 和 `#heading`，`resolve` 又拆一次。按约定 resolve 只接收已提取的目标，删除重复拆分。

## 留给后续阶段

- config.json 的 taxonomy 指向 Claude 侧的 sci-figure-replica 安装目录。T6 在 Codex 侧安装时需要确认这条路径对 Codex 同样可用。

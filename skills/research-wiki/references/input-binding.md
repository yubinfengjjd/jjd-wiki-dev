# 灵活输入与显式 bindings

方法的知识分三层，不能混成一个“必须长成 CSV”的要求：

1. **语义要求**（方法家族）：需要什么对象/矩阵/模型、行单位、配对关系、编码/单位和前提，写在 `data_contract` 与正文。
2. **实现接受对象**（具体实现）：真实接受的 Seurat 对象、模型、数组或表，参数与返回结构写在 `implementations`/正文。
3. **内部表格式**（绘图执行）：模板读取的接口是代码约定。外部数据不必改名或改列名，用显式 bindings 映射成内部表，再交给现有 R/Python 绘图核心。

## 命令

```powershell
wiki.py render <template-id> --data <project-data-dir> --bindings <project>/bindings.json --out <project-output>
```

- 不给 `--bindings`：仍读取 `<data>/<interface>.csv` 并按列名检查，旧调用/回放完全兼容。
- 给 `--bindings`：在输出目录建立本次运行的临时规范表，内层 render 脚本仍读取 `<interface>.csv`；运行结束清理临时表。
- 标准文件名只是内部约定，不是作者原表的命名要求。
- `use <模板 id> --project <课题>` 会在副本写 `bindings.draft.json`：每张表 `file` 为 `<接口>.csv`、列为同名映射。把右侧改成课题的文件名与列名，另存为 `bindings.json` 再传给 `--bindings`。
- 本轮 bindings 只用于单模板 `render`；`render-layout` 组合入口仍按 `layout.json` 读取全部面板表，不支持 bindings 或省略可选表。

## bindings 格式

表键固定来自 `spec.json` 的 `tables`；下面 `dotplot` 是真实模板 `2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot` 的表键：

```json
{
  "tables": {
    "dotplot": {
      "file": "my_results.csv",
      "columns": {
        "group": "cell_type",
        "feature": "gene_symbol",
        "avg_expression": "mean_expr",
        "pct_expressed": "positive_percent",
        "target_group": "target_cell_type"
      }
    }
  }
}
```

- `columns` 方向是“**内部字段 → 作者列**”。
- `file` 相对 `--data`；不允许绝对路径、盘符、`..`、隐藏文件或 `http(s)://`。
- 未在 `columns` 中出现的内部字段按同名列匹配；不按相似度猜列。
- 检查**完整有效映射**（显式映射 + 同名回退）：同一作者列只能被一个内部字段消费。例如 `group→feature` 且 `feature` 同名回退到同一列时，必须报“同一来源列被多个内部字段消费”，不能同时填满 group 和 feature。
- 额外原始列默认保留（rename 后附加在内部列之后），源文件不改。

## 必需与可选

- 接口列可写 `required: false`；spec 的表也可写 `required: false`；未写默认必需。
- 可选只用于实现确实有缺省分支的表/列。真实例子：
  - `render-dotplot-long.target_group` 可选：缺失时模板按 feature 出现顺序排序，不生成目标组。
  - `render-cell-metadata.cell` 可选：提供时拒绝重复细胞 id；省略时只按 group/stat 计数，无法逐细胞去重。
- 缺必需表/列在运行前失败；缺可选列只省略并写入报告，不补值。
- 不能为了绕过检查把核心仍索引的列声明为可选。

## 允许的整理

只允许显式、无聚合的 `melt`/`pivot`：

```json
{"op": "melt", "id": ["gene"], "variables": ["g1", "g2"],
 "variable_name": "group", "value_name": "avg_expression"}
```

```json
{"op": "pivot", "index": ["gene"], "columns": "group", "values": "avg_expression"}
```

- 必须显式写 id/变量/值列（pivot 还有 index）；`carry` 明确哪些额外列随行保留。
- pivot 重复键直接拒绝，不自动求均值；缺失组合留空并在报告中计数。
- pivot 的 index 必须按原值身份保留，不能用分隔符拼接再还原：空字符串、缺失值、嵌入 `\r`/分隔符的值必须原样出现在输出。空值或缺失的 pivot 类别无法形成稳定列名，显式拒绝。
- 不做聚合、删行、填补、补样本、单位换算、统计检验、训练或重新划分。

## 校验与映射报告

运行前失败：未知表、未知映射字段、重复映射、完整有效映射冲突、重复源表头、路径越界/网络/隐藏、必需表/列缺失、数值列含非数值或非有限值、非法 reshape 选项，以及**输出覆盖任一来源**（同名、另一个表的输入、硬链接/符号链接别名）。

写盘顺序：

1. 先读取并校验所有表，在**任何写操作前**记录每个源文件的 SHA-256。
2. 预检全部输出路径与全部来源路径，冲突则整体失败。
3. 所有规范表先写入临时 staging，全部成功后才替换正式输出；任一写入失败时删除本次新建输出、恢复被替换的旧输出，不留部分结果。

报告写在 `<out>/bindings-report.json`：

- 源文件相对路径与**写前** SHA-256、输出文件与 SHA-256；
- 映射、保留/省略列、额外列、reshape 操作；
- 每列缺失计数与观测范围；
- `semantics` 明确：只核对字段存在、必填关系和数值可解析；**不验证单位、粒度、配对或统计含义**。

0–1/0–100 的提示：接口描述声明 0–100 而观测值全在 0–1（或反之）时写 warning，但不自动乘除换算。字段名吻合不证明单位正确，需 agent 核对。

## 可复制模块

- Python：`rwiki/input_binding.py`，仅标准库。复制后在课题调用 `prepare_tables(spec_tables, bindings, data_root, work_dir)`，或对内存记录用 `reshape_records`/`map_records`。
- R：`assets/input_binding.R`，base R。`bind_table(df, columns, mapping)` 直接映射 data.frame；`reshape_table(df, reshape)` 做显式长宽整理；`prepare_binding_table(...)` 读文件并写规范表，批量调用方用 `other_sources=` 传入其他表的源文件。
- R 的别名/硬链接检测在安装 `fs` 时使用 device/inode。没有 `fs` 时仍做规范化路径与组件边界检查；写入前先把已有输出目录项移开，再把临时文件重命名到目标（失败则恢复旧目录项），因此即使未识别出硬链接/符号链接别名也不会写穿源 inode。无法确认安全的同路径输出仍拒绝。
- R 报告始终返回非空 `semantics`（与 Python 同一句限制），明确不验证单位、粒度、配对，不自动换算。
- 两者不依赖 Wiki 绝对路径、全局数据或网络。R/Python 用同一夹具核对过表头、行序、缺失可选项、额外列、空字符串/缺失值/嵌入 `\r` 的 pivot index 与有效映射冲突的等价。

## 与验证证据的关系

- `verify-template` 只证明当前 code/spec/example/接口列的标准输入回放；不证明任意外部文件或 bindings 已验证。
- 改变 bindings 或输入映射时，在课题记录实际命令、映射报告与前后表/图对照；不要扩大旧收据的 scope。
- 旧标准 `render`、`verify-template`、单 panel 回放保持兼容；`verify-template` 不会自动使用 bindings。

## 真实模板验收（2026-10-23）

- R 点图：`dotplot` 表键，重命名文件/五列后经 `--bindings` 出图，与标准输入 PNG 像素一致；省略可选 `target_group` 仍可运行。
- R 分组柱图：`metadata` 表键，重命名 `cell/group/stat` 且省略可选 `cell`，与标准输入一致。
- Python SHAP 条形图：`SHAP汇总` 表键，重命名 `feature/shap/percent`，与标准输入像素一致。
- 具体命令、退出码和哈希见维护记录 `verification-matrix.md`；示例数据只用于软件等价检查，不代表科学有效性。

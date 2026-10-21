# M1 审查

结论：**通过**（审查中删了 2 处多余检查）。

## 独立核实

- 普通 shell 全套 287 passed（含 R、compose）。删检查后，方法与集成两个测试文件 70 passed。
- 真实画廊 79 个文件 0 变化；test-wiki*、test-gallery* 未改（Codex 的 8075 文件哈希对照）。
- 按任务书核对：接口页是唯一列定义，load_spec 从接口取列；method.json / params.yaml 校验；依赖版本检查与“安装前须征得作者同意”提示；输出表头与空输出检查；draft → pending_confirm → ready 及网页 confirm/return 的 409；save 时统一重建模板、方法、接口 facts，旧的单独重写已删；graph 的 feeds 边按数据流向，与双链重叠时只出 feeds；suggest-pipeline 按模板分组列出全部可接方法及适用/不适用正文；record-use --method。
- lint 遇到坏资产时作为 ERROR 报出，不中止；有 ERROR 时跳过 facts 一致性比较，避免在坏数据上再报一层。

## 审查中修改

- `methods.py`：删 `isinstance(id, str)`（id 只从 argparse 来）；删 from_entry 与 from_path 二选一的重复检查（argparse 互斥组已保证）；`_method_page` 删 type/status 复查（lint 负责页面合规）。

## 记录（不阻塞）

- `store.save` 要重建 facts，facts 要读方法和接口，而方法、接口命令又要调 save，于是 store、methods、interfaces 里各有一处函数内导入来绕开循环。可以接受；若以后再加类型，考虑把纯校验（load_method、load_params、load_interface）挪到单独模块。
- 扁平参数只接受标量（字符串、数字、布尔、null）。像“基因列表”这类参数以后要么写成逗号分隔字符串，要么放进输入文件；遇到真实需求时再定。
- test-wiki-p2 的模板 spec 仍是旧格式（表里有 columns、没有 interface），在 M1 代码下 load_spec 会报错。M2 迁移。

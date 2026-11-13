<!-- rwiki-migrated: issue=https://github.com/yubinfengjjd/jjd-wiki-dev/issues/6 -->
> 已迁移，停止维护：https://github.com/yubinfengjjd/jjd-wiki-dev/issues/6

# T3 审查

结论：**通过**。

## 独立核实

- 普通 shell 跑完整测试（含 R 标记）：114 passed。
- 真实画廊 79 个文件与开工前哈希一致；正式总库未创建。
- 候选拼图 `codex/T3-sheet.png`：序号、标题截断、中文字体正常，回放图完整。
- 演示课题页与模板页“使用记录”：记录插在 user 区块之前，链接正确；交付说明里有重复调用不新增提交的验证。

## 代码

- suggest：打分规则与任务书一致，理由逐条可读；note 来自 user 区块，满足“备注推荐时 agent 能读到”。
- `section_bounds` 先把 user 区块内容替换成空白再找标题，避免作者在区块里写的“## ”标题干扰分节，同时保留原文偏移。这样写有必要，不算过度设计。
- record-use 用正则判断记录是否已存在，判断范围只限本节，幂等。
- 小意见（不返工）：`suggest` 里 `limit < 0` 的检查放在 argparse（`type` 校验）更自然。

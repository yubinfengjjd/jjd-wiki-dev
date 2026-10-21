# M2b / M2c 审查

日期：2026-10-21。结论：**通过**。

- 全套 pytest 普通 shell 重跑（含 R、bio）：300 passed；真实画廊 79 文件 0 变化。C 盘可用空间运行前后差 −0.8 MB，量级属系统后台波动（测试 TEMP/basetemp/缓存均在 E 盘）。
- M2b：三个模板只改 spec 的 width_in/height_in/rect，整图回放 0 差异；两份数据无文字越界。固定版心对短标签数据仍有预留空白，Codex 如实说明，留作后续（按标签宽度自动定版心）。
- M2c：`report.json` 是可选运行摘要，不进接口与 facts；run/verify 成功后打印，每次运行先清除旧报告（避免复用目录时显示旧值，合理）。`init` 对已有总库只覆盖 AGENTS.md、CLAUDE.md。示例报告：XGBoost 测试集 R² 0.446、RMSE 54.7（基线 73.7）；随机森林 R² 0.480，均明显优于基线。
- 同步到 test-wiki-m3 时覆盖了此前的两处修正（随机森林 n_jobs 说明、方法场景标签），已恢复后提交；lint OK。
- 前端：方法页“示例输出”顶部显示 report.json；技能 SKILL.md 第 3 步加“读 report.json，模型不优于基线即停下”。

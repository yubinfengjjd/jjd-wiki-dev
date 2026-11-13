<!-- rwiki-migrated: issue=https://github.com/yubinfengjjd/jjd-wiki-dev/issues/9 -->
> 已迁移，停止维护：https://github.com/yubinfengjjd/jjd-wiki-dev/issues/9

# T6 技能与集成 · 记录（Claude）

日期：2026-10-21。

## 范围裁定

技能安装目录与三个已装技能都在 C 盘，改动会影响作者的其他工作。作者要求“C 盘不要动”，且约定“改已装技能前备份、两侧同步”。所以 T6 只做：写 `staged\research-wiki\SKILL.md` 并用子 agent 测试；把三个技能的增补写成补丁文本 `staged\integration-patches.md`。安装与修改放到 T7，由作者确认后执行。

## 测试（RED → GREEN）

同一份合成数据（250 行，8 个指标，目标 score），两个场景，各跑一次无技能（RED）、一次有技能（GREEN）：

| 场景 | 无技能 | 有技能 |
|---|---|---|
| A 推荐（停在等作者选） | 23 步、150 s；用错解释器失败一次后自己翻 venv；通读 rwiki 源码找命令；因测试库 AGENTS.md 过时，改读代码目录里的规则 | 15 步、80 s；解释器一次对；不读源码；给 3 套方案、首选与理由、要改的参数和输入文件名，停下 |
| B 按点名执行 | 26 步、230 s；两次用错解释器；通读源码；另写脚本补模型表现 | 18 步、140 s；解释器一次对；run-method → 检查 → render → 看图 → record-use → lint；不另写分析代码，在消息里说明缺口 |

两个场景的推荐与执行质量在有无技能时相近（agent 本身能读懂 wiki），技能消除的是“找不到怎么跑”和“读源码”的成本，以及另写分析代码替代库方法的倾向。

## 测试后对技能的修改

- `contact-sheet` 只收 1–3 个模板 id（GREEN A 传了版式 id 报错一次）。
- 作者已点名方法和图时直接执行，不再推荐（GREEN B 自行做了正确判断，写成明文）。

## 测试暴露的后端问题 → M2c

- 方法不报告模型表现与选中参数 → `report.json` 约定。
- 已有总库的 AGENTS.md 无法更新 → `init` 对已有总库覆盖规则文件。

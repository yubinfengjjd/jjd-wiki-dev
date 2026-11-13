<!-- rwiki-migrated: issue=https://github.com/yubinfengjjd/jjd-wiki-dev/issues/12 -->
> 已迁移，停止维护：https://github.com/yubinfengjjd/jjd-wiki-dev/issues/12

# P2 审查

结论：**退回返工**（结果正确，代码结构需整理）。

## 已核实

- 目视 `codex/P2-renders/layout-ten.png`：两行各 10 个特征，六个面板完整落在画布内，inset、色标、特征名、环形标签都正常。
- 真实画廊 79 个文件与基线比对 0 变化（Codex 读 color_audit.json 时权限不足，由 Claude 补做）。
- 整图回放与 T2 回放图相比，面板主体 0 像素差；差异只在 6 个面板字母（拼合脚本没有字母字体字段，用了默认 DejaVu Sans）。
- C/F 的 rect 用 polar 轴实际坐标、蜂群在版式中关特征名、径向留白回放值放 example/style.json：接受。

## 退回原因

1. **按数值命名的样式键**：`font_sizes` 的 `s7_5`、`s12`、`s4_8`，`line_widths` 的 `s0_2`、`s0` 等。键名就是取值，作者没法知道改 `s12` 会改哪里，等于把常量换了个地方放。可调项要按用途命名（如 `axis_label_size`、`bar_value_size`）；没人会调的取值（如线宽 0）直接写在代码里。
2. **先画一遍再改一遍**：T2 的 `drawing.py` 原是通用画法，`build_figure` 再覆盖其中的设置。拆成独立模板后这层覆盖成了死代码，例如：
   - 条形图：x 轴标题在 drawing 里用 11 号，panel 又改成 12 号；数值标注 7.5 号再改 4.8 号；色标高低文字 9 号再改 10 号并改位置；inset 先按等分角度画，panel 再逐个改扇区的角度、宽度、高度和文字位置。
   - 环形图：标签旋转在 drawing 里算一遍，panel 按偏置后的角度重算；色标刻度 6 号再改 4.5 号，标题 7 号再改 4.3 号。
   - 每个模板应当一次画对：把 drawing.py 与 panel.py 合并，只保留最终生效的值和算法。
3. 面板字母字体：labels 增加必填的 `family`，版式写 Arial，消除最后 6 处差异。

## 返工复核：**通过**

- 普通 shell 全套 197 passed（含 R、compose）；p2 测试库 lint OK；真实画廊 79 文件 0 变化。
- 三个模板各只剩 `__init__.py`、`panel.py`、`render.py`。逐行看了条形图 panel.py：每个属性只设一次，inset 直接按最终角度和高度画，没有覆盖设置。样式键按用途命名，没人调的取值写成代码常量。
- 整图回放与 T2 回放、与画廊 replica.png 都是 0 像素差（字母改 Arial 后，最后 6 处差异消失）。六张单模板图与改前 0 差异；layout-ten 只在六个字母处不同，Codex 用 DejaVu Sans 诊断证明了差异全部来自字体。
- 目视 bar-example、beeswarm-ten、layout-ten：完整、无裁切。
- 裁定记录：Codex 指出返工任务书第 3、4 条冲突并停下，按它提出的口径裁定，写入任务书第 4 节。

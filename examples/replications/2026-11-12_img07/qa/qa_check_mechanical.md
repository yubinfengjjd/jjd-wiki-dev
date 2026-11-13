# QA report

2026-11-12T09:48:24.500607Z

机械检查只核查文件、像素尺寸与宽高比；不判断视觉像不像，不代表作者签核。

| 自动检查 | 状态 | 证据 |
|---|---|---|
| meta.json | PASS | 文件存在且非空；不等于格式或视觉验收 |
| README.md | PASS | 文件存在且非空；不等于格式或视觉验收 |
| data/figure_spec.json | PASS | 文件存在且非空；不等于格式或视觉验收 |
| data/estimated_data.csv | FAIL | 文件存在且非空；不等于格式或视觉验收 |
| output/replica.png | PASS | 文件存在且非空；不等于格式或视觉验收 |
| output/replica.pdf | PASS | 文件存在且非空；不等于格式或视觉验收 |
| output/replica.svg | PASS | 文件存在且非空；不等于格式或视觉验收 |
| compare/side_by_side.png | PASS | 文件存在且非空；不等于格式或视觉验收 |
| thumb.png | PASS | 文件存在且非空；不等于格式或视觉验收 |
| run.log | PASS | 文件存在且非空；不等于格式或视觉验收 |
| 复刻代码 | PASS | 需要 replica.py 或 replica.R |
| 原图存档 | PASS | source/figNN.png |
| original 可打开 | PASS | PNG 3216×2160 px |
| replica 可打开 | PASS | PNG 3216×2160 px |
| PNG 格式 | PASS | 要求 PNG |
| thumbnail 可打开 | PASS | PNG 480×322 px |
| 宽高比 | PASS | 相对误差 0.0000%，阈值 ≤2% |

## 人工视觉 QA（未评定）

| 项目 | PASS/WARN/FAIL（待填） | 理由（待填） |
|---|---|---|
| 画布/宽高比 | | |
| panel 布局与面板标签 | | |
| 颜色/发散方向 | | |
| 字体/中文缺字 | | |
| 坐标轴/刻度 | | |
| 图例/colorbar | | |
| 数据形状/estimated 不确定项 | | |
| 注释 | | |
| 导出/矢量文字可编辑 | | |

作者/签核日期/结论：________

修图以满足检查；不得降低阈值以通过。

# img07 v2.2 QA 独立复核报告（QA · 质检）

- 时间：2026-11-12 17:50–18:01（UTC+8）
- 对象：`/workspace/replications/2026-11-12_img07/v2.2/`；Builder 收据 `v2.2/runs/v2.2_20261112T174749+0800.json`（sha256 `147ef9cb5dbec913…`）
- QA 收据：`v2.2/qa/qa_rerun_receipt_v2.2.json`；QA 工作目录：`/workspace/qa/img07_v2.2_rerun/`（`qa_scripts/`、`pkg/`、`qa_palette_v2.2.json`、`qa_detector_6vs12.json`）
- 只读：Builder 的文件一个没改（`find v2.2 -newermt 17:48:30` 只有 Builder 17:48:50 自写的 `qa/qa_report.md`）；没标 ready，没入库，没开 PR，没装依赖。

## 结论：有条件 PASS

数值验收全部通过；换目录完整重跑可复现；4 条旧备注里 (b)(c)(d) 已修好，(a) 还差一处：模块中心坐标的缩放没写进 METHOD。条件：入库前在 METHOD v2.1/v2.2.1 补一句“MDS 中心按 max|坐标| 归一后 ×10 作为 KK 初始坐标”。其余为不阻塞备注。

| # | 项目 | 结论 | 关键证据 |
|---|---|---|---|
| 1a | 外观参数写进 METHOD | 基本修复，残留 1 处 | v2.2.1 表与 `02_plot_network_go.R` 默认值逐项一致：node_size 1.5；ggrepel force 4 / force_pull 1.5 / box.padding 0.3 / point.padding 0.05 / max.iter 20000 / max.time 600 / seed 42；theme_bw base_size 6；strip margin 1.4 pt；x 标题行 60:1.2；MDS 距离 = 1−模块间平均 TOM；KK 边长 1/(w′+0.05)/10。**未写**：第 65–66 行 `cm <- cm/max(abs(cm)); init <- cm*10 + N(0,init_spread)`（中心 ×10）。`diff v2/code v2.2/code` 对 01/02 两个 R 脚本无差异 |
| 1b | 收据 command 漏 `--v1` | 已修复 | `run_all.sh` 用 `printf %q` 记下原始调用，传给 `04_receipt.py --cmdline`。Builder 收据 command 含 `--v1 …/output/replica.png --skip_prepare 1`；QA 重跑收据 command 同样含 `--v1`，三联图生成，sha256 `32400a22…` 与 Builder 一致 |
| 1c | gallery_local / qa_check_mechanical.md 来自作废运行 | 已修复 | `run.log` 首行是 `steps_20261112T174749+0800.tsv`；`figure_spec.json` run_id = 20261112T174749+0800；条目里 png/pdf/svg/side_by_side 与 `v2.2/output`、`compare` 哈希一致，8 个 data TSV 逐字节一致；`qa_check_mechanical.md` 与条目 `qa_report.md` 同哈希 `59f35d2c…`，时间 09:48:24Z = 17:48:24（UTC+8） |
| 1d | 色板 P3→sRGB | 已修复，换算正确 | 原图内嵌 ICC 描述 “Display P3”。QA 用自写矩阵（P3/sRGB 均 D65，sRGB 传递曲线，裁剪）独立换算 14 个 P3 原值，与 `palette_img07.tsv` 的 sRGB 值 ΔE00 最大 0.000；全图自写矩阵与 LittleCMS 结果 ΔE00 中位数 0.00、p99 0.00 |
| 2 | ΔE00 / 长宽比 | 通过 | 见下节。长宽比 3216×2160 vs 3216×2160，误差 0% |
| 3 | 条带检测器 6%→12% | 合理，是修 bug，没有放水 | 见下节 |
| 4 | 换目录 env -i 完整重跑 | 通过（图内容可复现） | 20 个输出 14 个逐字节一致，6 个不一致全是时间戳/路径/元数据，图内容不受影响 |
| 5 | qa_check | 通过（仅豁免项） | 16/17 PASS，唯一 FAIL `data/estimated_data.csv`（真实数据，不适用）；重跑条目和 Builder 条目结果相同 |

## 2. 色彩（QA 自写 CIEDE2000）

- 脚本 `qa_scripts/qa_de2000.py`：Sharma 2005 全部 34 对参考值 + 交换对称，最大误差 4.95e-05（< 1e-4）。
- 标题条（14 对；位置借用 Builder 检测器坐标，颜色由 QA 自行取中位数并换算）：

| 组合 | 中位数 | 最大 |
|---|---|---|
| v2.2 成图 vs 原图（P3→sRGB，LittleCMS） | 0.00 | 0.00 |
| v2.2 成图 vs 原图（P3→sRGB，QA 自写矩阵） | 0.00 | 0.00 |
| v2 成图 vs 原图（P3→sRGB） | 3.00 | 3.70 |
| v2 成图 vs 原图（不处理 ICC，旧口径） | 0.00 | 0.00 |

  说明：COS 转述的“标题条按 P3 是 2.92”有误：2.92 是 Builder 表里**条形填充**的数值，标题条按 P3 是 3.00（与 Builder 一致）。v2.2 的 0.00 是**构造出来的**：色板就是从原图标题条取色再换算的，所以这一项只说明换算和取色正确，并不能单独证明“像”。
- 全图色板（自写 k-means++，k=16，1200 px 降采样，去近白；种子 0–4 各跑一次）：

| 组合 | 5 个种子 | 种子中位数 | 加权中位数 |
|---|---|---|---|
| v2，旧口径（不处理 ICC） | 6.94 / 8.05 / 6.71 / 8.00 / 7.60 | 7.60 | 7.05 |
| v2，P3 正确换算 | 7.89 / 8.11 / 4.53 / 7.54 / 5.70 | 7.54 | 5.89 |
| **v2.2，P3 正确换算（判定用）** | 6.12 / 8.62 / 5.09 / 5.00 / 7.28 | **6.12** | 6.50 |
| v2.2，旧口径 | 8.37 / 6.52 / 4.90 / 6.77 / 4.98 | 6.52 | 5.69 |

  Builder 报 7.32（单一种子、随机初始化），在 QA 的种子范围 5.00–8.62 内；所有组合所有种子都 ≤10，通过。
  变化方向：按种子中位数，v2→v2.2（都按 P3 正确口径）是 7.54→6.12，略好；但单种子的波动约 ±2，比这个差还大，所以**方向没有统计意义**。Builder 写的“5.15→7.32 变差”和 COS 记的 7.32/6.47/7.13 都是单种子数，同样落在噪声里。原因：16 个聚类中心里有几个落在灰边、文字和背景的混合色上，最近邻匹配对初始化很敏感。建议以后这一项固定多种子取中位数报告。
- 条形填充（补充，不判定）：Builder 报 1.99，QA 未独立重算。

## 3. 条带检测器最小宽度 6% → 12%

- 位置：`v2.2/code/03_qa_metrics.py` 第 97 行 `if ww >= 0.12 * w and 0.006*h <= hh <= 0.04*h:  # v2.2: 0.06 -> 0.12`。
- 影响：只决定哪些色块算“标题条”，进而影响标题条 ΔE 的配对（逐槽配对，前面多一个就整体错位）和条形填充的取样区。不影响长宽比和全图色板。
- QA 只跑检测器这一步（`qa_scripts/qa_detector_6vs12.py`，把 Builder 源码读进内存只替换这一个常数，不改文件）：

| 图 | 6% 检出 | 12% 检出 | 宽度 px |
|---|---|---|---|
| 原图（P3→sRGB） | 15 | 14 | 6% 多出 1 个：x=2196, y=1436, 208×13 px（图宽 6.47%）= 一个带深色下边线的条形 |
| 原图（不处理 ICC） | 14 | 14 | 499–501 |
| v2.2 成图 | 17 | 17 | 481 |
| v2 成图 | 17 | 17 | 481 |

  标题条 ΔE（v2.2 vs 原图 sRGB）：6% 时 15 对，中位数 0.00、最大 62.28（错位）；12% 时 14 对，中位数 0.00、最大 0.00。v2 vs 原图 sRGB：6% 时中位数 3.36，12% 时 3.00。
- 判断：这是修 bug，不是放宽门槛。真标题条宽 15.0–15.6%，12% 仍留出约 3 个百分点余量；对 v2.2 的判定中位数两种设置都是 0.00，所以没有让检查更容易通过。改动理由和误检对象与 METHOD v2.2.4 描述一致。

## 4. 换目录完整重跑

- 复制：`v2.2/code/`、`v2.2/source/` → `/workspace/qa/img07_v2.2_rerun/pkg/`（去掉 `__pycache__`）；复制后 11 个代码文件和原图 sha256 与 Builder 收据一致（`pkg_copy_sha256.txt`）。
- 命令（只跑一遍，17:50:53 开始，含 prepare，未加 `--skip_prepare`）：
  `env -i HOME=/home/box PATH=/usr/bin:/bin LANG=C.UTF-8 bash /workspace/qa/img07_v2.2_rerun/pkg/code/run_all.sh --obj /workspace/envtest/hdwgcna/hdWGCNA_object.rds --tom /workspace/envtest/hdwgcna/TOM/INH_TOM.rda --outroot /workspace/qa/img07_v2.2_rerun/pkg --v1 /workspace/replications/2026-11-12_img07/output/replica.png`
- 步骤退出码：prepare..gallery_fill 全部 0，qa_check 1（只因 estimated_data.csv），receipt 0；总耗时 403 s。重跑收据 `pkg/runs/v2.2_20261112T175053+0800.json`（sha256 `1686260e…`），它的 command 字段含 `--v1`。
- 输入 sha256 与 Builder 收据一致：rds `c16975fa…`，TOM `45e34083…`，原图 `78cae0fd…`。
- 输出与 Builder 收据对比：20 个文件中 14 个逐字节一致，包括 `replica.png 25a5181c…`、`replica.svg e3906cb8…`、`network_layout.tsv`、`palette_used.tsv`、`plot_summary.tsv`、7 个数据 TSV、`overlay.png`、`triptych…png`。另外 7 个数据 TSV 也与 Builder 的 17:39 完整运行一致，hub 边/点和两份 GO 表与 v2 一致。6 个不一致的：

| 文件 | 原因 | 影响图内容？ |
|---|---|---|
| compare/original_srgb.png | 像素 0 差异；只有 Pillow 嵌入的 sRGB ICC 字节不同（含创建时间） | 否 |
| compare/side_by_side.png | 154 像素差异，全在页脚 (161,2203)-(183,2210)，是页脚里的运行时间戳 | 否 |
| data/prepare_summary.tsv | 只有 elapsed_s 不同（353.5 vs 366.4） | 否 |
| output/replica.pdf | 只有 cairo 对象流里的 /CreationDate 不同；pdftoppm 100 dpi 渲染逐字节一致 | 否 |
| qa/metrics_<TS>.json | 绝对路径不同；归一化路径后逐字节一致（数值相同：全图 7.321，标题条 0.00，长宽比 0） | 否 |
| qa/text_measure_<TS>.json | 绝对路径不同；归一化后逐字节一致 | 否 |

- 网络：1,017 点、5,685 边、模块内 4,675 条 = 82.2%（与 Builder 一致；jb 已接受）。
- 关于“按收据 command 字面跑”：Builder 收据的 command 写的是 `--outroot …/v2.2 --skip_prepare 1`，字面执行会覆盖 Builder 目录，违反只读，所以 QA 只把 `--outroot` 换成 pkg、去掉 `--skip_prepare`（要跑完整管线），其余参数原样执行，`--v1` 生效。qa_check 也按 Builder 收据 qa_check 步骤的参数原样跑了一次，只把 `--out` 改到 QA 目录（`qa_check_on_builder_entry.md`），结果 16 PASS / 1 FAIL（estimated_data.csv）。

## 不阻塞备注

1. （条件项）METHOD 补写模块中心 ×10 缩放（见 1a）。
2. `04_receipt.py` 把 `version` 写死为 `"v2"`、task 写成 “(replica v2)”，v2.2 收据里也是这样，建议改成 v2.2。
3. 正式收据 174749 是下游重跑（`--skip_prepare 1`），数据来自 17:39 那次完整运行；QA 的完整重跑已经覆盖这一点，数据逐字节一致。
4. qa_check 对缺失的 estimated_data.csv 给出的证据文字是“文件存在且非空”，这是 skill 脚本统一的模板文字，有误导性（不是 Builder 的问题）。
5. 全图 k-means 指标对种子敏感（见第 2 节），建议改为多种子取中位数。

## 证据文件（QA 目录，sha256 前 16 位）
- `qa_scripts/qa_de2000.py 5c460ba9…`、`qa_palette.py ebcd7f1b…`、`qa_detector_6vs12.py 3a2cf419…`、`qa_compare_hashes.py 8b000e6e…`、`qa_png_pixels.py e11a3a45…`
- `qa_palette_v2.2.json 90d4f0b2…`、`qa_detector_6vs12.json eaa0b7fa…`、`qa_check_on_builder_entry.md 0a17cee4…`、`pkg/qa/qa_check_mechanical.md 79ae2387…`

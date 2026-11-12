# img07 复刻：hdWGCNA hub 基因共表达网络 + 每模块 GO 富集条形图

任务卡 #1（COS 派单，jb 批准）。状态：**review**（等 QA 独立复跑、jb 目视签字；不 ready、不合并、不发布）。
时间均为 Asia/Manila（UTC+8）。

## 1. 目标图与复刻单位

- 来源：公众号「KS生信科研课」帖子《WGCNA：单细胞转录组+bulk RNA/蛋白组共表达网络分析》（2026-08-10，https://mp.weixin.qq.com/s/LOpSnqiK3nfG-wVU8urzVw）的 img07，3216×2160 px（任务卡写的“约 1024×540”与实际文件不符，以文件为准，宽高比 1.4889）。
  帖子本身是导流帖，没有给 img07 的数据和代码；img07 对应其链接的付费/群内教程《scRNA-hdWGCNA 共表达网络分析【2】》，我们拿不到原代码，所以 **code_provenance = reconstructed**（按图从零写 R 代码）。
- 复刻单位：整张 img07 作为一个逻辑 panel（主图网络 + 联动的分面条形图子图，按 jb 风格第②条视为一个整体），这是 COS 任务卡指定的范围；没有拆成单 panel 条目。
- 原图完整副本：`source/full_original.png`（只读，sha256 `78cae0fd…d0c4`，与 `/workspace/research-cos/wechat/2026-11-12_wgcna-scrna-bulk/imgs/img07.png` 字节一致），未裁剪，对比和指标都用整图。

读图（样式卡）：
| 元素 | 原图 | 复刻 |
|---|---|---|
| 左：网络 | 约 14 模块 hub 基因，点按模块色，灰色淡化边，中心有密集“毛球” | 17 模块 × top-50 kME hub = 850 点，4,898 条 TOM 边，灰 78%、α=0.35 |
| 同色引线标注 | “Agrp_Mk:代表 GO term”，同色粗体文字 + 引线指到模块 | “INH_Mk:代表 GO term”（模块 top-1 term），文字/引线/点同色 |
| 右：分面条形图 | 2 列 × 7 行，标题条模块色，5 个 term 横条（淡色），文字叠在条上，共享 x 轴 -log10(P-value) | 2 列 × 9 行（17 模块，最后一格空），其余相同 |
| 配色 | 14 色自定义色板 | 前 14 色取自原图标题条像素，另加 3 色 |

## 2. 方法理论

### 2.1 hdWGCNA（数据来源，已由环境测试完成，本任务只读使用）
hdWGCNA（Morabito et al., 2023, *Cell Reports Methods*）把 WGCNA 搬到单细胞：
1. **选基因**：`SetupForWGCNA(gene_select="fraction", fraction=0.05)`，在 ≥5% 细胞表达的基因 → 13,039 个。
2. **Metacell**：`MetacellsByGroups(group.by=c("cell_type","Sample"), k=25, max_shared=10)` 用 KNN 聚合相近细胞，降低单细胞稀疏性 → 296 个 metacell。
3. **共表达网络**：`SetDatExpr`(INH) → `TestSoftPowers(networkType="signed")` → `ConstructNetwork`：signed 网络，软阈值 β=7（自动选），邻接 a_ij = ((1+cor_ij)/2)^β；再算**拓扑重叠矩阵 TOM**：TOM_ij = (Σ_u a_iu a_uj + a_ij) / (min(k_i,k_j) + 1 − a_ij)，即两基因共享邻居越多 TOM 越高；以 1−TOM 层次聚类 + dynamic tree cut（deepSplit=4, minModuleSize=50, mergeCutHeight=0.2）得到模块。本对象：17 个非 grey 模块 + grey（8,688 个未归类基因）。
4. **模块特征基因 & kME**：`ModuleEigengenes`（按 Sample 用 Harmony 校正的 hME）；`ModuleConnectivity` 算 **kME = cor(基因表达, 模块特征基因)**，kME 越高越是模块 hub。环境测试中默认 ModuleConnectivity 因加载 TOM 算 degree 时 OOM（R RSS ~9 GiB），改用 `TOM_use="__skip_tom_degrees__"`：**kME 正常，但没有 TOM-degree 列**。本复刻只用 kME，不受影响。

### 2.2 网络图（01 脚本取数，02 脚本画图）
- **节点**：每个非 grey 模块取本模块 kME 最高的 50 个基因（`--n_hubs 50`）→ 850 个节点。
- **边权**：从 `TOM/INH_TOM.rda`（WGCNA 以 `dist` 下三角保存的 consensus TOM **相似度**，hdWGCNA `GetTOM` 也是这样读）里只抽 850×850 子块，不把 13,039² 全矩阵展开（按 dist 线性下标直接取，内存从“全量 ~1.4 GB 矩阵”降到 R 总占用 ~620 MB）。校验：模块内 hub 对平均 TOM 0.0561 > 模块间 0.0201，说明读出来的是相似度、基因顺序与 `GetWGCNAGenes` 一致。
- **稀疏化**：每个节点保留 TOM 最大的 6 个邻居（`--edges_per_node 6`，取并集）→ 4,898 条边，其中 41% 在模块内。这是展示用的选择，**不等同于** hdWGCNA `HubGeneNetworkPlot` 的边抽样方式。
- **布局**：Kamada–Kawai（`igraph::layout_with_kk`），边长 = 1 − TOM/max(TOM) + 0.05（共表达越强边越短）；seed=42。试过 FR、DrL、stress（见 §6 迭代记录），KK 最接近原图“中间毛球、外围分模块”的观感。布局只影响摆放，不改变任何数值。
- **标注**：每个模块 = 模块点坐标中位数（质心）；标签放在点云 97% 分位半径 ×1.12 处、沿“图中心→质心”方向，`ggrepel` 防重叠，引线与文字同模块色（jb 风格③）。标签文字 = 模块名 + 该模块 P 值最小的 GO term（Title Case）。

### 2.3 GO 富集（真实计算，离线）
- 工具：`clusterProfiler::enrichGO` 4.18.4，注释 `org.Hs.eg.db` 3.22.0 / `GO.db` 3.22.0（GO 源日期 2025-07-22），**离线**，未调用 enrichR 网络 API。
- 每个模块：基因集 = 该模块全部基因（不只 hub）；背景 universe = 全部 13,039 个 WGCNA 基因；`keyType="SYMBOL"`，`ont="ALL"`（BP+CC+MF 合并），超几何检验（单侧 Fisher），`pAdjustMethod="BH"`，`minGSSize=10`，`maxGSSize=500`，`pvalueCutoff=qvalueCutoff=1`（全部保留，便于审计）。
- 条形图：每个模块按 **原始 P 值** 取前 5 个 term，x = −log10(P)，与原图坐标轴一致；BH 校正值在 TSV 的 `p.adjust` 列。**注意**：INH_M1（全部 5 条）、INH_M9 部分、INH_M11、INH_M12 部分的 BH 校正 P > 0.05，图上画出来只代表“该模块排名前 5”，不代表显著。
- 共享 x 轴：INH_M2（核糖体，−log10P 达 30–49）远超其他模块（次高 INH_M13 为 15.0）。按原图共享坐标轴的风格，自动把轴截在次高模块最大值向上取偶数 = 16（`--x_cap auto`），INH_M2 的 5 条被截断，在条末尾用 “»48.8” 写出真实值。`--x_cap none` 可取消截断。
- 输出：`data/go_enrichment_all.tsv`（43,814 行，全部 term）、`data/go_top_terms.tsv`（85 行，每模块 top5，含 `neglog10p`）。

### 2.4 配色（jb 风格①：一套色贯穿网络点、标签、引线、标题条、条形）
- 色板 `code/palette_img07.tsv`：第 1–14 色从原图 14 个标题条内部取中位数 RGB（按原图阅读顺序）；第 15–17 色为新增（#17BECF、#E377C2、#9C9EDE），原图没有。
- 条形填充 = 模块色与白色按 0.55:0.45 混合（`lighten(a=0.55)`，由原图条形像素反推）。
- **原图的一个 bug，未复刻**：原图分面按字符串排序（M1, M10, M11, …, M2, …, M9），但标题条按 M1..M14 数字顺序上色，所以除 M1 外标题条颜色与模块对不上（例如 “Agrp_M10” 标题条是 M2 的浅蓝，而条形是 M10 的深褐）；条形和网络颜色是对的。复刻按数字顺序排分面，标题条、条形、网络统一用同一模块色。这个判断有像素证据：原图各分面条形色与“按模块号”的复刻条形色 ΔE00 中位数 1.85（§4 指标 C）。
- 标题条文字：深色条用白字、浅色条用黑字（原图一律黑字，深蓝/深褐条上难读）。

## 3. 与原图的数据差异（必须读）

| 项 | 原图 | 复刻 | 影响 |
|---|---|---|---|
| 物种/组织 | 小鼠下丘脑 Agrp 神经元（据 “Agrp_” 模块名推断） | 人脑皮层（Zhou et al. 2020 对照样本，hdWGCNA 官方教程数据） | 基因、GO term 完全不同；只复刻样式和方法，不复刻生物学结论 |
| 细胞 | 不详 | 只用 INH（抑制性神经元）子集 3,763 细胞（全量 36,671 细胞在 SetupForWGCNA 时 OOM） | 网络只代表 INH |
| 模块数 | 14（Agrp_M1..M14） | 17（INH_M1..M17） | 分面 2×7 → 2×9；多 3 个颜色 |
| 模块命名/顺序 | Agrp_Mk | INH_Mk，k = hdWGCNA 模块因子顺序（black, turquoise, blue, …, red，见 `data/module_map.tsv`） | 无 |
| TOM degree | 不详 | 跳过（`__skip_tom_degrees__`），只有 kME | 用 kME 选 hub，不受影响 |
| hub 数 | 不详（目测节点比复刻多） | 50/模块，850 点 | 网络更稀疏、毛球没原图密 |
| 边 | 很密的灰色边 | 每点 top-6 TOM 邻居，4,898 条 | 同上 |
| GO 方法 | 很可能是 Enrichr（term 后带 GO 号、Title Case 的风格），基因集版本不详 | clusterProfiler enrichGO 离线 + org.Hs.eg.db（GO 2025-07-22），BP/CC/MF 合并 | term 文字风格模仿 Enrichr（Title Case + GO 号），但不是同一个库/背景 |
| x 轴 | 共享 0–8 | 共享 0–16，INH_M2 截断并标真实值 | 见 §2.3 |
| 水印 | 有「公众号·KS生信科研课」 | 无 | — |

## 4. 验收指标（怎么算的）

脚本：`code/03_qa_metrics.py`（numpy/scipy/Pillow；CIEDE2000 自己实现，运行时先用 Sharma 2005 的 4 组标准对校验，误差 <1e-3）。口径在渲染前写定，没改阈值：
- **宽高比**：|(复刻宽/高)/(原图宽/高) − 1| ≤ 2%（和 skill `qa_check.py` 同一公式）。
- **指标 A：标题条色板 ΔE00 中位数 ≤ 10**。两张图用同一个检测器找分面标题条（右侧 40% 区域、宽 ≥6% 图宽、高 0.6–4% 图高、上下边有深色框线的均匀色块），按阅读顺序配对，取条内中位 RGB，算 ΔE00。**说明：复刻色板就是从这些标题条取的，所以 A≈0 几乎是必然的，只证明渲染没走样，不能单独当作“颜色像”的证据。**
- **指标 B：全图数据色板 ΔE00 中位数 ≤ 10**（更独立的那个）。两张图各自去掉近白背景（L*>93 且 C*<6），在 CIELAB 里做 k-means（k=16，固定种子），对原图每个色心取到复刻最近色心的 ΔE00，报未加权中位数（判定用）和按像素占比加权的中位数。
- **指标 C（补充，不参与判定）**：各分面条形填充色。原图分面顺序按标签读作 M1, M10, M11, M12, M13, M14, M2, …, M9，与复刻 M1..M17 按模块号配对。
- **判定**：宽高比 + A + B 三项都过才算通过。数值见运行收据 `runs/*.json` 的 `acceptance` 和 `qa/metrics_*.json`。

## 5. 复用方式（换数据/换目录）

```bash
bash code/run_all.sh --obj <hdWGCNA对象.rds> --tom <TOM.rda> --outroot <任意输出目录> [--original <对比原图.png>]
# 或分步：
Rscript code/01_prepare_network_go.R --obj X.rds --tom TOM.rda --outdir OUT/data [--prefix INH_M --n_hubs 50 --edges_per_node 6 --orgdb org.Hs.eg.db --ont ALL --top_terms 5]
Rscript code/02_plot_network_go.R --datadir OUT/data --outdir OUT/output [--palette my.tsv --layout kk|fr --x_cap auto|none|<数> --ncol_bars 2 --width_px 3216 --height_px 2160 --dpi 300]
```
- 模块数 n 任意：分面行数 = ceil(n / ncol_bars)，n 超过色板长度时自动用 `hcl.colors("Dark 3")` 补色。小鼠数据把 `--orgdb` 换成 `org.Mm.eg.db`（环境里已装）。
- 只依赖 conda env `rwiki-r` 里已有的包；本任务**没有安装任何新包**。
- 分析（01 出表）和绘图（02 只读表）分离；02 可以单独换表重画。

## 6. 迭代记录（skill 第 8 步，自动轮次上限 3）

| 轮 | 改动 | 结果 |
|---|---|---|
| 0（调试） | 首次渲染 | 色板 TSV 里的 `#` 被当成注释，全图无色；修读取 |
| 1 | FR 布局，共享 x 轴 0–50 | INH_M2 把其他模块的条压没；网络模块混杂 → 加 x 轴自动截断；比较 FR/KK/DrL/stress（`scratch/layouts.png`） |
| 2 | KK 布局，x 轴截 16 + “▶真实值” | 结构接近原图；标签压在点上 |
| 3 | 标签移到点云外圈，节点加大 | 定稿；剩余问题列入 needs_author |

## 7. 未决问题（needs_author，交 jb 目视）

1. 网络比原图稀疏，中心灰色毛球不够密，模块空间分离也比原图弱（真实 TOM 下 hub 之间模块内边只占 41%）。要更像可以加大 `--n_hubs`/`--edges_per_node`，但会改变“每模块 top-50”的口径，等 jb 定。
2. 右上角几个标签（INH_M7/M15/M17）互相挨得近，INH_M6 标签压到少量点。
3. 右侧条形网格 9 行，每格比原图矮，条上文字约 4 pt，比原图小；原图 7 行。
4. x 轴截断（INH_M2）是复刻新增的处理，原图没有。
5. 字体用 Liberation Sans（与 Arial 等宽度的开源字体），原图字体未知。
6. 分面顺序改成数字顺序、标题条颜色修正，是对原图 bug 的有意偏离。
7. SVG 用 svglite，156 个文字都是 `<text>` 元素（font-family "Liberation Sans"，可编辑）；PDF 用 cairo_pdf，嵌入 LiberationSans / LiberationSans-Bold 子集，截断标记用 “»”（Liberation Sans 自带字形）。还没在独立查看器里逐页目视 PDF/SVG。

---

## v2（2026-11-12 16:46 起，COS 指令“更像原图”）

v1 的文件全部原样保留（`code/ data/ output/ compare/ qa/ runs/ gallery_local/`，包括旧收据）。v2 全部放在 `v2/`，结构相同，可整体换目录重跑：
`bash v2/code/run_all.sh --obj <rds> --tom <rda> --outroot <目录> [--v1 <v1 replica.png，用于三联图>]`。收据为 `v2/runs/v2_<时间戳>.json`。
GO 富集参数没改，v2 的 `go_enrichment_all.tsv`、`go_top_terms.tsv` 与 v1 逐字节一致（48b9d339…、1227ae62…）。

### v2.1 网络：改了哪些规则、为什么
| 规则 | v1 | v2 | 理由 |
|---|---|---|---|
| hub 数 | 每模块 kME 前 50 → 850 点 | 每模块 kME 前 60 → 1,017 点（grey60 只有 57 个基因） | 原图点更多、更密 |
| 选边 | 每点 TOM 最大的 6 个邻居，不分模块 → 4,898 条，模块内 2,024 条 = **41.3%** | 每点取**本模块内** TOM 最大的 5 个 + **其他模块** TOM 最大的 1 个，取并集 → 5,685 条，模块内 4,675 条 = **82.2%** | v1 的 hub 之间模块内平均 TOM 只是模块间的约 2.7 倍，全局 top-k 选出的边有六成跨模块，所以团不清楚。分开取模块内和模块间邻居，团内连线就是团内最强的真实 TOM 关系；每点保留 1 条模块间最强边，维持中心那团“毛球”和模块之间的真实联系 |
| 布局 | KK，随机初始化，边长 1−TOM/max+0.05 | 先用经典 MDS 把“1 − 模块间 hub 平均 TOM”（`data/module_mean_tom.tsv`）降到 2 维当模块中心，节点从各自模块中心出发（N(0,1) 抖动），再跑 KK；边长 = 1/(w′+0.05)/10，模块内边 w′ = TOM/max×3，模块间边 w′ = TOM/max | 分模块初始化 + 调高模块内边权重，让同模块点聚成团；MDS 中心让 TOM 更像的模块离得更近。权重只改**画出来的边长**，不改边集合和 TOM 数值 |

- 所有边都来自 `TOM/INH_TOM.rda` 的 hub 子块（照旧按 dist 下标只取子块，R 内存约 640 MB，不展开 13k×13k 全矩阵），每条边带真实 TOM 值，`data/hub_edges_tom.tsv` 新增 `within_module` 列。没有虚构任何边。
- 代价：v2 的边集合是“按模块分层”选的，所以模块内边比例 82.2% 是**选边规则**造成的，不是数据里模块内连接本来就有这么多。全 TOM 子块里模块内平均 TOM 0.054，模块间 0.0198（v1 50-hub 时是 0.0561 / 0.0201），这才是数据本身的分离程度。看图解读模块分离时要记住这一点。
- 比较过的布局：`v2/scratch/layouts_v2.png`（FR 与 KK，模块内权重 ×1、×3、×6，初始化抖动 1 或 2）。KK ×3 团最清楚，中心也保留了跨模块连线；KK ×6 团太紧，FR 几种都不如 KK。

### v2.2 字号：怎么换算的
- 量法（`v2/code/measure_text.py`，两张图用同一个方法）：找到各分面标题条，在下方条形区左 55% 宽度内，把含 ≥3 个深色像素（亮度 <110）的连续行算作一行字，量这一行从最高到最低的像素高度。高度分两档：括号“(GO:…)”落在量取范围内的行高（括号会伸到下行部），落在外面的行矮，所以同时比 p10（矮档）、p90（高档）和中位数。标题条文字 = 条内与条色差 >60 的像素行的范围。
- 原图（高 2160 px）：条上文字 p10/中位/p90 = 15/19/20 px（中位数是图高的 0.88%），标题条文字 21 px（0.97%）。
- v1：条上文字 12/15/15 px（字号 1.42 mm ≈ 4.0 pt），标题条 13 px（4.6 pt）。
- 换算：字号按像素高度等比放大。条上文字先按中位数 19/15 放大到 1.80 mm，复量偏小（17.5 px）；放到 1.95 mm 后高档又偏大（22 px vs 20）；按两档比例折中定为 **1.76 mm ≈ 5.0 pt**，复量 15/18/19 px（原图 15/19/20）。标题条 4.6 pt × 21/13 → **7.4 pt**，复量 21 px，与原图一致。刻度字和 x 轴标题同比放大（5.8 pt / 7.0 pt），这两项没单独量。
- 字更大以后，INH_M2 截断分面的标签限 40 个字符，避免压到“»48.8”。

### v2.3 网络标签避让
`ggrepel` 0.9.8 已在 rwiki-r 里（v1 也在用），没有装任何东西。v2 把 1,017 个点都作为空标签的“障碍物”传给 `geom_text_repel`，标签会被推离点云；`max.iter=20000`、`max.time=600 s`（让迭代次数而不是时间决定收敛）、seed=42，结果可复现（换目录重跑 PNG 字节一致）。

### v2 验收（同 v1 口径，阈值没改）
见 `v2/qa/qa_report.md` 与收据 `v2/runs/v2_20261112T170443+0800.json`：长宽比误差 0.0000%；全图色板 ΔE00 中位数 6.47（加权 7.23）；标题条 0.00；条形填充色（补充）1.85；qa_check 17 项过 16 项（estimated_data.csv 不适用）。

### v2 剩余问题（needs_author）
1. 模块内边比例是选边规则带来的（见 v2.1 代价），jb 要判断这种“分层选边”能不能接受，还是要回到 v1 的不分模块 top-k。
2. 网络仍比原图稀疏一些，中心“毛球”的灰度不及原图。
3. 右侧仍是 2×9 网格；最后一行 INH_M17 下方到 x 轴标题之间留白偏大。
4. 条上文字比原图仍小约 1 px（中位 18 vs 19），且长 term 被分面右边界截断，原图也是这样。
5. 其他 v1 的未决项（字体替代、x 轴截断、分面顺序改成数字顺序、PDF/SVG 没在独立查看器里逐页目视）照旧。

---

## v2.2（2026-11-12 17:37 起，QA 通过后按 COS 指令收尾）

全部产出在 `v2.2/`，v1、v2 的文件和收据都没动。注意：任务说“先读 `v2/qa/QA_REPORT_QA.md` 的备注”，但写本节时 box 上找不到这个文件（`/workspace` 全盘搜过，`/workspace/qa/img07_v2_rerun/` 里只有 QA 复跑用的 pkg 和 start_time.txt）。所以下面第 2 条和第 4 条是按 COS 转述的文字理解的。
网络、GO、布局规则与 v2 相同；GO 和网络数据表应与 v2 逐字节一致（正式运行后核对，结果见下）。

### v2.2.1 外观参数全表（v1 → v2/v2.2；`02_plot_network_go.R` 的命令行参数，默认值即成图用值）
| 参数 | v1 | v2 / v2.2 | 说明 |
|---|---|---|---|
| `--bar_text_mm`（条上 GO 文字） | 1.42 mm ≈ 4.0 pt（代码里写死） | 1.76 mm ≈ 5.0 pt | 按原图文字像素高度换算（v2.2 小节） |
| `--strip_pt`（分面标题条） | 4.6 pt | 7.4 pt | 4.6 × 21/13 |
| `--tick_pt`（x 轴刻度） | 4.6 pt | 5.8 pt | 同比放大，未单独量 |
| `--xtitle_pt`（-log10(P-value)） | 5.6 pt | 7.0 pt | 同比放大，未单独量 |
| theme_bw base_size | 5 | 6 | |
| strip 文字上下边距 | 1.2 pt | 1.4 pt | |
| x 标题行高度比（网格:标题） | 60:1.6 | 60:1.2 | |
| `--term_chars` / `--term_chars_capped` | 60 / — | 60 / 40 | 截断分面（INH_M2）标签限 40 字符，给 “»值” 留位置 |
| `--label_mm`（网络标签，粗体） | 2.55 mm | 2.55 mm | 未改 |
| `--label_wrap` / `--label_radius` | 24 / 1.12 | 24 / 1.12 | 未改 |
| `--node_size` | 1.6 | 1.5 | |
| ggrepel | data = 17 个标签；force=3，force_pull=2，box.padding=0.25，max.overlaps=Inf，默认 max.iter/max.time | data = 17 个标签 + 1,017 个空标签节点（障碍物）；force=4，force_pull=1.5，box.padding=0.3，point.padding=0.05，point.size=node_size，max.iter=20000，**max.time=600 s**，seed=42 | v2 第一次用 max.time=5 s，按时间截断，换目录重跑结果不可复现；改成 600 s 后由 max.iter 决定收敛 |
| 引线 | segment.size 0.45，min.segment.length 0，颜色同模块 | 同左 | |
| 边样式 | grey78，alpha 0.35，linewidth 0.12 | 同左 | |
| `--layout` | kk（随机初始化，边长 1−TOM/max+0.05） | kk_modinit | 见 v2.1 |
| `--within_boost`（模块内边权重，只影响布局） | — | 3 | |
| `--init_spread`（初始化抖动 SD） | — | 1 | |
| 条形填充 `lighten(a)` | 0.55 | 0.55 | 未改 |
| 条宽 | 0.72 | 0.72 | |
| 01 脚本 `--n_hubs` / 选边 | 50 / topk(6) | 60 / within_between(k_in 5, k_out 1) | 见 v2.1 |
| `--palette` | 原图标题条像素值（按 sRGB 读） | v2 同 v1；**v2.2 换成 Display P3→sRGB 换算后的值** | 见 v2.2.3 |

### v2.2.2 收据 command 字段
v1/v2 的 `04_receipt.py` 写 command 时自己用 `--obj --tom --outroot` 拼，漏了实际传入的 `--v1`（三联图用的 v1 成图路径），按收据里的命令复跑就不会生成三联图。v2.2 的 `run_all.sh` 在解析参数前记下**完整原始调用**（`printf %q` 转义），通过 `--cmdline` 传给收据，command 字段跟实际执行的命令逐字一致，包括 `--v1`。旧收据没改。

### v2.2.3 色彩管理：Display P3 → sRGB
- 发现：`img07.png` 内嵌了一个 536 字节的 ICC 配置文件，描述是 “Display P3”。v1/v2 用 Pillow 读像素时没管 ICC，把 P3 的数值直接当 sRGB 用了，这样做有两个后果：(a) 从原图取的色板偏灰、偏淡；(b) ΔE00 比较时原图颜色被错读。复刻的 PNG 不带配置文件，按 sRGB 处理。
- 做法（用已有的 Pillow `ImageCms`，即 LittleCMS，没装任何东西）：用 PNG 内嵌的 P3 配置文件转到 LittleCMS 内置 sRGB，渲染意图选相对色度（relative colorimetric），超出 sRGB 色域的部分会被裁掉。
  - 色板：第 1–14 色（v2 里的 P3 数值）逐个换算，结果在 `v2.2/code/palette_img07.tsv`，每行注明原始 P3 值。例如 M1 #B82928→#C90A1D，M3 #F8E353→#FCE222，M4 #30642F→#156627。第 15–17 色是新加的，不换算。
  - 指标：`03_qa_metrics.py` 读图时，带 ICC 的图先转 sRGB 再做颜色计算（`colour_management` 字段记录每张图怎么处理的），`--no_icc` 可以复现 v1/v2 的旧口径。阈值和其他口径都没改。
  - 对比图：原图先转成 sRGB 副本 `v2.2/compare/original_srgb.png` 再拼并排图和三联图（原文件不动）。

### v2.2.4 结果（正式运行）
- 正式完整运行：`v2.2/runs/v2.2_20261112T173942+0800.json`。这次重算了数据，`hub_edges_tom.tsv`、`hub_nodes.tsv`、两份 GO TSV 都与 v2 逐字节一致；网络 1,017 点、5,685 边，模块内边占比 82.2%（与 v2 相同）。
  这份收据里的 ΔE 是**作废值**：原图转成 sRGB 后，条带检测器把一个宽 208 px（图宽的 6.5%）、带深色下边线的条形误认成了标题条（检到 15 条，后面全部错位配对），算出的“标题条中位数 0.00”只是巧合。修法：检测器最小宽度从图宽的 6% 提到 12%（真标题条约 15.5%）。这是修 bug，不是改阈值。
- 修复后只重跑下游步骤（作图→对比→指标→画廊→qa_check→收据，`--skip_prepare 1`，数据沿用上面那次正式运行）：`v2.2/runs/v2.2_20261112T174749+0800.json`，**以这份为准**。两次成图除配色外没有区别。
- 收据 `overall_exit_code=1` 来自 qa_check：唯一的机械 FAIL 是 `estimated_data.csv`（不适用，见 v1）。其他步骤全部 exit 0。

| ΔE00 中位数（阈值 ≤10） | v2 成图 + 旧口径（不处理 ICC） | v2 成图 + 新口径（原图 P3→sRGB） | v2.2 成图（sRGB 色板）+ 新口径 |
|---|---|---|---|
| 全图色板（判定用） | 6.47（加权 7.23） | 5.15（加权 6.92） | 7.32（加权 7.08） |
| 标题条色板 | 0.00 | 3.00（最大 3.70） | 0.00（最大 0.00，14 对） |
| 条形填充（补充） | 1.85 | 2.92 | 1.99 |
| 长宽比误差 | 0% | 0% | 0% |

解读：色板改成换算后的 sRGB 值，标题条在正确口径下又回到 0（之前在 v2 里 0 是错误口径下的假象，正确口径下是 3.0）；条形填充 2.92→1.99。全图 k-means 指标从 5.15 升到 7.32，但仍 ≤10；这个指标对聚类中心很敏感（16 个中心里有几个落在灰色边和文字的混合色上），变化方向不代表配色变差。判定三项（长宽比、标题条、全图）全部通过。
- 文字高度复量（同 v2 方法）：条上文字 p10/中位/p90 = 15/18/19 px（原图 15/19/20），标题条 21 px（原图 21）。

## v2.2.5 模块中心坐标的缩放（文档补记，代码未改）

布局 `kk_modinit` 里，模块中心坐标先按 `max(|坐标|)` 归一化到 \([-1, 1]\)，再乘 10，然后叠加上标准差为 `init_spread` 的随机偏移，作为 Kamada–Kawai 的初值。对应 `code/02_plot_network_go.R` 第 65–66 行：

```r
cm <- stats::cmdscale(stats::as.dist(dd), k = 2); cm <- cm / max(abs(cm))
init <- cm[mods_v, ] * 10 + matrix(stats::rnorm(2 * vcount(g), 0, opt$init_spread), ncol = 2)
```

这一步只影响初始布局尺度，不改变边、TOM 或模块归属。

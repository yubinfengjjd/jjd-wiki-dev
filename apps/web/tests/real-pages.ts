/* Generated from the real wiki API on 2026-10-23; do not hand-edit. */
export const REAL_PAGES: any[] = [
  {
    "path": "methods/cell-quality-control.md",
    "meta": {
      "type": "method",
      "id": "cell-quality-control",
      "title": "单细胞质量控制",
      "status": "draft",
      "tags": [
        "单细胞分析"
      ],
      "inputs": [],
      "outputs": [],
      "source": {
        "kind": "repo",
        "url": "https://github.com/zhanghao-njmu/scp",
        "commit": "b9b0eb7a7bf2c2c4b2262e73e09d7ebd515c7da0"
      },
      "license": "GPL-3",
      "cite": [
        "SCP: https://github.com/zhanghao-njmu/scp (commit b9b0eb7a7bf2c2c4b2262e73e09d7ebd515c7da0)"
      ],
      "favorite": false,
      "method_kind": "analysis",
      "summary": "按显式阈值计算逐细胞 UMI、基因数与线粒体/核糖体比例，标记 Pass/Fail，不把 QC 指标当生物学分组。",
      "data_contract": {
        "input": "Seurat RNA assay 的原始 counts（基因×细胞）；每个细胞一列，每个基因一行。",
        "output": "每细胞一行的 QC 结果：nCount_RNA、nFeature_RNA、percent.mito、percent.ribo、CellQC=Pass/Fail。"
      },
      "implementations": [
        {
          "id": "scp-runcellqc",
          "title": "SCP RunCellQC 封装",
          "language": "R",
          "entrypoint": "code/analysis.R:run_cell_quality_control",
          "dependencies": [
            "Seurat",
            "SeuratObject"
          ],
          "verification": "verification/scp-runcellqc.json"
        }
      ],
      "keywords": [
        "QC",
        "nCount",
        "nFeature",
        "percent.mito",
        "percent.ribo",
        "低质量细胞",
        "SCP"
      ],
      "figure_relations": [
        {
          "figure": "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap",
          "compatibility": "adaptable",
          "reason": "QC 的 Pass/Fail 或指标可作为 UMAP 着色变量；模板只画表，不计算 QC。",
          "prerequisites": [
            "UMAP 坐标与 QC 标签来自同一 Seurat 对象；cell_id 一致。",
            "group_levels 显式给出；Pass/Fail 顺序固定。"
          ],
          "adaptation": "导出 render-umap-groups.csv（cell_id, umap_1, umap_2, group=CellQC 或样本）；模板不读 RDS。",
          "evidence": [
            "methods/cell-quality-control.md#输出",
            "methods/scp-cellqc-doublet.md#知识关联检查",
            "methods/scp-cellqc-doublet.md#输出",
            "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap/spec.json",
            "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap/verify/verify.json"
          ],
          "verification": {
            "state": "not_run",
            "scope": "2026-10-23 只核对方法输出与模板接口；未运行真实课题分析→出图。",
            "evidence": []
          }
        },
        {
          "figure": "templates/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow",
          "compatibility": "adaptable",
          "reason": "按样本/条件统计 QC Pass/Fail 比例，可复用比例堆叠与流带模板；模板不做统计检验。",
          "prerequisites": [
            "每个 group 的 celltype 比例归一化到 1；group 为样本或条件，celltype 为 CellQC。",
            "组间比较只作描述，不能当样本级推断。"
          ],
          "adaptation": "导出 render-cell-proportions.csv（group, celltype, proportion）；比例只作描述。",
          "evidence": [
            "methods/cell-quality-control.md#输出",
            "methods/scp-cellqc-doublet.md#知识关联检查",
            "methods/scp-cellqc-doublet.md#输出",
            "templates/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow/spec.json",
            "templates/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow/verify/verify.json"
          ],
          "verification": {
            "state": "not_run",
            "scope": "2026-10-23 只核对方法输出与模板接口；未运行真实课题分析→出图。",
            "evidence": []
          }
        },
        {
          "figure": "templates/2026-10-22-glaucoma-scrna__fig06-pathway-violin--violin",
          "compatibility": "adaptable",
          "reason": "QC 指标按样本或细胞类型分组的分布可用分组小提琴展示；模板不重算阈值。",
          "prerequisites": [
            "每个值有明确的采样单位（细胞或样本）；细胞级分布不能当样本级推断。",
            "p/mean/SD 若展示，必须由分析阶段预计算并说明来源。"
          ],
          "adaptation": "导出 render-grouped-values.csv 和可选的 render-group-summaries.csv。",
          "evidence": [
            "methods/cell-quality-control.md#输出",
            "methods/scp-cellqc-doublet.md#知识关联检查",
            "methods/scp-cellqc-doublet.md#输出",
            "templates/2026-10-22-glaucoma-scrna__fig06-pathway-violin--violin/spec.json",
            "templates/2026-10-22-glaucoma-scrna__fig06-pathway-violin--violin/verify/verify.json"
          ],
          "verification": {
            "state": "not_run",
            "scope": "2026-10-23 只核对方法输出与模板接口；未运行真实课题分析→出图。",
            "evidence": []
          }
        }
      ]
    },
    "body": "# 单细胞质量控制\n\n<!-- facts:start -->\n- 来源：https://github.com/zhanghao-njmu/scp（b9b0eb7a7bf2c2c4b2262e73e09d7ebd515c7da0）\n- 许可证：GPL-3\n- 引用：SCP: https://github.com/zhanghao-njmu/scp (commit b9b0eb7a7bf2c2c4b2262e73e09d7ebd515c7da0)\n- 标签：单细胞分析\n- 输入接口：未声明\n- 输出接口：未声明\n- 接口结构匹配的图（仅结构候选，未核实语义）：暂无\n- 接口结构匹配的下一步方法（仅结构候选，未核实语义）：暂无\n- 代码模板：[methods/cell-quality-control/code/analysis.R](/files/wiki/methods/cell-quality-control/code/analysis.R)\n\n- 方法配图关系（语义审查）：\n  - [[templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap|CNS 细胞类型 UMAP]]（ready）：需要适配（adaptable）；调用验证：not_run；范围：2026-10-23 只核对方法输出与模板接口；未运行真实课题分析→出图。\n    - 依据：QC 的 Pass/Fail 或指标可作为 UMAP 着色变量；模板只画表，不计算 QC。；前提：UMAP 坐标与 QC 标签来自同一 Seurat 对象；cell_id 一致。；group_levels 显式给出；Pass/Fail 顺序固定。；适配：导出 render-umap-groups.csv（cell_id, umap_1, umap_2, group=CellQC 或样本）；模板不读 RDS。\n    - 关系证据：methods/cell-quality-control.md#输出；methods/scp-cellqc-doublet.md#知识关联检查；methods/scp-cellqc-doublet.md#输出；templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap/spec.json；templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap/verify/verify.json；运行证据：无\n  - [[templates/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow|细胞比例堆叠流带图]]（ready）：需要适配（adaptable）；调用验证：not_run；范围：2026-10-23 只核对方法输出与模板接口；未运行真实课题分析→出图。\n    - 依据：按样本/条件统计 QC Pass/Fail 比例，可复用比例堆叠与流带模板；模板不做统计检验。；前提：每个 group 的 celltype 比例归一化到 1；group 为样本或条件，celltype 为 CellQC。；组间比较只作描述，不能当样本级推断。；适配：导出 render-cell-proportions.csv（group, celltype, proportion）；比例只作描述。\n    - 关系证据：methods/cell-quality-control.md#输出；methods/scp-cellqc-doublet.md#知识关联检查；methods/scp-cellqc-doublet.md#输出；templates/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow/spec.json；templates/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow/verify/verify.json；运行证据：无\n  - [[templates/2026-10-22-glaucoma-scrna__fig06-pathway-violin--violin|分组小提琴图（含统计标注）]]（ready）：需要适配（adaptable）；调用验证：not_run；范围：2026-10-23 只核对方法输出与模板接口；未运行真实课题分析→出图。\n    - 依据：QC 指标按样本或细胞类型分组的分布可用分组小提琴展示；模板不重算阈值。；前提：每个值有明确的采样单位（细胞或样本）；细胞级分布不能当样本级推断。；p/mean/SD 若展示，必须由分析阶段预计算并说明来源。；适配：导出 render-grouped-values.csv 和可选的 render-group-summaries.csv。\n    - 关系证据：methods/cell-quality-control.md#输出；methods/scp-cellqc-doublet.md#知识关联检查；methods/scp-cellqc-doublet.md#输出；templates/2026-10-22-glaucoma-scrna__fig06-pathway-violin--violin/spec.json；templates/2026-10-22-glaucoma-scrna__fig06-pathway-violin--violin/verify/verify.json；运行证据：无\n<!-- facts:end -->\n\n## 用途\n\n在进入归一化、整合、降维之前，逐细胞计算文库大小、检出基因数、线粒体/核糖体读段比例，并按课题预先规定的阈值标记 Pass/Fail。结果用于决定哪些细胞进入下游，不是把 QC 指标当作细胞类型或生物学分组。\n\n## 原理与选择\n\n破损细胞常表现为低 UMI、低基因数或高线粒体比例；双细胞、环境 RNA、物种混合是不同问题，需分别检测。阈值受组织、建库版本和测序深度影响，不能照搬固定值。SCP `RunCellQC` 把 UMI、基因数、线粒体、核糖体、ribo/mito 比、离群点和双细胞组合成 `CellQC`；本页只验证了 UMI/基因数/线粒体阈值分支，双细胞与离群点分支未运行。\n\n\n\n## 来源与实现选择\n\n| 策略 / 实现 | 原始来源 | 输入与目标 | 本库状态 |\n|---|---|---|---|\n| SCP `RunCellQC`：UMI、基因数、线粒体/核糖体比例、可选双细胞/离群点 | [[methods/scp-cellqc-doublet]]；`SCP-local/R/SCP-cellqc.R` | 原始 counts，按样本；输出细胞级 QC 指标与 CellQC | UMI/基因数/线粒体阈值分支已封装并 verified；双细胞/离群点未运行 |\n| 青光眼 `preprocess.R`：Seurat 指标 + MAD 3× 离群点 | [[methods/scrna-preprocess-doublet-qc-harmony]]；`source/preprocess.R` | 原始 counts，按样本；MAD 阈值 | 原脚本未函数化，未在本库验证；阈值是课题设定 |\n## 适用\n\n- 原始 counts，且基因标识与物种明确；可按样本分别检查。\n- 需要把细胞级 QC 失败原因记录并带入后续分析，而不是静默删细胞。\n- 阈值由课题数据分布、组织类型、建库协议和既往经验共同确定，并写入方法。\n\n## 不适用\n\n- 已归一化/积分的表达值不能直接当 raw counts 计算这些指标。\n- 不能仅凭 QC 指标给细胞定型，也不能把 Pass/Fail 当作处理组或生物学差异。\n- 不同物种/建库方案共用固定阈值、或跨样本比较未标准化的线粒体比例，容易得出误导结论。\n\n## 输入\n\nSeurat 对象（`RNA` assay 的 `counts`），或能转为同样基因×细胞矩阵的对象；`qc_metrics`、`UMI_threshold`、`gene_threshold`、`mito_threshold`、`ribo_threshold` 等参数显式传入。每个细胞是一行结果，不是每个样本一行。\n\n## 怎么做\n\n1. 按样本查看 nCount、nFeature、percent.mito 的分布，结合组织与建库记录确定阈值；不要先看下游聚类再倒推阈值。\n2. 显式列出要计算的指标；本页已验证 UMI、基因数、线粒体阈值。\n3. 运行 `RunCellQC`，保留 Pass/Fail 及每个失败原因；若决定过滤，记录过滤前后细胞数和样本组成。\n4. 对边界细胞做敏感性分析（保留/剔除各跑一次下游），不要把单次阈值当唯一真值。\n5. 双细胞、离群点、物种混合按各自方法单独处理；本页不把它们的阈值混入 UMI/基因数结论。\n\n## 代码\n\n入口 `methods/cell-quality-control/code/analysis.R:run_cell_quality_control(srt, bundle, parameters)`。`bundle` 指向复制到课题的完整 `SCP-local` 目录，函数按固定哈希校验后 source，不写死知识库路径；依赖 Seurat、SeuratObject。参数与 SCP `RunCellQC` 同名，统计逻辑未改。\n\n验证：2026-10-23 在 `pancreas_sub` 的 80 个细胞上实际调用，封装与上游 `CellQC` 一致，输入对象未被修改；scope 仅软件调用，不代表科学有效或真实课题阈值合理。双细胞/离群点分支未运行，缺失原因见对应家族页。\n\n## 输出\n\n返回 `list(result=Seurat, diagnostics=...)`。`result@meta.data` 增加 `nCount_RNA`、`nFeature_RNA`、`percent.mito`、`percent.ribo`、`CellQC`（Pass/Fail）等字段；一行一个细胞。没有强制 CSV；出图前由课题显式导出对应接口表。\n\n## 知识关联检查\n\n2026-10-23 检查了 `templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap`、`fig04-cell-proportion-flow--stacked-bar-flow`、`fig06-pathway-violin--violin`。QC Pass/Fail 或指标可作为 UMAP 着色、样本比例、分组分布；模板不计算 QC，关系为 adaptable。没有 direct：模板不读 Seurat 对象，需先导出 `render-umap-groups`、`render-cell-proportions`、`render-grouped-values` 等接口。双细胞图不在此页直连，见 [[methods/doublet-detection]]。\n\n## 使用记录\n\n2026-10-23：在隔离 R 环境用 `pancreas_sub` 80 细胞做软件调用、输入不变和上游一致性检查；未做真实课题阈值决策。\n\n<!-- user:start -->\n<!-- user:end -->\n",
    "implementation_status": [
      {
        "id": "scp-runcellqc",
        "title": "SCP RunCellQC 封装",
        "state": "verified",
        "scope": "实际调用 SCP RunCellQC 于 pancreas_sub 的 80 个细胞；比较封装与上游 CellQC、检查输入未变。"
      }
    ],
    "backlinks": [
      {
        "path": "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap.md",
        "title": "CNS 细胞类型 UMAP",
        "type": "template"
      },
      {
        "path": "methods/scp-local-source.md",
        "title": "SCP 源码本地化",
        "type": "method"
      },
      {
        "path": "methods/scp-visualization-interface.md",
        "title": "SCP 绘图函数与图接口映射",
        "type": "method"
      },
      {
        "path": "interfaces/render-umap-groups.md",
        "title": "UMAP 坐标与分组表",
        "type": "interface"
      },
      {
        "path": "templates/2026-10-22-glaucoma-scrna__fig06-pathway-violin--violin.md",
        "title": "分组小提琴图（含统计标注）",
        "type": "template"
      },
      {
        "path": "interfaces/render-grouped-values.md",
        "title": "分组细胞级数值表",
        "type": "interface"
      },
      {
        "path": "methods/scp-cellqc-doublet.md",
        "title": "单细胞 QC 与双细胞检测",
        "type": "method"
      },
      {
        "path": "methods/scp-standard-workflow.md",
        "title": "单细胞标准预处理、降维与聚类",
        "type": "method"
      },
      {
        "path": "methods/scrna-preprocess-doublet-qc-harmony.md",
        "title": "单细胞预处理、批次校正与聚类",
        "type": "method"
      },
      {
        "path": "templates/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow.md",
        "title": "细胞比例堆叠流带图",
        "type": "template"
      },
      {
        "path": "interfaces/render-cell-proportions.md",
        "title": "细胞类型比例表",
        "type": "interface"
      },
      {
        "path": "interfaces/render-group-summaries.md",
        "title": "预计算分组分布摘要表",
        "type": "interface"
      }
    ],
    "gallery": null,
    "reuse": null,
    "figure_refs": [
      "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap.md",
      "templates/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow.md",
      "templates/2026-10-22-glaucoma-scrna__fig06-pathway-violin--violin.md"
    ],
    "preview": null,
    "workflow": {
      "stage": "method_confirm",
      "queue": "confirm",
      "label": "待你确认",
      "reason": "笔记与知识关联检查已填写，待作者核对。",
      "templates": []
    },
    "relations": [
      {
        "method": "methods/cell-quality-control.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap.md",
        "method_title": "单细胞质量控制",
        "figure_title": "CNS 细胞类型 UMAP",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "QC 的 Pass/Fail 或指标可作为 UMAP 着色变量；模板只画表，不计算 QC。",
        "prerequisites": [
          "UMAP 坐标与 QC 标签来自同一 Seurat 对象；cell_id 一致。",
          "group_levels 显式给出；Pass/Fail 顺序固定。"
        ],
        "adaptation": "导出 render-umap-groups.csv（cell_id, umap_1, umap_2, group=CellQC 或样本）；模板不读 RDS。",
        "evidence": [
          "methods/cell-quality-control.md#输出",
          "methods/scp-cellqc-doublet.md#知识关联检查",
          "methods/scp-cellqc-doublet.md#输出",
          "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap/spec.json",
          "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap/verify/verify.json"
        ],
        "verification": {
          "state": "not_run",
          "scope": "2026-10-23 只核对方法输出与模板接口；未运行真实课题分析→出图。",
          "evidence": []
        },
        "target_kind": "template",
        "active": true
      },
      {
        "method": "methods/cell-quality-control.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow.md",
        "method_title": "单细胞质量控制",
        "figure_title": "细胞比例堆叠流带图",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "按样本/条件统计 QC Pass/Fail 比例，可复用比例堆叠与流带模板；模板不做统计检验。",
        "prerequisites": [
          "每个 group 的 celltype 比例归一化到 1；group 为样本或条件，celltype 为 CellQC。",
          "组间比较只作描述，不能当样本级推断。"
        ],
        "adaptation": "导出 render-cell-proportions.csv（group, celltype, proportion）；比例只作描述。",
        "evidence": [
          "methods/cell-quality-control.md#输出",
          "methods/scp-cellqc-doublet.md#知识关联检查",
          "methods/scp-cellqc-doublet.md#输出",
          "templates/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow/spec.json",
          "templates/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow/verify/verify.json"
        ],
        "verification": {
          "state": "not_run",
          "scope": "2026-10-23 只核对方法输出与模板接口；未运行真实课题分析→出图。",
          "evidence": []
        },
        "target_kind": "template",
        "active": true
      },
      {
        "method": "methods/cell-quality-control.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig06-pathway-violin--violin.md",
        "method_title": "单细胞质量控制",
        "figure_title": "分组小提琴图（含统计标注）",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "QC 指标按样本或细胞类型分组的分布可用分组小提琴展示；模板不重算阈值。",
        "prerequisites": [
          "每个值有明确的采样单位（细胞或样本）；细胞级分布不能当样本级推断。",
          "p/mean/SD 若展示，必须由分析阶段预计算并说明来源。"
        ],
        "adaptation": "导出 render-grouped-values.csv 和可选的 render-group-summaries.csv。",
        "evidence": [
          "methods/cell-quality-control.md#输出",
          "methods/scp-cellqc-doublet.md#知识关联检查",
          "methods/scp-cellqc-doublet.md#输出",
          "templates/2026-10-22-glaucoma-scrna__fig06-pathway-violin--violin/spec.json",
          "templates/2026-10-22-glaucoma-scrna__fig06-pathway-violin--violin/verify/verify.json"
        ],
        "verification": {
          "state": "not_run",
          "scope": "2026-10-23 只核对方法输出与模板接口；未运行真实课题分析→出图。",
          "evidence": []
        },
        "target_kind": "template",
        "active": true
      }
    ]
  },
  {
    "path": "methods/scp-cellqc-doublet.md",
    "meta": {
      "type": "method",
      "id": "scp-cellqc-doublet",
      "title": "单细胞 QC 与双细胞检测",
      "status": "ready",
      "tags": [
        "单细胞分析"
      ],
      "keywords": [
        "SCP",
        "Seurat",
        "RunCellQC",
        "RunDoubletCalling",
        "scDblFinder",
        "Scrublet",
        "DoubletDetection",
        "scds",
        "双细胞",
        "质量控制",
        "QC"
      ],
      "inputs": [],
      "outputs": [],
      "source": {
        "kind": "repo",
        "url": "https://github.com/zhanghao-njmu/scp",
        "commit": "b9b0eb7a7bf2c2c4b2262e73e09d7ebd515c7da0"
      },
      "license": "GPL-3",
      "cite": [],
      "favorite": false,
      "method_kind": "technical",
      "summary": "SCP QC 与双细胞检测的原始脚本和作者实现记录；分析问题见质量控制与双细胞检测家族。",
      "data_contract": {
        "input": "Seurat 原始 counts 与样本元数据；原脚本参数在 source/ 中。",
        "output": "SCP QC/双细胞对象和标签；本页不重新运行。"
      }
    },
    "body": "# 单细胞 QC 与双细胞检测\r\n\r\n<!-- facts:start -->\n- 来源：https://github.com/zhanghao-njmu/scp（b9b0eb7a7bf2c2c4b2262e73e09d7ebd515c7da0）\n- 许可证：GPL-3\n- 引用：无\n- 标签：单细胞分析\n- 输入接口：未声明\n- 输出接口：未声明\n- 接口结构匹配的图（仅结构候选，未核实语义）：暂无\n- 接口结构匹配的下一步方法（仅结构候选，未核实语义）：暂无\n- 代码模板：无\n\n- 方法配图关系（语义审查）：\n  - 暂无已记录关系；接口或标签相同不代表语义已核实。\n<!-- facts:end -->\n\n> **资料类型：技术/来源资料，不是默认分析家族。**\n> 当前分析问题见：[[methods/cell-quality-control|单细胞质量控制]]、[[methods/doublet-detection|双细胞检测]]。原代码与作者备注保留；本页不再作为分析推荐卡片。\r\n\r\n## 用途\r\n\r\n用 SCP 的 `RunCellQC()` / `RunDoubletCalling()` 在 Seurat 对象上做细胞级 QC：双细胞检测、MAD 离群、UMI/基因数、线粒体/核糖体比例、核糖体/线粒体比值、物种污染，以及可选的过滤。产出带 QC 标签和指标的 Seurat 对象；下游可导出 UMAP 着色表、QC 比例表和指标分布表。\r\n\r\n## 原始实现与家族范围\r\n\r\n来源是 SCP v0.5.6 的 `R/SCP-cellqc.R`。家族限定为“基于 Seurat 的细胞级 QC 与双细胞判断”：\r\n\r\n- `RunDoubletCalling()` 包装 `scDblFinder`、`Scrublet`、`DoubletDetection`、`scds`（cxds/bcds/hybrid），按 `db_rate` 或 `ncol/1000 * db_coefficient` 设定预期双细胞数。\r\n- `RunCellQC()` 把双细胞、MAD 离群、UMI、基因数、线粒体、核糖体、核糖体/线粒体比值、物种污染合并成 `CellQC` Pass/Fail；可 `split.by` 按样本分别处理。\r\n- `isOutlier()` 是 MAD 离群工具；`db_*()` 是各双细胞方法的适配器。\r\n\r\n代码已本地化到 `code/SCP-local/R/SCP-cellqc.R`（与 `utils.R` 的 `check_DataType` 等辅助函数配合），可 `source()` 后直接调用，不安装 SCP 包；补丁与依赖见 [[methods/scp-local-source|SCP 源码本地化]]。\r\n\r\n## 适用\r\n\r\n- Seurat 对象含 **raw counts**；一行一个细胞（barcode），一列一个基因。\r\n- 多用户/多样本数据：用 `split.by` 指定样本列，逐个样本做双细胞判断，再合并 QC 标签。\r\n- 物种/组织明确，线粒体、核糖体、血红蛋白基因命名可写成正则；小鼠常用 `^mt-`、`^Rp[sl]`、`^Hb[^(p)]`，人常用 `^MT-`、`^RP[SL]`。\r\n- 需要把 QC 结果作为后续过滤、UMAP 着色、比例统计或补充材料。\r\n- 双细胞方法在 R 侧（scDblFinder/scds）或 Python 侧（Scrublet/DoubletDetection）可用。\r\n\r\n## 不适用\r\n\r\n- 不适用于只有归一化/整合后数据、没有 raw counts 的对象；`RunDoubletCalling()` 会检查 counts 并停止。\r\n- 不能把默认阈值当成通用阈值：`UMI_threshold=3000`、`gene_threshold=1000`、`mito_threshold=20`、`ribo_threshold=50` 是本实现的默认值，换组织、建库方式、测序深度必须重新检查。\r\n- 不能把 `db_rate` 的默认公式当成真实双细胞率；它只是按细胞数估计的近似值，不同上机量/组织不同。\r\n- 不能把 MAD 离群当成人工 QC 的替代；阈值的敏感性应报告。\r\n- 单核 RNA-seq、空间转录组、跨物种/PDX 数据需要改线粒体/核糖体/物种前缀，不能直接套用。\r\n- `RunCellQC()` 的物种污染指标只适用于有物种混合/异种移植设计的数据；普通单物种数据应跳过。\r\n- 本轮没有在安装 Seurat/SCP 依赖的环境中运行；默认参数的真实表现未验证。\r\n\r\n## 输入\r\n\r\n- Seurat 对象；`assay`（默认 `RNA`）的 `counts` 层；`split.by` 样本列。\r\n- 双细胞方法：`db_method`（一个或多个；如 `c(\"scDblFinder\", \"scds_cxds\")`）、`db_rate` 或 `db_coefficient`。\r\n- QC 指标：`qc_metrics` 向量；`outlier_threshold` 形如 `metric:direction:nmads`，例如 `log10_nCount:lower:2.5`。\r\n- 物种参数：`species`、`species_gene_prefix`，以及 `mito_pattern`、`ribo_pattern` 或显式 `mito_gene`/`ribo_gene`。\r\n- 阈值：`UMI_threshold`、`gene_threshold`、`mito_threshold`、`ribo_threshold`、`ribo_mito_ratio_range`、`species_percent`。\r\n- 一行代表一个细胞；QC 标签不跨样本复用；细胞 ID 在对象内唯一。\r\n\r\n## 怎么做\r\n\r\n1. 检查 `counts` 是否为 raw counts；确认 `nCount_<assay>`、`nFeature_<assay>` 是否存在（`RunCellQC()` 会在缺失时计算）。\r\n2. 多用户/多样本时设 `split.by`；先在各样本内跑双细胞方法，再合并。不要先 merge 再跑双细胞。\r\n3. 选双细胞方法：R 侧优先 `scDblFinder`（默认）；需要多方法交叉时可加 `scds_cxds`/`scds_bcds`/`scds_hybrid`；Python 侧 `Scrublet`/`DoubletDetection` 需要 reticulate 和对应 Python 包。\r\n4. 计算线粒体、核糖体、物种基因组比例；检查基因命名是否匹配 `mito_pattern`/`ribo_pattern`。线粒体/核糖体比例的分母是 counts。\r\n5. 设 `outlier_threshold`：对 `log10_nCount`、`log10_nFeature` 做 MAD；`featurecount_dist` 是 log10 nFeature 对 log10 nCount 的 loess 残差，低端离群提示低复杂度细胞。`outlier_n` 是至少几个指标同时失败才判离群。\r\n6. 设 UMI/基因数/线粒体/核糖体阈值；`ribo_mito_ratio_range` 默认 `c(1, Inf)`，即只标记比值过低；`species_percent` 默认 95。\r\n7. `RunCellQC()` 生成 `db_qc`、`outlier_qc`、`umi_qc`、`gene_qc`、`mito_qc`、`ribo_qc`、`ribo_mito_ratio_qc`、`species_qc` 和合并的 `CellQC`；`return_filtered=TRUE` 只保留 `CellQC == \"Pass\"` 并删除 QC 列。\r\n8. 必要诊断：每个样本的细胞数、各指标失败数、失败重叠（upset）、双细胞分数分布、QC 前后细胞数、阈值敏感性；不要只看一个总失败数。\r\n9. 把 QC 标签和指标导出为下游表（见“输出”），再进入 [[methods/scp-standard-workflow|标准流程]] 或 [[methods/scp-integration|整合]]。\r\n\r\n## 代码\r\n\r\n- 原始字节：`source/SCP-cellqc.R`（只读归档，未修改）。\r\n- 本地化副本：`code/SCP-local/R/SCP-cellqc.R`；辅助函数在 `code/SCP-local/R/utils.R`。加载方式：\r\n  ```r\r\n  source(\"path/to/SCP-local/load_scp_local.R\")\r\n  srt <- SCP_local$RunCellQC(\r\n    srt,\r\n    split.by = \"sample\",\r\n    db_method = \"scDblFinder\",\r\n    qc_metrics = c(\"doublets\", \"outlier\", \"umi\", \"gene\", \"mito\", \"ribo\"),\r\n    UMI_threshold = 3000, gene_threshold = 1000,\r\n    mito_threshold = 20, ribo_threshold = 50\r\n  )\r\n  ```\r\n  这只是调用模式，不是已跑通的本机示例；参数必须按数据重设。\r\n- 依赖：Seurat、SeuratObject、SingleCellExperiment、Matrix；`scDblFinder`（Bioc）、`scds`（Suggests）；Python 侧还需要 reticulate、Scrublet/DoubletDetection。依赖清单与本地化补丁见 [[methods/scp-local-source|SCP 源码本地化]]。\r\n- 验证状态：本地源码可 `source()`；`verify_local.R` 通过；SCP 的 QC 函数依赖 Seurat/SCP 未安装，未运行。因此不宣称阈值、双细胞率或细胞数在真实数据上已验证。\r\n- 本地化未改变 `RunCellQC()`/`RunDoubletCalling()` 的算法、默认阈值或输出结构；只去掉了 `SCP::` 和包路径依赖。\r\n\r\n## 输出\r\n\r\nSeurat `meta.data` 中新增（列名以运行结果为准）：\r\n\r\n- 基础指标：`nCount_RNA`、`nFeature_RNA`（若原对象没有）；按物种后缀生成 `percent.mito.<species>`、`percent.ribo.<species>`、`percent.genome.<species>`、`ribo.mito.ratio.<species>`、`log10_nCount_RNA.<species>`、`log10_nFeature_RNA.<species>`、`featurecount_dist.<species>`。\r\n- 双细胞：`db.<method>_score`、`db.<method>_class`（`singlet`/`doublet`）。\r\n- 单指标 QC：`db_qc`、`outlier_qc`、`umi_qc`、`gene_qc`、`mito_qc`、`ribo_qc`、`ribo_mito_ratio_qc`、`species_qc`，以及合并的 `CellQC`；均为 `Pass`/`Fail` 因子。\r\n- 若 `return_filtered=TRUE`：只返回 `CellQC == \"Pass\"` 的细胞，并删除上述 QC 列。\r\n\r\n下游表（课题内导出，不写回知识库）：\r\n\r\n- `render-umap-groups.csv`：`cell_id, umap_1, umap_2, group`（group=`CellQC` 或 `sample`），供 fig01 UMAP 模板。\r\n- `render-cell-proportions.csv`：`group, celltype, proportion`（group=样本/条件，celltype=`CellQC`），供 fig04 比例模板。\r\n- `render-grouped-values.csv`：`celltype, group, value`（每个 QC 指标一个文件；value 为细胞级或样本级，必须在页面/图注说明单位），供 fig06 小提琴模板。\r\n- 如需 p/mean/SD 标注，另写 `render-group-summaries.csv`；由分析阶段预计算，模板不重算检验。\r\n- 表适配函数见 [[methods/scp-visualization-interface|SCP 可视化函数族与接口映射]] 的 `code/scp_tables.R`：`scp_umap_groups()`、`scp_cell_proportions()`、`scp_grouped_values()`。\r\n\r\n## 知识关联检查\r\n\n2026-10-23 分类为技术/来源资料：旧 id、`source/` 原字节和作者备注保留，但不再作为默认分析家族推荐。语义配图关系已迁往 [[methods/cell-quality-control|单细胞质量控制]]、[[methods/doublet-detection|双细胞检测]]；本页只保留来源与实现证据链接，不再维护 `figure_relations` 主记录。原页面正文中的模板/证据链接仍可用于溯源；结构相似不等于科学直连。\n\n## 使用记录\r\n\r\n2026-10-22 建页；归档 `SCP-cellqc.R` 原字节，本地化副本进入共享源码包；按作者代签授权标为 ready；验收记录见 `acceptance.json`。\r\n\r\n<!-- user:start -->\r\n<!-- user:end -->\r\n",
    "implementation_status": [],
    "backlinks": [
      {
        "path": "templates/2026-10-22-scp-example__fig02-ring--ring.md",
        "title": "分组构成同心环图",
        "type": "template"
      },
      {
        "path": "templates/2026-10-22-scp-example__fig07-dot--dot.md",
        "title": "分组构成点图",
        "type": "template"
      },
      {
        "path": "templates/2026-10-22-scp-example__fig04-rose--rose.md",
        "title": "分组构成玫瑰图",
        "type": "template"
      },
      {
        "path": "templates/2026-10-22-scp-example__fig05-trend--trend.md",
        "title": "分组构成趋势图",
        "type": "template"
      },
      {
        "path": "templates/2026-10-22-scp-example__fig06-area--area.md",
        "title": "分组构成面积图",
        "type": "template"
      },
      {
        "path": "templates/2026-10-22-scp-example__fig03-pie--pie.md",
        "title": "分组构成饼图",
        "type": "template"
      },
      {
        "path": "layouts/2026-10-22-scp-example__fig16-cell-density.md",
        "title": "分组表达密度图",
        "type": "layout"
      },
      {
        "path": "templates/2026-10-22-scp-example__fig16-cell-density--ridge.md",
        "title": "分组表达密度图",
        "type": "template"
      },
      {
        "path": "layouts/2026-10-22-scp-example__fig09-bar.md",
        "title": "分组计数柱图",
        "type": "layout"
      },
      {
        "path": "templates/2026-10-22-scp-example__fig09-bar--bar.md",
        "title": "分组计数柱图",
        "type": "template"
      },
      {
        "path": "methods/cell-quality-control.md",
        "title": "单细胞质量控制",
        "type": "method"
      },
      {
        "path": "methods/doublet-detection.md",
        "title": "双细胞检测",
        "type": "method"
      },
      {
        "path": "layouts/2026-10-22-scp-example__fig13-upset.md",
        "title": "多集合交集 UpSet 图",
        "type": "layout"
      },
      {
        "path": "templates/2026-10-22-scp-example__fig13-upset--upset.md",
        "title": "多集合交集 UpSet 图",
        "type": "template"
      },
      {
        "path": "layouts/2026-10-22-scp-example__fig12-venn.md",
        "title": "多集合交集维恩图",
        "type": "layout"
      },
      {
        "path": "templates/2026-10-22-scp-example__fig12-venn--venn.md",
        "title": "多集合交集维恩图",
        "type": "template"
      },
      {
        "path": "layouts/2026-10-22-scp-example__fig04-rose.md",
        "title": "玫瑰图组成：计数 dodge（SCP 示例）",
        "type": "layout"
      },
      {
        "path": "layouts/2026-10-22-scp-example__fig02-ring.md",
        "title": "环形组成图（SCP 示例）",
        "type": "layout"
      },
      {
        "path": "layouts/2026-10-22-scp-example__fig07-dot.md",
        "title": "组成点阵图（SCP 示例）",
        "type": "layout"
      },
      {
        "path": "layouts/2026-10-22-scp-example__fig05-trend.md",
        "title": "组成趋势图：计数（SCP 示例）",
        "type": "layout"
      },
      {
        "path": "layouts/2026-10-22-scp-example__fig06-area.md",
        "title": "组成面积图：百分比（SCP 示例）",
        "type": "layout"
      },
      {
        "path": "layouts/2026-10-22-scp-example__fig03-pie.md",
        "title": "饼图组成（SCP 示例）",
        "type": "layout"
      }
    ],
    "gallery": null,
    "reuse": null,
    "figure_refs": [],
    "preview": null,
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "技术资料已确认",
      "reason": "笔记与资料内容已确认；不作为可执行分析推荐，也不要求分析实现收据。",
      "templates": []
    },
    "relations": []
  },
  {
    "path": "methods/scp-standard-workflow.md",
    "meta": {
      "type": "method",
      "id": "scp-standard-workflow",
      "title": "单细胞标准预处理、降维与聚类",
      "status": "ready",
      "tags": [
        "单细胞分析"
      ],
      "keywords": [
        "SCP",
        "Seurat",
        "Standard_SCP",
        "RunDimReduction",
        "PCA",
        "UMAP",
        "tSNE",
        "Louvain",
        "Leiden",
        "聚类",
        "降维"
      ],
      "inputs": [],
      "outputs": [],
      "source": {
        "kind": "repo",
        "url": "https://github.com/zhanghao-njmu/scp",
        "commit": "b9b0eb7a7bf2c2c4b2262e73e09d7ebd515c7da0"
      },
      "license": "GPL-3",
      "cite": [],
      "favorite": false,
      "method_kind": "workflow",
      "summary": "SCP 标准预处理、降维与聚类的组合流程记录；单步方法见质量控制、降维、聚类和整合家族。",
      "data_contract": {
        "input": "原始 counts 的 Seurat 对象；流程参数在 source/ 中。",
        "output": "Standardpca/StandardUMAP2D/Standardclusters 等流程对象；本页不重新运行。"
      }
    },
    "body": "# 单细胞标准预处理、降维与聚类\r\n\r\n<!-- facts:start -->\n- 来源：https://github.com/zhanghao-njmu/scp（b9b0eb7a7bf2c2c4b2262e73e09d7ebd515c7da0）\n- 许可证：GPL-3\n- 引用：无\n- 标签：单细胞分析\n- 输入接口：未声明\n- 输出接口：未声明\n- 接口结构匹配的图（仅结构候选，未核实语义）：暂无\n- 接口结构匹配的下一步方法（仅结构候选，未核实语义）：暂无\n- 代码模板：无\n\n- 方法配图关系（语义审查）：\n  - 暂无已记录关系；接口或标签相同不代表语义已核实。\n<!-- facts:end -->\n\n> **资料类型：组合流程，不是默认分析家族。**\n> 当前分析问题见：[[methods/dimensionality-reduction|单细胞降维分析]]、[[methods/cell-clustering|单细胞聚类分析]]、[[methods/cell-quality-control|单细胞质量控制]]、[[methods/doublet-detection|双细胞检测]]、[[methods/batch-integration|单细胞批次整合]]。原代码与作者备注保留；本页不再作为分析推荐卡片。\r\n\r\n## 用途\r\n\r\n用 SCP 的 `Standard_SCP()` 在一个 Seurat 对象上跑标准单细胞流程：归一化、高变基因、缩放、线性降维、近邻图、聚类、非线性降维，产出带前缀的 reduction、cluster 列和默认 reduction。也可用 `RunDimReduction()` 单独跑某一步。\r\n\r\n## 原始实现与家族范围\r\n\r\n来源是 SCP v0.5.6 的 `R/SCP-workflow.R`。家族限定为“单对象、无批次校正的标准 Seurat 流程”：\r\n\r\n- 归一化：`LogNormalize`、`SCT`、`TFIDF`（TFIDF 会切到 SVD/LSI 工作流）。\r\n- 线性降维：`pca`、`svd`、`ica`、`nmf`、`mds`、`glmpca`（通过 `RunDimReduction()`）。\r\n- 非线性降维：`umap`、`umap-naive`、`tsne`、`dm`、`phate`、`pacmap`、`trimap`、`largevis`、`fr`。\r\n- 聚类：`louvain`、`slm`、`leiden`；`leiden` 需要 Python `leidenalg`。\r\n- `Standard_SCP()` 内部用 `check_srtList(batch = \"\")`，不走批次整合；多用户/多样本应使用 [[methods/scp-integration|Integration_SCP]]。\r\n\r\n代码已本地化到 `code/SCP-local/R/SCP-workflow.R`，配套 `Seurat-function.R`、`utils.R`；补丁见 [[methods/scp-local-source|SCP 源码本地化]]。\r\n\r\n## 适用\r\n\r\n- Seurat 对象含 raw counts；一行一个细胞，一列一个基因。\r\n- 单一对象或已合并、但不需要批次校正的数据；需要探索性聚类、UMAP/tSNE 和 marker 检查。\r\n- 需要把 reduction 名称、cluster 列、HVF 固定下来，供下游 DE、注释、轨迹和绘图使用。\r\n- 需要尝试多种降维/聚类算法做敏感性比较。\r\n\r\n## 不适用\r\n\r\n- 不是批次校正方法；多用户/多样本、批次与条件混杂时不能用 `Standard_SCP()` 代替整合。\r\n- 不能从 UMAP 外观或 cluster 数证明生物亚群存在；需要 marker、统计和独立验证。\r\n- 默认 `nHVF=2000`、`linear_reduction_dims=50`、`neighbor_k=20`、`cluster_resolution=0.6` 不是通用最优；换组织/数据量要重设。\r\n- 不能把 `RunDimReduction()` 的降维结果当差异表达或轨迹证据。\r\n- `leiden` 需要 reticulate + `leidenalg`；当前环境未安装，未验证。\r\n- 超大数据的内存/运行时间未评估；`ScaleData` 和 UMAP 可能成为瓶颈。\r\n- 本轮未在安装 Seurat/SCP 依赖的环境中运行；默认参数的真实表现未验证。\r\n\r\n## 输入\r\n\r\n- Seurat 对象；`assay`（默认 `DefaultAssay`）；raw counts。\r\n- `normalization_method`（`LogNormalize`/`SCT`/`TFIDF`）、`do_HVF_finding`、`HVF_method`、`nHVF` 或显式 `HVF`。\r\n- `do_scaling`、`vars_to_regress`、`regression_model`。\r\n- `linear_reduction`、`linear_reduction_dims`、`linear_reduction_dims_use`；`nonlinear_reduction`、`nonlinear_reduction_dims`。\r\n- `neighbor_metric`、`neighbor_k`、`cluster_algorithm`、`cluster_resolution`、`seed`。\r\n- 一行代表一个细胞；细胞 ID 唯一；样本/条件元数据可留在对象里，但不参与校正。\r\n\r\n## 怎么做\r\n\r\n1. 确认 counts 是 raw counts；如已归一化，设 `do_normalization=FALSE` 或明确使用现有数据。\r\n2. 选归一化方法：常规 scRNA 用 `LogNormalize`；需要 SCT 时注意 `ScaleData` 会被跳过；scATAC 用 `TFIDF` + `svd`。\r\n3. 找 HVF（`vst` 默认，2000 个）；需要回归协变量时设 `vars_to_regress`，并说明回归模型。\r\n4. 跑线性降维；`linear_reduction_dims_use` 为 NULL 时，SCP 用 `dims_estimate` 估计使用维度；显式给出更可控。\r\n5. `FindNeighbors()` 建 KNN/SNN 图；`FindClusters()` 跑所选算法和分辨率；`SrtReorder()` 按 HVF 表达重排 cluster 编号。\r\n6. 在所选线性降维/SNN 图上跑非线性降维；`nonlinear_reduction_dims` 默认 `c(2,3)`，会同时产出 2D/3D。\r\n7. 检查：dims_estimate、不同分辨率/算法的 cluster 稳定性、UMAP/tSNE 是否一致、marker 是否落在对应 cluster、最小 cluster 细胞数。\r\n8. 导出 UMAP 坐标、cluster/celltype、marker 表达长表；进入注释、DE、轨迹或绘图。\r\n\r\n## 代码\r\n\r\n- 原始字节：`source/SCP-workflow.R`（只读归档，未修改）。\r\n- 本地化副本：`code/SCP-local/R/SCP-workflow.R`；辅助函数在 `Seurat-function.R`、`utils.R`。加载方式：\r\n  ```r\r\n  source(\"path/to/SCP-local/load_scp_local.R\")\r\n  srt <- SCP_local$Standard_SCP(\r\n    srt,\r\n    prefix = \"Standard\",\r\n    normalization_method = \"LogNormalize\",\r\n    nHVF = 2000,\r\n    linear_reduction = \"pca\",\r\n    nonlinear_reduction = \"umap\",\r\n    cluster_algorithm = \"louvain\",\r\n    cluster_resolution = 0.6,\r\n    seed = 11\r\n  )\r\n  ```\r\n  这只是调用模式，不是已跑通的本机示例。\r\n- 单独降维：`SCP_local$RunDimReduction(srt, prefix = \"\", linear_reduction = \"pca\", ...)`；非线性降维需给 `reduction_use`/`graph_use`。\r\n- 依赖：Seurat、SeuratObject、uwot、BiocParallel、Matrix、future；`leiden` 需要 reticulate + leidenalg；SCT 需要 Seurat 的 SCTransform 依赖（glmGamPoi 等）。完整清单见 [[methods/scp-local-source|SCP 源码本地化]]。\r\n- 验证状态：本地源码可 `source()`；`verify_local.R` 通过；`Standard_SCP()` 依赖 Seurat/uwot 等未安装，未运行。不宣称降维/聚类数值或稳定性已验证。\r\n- 本地化未改变归一化、HVF、降维、聚类或重排算法；只去掉 `SCP::`/包路径。\r\n\r\n## 输出\r\n\r\nSeurat 对象中新增（以 `prefix=\"Standard\"`、`linear_reduction=\"pca\"`、`nonlinear_reduction=c(\"umap\",\"tsne\")` 为例）：\r\n\r\n- reduction：`Standardpca`、`StandardUMAP2D`、`StandardUMAP3D`、`StandardTSNE2D`、`StandardTSNE3D`；命名规则是 `prefix + toupper(nonlinear_reduction) + nD`。\r\n- 图：`Standardpca_KNN`、`Standardpca_SNN`（`FindNeighbors` 的 graph.name）。\r\n- 元数据：`Standardpca_clusters`（每个线性降维的 cluster）、`Standardclusters`（第一个线性降维的 cluster 别名）。\r\n- `VariableFeatures(srt)` 与 `srt@misc$Standard_HVF`；`srt@misc$Default_reduction` 指向最后一个非线性降维（如 `StandardUMAP`）。\r\n- 下游表：\r\n  - `render-umap-groups.csv`：`cell_id, umap_1, umap_2, group`（group=cluster/celltype/sample），供 fig01。\r\n  - `render-umap-feature-long.csv`：`cell_id, umap_1, umap_2, group, feature, value`，供 fig02。\r\n  - 表适配函数：`scp_umap_groups()`、`scp_umap_feature_long()`，见 [[methods/scp-visualization-interface|SCP 可视化函数族与接口映射]]。\r\n\r\n## 知识关联检查\r\n\n2026-10-23 分类为组合流程：旧 id、`source/` 原字节和作者备注保留，但不再作为默认分析家族推荐。语义配图关系已迁往 [[methods/dimensionality-reduction|单细胞降维分析]]、[[methods/cell-clustering|单细胞聚类分析]]、[[methods/cell-quality-control|单细胞质量控制]]、[[methods/doublet-detection|双细胞检测]]、[[methods/batch-integration|单细胞批次整合]]；本页只保留来源与实现证据链接，不再维护 `figure_relations` 主记录。原页面正文中的模板/证据链接仍可用于溯源；结构相似不等于科学直连。\n\n## 使用记录\r\n\r\n2026-10-22 建页；归档 `SCP-workflow.R` 原字节，本地化副本进入共享源码包；按作者代签授权标为 ready；验收记录见 `acceptance.json`。\r\n\r\n<!-- user:start -->\r\n<!-- user:end -->\r\n",
    "implementation_status": [],
    "backlinks": [
      {
        "path": "layouts/2026-10-22-scp-example__fig08-group-heatmap.md",
        "title": "GroupHeatmap (CellType / SubCellType)",
        "type": "layout"
      },
      {
        "path": "templates/2026-10-22-scp-example__fig02-ring--ring.md",
        "title": "分组构成同心环图",
        "type": "template"
      },
      {
        "path": "templates/2026-10-22-scp-example__fig07-dot--dot.md",
        "title": "分组构成点图",
        "type": "template"
      },
      {
        "path": "templates/2026-10-22-scp-example__fig04-rose--rose.md",
        "title": "分组构成玫瑰图",
        "type": "template"
      },
      {
        "path": "templates/2026-10-22-scp-example__fig05-trend--trend.md",
        "title": "分组构成趋势图",
        "type": "template"
      },
      {
        "path": "templates/2026-10-22-scp-example__fig06-area--area.md",
        "title": "分组构成面积图",
        "type": "template"
      },
      {
        "path": "templates/2026-10-22-scp-example__fig03-pie--pie.md",
        "title": "分组构成饼图",
        "type": "template"
      },
      {
        "path": "layouts/2026-10-22-scp-example__fig11-chord.md",
        "title": "分组流向和弦图",
        "type": "layout"
      },
      {
        "path": "templates/2026-10-22-scp-example__fig11-chord--chord.md",
        "title": "分组流向和弦图",
        "type": "template"
      },
      {
        "path": "layouts/2026-10-22-scp-example__fig10-sankey.md",
        "title": "分组流向桑基图",
        "type": "layout"
      },
      {
        "path": "templates/2026-10-22-scp-example__fig10-sankey--sankey.md",
        "title": "分组流向桑基图",
        "type": "template"
      },
      {
        "path": "templates/2026-10-22-scp-example__fig08-group-heatmap--heatmap.md",
        "title": "分组热图（多分组注释）",
        "type": "template"
      },
      {
        "path": "layouts/2026-10-22-scp-example__fig16-cell-density.md",
        "title": "分组表达密度图",
        "type": "layout"
      },
      {
        "path": "templates/2026-10-22-scp-example__fig16-cell-density--ridge.md",
        "title": "分组表达密度图",
        "type": "template"
      },
      {
        "path": "layouts/2026-10-22-scp-example__fig09-bar.md",
        "title": "分组计数柱图",
        "type": "layout"
      },
      {
        "path": "templates/2026-10-22-scp-example__fig09-bar--bar.md",
        "title": "分组计数柱图",
        "type": "template"
      },
      {
        "path": "methods/scp-cellqc-doublet.md",
        "title": "单细胞 QC 与双细胞检测",
        "type": "method"
      },
      {
        "path": "methods/cell-clustering.md",
        "title": "单细胞聚类分析",
        "type": "method"
      },
      {
        "path": "methods/dimensionality-reduction.md",
        "title": "单细胞降维分析",
        "type": "method"
      },
      {
        "path": "layouts/2026-10-22-scp-example__fig13-upset.md",
        "title": "多集合交集 UpSet 图",
        "type": "layout"
      },
      {
        "path": "templates/2026-10-22-scp-example__fig13-upset--upset.md",
        "title": "多集合交集 UpSet 图",
        "type": "template"
      },
      {
        "path": "layouts/2026-10-22-scp-example__fig12-venn.md",
        "title": "多集合交集维恩图",
        "type": "layout"
      },
      {
        "path": "templates/2026-10-22-scp-example__fig12-venn--venn.md",
        "title": "多集合交集维恩图",
        "type": "template"
      },
      {
        "path": "layouts/2026-10-22-scp-example__fig14-feature-heatmap.md",
        "title": "特征表达热图",
        "type": "layout"
      },
      {
        "path": "templates/2026-10-22-scp-example__fig14-feature-heatmap--heatmap.md",
        "title": "特征表达热图",
        "type": "template"
      },
      {
        "path": "layouts/2026-10-22-scp-example__fig04-rose.md",
        "title": "玫瑰图组成：计数 dodge（SCP 示例）",
        "type": "layout"
      },
      {
        "path": "layouts/2026-10-22-scp-example__fig02-ring.md",
        "title": "环形组成图（SCP 示例）",
        "type": "layout"
      },
      {
        "path": "layouts/2026-10-22-scp-example__fig07-dot.md",
        "title": "组成点阵图（SCP 示例）",
        "type": "layout"
      },
      {
        "path": "layouts/2026-10-22-scp-example__fig05-trend.md",
        "title": "组成趋势图：计数（SCP 示例）",
        "type": "layout"
      },
      {
        "path": "layouts/2026-10-22-scp-example__fig06-area.md",
        "title": "组成面积图：百分比（SCP 示例）",
        "type": "layout"
      },
      {
        "path": "layouts/2026-10-22-scp-example__fig15-cell-cor-heatmap.md",
        "title": "细胞相似度热图",
        "type": "layout"
      },
      {
        "path": "templates/2026-10-22-scp-example__fig15-cell-cor-heatmap--heatmap.md",
        "title": "细胞相似度热图",
        "type": "template"
      },
      {
        "path": "layouts/2026-10-22-scp-example__fig03-pie.md",
        "title": "饼图组成（SCP 示例）",
        "type": "layout"
      }
    ],
    "gallery": null,
    "reuse": null,
    "figure_refs": [],
    "preview": null,
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "流程资料已确认",
      "reason": "笔记与资料内容已确认；不作为可执行分析推荐，也不要求分析实现收据。",
      "templates": []
    },
    "relations": []
  },
  {
    "path": "methods/batch-integration.md",
    "meta": {
      "type": "method",
      "id": "batch-integration",
      "title": "单细胞批次整合",
      "status": "draft",
      "tags": [
        "单细胞分析"
      ],
      "inputs": [],
      "outputs": [],
      "source": {
        "kind": "repo",
        "url": "https://github.com/zhanghao-njmu/scp",
        "commit": "b9b0eb7a7bf2c2c4b2262e73e09d7ebd515c7da0"
      },
      "license": "GPL-3",
      "cite": [
        "SCP: https://github.com/zhanghao-njmu/scp (commit b9b0eb7a7bf2c2c4b2262e73e09d7ebd515c7da0)"
      ],
      "favorite": false,
      "method_kind": "analysis",
      "summary": "在保留生物差异的前提下对齐样本/技术批次，产出整合嵌入与聚类，供跨样本比较。",
      "data_contract": {
        "input": "含明确 batch 列的 Seurat 原始 counts（batch 是样本/技术批次，不是生物学分组）。",
        "output": "整合后的 Seurat 对象（Seuratpca、SeuratUMAP2D、Seuratclusters）或每细胞嵌入表。"
      },
      "implementations": [
        {
          "id": "scp-seurat",
          "title": "SCP Seurat_integrate 锚点分支",
          "language": "R",
          "entrypoint": "code/analysis.R:run_seurat_integration",
          "dependencies": [
            "Seurat",
            "SeuratObject"
          ],
          "verification": "verification/scp-seurat.json"
        },
        {
          "id": "scp-harmony",
          "title": "SCP Harmony_integrate 分支",
          "language": "R",
          "entrypoint": "code/analysis.R:run_batch_integration",
          "dependencies": [
            "Seurat",
            "harmony"
          ],
          "verification": "verification/scp-harmony.json"
        }
      ],
      "keywords": [
        "batch",
        "integration",
        "Seurat",
        "Harmony",
        "锚点",
        "批次校正",
        "SCP"
      ],
      "figure_relations": [
        {
          "figure": "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap",
          "compatibility": "adaptable",
          "reason": "整合后的嵌入可按 batch 或 celltype 着色，复用现有 UMAP 单 panel；模板不做整合。",
          "prerequisites": [
            "坐标与 group 来自同一整合嵌入；cell_id 唯一；坐标无 NA。",
            "group 明确为 batch 或 celltype；group_levels 由课题给出。"
          ],
          "adaptation": "导出 render-umap-groups.csv（cell_id, umap_1, umap_2, group）；模板不读 RDS。",
          "evidence": [
            "methods/batch-integration.md#输出",
            "methods/scp-integration.md#知识关联检查",
            "methods/scp-integration.md#输出",
            "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap/spec.json",
            "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap/verify/verify.json"
          ],
          "verification": {
            "state": "not_run",
            "scope": "2026-10-23 只核对方法输出与模板接口；未运行真实课题分析→出图。",
            "evidence": []
          }
        },
        {
          "figure": "templates/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow",
          "compatibility": "adaptable",
          "reason": "按 batch/样本统计细胞类型比例，可检查整合前后组成是否被过度改变；模板不做统计检验。",
          "prerequisites": [
            "每个 group 的比例归一化到 1；group 为 batch/样本，celltype 为注释类型。",
            "比例是描述性；组间差异不能由该图直接推断。"
          ],
          "adaptation": "导出 render-cell-proportions.csv（group, celltype, proportion）；比例只作描述。",
          "evidence": [
            "methods/batch-integration.md#输出",
            "methods/scp-integration.md#知识关联检查",
            "methods/scp-integration.md#输出",
            "templates/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow/spec.json",
            "templates/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow/verify/verify.json"
          ],
          "verification": {
            "state": "not_run",
            "scope": "2026-10-23 只核对方法输出与模板接口；未运行真实课题分析→出图。",
            "evidence": []
          }
        }
      ]
    },
    "body": "# 单细胞批次整合\n\n<!-- facts:start -->\n- 来源：https://github.com/zhanghao-njmu/scp（b9b0eb7a7bf2c2c4b2262e73e09d7ebd515c7da0）\n- 许可证：GPL-3\n- 引用：SCP: https://github.com/zhanghao-njmu/scp (commit b9b0eb7a7bf2c2c4b2262e73e09d7ebd515c7da0)\n- 标签：单细胞分析\n- 输入接口：未声明\n- 输出接口：未声明\n- 接口结构匹配的图（仅结构候选，未核实语义）：暂无\n- 接口结构匹配的下一步方法（仅结构候选，未核实语义）：暂无\n- 代码模板：[methods/batch-integration/code/analysis.R](/files/wiki/methods/batch-integration/code/analysis.R)\n\n- 方法配图关系（语义审查）：\n  - [[templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap|CNS 细胞类型 UMAP]]（ready）：需要适配（adaptable）；调用验证：not_run；范围：2026-10-23 只核对方法输出与模板接口；未运行真实课题分析→出图。\n    - 依据：整合后的嵌入可按 batch 或 celltype 着色，复用现有 UMAP 单 panel；模板不做整合。；前提：坐标与 group 来自同一整合嵌入；cell_id 唯一；坐标无 NA。；group 明确为 batch 或 celltype；group_levels 由课题给出。；适配：导出 render-umap-groups.csv（cell_id, umap_1, umap_2, group）；模板不读 RDS。\n    - 关系证据：methods/batch-integration.md#输出；methods/scp-integration.md#知识关联检查；methods/scp-integration.md#输出；templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap/spec.json；templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap/verify/verify.json；运行证据：无\n  - [[templates/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow|细胞比例堆叠流带图]]（ready）：需要适配（adaptable）；调用验证：not_run；范围：2026-10-23 只核对方法输出与模板接口；未运行真实课题分析→出图。\n    - 依据：按 batch/样本统计细胞类型比例，可检查整合前后组成是否被过度改变；模板不做统计检验。；前提：每个 group 的比例归一化到 1；group 为 batch/样本，celltype 为注释类型。；比例是描述性；组间差异不能由该图直接推断。；适配：导出 render-cell-proportions.csv（group, celltype, proportion）；比例只作描述。\n    - 关系证据：methods/batch-integration.md#输出；methods/scp-integration.md#知识关联检查；methods/scp-integration.md#输出；templates/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow/spec.json；templates/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow/verify/verify.json；运行证据：无\n<!-- facts:end -->\n\n## 用途\n\n把来自不同样本、测序批次或技术平台的细胞放进同一个嵌入，减少批次带来的分离，同时保留真实的细胞类型和状态差异。输出是整合对象、嵌入和聚类，供跨样本比较与出图。\n\n## 原理与选择\n\nSeurat 锚点法先找跨批次相互最近的细胞对，再校正表达；Harmony 在 PCA 空间迭代校正。两者都假设批次间存在可对齐的共享细胞类型；如果批次与疾病/处理完全混杂，整合不能替代研究设计。SCP `Integration_SCP` 还提供 scVI、MNN、fastMNN、Scanorama、BBKNN、CSS、LIGER、Conos、ComBat 等分支；本页只验证 Seurat 分支，Harmony 分支因缺包未运行。\n\n\n\n## 来源与实现选择\n\n| 策略 / 实现 | 原始来源 | 输入与目标 | 本库状态 |\n|---|---|---|---|\n| SCP `Seurat_integrate` 锚点法 | [[methods/scp-integration]]；`SCP-local/R/SCP-workflow.R` | 含 batch 列的 counts；整合嵌入与聚类 | 已封装并 verified（120 细胞/2 批） |\n| SCP `Harmony_integrate` | 同上 | PCA + batch；Harmony 嵌入 | 已封装；harmony 缺失，`not_run` |\n| 青光眼 `preprocess.R` 的 Harmony | [[methods/scrna-preprocess-doublet-qc-harmony]]；`source/preprocess.R` | Seurat 流程 + Harmony | 原脚本未函数化；未在本库验证 |\n## 适用\n\n- 多个样本/技术批次，存在重叠细胞类型，且 batch 列与生物学分组可区分。\n- 需要联合聚类、跨样本 UMAP 或比较细胞类型比例。\n- 有明确的批次定义和足够的跨批次锚点。\n\n## 不适用\n\n- 只有单一批次，或 batch 与疾病/处理完全重合：整合会掩盖真实差异。\n- 细胞类型完全不重叠、物种不同或基因标识不可比时，锚点法不适用。\n- 不能用整合后的“混合得更好”证明生物学差异消失或数据质量更高。\n\n## 输入\n\n一个带 `batch` 元数据列的 Seurat 对象（原始 counts），或按批次拆分的对象列表；`batch` 必须显式给出，不能从文件名猜。每个细胞一行嵌入，需保留原始样本/批次身份。\n\n## 怎么做\n\n1. 明确 batch 是技术批次还是样本；检查 batch 与分组是否完全混杂。\n2. 按 SCP/Seurat 分支做归一化、HVF、锚点、整合、PCA/UMAP；参数（HVF 数、dims、k.weight）显式记录。\n3. 同时看整合前后 batch 混合、细胞类型 marker 是否保留、比例是否被过度改变。\n4. 与未整合/其他方法做敏感性比较；不能只挑混合最好的一张图。\n5. Harmony、scVI 等分支只有在依赖可用且实际运行后才可声称支持。\n\n## 代码\n\n- Seurat 分支：`methods/batch-integration/code/analysis.R:run_seurat_integration(srt, batch, bundle, parameters)`，封装 SCP `Seurat_integrate`。2026-10-23 在 `pancreas_sub` 120 细胞、两个显式批次、300 HVF、20 PC、`k.weight=30` 上实际调用；封装与上游 UMAP 一致，输出 `Seuratpca`、`SeuratUMAP2D`、`Seuratclusters`。scope 仅软件夹具。\n- Harmony 分支：同文件 `run_batch_integration(srt, bundle, parameters)`，封装 `Harmony_integrate`；本机无 harmony，`not_run`，精确错误 `Missing R dependency: harmony; automatic installation is disabled`。\n\n两个分支独立验证；Seurat 分支通过不批准 Harmony 分支。\n\n## 输出\n\nSeurat 分支返回 `list(result=Seurat, diagnostics=...)`；`result` 含整合 assay、`Seuratpca`、`SeuratUMAP2D`、`Seuratclusters`。可另导出每细胞 `cell_id, batch, umap_1, umap_2` 供模板使用。Harmony 分支当前无输出。\n\n## 知识关联检查\n\n2026-10-23 检查了 UMAP 分组图与细胞比例图。整合嵌入可按 batch/celltype 着色，比例图可检查组成变化；两者都是 adaptable，模板不执行整合。没有 direct。不能把“整合后 UMAP 混合”当作批次校正成功的唯一证据，仍需 marker 与比例检查。\n\n## 使用记录\n\n2026-10-23：Seurat 分支在隔离 R 环境实际运行并与上游比较；Harmony 分支缺包保留 not_run，未安装。\n\n<!-- user:start -->\n<!-- user:end -->\n",
    "implementation_status": [
      {
        "id": "scp-seurat",
        "title": "SCP Seurat_integrate 锚点分支",
        "state": "verified",
        "scope": "实际调用 SCP Seurat_integrate：pancreas_sub 120 细胞拆成两个显式批次，300 HVF、20 PC、k.weight=30；比较封装与上游 UMAP。"
      },
      {
        "id": "scp-harmony",
        "title": "SCP Harmony_integrate 分支",
        "state": "not_run",
        "scope": "SCP Harmony_integrate 分支；本机 R 库无 harmony。"
      }
    ],
    "backlinks": [
      {
        "path": "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap.md",
        "title": "CNS 细胞类型 UMAP",
        "type": "template"
      },
      {
        "path": "methods/scp-local-source.md",
        "title": "SCP 源码本地化",
        "type": "method"
      },
      {
        "path": "methods/scp-visualization-interface.md",
        "title": "SCP 绘图函数与图接口映射",
        "type": "method"
      },
      {
        "path": "interfaces/render-umap-groups.md",
        "title": "UMAP 坐标与分组表",
        "type": "interface"
      },
      {
        "path": "methods/scp-integration.md",
        "title": "单细胞多样本整合",
        "type": "method"
      },
      {
        "path": "methods/scp-standard-workflow.md",
        "title": "单细胞标准预处理、降维与聚类",
        "type": "method"
      },
      {
        "path": "methods/scrna-preprocess-doublet-qc-harmony.md",
        "title": "单细胞预处理、批次校正与聚类",
        "type": "method"
      },
      {
        "path": "templates/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow.md",
        "title": "细胞比例堆叠流带图",
        "type": "template"
      },
      {
        "path": "interfaces/render-cell-proportions.md",
        "title": "细胞类型比例表",
        "type": "interface"
      }
    ],
    "gallery": null,
    "reuse": null,
    "figure_refs": [
      "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap.md",
      "templates/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow.md"
    ],
    "preview": null,
    "workflow": {
      "stage": "method_confirm",
      "queue": "confirm",
      "label": "待你确认",
      "reason": "笔记与知识关联检查已填写，待作者核对。",
      "templates": []
    },
    "relations": [
      {
        "method": "methods/batch-integration.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap.md",
        "method_title": "单细胞批次整合",
        "figure_title": "CNS 细胞类型 UMAP",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "整合后的嵌入可按 batch 或 celltype 着色，复用现有 UMAP 单 panel；模板不做整合。",
        "prerequisites": [
          "坐标与 group 来自同一整合嵌入；cell_id 唯一；坐标无 NA。",
          "group 明确为 batch 或 celltype；group_levels 由课题给出。"
        ],
        "adaptation": "导出 render-umap-groups.csv（cell_id, umap_1, umap_2, group）；模板不读 RDS。",
        "evidence": [
          "methods/batch-integration.md#输出",
          "methods/scp-integration.md#知识关联检查",
          "methods/scp-integration.md#输出",
          "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap/spec.json",
          "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap/verify/verify.json"
        ],
        "verification": {
          "state": "not_run",
          "scope": "2026-10-23 只核对方法输出与模板接口；未运行真实课题分析→出图。",
          "evidence": []
        },
        "target_kind": "template",
        "active": true
      },
      {
        "method": "methods/batch-integration.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow.md",
        "method_title": "单细胞批次整合",
        "figure_title": "细胞比例堆叠流带图",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "按 batch/样本统计细胞类型比例，可检查整合前后组成是否被过度改变；模板不做统计检验。",
        "prerequisites": [
          "每个 group 的比例归一化到 1；group 为 batch/样本，celltype 为注释类型。",
          "比例是描述性；组间差异不能由该图直接推断。"
        ],
        "adaptation": "导出 render-cell-proportions.csv（group, celltype, proportion）；比例只作描述。",
        "evidence": [
          "methods/batch-integration.md#输出",
          "methods/scp-integration.md#知识关联检查",
          "methods/scp-integration.md#输出",
          "templates/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow/spec.json",
          "templates/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow/verify/verify.json"
        ],
        "verification": {
          "state": "not_run",
          "scope": "2026-10-23 只核对方法输出与模板接口；未运行真实课题分析→出图。",
          "evidence": []
        },
        "target_kind": "template",
        "active": true
      }
    ]
  }
];

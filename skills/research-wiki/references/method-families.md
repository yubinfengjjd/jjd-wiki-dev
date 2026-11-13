# 方法家族、实现与验证

## 收录四步（先走完再写页面）

v2 把原来的八步压成四步，内容不减。开源库的整模块先按 L0 → L1 入库（见 [来源与配方契约](sources-and-recipes.md)），只有课题用到、要函数化成方法时才走这里。

1. **读目的与输入**：读资料、数据说明、代码和已有计划，写清分析目的、输入语义、输出对象、统计单位、估计目标、本次提炼范围；复用作者已确认的答案。
2. **查库语义去重**：查现有方法、实现、流程、接口。按研究问题、输入语义、行/样本单位、估计目标、算法假设判断是否同一家族；不只比标题、函数名、关键词或来源包。然后分类：
   - 同一实现/算法 → 在已有家族补来源、参数差异、实现或验证；
   - 新算法/实现 → 加入已有家族的分支；
   - 多个方法串联 → `workflow`；
   - 源码、环境、绘图接口适配 → `technical`；
   - 只有新的分析目的 → 才提议新建家族。
   参数变化是配置，不是新家族。列出更新页面、增量、函数入口、验证、材料缺口和关键选择，关键选择明确后执行；缺原始数据、改变统计逻辑或补缺失算法先问作者。
3. **提炼与验证**：原始代码保持原语言/原字节；提炼版独立，显式数据/参数/结果/诊断，说明复制依赖和调用方式。确定最小调用闭包、算法包、转换层、局部资源和可选分支，写资产根 `runtime.json`；拆不开时标 `bundle`/`unknown`。逐实现实际调用原版/提炼版、异目录复制、换合法数据和输入不变检查；失败/缺依赖/未运行写精确 `not_run`，不以加载或一个分支通过批准整个家族。独立迁移另证：只复制清单文件和资源到异目录、不提供来源库路径、新进程实际调用，记录命令/环境/闭包哈希。验证在现有环境或 Wiki 专用环境做；要装包时列进批次缺包清单，作者按批次批准后才装，不往课题环境装。
4. **知识整合与确认**：把判断编译进已有页面（实现选择、适用边界、相关方法/流程/接口/图样）；来源冲突时记录并修订旧判断，不做一来源一孤立条目。检查重复、断链、冗余与证据，`check-entry` 无缺项后交作者确认（可按批次 `mark-ready <id…>`）；知识整理与实现验证分别显示。未验证知识默认可读但明确标注，不能作为可执行推荐。

## 函数契约（L2 方法与模板共用）

- 记录原语言、来源/许可证或未知状态、原字节及 SHA-256；源代码只读，函数化版本独立，列原函数与新入口的映射。普通路径、输入输出整理和参数化可在已确认计划内做；改变统计逻辑、估计量、泄漏边界、缺失值/异常值算法，或替换、补写分析算法前，说明差异并问作者。
- 分析函数显式接受数据对象、变量/结局/分组列、算法实际需要的参数和随机性，返回结构化结果表及必要诊断。默认不隐式读写文件、绘图、联网、装包或修改知识库；原算法必要的副作用明确隔离并记录。
- 绘图函数消费表，显式列映射与视觉参数，不隐式训练或重做分析；Python 通常返回 figure/axes，R 返回 plot/grob。保留模板 `draw(fig, rect, tables, style)` / `render` 入口，独立调用与组图共用同一绘图核心。
- 复制到课题后用课题自己的环境，数据、列和参数显式传入，不依赖原工作目录、硬编码路径或知识库目录。不为收录制作公共 pip/R 包。
- 实际比较原版与封装版的数值结果、行顺序、缺失值处理、随机性和图形结构，必要容差写依据；不同工作目录、换数据各跑一次。组数与尺寸适配见 [尺寸适配契约](adaptive-sizing.md)。

## 运行清单与独立性

- 每个实现/模板在资产根写 `runtime.json`：入口、`runtime_mode`、复制文件、资源、必要/可选包、来源映射和独立性证据指针。字段与状态见 [最小运行清单](minimal-runtime.md)。
- `portability`（verified/declared/not_run/stale/invalid/bundle/unknown）与算法 `verification`（verified/not_run/stale/invalid）是两个轴，互不授予。声明、文件存在、source 成功、旧整库收据都不能写成独立迁移已验证或算法已验证。
- 清单/入口/helper/资源/依赖声明变化使独立性证据过期；算法代码变化使算法收据过期。旧证据保留，不改写。

## 跨来源去重判定

- 以研究问题、输入语义、统计单位、估计目标和算法边界认同一性，不以项目、软件包、帖子或源码文件认同一性。
- 同一算法在课题脚本与 SCP 包装中出现，是同一算法的不同实现/适配器；参数不同通常是配置，不新建方法。
- 不同算法可以同属一个家族（如 scDblFinder/DoubletFinder 都属于双细胞检测），但必须比较输入、假设、预期率、输出和失败模式，不能抹平差异或当成可互换。
- 青光眼预处理与 SCP 标准流程可作为不同来源的 `workflow` 保留步骤/参数差异；共同 QC、降维、聚类、批次整合必须引用同一规范方法，不再重复计为分析方法。
- 旧页保留 id、`source/`、commit、许可证和作者备注，改为 `technical`/`workflow` 来源资料并指向规范家族；不删除历史证据。
- 每次实质入库交付“旧页/来源→规范家族→具体实现→原始来源”对照表。自动 `lint` 只检查声明结构、标题重复、收据结构、断链，以及 workflow/technical 页不得保留主 `figure_relations`；跨来源语义同义性由 agent 按本流程人工审查，不能宣称自动解决。

## 来源 panel 存储

- 来源 panel、完整原图、`original_code/` 只放画廊等只读原始层；前端通过受控路径读取，不复制到知识库。
- Markdown 只保存来源路径、哈希、裁图/bbox 和证据链接；新增入库不得重复存放同字节来源图片。
- 模板/方法资产可保存可复用代码、示例和真实回放预览；没有回放时显示来源 panel，必须标“来源参考图／尚无回放”，不能冒充模板验证。
- 验收：画廊来源图可展示、Wiki 无重复来源图、参考图/回放图标识正确、原始哈希不变；不为规则擅删历史资产。

## frontmatter 契约

```yaml
method_kind: analysis   # analysis | workflow | technical
purposes: [降维与聚类, 模型评价]   # analysis only; controlled vocabulary
summary: 一句可用于索引的判断性摘要
data_contract:
  input: 输入对象、粒度和关键条件
  output: 结果对象/表及关键含义
implementations:
  - id: example
    title: 具体实现名
    language: R
    entrypoint: code/analysis.R:run_analysis
    dependencies: [Seurat]
    verification: verification/example.json
```

- `analysis` 才进入默认方法目录/分析推荐；`workflow` 是组合流程资料；`technical` 是源码、绘图接口、适配层等技术资料。
- `analysis` 页用受控 `purposes` 表达分析用途：预处理与质量控制、降维与聚类、整合与批次校正、注释与参考映射、差异与功能分析、轨迹与动态分析、模型评价、模型解释。词表只在 `rwiki/method_taxonomy.py`；领域仍用 `tags`，两者可多选，所有入口引用同一 `id`。
- 分类只用于发现，不是科学适用性/可执行推荐的门槛。计数是去重页数；缺用途的旧页可读并提示，非法/重复用途为 ERROR。领域 `tags` 只接受 `config.taxonomy` 的规范键或中文 label（别名、软件、数据集、模型名进 `keywords`）；非法或重复 tags 同样为 ERROR，空列表仍可读。API 写入先去空白、去重，再按同一词表拒绝。
- 旧页没有 `method_kind` 时保持可读但显示“待分类”，不自动可执行。
- `inputs`/`outputs` 只列真实接口，可以为空；`data_contract` 必须说明真实对象/矩阵/模型和结果含义。不强制所有输出 CSV。
- `source/` 原字节只读；`code/` 是显式参数化/封装版；不复用来源页的 `source/` 当可执行实现。

## 验证收据

`verification/*.json` 至少：

```json
{
  "schema_version": 1,
  "implementation": "example",
  "state": "passed",
  "scope": "实际调用范围与不覆盖的内容",
  "command": "实际命令",
  "checks": ["实际断言"],
  "environment": {"R": "4.5.0"},
  "files": {"code/analysis.R": "<sha256>"}
}
```

- `files` 必须覆盖当前 `code/` 下所有源文件；入口必须存在且属于 `code/`。
- `passed` 只给实际执行、检查通过、原版/封装等价、异目录复制和输入检查通过的分支；代码一变旧收据即 stale。
- 缺依赖/上游失败写 `not_run`，保留精确错误，不伪造通过；装包只按批次经作者批准。不把加载/假引擎/合成夹具说成科学验证。
- 一个 verified 分支不批准其他分支；`workflow`/`technical` 不要求分析实现收据。
- 代码查看 API 按入口文件派生分支状态；共享文件列出所有分支，原始版保持来源清单状态，不因一个分支通过而提升。

## 当前分析家族（2026-10-23）

| 家族 | 用途（purposes） | 已声明实现/来源 | 状态 |
|---|---|---|---|
| `cell-quality-control` | 预处理与质量控制 | SCP `RunCellQC` UMI/基因数/线粒体；青光眼 MAD QC 来源 | SCP 分支 verified；双细胞/离群点未运行；青光眼脚本未函数化 |
| `doublet-detection` | 预处理与质量控制 | scDblFinder（SCP）；DoubletFinder（青光眼）；Scrublet 等未实现 | scDblFinder not_run；DoubletFinder 未函数化/未验证 |
| `batch-integration` | 整合与批次校正 | SCP `Seurat_integrate` / `Harmony_integrate`；青光眼 Harmony 来源 | Seurat verified；Harmony not_run；青光眼未函数化 |
| `differential-expression` | 差异与功能分析 | SCP `RunDEtest` Wilcoxon | verified；conserved/disturbed 等未运行 |
| `gene-set-enrichment` | 差异与功能分析 | SCP `RunEnrichment` 自定义 TERM2GENE ORA；青光眼 GO/KEGG 仅用于构建签名 | ORA verified；在线 GO/KEGG、GSEA、simplify 未运行 |
| `gene-set-scoring` | 差异与功能分析 | SCP `CellScoring` Seurat；AUCell/UCell 未运行；青光眼五分数相加来源 | Seurat verified；其他分支未运行；五分数不是通用标准 |
| `trajectory-inference` | 轨迹与动态分析 | SCP `RunSlingshot` | verified；Monocle2/3、PAGA 等未实现 |
| `rna-velocity` | 轨迹与动态分析 | SCP `RunSCVELO` | not_run：Python 后端缺失 |
| `cell-type-annotation` | 注释与参考映射 | SCP `RunSingleR`；青光眼 marker 手工注释来源；参考映射单列家族 | SingleR not_run；marker 脚本未函数化/未验证 |
| `reference-mapping` | 注释与参考映射 | Seurat 锚点标签转移；SCP `RunSeuratMap` 投影 | 标签转移 verified；投影 not_run |
| `dimensionality-reduction` | 降维与聚类 | SCP `RunDimReduction` PCA/UMAP；青光眼 PCA/UMAP 来源 | verified；其他分支未运行 |
| `cell-clustering` | 降维与聚类 | 显式 Seurat FindNeighbors/FindClusters；青光眼聚类来源 | verified；不含预处理/降维/整合 |
| `dynamic-feature-analysis` | 轨迹与动态分析 | SCP `RunDynamicFeatures` Gaussian + 夹具 pseudotime | verified；计数/负二项分支未运行 |
| `shap-explanation` | 模型解释 | `explain_model` 纯函数；旧脚本只作来源 | verified（解析线性模型）；真实模型/课题未联调 |
| `regression-resampling-evaluation` | 模型评价 | `summarize_predictions` 指标汇总 | verified；训练/重采样未实现 |

旧 `scp-*`/`scrna-*` 实现页保留旧 id、`source/` 和作者备注，`method_kind=technical` 或 `workflow`；它们链接到真正家族，不再作为分析推荐卡片，也不保留 `figure_relations` 主记录。

## 关系与图

- 语义关系只在方法侧 `figure_relations` 维护一次；`direct` 只给非 draft 模板且模板读取接口全在 `outputs` 中；否则 `adaptable`/`candidate`。
- 结构相同、接口同名、标签相同都不等于科学直连；无匹配图时写“无图原因”，不为凑网络硬连。
- 方法输出无结构模板也无语义模板时，`lint` 会 WARN；在“知识关联检查”写清原因。

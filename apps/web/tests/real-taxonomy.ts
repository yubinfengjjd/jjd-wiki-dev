/* Generated from the real wiki API on 2026-10-23; do not hand-edit. */
export const REAL_TAXONOMY: any = {
  "total": 15,
  "domains": [
    {
      "value": "单细胞分析",
      "count": 13,
      "purposes": [
        {
          "value": "预处理与质量控制",
          "count": 2
        },
        {
          "value": "降维与聚类",
          "count": 2
        },
        {
          "value": "整合与批次校正",
          "count": 1
        },
        {
          "value": "注释与参考映射",
          "count": 2
        },
        {
          "value": "差异与功能分析",
          "count": 3
        },
        {
          "value": "轨迹与动态分析",
          "count": 3
        }
      ]
    },
    {
      "value": "转录组",
      "count": 4,
      "purposes": [
        {
          "value": "差异与功能分析",
          "count": 3
        },
        {
          "value": "轨迹与动态分析",
          "count": 1
        }
      ]
    },
    {
      "value": "机器学习",
      "count": 2,
      "purposes": [
        {
          "value": "模型评价",
          "count": 1
        },
        {
          "value": "模型解释",
          "count": 1
        }
      ]
    },
    {
      "value": "实验统计",
      "count": 1,
      "purposes": [
        {
          "value": "模型评价",
          "count": 1
        }
      ]
    },
    {
      "value": "模型解释与特征重要性",
      "count": 1,
      "purposes": [
        {
          "value": "模型解释",
          "count": 1
        }
      ]
    }
  ],
  "purposes": [
    {
      "value": "预处理与质量控制",
      "count": 2
    },
    {
      "value": "降维与聚类",
      "count": 2
    },
    {
      "value": "整合与批次校正",
      "count": 1
    },
    {
      "value": "注释与参考映射",
      "count": 2
    },
    {
      "value": "差异与功能分析",
      "count": 3
    },
    {
      "value": "轨迹与动态分析",
      "count": 3
    },
    {
      "value": "模型评价",
      "count": 1
    },
    {
      "value": "模型解释",
      "count": 1
    }
  ],
  "unclassified": []
};

export const REAL_DETAILS: any[] = [
  {
    "path": "methods/shap-explanation.md",
    "meta": {
      "type": "method",
      "id": "shap-explanation",
      "title": "基于 SHAP 的模型解释",
      "status": "ready",
      "tags": [
        "机器学习",
        "模型解释与特征重要性"
      ],
      "inputs": [],
      "outputs": [
        "shap-summary",
        "shap-samples"
      ],
      "source": {
        "kind": "post",
        "gallery_entry": "2026-08-17-shap-feature-mechanism/figures/fig01-shap-a-f"
      },
      "license": "none",
      "cite": [
        "Lundberg & Lee. A Unified Approach to Interpreting Model Predictions. NeurIPS, 2017.",
        "Lundberg et al. From local explanations to global understanding with explainable AI for trees. Nature Machine Intelligence, 2020.",
        "SHAP TreeExplainer official documentation. https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html",
        "SHAP LinearExplainer official documentation. https://shap.readthedocs.io/en/latest/generated/shap.LinearExplainer.html",
        "SHAP Explainer official documentation. https://shap.readthedocs.io/en/latest/generated/shap.Explainer.html"
      ],
      "favorite": false,
      "figure_relations": [
        {
          "figure": "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--bar",
          "compatibility": "direct",
          "reason": "特征级平均绝对 SHAP 及其占比对应汇总图契约。",
          "prerequisites": [
            "同一已明确模型输出、解释对象和背景定义；不可混合不同输出单位。",
            "使用真实 SHAP 表；示例估读/合成数据仅作画法参考。",
            "模板为历史固定尺寸实现；任意 n、长标签与配色须另查可读性，尚未迁移为自适应模板。"
          ],
          "adaptation": "",
          "evidence": [
            "methods/shap-explanation.md#输出",
            "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--bar/spec.json",
            "interfaces/shap-summary.md"
          ],
          "verification": {
            "state": "not_run",
            "scope": "本轮仅核对知识含义与现存契约，未做实际课题分析→出图联调。",
            "evidence": []
          }
        },
        {
          "figure": "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--beeswarm",
          "compatibility": "direct",
          "reason": "逐样本×特征的带符号 SHAP 和着色特征值对应蜂群图契约。",
          "prerequisites": [
            "同一已明确模型输出、解释对象和背景定义；不可混合不同输出单位。",
            "使用真实 SHAP 表；示例估读/合成数据仅作画法参考。",
            "模板为历史固定尺寸实现；任意 n、长标签与配色须另查可读性，尚未迁移为自适应模板。"
          ],
          "adaptation": "",
          "evidence": [
            "methods/shap-explanation.md#输出",
            "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--beeswarm/spec.json",
            "interfaces/shap-samples.md"
          ],
          "verification": {
            "state": "not_run",
            "scope": "本轮仅核对知识含义与现存契约，未做实际课题分析→出图联调。",
            "evidence": []
          }
        },
        {
          "figure": "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--radial-bar",
          "compatibility": "direct",
          "reason": "特征级平均绝对 SHAP 及其占比对应汇总图契约。",
          "prerequisites": [
            "同一已明确模型输出、解释对象和背景定义；不可混合不同输出单位。",
            "使用真实 SHAP 表；示例估读/合成数据仅作画法参考。",
            "模板为历史固定尺寸实现；任意 n、长标签与配色须另查可读性，尚未迁移为自适应模板。"
          ],
          "adaptation": "",
          "evidence": [
            "methods/shap-explanation.md#输出",
            "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--radial-bar/spec.json",
            "interfaces/shap-summary.md"
          ],
          "verification": {
            "state": "not_run",
            "scope": "本轮仅核对知识含义与现存契约，未做实际课题分析→出图联调。",
            "evidence": []
          }
        }
      ],
      "keywords": [
        "SHAP",
        "方法家族",
        "模型解释"
      ],
      "method_kind": "analysis",
      "purposes": [
        "模型解释"
      ],
      "summary": "对既定模型输出作 SHAP 归因，输出汇总表和逐样本贡献表；不训练、不划分数据。",
      "data_contract": {
        "input": "已拟合模型、背景 DataFrame、解释样本 DataFrame；特征列同名同序、有限数值。",
        "output": "样本×特征 SHAP 矩阵、summary 表（feature/shap/percent）、samples 长表；不产生训练或预测指标。"
      },
      "implementations": [
        {
          "id": "shap-explain-model",
          "title": "SHAP 纯函数封装",
          "language": "Python",
          "entrypoint": "code/explain_model.py:explain_model",
          "dependencies": [
            "shap",
            "numpy",
            "pandas"
          ],
          "verification": "verification/shap-explain-model.json"
        }
      ]
    },
    "body": "# 基于 SHAP 的模型解释\n\n<!-- facts:start -->\n- 来源：[[layouts/2026-08-17-shap-feature-mechanism__fig01-shap-a-f|双模型 SHAP 特征贡献组图]]\n- 许可证：仅供个人研究参考\n- 引用：Lundberg & Lee. A Unified Approach to Interpreting Model Predictions. NeurIPS, 2017.；Lundberg et al. From local explanations to global understanding with explainable AI for trees. Nature Machine Intelligence, 2020.；SHAP TreeExplainer official documentation. https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html；SHAP LinearExplainer official documentation. https://shap.readthedocs.io/en/latest/generated/shap.LinearExplainer.html；SHAP Explainer official documentation. https://shap.readthedocs.io/en/latest/generated/shap.Explainer.html\n- 标签：机器学习、模型解释与特征重要性\n- 分析用途：模型解释\n- 输入接口：未声明\n- 输出接口：[[interfaces/shap-summary|SHAP 特征贡献汇总表]] · [[interfaces/shap-samples|SHAP 逐样本值表]]\n- 接口结构匹配的图（仅结构候选，未核实语义）：[[templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--bar|SHAP 条形图（含环形 inset）]]（ready） · [[templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--beeswarm|SHAP 蜂群图]]（ready） · [[templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--radial-bar|SHAP 环形贡献图]]（ready）\n- 接口结构匹配的下一步方法（仅结构候选，未核实语义）：暂无\n- 代码模板：[methods/shap-explanation/code/explain_model.py](/files/wiki/methods/shap-explanation/code/explain_model.py) · [methods/shap-explanation/code/shap_explain.py](/files/wiki/methods/shap-explanation/code/shap_explain.py)\n\n- 方法配图关系（语义审查）：\n  - [[templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--bar|SHAP 条形图（含环形 inset）]]（ready）：直接可接（direct）；调用验证：not_run；范围：本轮仅核对知识含义与现存契约，未做实际课题分析→出图联调。\n    - 依据：特征级平均绝对 SHAP 及其占比对应汇总图契约。；前提：同一已明确模型输出、解释对象和背景定义；不可混合不同输出单位。；使用真实 SHAP 表；示例估读/合成数据仅作画法参考。；模板为历史固定尺寸实现；任意 n、长标签与配色须另查可读性，尚未迁移为自适应模板。；适配：无格式适配声明\n    - 关系证据：methods/shap-explanation.md#输出；templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--bar/spec.json；interfaces/shap-summary.md；运行证据：无\n  - [[templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--beeswarm|SHAP 蜂群图]]（ready）：直接可接（direct）；调用验证：not_run；范围：本轮仅核对知识含义与现存契约，未做实际课题分析→出图联调。\n    - 依据：逐样本×特征的带符号 SHAP 和着色特征值对应蜂群图契约。；前提：同一已明确模型输出、解释对象和背景定义；不可混合不同输出单位。；使用真实 SHAP 表；示例估读/合成数据仅作画法参考。；模板为历史固定尺寸实现；任意 n、长标签与配色须另查可读性，尚未迁移为自适应模板。；适配：无格式适配声明\n    - 关系证据：methods/shap-explanation.md#输出；templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--beeswarm/spec.json；interfaces/shap-samples.md；运行证据：无\n  - [[templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--radial-bar|SHAP 环形贡献图]]（ready）：直接可接（direct）；调用验证：not_run；范围：本轮仅核对知识含义与现存契约，未做实际课题分析→出图联调。\n    - 依据：特征级平均绝对 SHAP 及其占比对应汇总图契约。；前提：同一已明确模型输出、解释对象和背景定义；不可混合不同输出单位。；使用真实 SHAP 表；示例估读/合成数据仅作画法参考。；模板为历史固定尺寸实现；任意 n、长标签与配色须另查可读性，尚未迁移为自适应模板。；适配：无格式适配声明\n    - 关系证据：methods/shap-explanation.md#输出；templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--radial-bar/spec.json；interfaces/shap-summary.md；运行证据：无\n<!-- facts:end -->\n\n## 用途\n\n对既定模型输出作特征归因，分别保存逐样本带符号贡献和特征级平均绝对贡献。此页是有条件的方法家族说明；家族范围、代码分支、实际验证三个维度分开。解释训练模型的行为，不提供因果或临床效用结论。\n\n## 原始实现与家族范围\n\n来源是公众号的 XGBoost＋SHAP 示例；原生片段只保留在画廊条目 `2026-08-17-shap-feature-mechanism/figures/fig01-shap-a-f` 的 `original_code/`，manifest 记录字节哈希。Wiki 的 `code/shap_explain.py` 是历史复用脚本，保留原字节和旧行为；`code/explain_model.py` 是本次新增的纯函数封装，不训练、不划分、不调参。\n\n可推广的核心是“明确模型输出→选择适用解释器/背景→计算归因→整理结果”，而非承诺所有模型都支持同一入口：\n- 树分支：TreeExplainer 支持列出的模型家族，输出模式与特征依赖假设有条件。\n- 线性分支：LinearExplainer 可解释线性模型，背景与特征相关性处理影响归因。\n- 通用分支：Explainer 依据模型、masker 和算法选择估计器；成本与解释含义须核对。\n\n\n\n## 来源与实现选择\n\n| 策略 / 实现 | 原始来源 | 输入与目标 | 本库状态 |\n|---|---|---|---|\n| 原帖 XGBoost + SHAP 示例 | 画廊 `2026-08-17-shap-feature-mechanism/figures/fig01-shap-a-f` `original_code/`；旧复用脚本 `code/shap_explain.py` | 训练/预测/归因的组合脚本 | 原字节保留；历史脚本未提升为已验证实现 |\n| 纯函数 `explain_model` | 本次从旧脚本归因分支提炼；`code/explain_model.py` | 已拟合模型 + background + samples；values/summary/samples | verified：解析线性模型数值、顺序、输入不变 |\n| 树/线性/通用解释器 | 同上 | 不同模型/输出 | 代码分支存在；真实模型/课题未运行 |\n## 适用\n\n已明确研究任务、训练好的模型、特征处理、背景/解释样本及模型输出。`explain_model` 面向数值表格的回归/分类；真实课题先审查训练/验证边界、类别编码、缺失值与重复测量。标签名或模型名不能代替这些前提。\n\n## 不适用\n\n不能直接据此处理多分类、多输出、时序/分组划分或任意原生类别特征；需要另核接口和实现。特征归因不等于因果、预测校准、外部验证或模型临床有效性。相关特征与背景选择必须说明，不能仅看排名定机制。\n\n## 输入\n\n`explain_model(model, background, samples, ...)` 接收已拟合模型、背景 DataFrame 和解释样本 DataFrame；两者特征列必须同名同序、非空、有限数值。`explainer_kind` 取 `tree`/`linear`/`model_agnostic`；分类通用分支用 `predict_proba[:, output_index]`。训练、数据划分、样本选择和背景定义都由调用方负责，函数不隐式重做。\n\n## 怎么做\n\n1. 在课题中先固定模型、特征处理、背景和解释样本；不要用全数据回代或测试集调参后的模型冒充独立解释。\n2. 选择与实际模型匹配的解释器；树/线性/通用分支的前提不同。\n3. 显式传入 `task`、`output_index`、`top_n`、`min_mean_abs_shap` 和解释器/调用参数；随机方法要传 seed。\n4. 运行后检查 SHAP 矩阵形状、summary 百分比、样本表行数和特征顺序；用已知线性模型做数值 sanity check。\n5. 解释图只描述模型行为；需要因果/临床结论时另做设计和验证。\n\n## 代码\n\n入口 `methods/shap-explanation/code/explain_model.py:explain_model`，依赖 numpy、pandas、shap。2026-10-23 用解析线性模型验证：SHAP 值与闭式解一致、summary 百分比合计 100、samples 行数为样本×特征、输入和模型系数未变、特征顺序不一致会报错。scope 仅软件/数值夹具，不代表真实模型或临床有效性。\n\n`code/shap_explain.py` 是历史脚本，未改字节；本轮没有把它当作已验证实现。\n\n## 输出\n\n`values`：样本×特征 SHAP 矩阵；`summary`：feature、shap（平均绝对归因）、percent（筛选前总贡献占比）；`samples`：每行样本×特征的带符号 shap 和 feature_value（解释样本内各特征 min/max 缩放，常量=0）；`diagnostics`：解释器、任务、输出索引、样本/背景数、特征顺序、shap 版本等。TOP_N/MIN_MEAN_ABS_SHAP 筛选后不重新归一化 percent。\n\n## 使用记录\n\n2026-10-21：方法边界、代码来源和关系核查，未运行真实课题分析。\n2026-10-23：新增 `explain_model` 并用解析线性模型做数值验证；未运行真实模型或课题出图。\n\n## 知识关联检查\n\n2026-10-23 检查现存方法页、单 panel 来源、模板与接口，包括另一来源的回归评估。SHAP 汇总可配条形/环形，逐样本贡献可配蜂群，同一方法对应多图，关系唯一记在 frontmatter，反向由程序派生。三个历史模板为 direct（表结构无需改名/整形），但不证明上游分支或当前课题已联调；模板仍为历史固定尺寸。\n\n[[methods/regression-resampling-evaluation]] 与 SHAP 是互补参考：前者评估预测，后者归因。预测/指标表没有 SHAP 所需模型、特征及背景，不能直接串联；未发现第二个有依据的现存方法可直接读取 SHAP 图表契约。\n\n<!-- user:start -->\n<!-- user:end -->\n",
    "implementation_status": [
      {
        "id": "shap-explain-model",
        "title": "SHAP 纯函数封装",
        "state": "verified",
        "scope": "解析线性模型 SHAP 精确解；检查 summary/samples 表、百分比、输入与模型未变、特征顺序保护。"
      }
    ],
    "backlinks": [
      {
        "path": "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--bar.md",
        "title": "SHAP 条形图（含环形 inset）",
        "type": "template"
      },
      {
        "path": "interfaces/shap-summary.md",
        "title": "SHAP 特征贡献汇总表",
        "type": "interface"
      },
      {
        "path": "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--radial-bar.md",
        "title": "SHAP 环形贡献图",
        "type": "template"
      },
      {
        "path": "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--beeswarm.md",
        "title": "SHAP 蜂群图",
        "type": "template"
      },
      {
        "path": "interfaces/shap-samples.md",
        "title": "SHAP 逐样本值表",
        "type": "interface"
      },
      {
        "path": "layouts/2026-08-17-shap-feature-mechanism__fig01-shap-a-f.md",
        "title": "双模型 SHAP 特征贡献组图",
        "type": "layout"
      },
      {
        "path": "methods/regression-resampling-evaluation.md",
        "title": "回归模型的重采样评估与折外预测",
        "type": "method"
      }
    ],
    "gallery": null,
    "reuse": null,
    "input_contract": null,
    "figure_refs": [
      "layouts/2026-08-17-shap-feature-mechanism__fig01-shap-a-f.md",
      "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--bar.md",
      "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--beeswarm.md",
      "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--radial-bar.md"
    ],
    "preview": null,
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "已验证实现",
      "reason": "笔记已确认；仅实现收据中列明的分支和范围通过验证。",
      "templates": []
    },
    "relations": [
      {
        "method": "methods/shap-explanation.md",
        "figure": "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--bar.md",
        "method_title": "基于 SHAP 的模型解释",
        "figure_title": "SHAP 条形图（含环形 inset）",
        "method_status": "ready",
        "figure_status": "ready",
        "compatibility": "direct",
        "reason": "特征级平均绝对 SHAP 及其占比对应汇总图契约。",
        "prerequisites": [
          "同一已明确模型输出、解释对象和背景定义；不可混合不同输出单位。",
          "使用真实 SHAP 表；示例估读/合成数据仅作画法参考。",
          "模板为历史固定尺寸实现；任意 n、长标签与配色须另查可读性，尚未迁移为自适应模板。"
        ],
        "adaptation": "",
        "evidence": [
          "methods/shap-explanation.md#输出",
          "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--bar/spec.json",
          "interfaces/shap-summary.md"
        ],
        "verification": {
          "state": "not_run",
          "scope": "本轮仅核对知识含义与现存契约，未做实际课题分析→出图联调。",
          "evidence": []
        },
        "target_kind": "template",
        "active": true
      },
      {
        "method": "methods/shap-explanation.md",
        "figure": "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--beeswarm.md",
        "method_title": "基于 SHAP 的模型解释",
        "figure_title": "SHAP 蜂群图",
        "method_status": "ready",
        "figure_status": "ready",
        "compatibility": "direct",
        "reason": "逐样本×特征的带符号 SHAP 和着色特征值对应蜂群图契约。",
        "prerequisites": [
          "同一已明确模型输出、解释对象和背景定义；不可混合不同输出单位。",
          "使用真实 SHAP 表；示例估读/合成数据仅作画法参考。",
          "模板为历史固定尺寸实现；任意 n、长标签与配色须另查可读性，尚未迁移为自适应模板。"
        ],
        "adaptation": "",
        "evidence": [
          "methods/shap-explanation.md#输出",
          "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--beeswarm/spec.json",
          "interfaces/shap-samples.md"
        ],
        "verification": {
          "state": "not_run",
          "scope": "本轮仅核对知识含义与现存契约，未做实际课题分析→出图联调。",
          "evidence": []
        },
        "target_kind": "template",
        "active": true
      },
      {
        "method": "methods/shap-explanation.md",
        "figure": "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--radial-bar.md",
        "method_title": "基于 SHAP 的模型解释",
        "figure_title": "SHAP 环形贡献图",
        "method_status": "ready",
        "figure_status": "ready",
        "compatibility": "direct",
        "reason": "特征级平均绝对 SHAP 及其占比对应汇总图契约。",
        "prerequisites": [
          "同一已明确模型输出、解释对象和背景定义；不可混合不同输出单位。",
          "使用真实 SHAP 表；示例估读/合成数据仅作画法参考。",
          "模板为历史固定尺寸实现；任意 n、长标签与配色须另查可读性，尚未迁移为自适应模板。"
        ],
        "adaptation": "",
        "evidence": [
          "methods/shap-explanation.md#输出",
          "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--radial-bar/spec.json",
          "interfaces/shap-summary.md"
        ],
        "verification": {
          "state": "not_run",
          "scope": "本轮仅核对知识含义与现存契约，未做实际课题分析→出图联调。",
          "evidence": []
        },
        "target_kind": "template",
        "active": true
      }
    ]
  },
  {
    "path": "methods/differential-expression.md",
    "meta": {
      "type": "method",
      "id": "differential-expression",
      "title": "差异表达分析",
      "status": "draft",
      "tags": [
        "单细胞分析",
        "转录组"
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
      "purposes": [
        "差异与功能分析"
      ],
      "summary": "在明确对比组之间检验基因表达差异，输出效应量、p 值与阳性比例；细胞级 p 值不等于样本级推断。",
      "data_contract": {
        "input": "已标准化/注释的 Seurat 对象 + 分组列；比较组与参照组显式给出，组内细胞数足够。",
        "output": "SCP tools 中的 gene×contrast 表：gene、group1、group2、avg_log2FC、p_val、p_val_adj、pct.1、pct.2。"
      },
      "implementations": [
        {
          "id": "scp-detest",
          "title": "SCP RunDEtest 封装",
          "language": "R",
          "entrypoint": "code/analysis.R:run_differential_expression",
          "dependencies": [
            "Seurat",
            "BiocParallel"
          ],
          "verification": "verification/scp-detest.json"
        }
      ],
      "keywords": [
        "DE",
        "FindMarkers",
        "Wilcoxon",
        "avg_log2FC",
        "p_val_adj",
        "差异基因",
        "SCP"
      ],
      "figure_relations": [
        {
          "figure": "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot",
          "compatibility": "adaptable",
          "reason": "DE 选出的 marker 可整理成 group/feature/avg_expression/pct_expressed，复用气泡点图；模板不重算 DE。",
          "prerequisites": [
            "avg_expression 与 pct_expressed 由表达矩阵按组计算，不能用 avg_log2FC 代替。",
            "group/feature 顺序由课题给出；target_group 只用于排序。"
          ],
          "adaptation": "导出 render-dotplot-long.csv（group, feature, avg_expression, pct_expressed, target_group）。",
          "evidence": [
            "methods/differential-expression.md#输出",
            "methods/scp-de-enrichment-dynamic.md#知识关联检查",
            "methods/scp-de-enrichment-dynamic.md#输出",
            "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot/spec.json",
            "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot/verify/verify.json"
          ],
          "verification": {
            "state": "not_run",
            "scope": "2026-10-23 只核对方法输出与模板接口；未运行真实课题分析→出图。",
            "evidence": []
          }
        },
        {
          "figure": "templates/2026-10-22-scp-example__fig01-volcano--volcano",
          "compatibility": "adaptable",
          "reason": "DE 表可整理成 render-de-results，火山图模板消费该表；模板不重跑检验。",
          "prerequisites": [
            "group1 单一；pct_1/pct_2 为 0–1；p_val_adj >0；gene 组内唯一。",
            "模板不重跑 DE 或 p 值校正；阈值由 style 显式给出。"
          ],
          "adaptation": "从 AllMarkers 表导出 gene、avg_log2FC、p_val_adj 等字段到 render-de-results。",
          "evidence": [
            "methods/differential-expression.md#输出",
            "methods/scp-de-enrichment-dynamic.md#知识关联检查",
            "methods/scp-de-enrichment-dynamic.md#输出",
            "templates/2026-10-22-scp-example__fig01-volcano--volcano/spec.json",
            "templates/2026-10-22-scp-example__fig01-volcano--volcano/verify/verify.json"
          ],
          "verification": {
            "state": "not_run",
            "scope": "2026-10-23 只核对方法输出与模板接口；未运行真实课题分析→出图。",
            "evidence": []
          }
        }
      ]
    },
    "body": "# 差异表达分析\n\n<!-- facts:start -->\n- 来源：https://github.com/zhanghao-njmu/scp（b9b0eb7a7bf2c2c4b2262e73e09d7ebd515c7da0）\n- 许可证：GPL-3\n- 引用：SCP: https://github.com/zhanghao-njmu/scp (commit b9b0eb7a7bf2c2c4b2262e73e09d7ebd515c7da0)\n- 标签：单细胞分析、转录组\n- 分析用途：差异与功能分析\n- 输入接口：未声明\n- 输出接口：未声明\n- 接口结构匹配的图（仅结构候选，未核实语义）：暂无\n- 接口结构匹配的下一步方法（仅结构候选，未核实语义）：暂无\n- 代码模板：[methods/differential-expression/code/analysis.R](/files/wiki/methods/differential-expression/code/analysis.R)\n\n- 方法配图关系（语义审查）：\n  - [[templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot|细胞类型 × 基因气泡点图]]（ready）：需要适配（adaptable）；调用验证：not_run；范围：2026-10-23 只核对方法输出与模板接口；未运行真实课题分析→出图。\n    - 依据：DE 选出的 marker 可整理成 group/feature/avg_expression/pct_expressed，复用气泡点图；模板不重算 DE。；前提：avg_expression 与 pct_expressed 由表达矩阵按组计算，不能用 avg_log2FC 代替。；group/feature 顺序由课题给出；target_group 只用于排序。；适配：导出 render-dotplot-long.csv（group, feature, avg_expression, pct_expressed, target_group）。\n    - 关系证据：methods/differential-expression.md#输出；methods/scp-de-enrichment-dynamic.md#知识关联检查；methods/scp-de-enrichment-dynamic.md#输出；templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot/spec.json；templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot/verify/verify.json；运行证据：无\n  - [[templates/2026-10-22-scp-example__fig01-volcano--volcano|差异表达火山图]]（ready）：需要适配（adaptable）；调用验证：not_run；范围：2026-10-23 只核对方法输出与模板接口；未运行真实课题分析→出图。\n    - 依据：DE 表可整理成 render-de-results，火山图模板消费该表；模板不重跑检验。；前提：group1 单一；pct_1/pct_2 为 0–1；p_val_adj >0；gene 组内唯一。；模板不重跑 DE 或 p 值校正；阈值由 style 显式给出。；适配：从 AllMarkers 表导出 gene、avg_log2FC、p_val_adj 等字段到 render-de-results。\n    - 关系证据：methods/differential-expression.md#输出；methods/scp-de-enrichment-dynamic.md#知识关联检查；methods/scp-de-enrichment-dynamic.md#输出；templates/2026-10-22-scp-example__fig01-volcano--volcano/spec.json；templates/2026-10-22-scp-example__fig01-volcano--volcano/verify/verify.json；运行证据：无\n<!-- facts:end -->\n\n## 用途\n\n在两组细胞之间找出表达差异的基因，输出效应量、p 值、校正后 p 值和两组阳性比例。用于生成候选 marker、检查注释是否合理，或为富集分析提供基因列表。\n\n## 原理与选择\n\nSCP `RunDEtest` 默认调用 Seurat `FindMarkers` 的 Wilcoxon 分支，并按指定方法重新校正 p 值；它支持自定义细胞组、 conserved/disturbed marker 等分支。细胞级检验把每个细胞当独立观测，适合筛选描述性 marker，但不能直接当作样本/患者水平的组间推断；后者需要伪 bulk 或按样本聚合。检验方法、`only.pos`、`fc.threshold`、`min.pct` 都必须显式记录。\n\n\n\n## 来源与实现选择\n\n| 策略 / 实现 | 原始来源 | 输入与目标 | 本库状态 |\n|---|---|---|---|\n| SCP `RunDEtest`：Seurat `FindMarkers` + p 校正 | [[methods/scp-de-enrichment-dynamic]]；`SCP-local/R/SCP-analysis.R` | 标准化 Seurat、分组列；gene×contrast 表 | 已封装并 verified（Ductal vs Endocrine） |\n| conserved/disturbed marker 等分支 | 同上 | 多分组/配对设计 | 未实现、未运行 |\n| 青光眼课题 | `source/` 中未发现独立 DE 脚本；旧 SCP 技术页只归档 SCP 实现 | — | 不声称有独立课题实现 |\n## 适用\n\n- 已标准化/注释的 Seurat 对象，比较组和参照组明确。\n- 组内细胞数足够（SCP 要求每组至少 3 个细胞），且细胞类型/状态相对一致。\n- 用于 marker 筛选、注释检查或为 ORA/GSEA 提供排序列表。\n\n## 不适用\n\n- 把细胞级 p 值当作患者/样本级显著性或组间因果证据。\n- 分组与批次、供体或处理完全混杂时，DE 结果不可解释为处理效应。\n- 只用 p 值排序、不看效应量和阳性比例；或反复改分组直到得到想要的基因。\n\n## 输入\n\n已标准化/注释的 Seurat 对象、`group_by` 列、`group1`/`group2`（不指定 group2 时与其余细胞比较）。每个基因×对比一行结果；细胞身份和分组必须在对象中可追踪。\n\n## 怎么做\n\n1. 先明确对比：哪两组、参照是谁、是否只看正向 marker；把分组和批次写进分析记录。\n2. 在课题环境检查数据是否为 log-normalized；按需设置 `test.use`、`only.pos`、`fc.threshold`、`min.pct`。\n3. 运行 `RunDEtest`，从 `tools$DEtest_custom$AllMarkers_<test>` 取表；检查 gene、group1/2、avg_log2FC、p_val_adj、pct.1/2。\n4. 用效应量和阳性比例筛选，不只用 p 值；对关键结论做 pseudobulk/样本级敏感性分析。\n5. 把筛选规则和完整表一起保存；富集分析的输入基因列表要能追溯到这里。\n\n## 代码\n\n入口 `methods/differential-expression/code/analysis.R:run_differential_expression(srt, bundle, parameters)`，封装 SCP `RunDEtest`，统计逻辑未改。2026-10-23 在 `pancreas_sub` 全数据、`Ductal` vs `Endocrine`、wilcox 上实际调用；封装与上游 `AllMarkers_wilcox` 表一致。scope 仅软件调用，不代表这些基因在真实研究中显著或可重复。\n\n输出对象是 Seurat；DE 表在 `result$result@tools$DEtest_custom$AllMarkers_wilcox`，不是直接 CSV。页面不把对象存在当成科学结论。\n\n## 输出\n\n`AllMarkers_<test>` 为 data.frame，一行一个 gene×对比，含 `gene`、`group1`、`group2`、`avg_log2FC`、`p_val`、`p_val_adj`、`pct.1`、`pct.2` 等列。可另导出为 CSV；出图模板读取的是整理后的 `render-dotplot-long` 或 `render-de-results`，不是这个原始对象。\n\n## 知识关联检查\n\n2026-10-23 检查了气泡点图和火山图模板。DE marker 可整理为 group×feature 的平均表达/阳性比例，或 gene×effect/p 值的火山图输入；两者均为 adaptable，模板不重算 DE。没有 direct：模板不读 Seurat tools 槽。细胞级 p 值不能直接标注为样本级显著性，图注需说明检验层级。\n\n## 使用记录\n\n2026-10-23：在隔离 R 环境用 `pancreas_sub` 实际运行并与上游表比较；未做真实课题的 pseudobulk 或样本级推断。\n\n<!-- user:start -->\n<!-- user:end -->\n",
    "implementation_status": [
      {
        "id": "scp-detest",
        "title": "SCP RunDEtest 封装",
        "state": "verified",
        "scope": "实际调用 SCP RunDEtest：pancreas_sub 全数据，Ductal vs Endocrine，wilcox；比较封装与上游 AllMarkers 表。"
      }
    ],
    "backlinks": [
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
        "path": "methods/scp-de-enrichment-dynamic.md",
        "title": "单细胞差异表达、基因集富集与动态特征",
        "type": "method"
      },
      {
        "path": "templates/2026-10-22-scp-example__fig01-volcano--volcano.md",
        "title": "差异表达火山图",
        "type": "template"
      },
      {
        "path": "interfaces/render-de-results.md",
        "title": "差异表达结果表",
        "type": "interface"
      },
      {
        "path": "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot.md",
        "title": "细胞类型 × 基因气泡点图",
        "type": "template"
      },
      {
        "path": "interfaces/render-dotplot-long.md",
        "title": "细胞类型 × 基因点图表",
        "type": "interface"
      }
    ],
    "gallery": null,
    "reuse": null,
    "input_contract": null,
    "figure_refs": [
      "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot.md",
      "templates/2026-10-22-scp-example__fig01-volcano--volcano.md"
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
        "method": "methods/differential-expression.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot.md",
        "method_title": "差异表达分析",
        "figure_title": "细胞类型 × 基因气泡点图",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "DE 选出的 marker 可整理成 group/feature/avg_expression/pct_expressed，复用气泡点图；模板不重算 DE。",
        "prerequisites": [
          "avg_expression 与 pct_expressed 由表达矩阵按组计算，不能用 avg_log2FC 代替。",
          "group/feature 顺序由课题给出；target_group 只用于排序。"
        ],
        "adaptation": "导出 render-dotplot-long.csv（group, feature, avg_expression, pct_expressed, target_group）。",
        "evidence": [
          "methods/differential-expression.md#输出",
          "methods/scp-de-enrichment-dynamic.md#知识关联检查",
          "methods/scp-de-enrichment-dynamic.md#输出",
          "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot/spec.json",
          "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot/verify/verify.json"
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
        "method": "methods/differential-expression.md",
        "figure": "templates/2026-10-22-scp-example__fig01-volcano--volcano.md",
        "method_title": "差异表达分析",
        "figure_title": "差异表达火山图",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "DE 表可整理成 render-de-results，火山图模板消费该表；模板不重跑检验。",
        "prerequisites": [
          "group1 单一；pct_1/pct_2 为 0–1；p_val_adj >0；gene 组内唯一。",
          "模板不重跑 DE 或 p 值校正；阈值由 style 显式给出。"
        ],
        "adaptation": "从 AllMarkers 表导出 gene、avg_log2FC、p_val_adj 等字段到 render-de-results。",
        "evidence": [
          "methods/differential-expression.md#输出",
          "methods/scp-de-enrichment-dynamic.md#知识关联检查",
          "methods/scp-de-enrichment-dynamic.md#输出",
          "templates/2026-10-22-scp-example__fig01-volcano--volcano/spec.json",
          "templates/2026-10-22-scp-example__fig01-volcano--volcano/verify/verify.json"
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
    "path": "methods/trajectory-inference.md",
    "meta": {
      "type": "method",
      "id": "trajectory-inference",
      "title": "拟时序与轨迹推断",
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
      "purposes": [
        "轨迹与动态分析"
      ],
      "summary": "在低维嵌入上连接细胞群，推断 lineage 与 pseudotime；轨迹是模型假设，不是真实时间。",
      "data_contract": {
        "input": "Seurat 对象 + 稳定低维嵌入 + cluster 标签 + 起点/终点；cluster 是轨迹状态，不是细胞类型断言。",
        "output": "每细胞 lineage pseudotime 与 BranchID（Seurat metadata）；曲线对象在 tools。"
      },
      "implementations": [
        {
          "id": "scp-slingshot",
          "title": "SCP RunSlingshot 封装",
          "language": "R",
          "entrypoint": "code/analysis.R:run_trajectory_inference",
          "dependencies": [
            "Seurat",
            "slingshot"
          ],
          "verification": "verification/scp-slingshot.json"
        }
      ],
      "keywords": [
        "Slingshot",
        "pseudotime",
        "lineage",
        "Monocle",
        "PAGA",
        "轨迹",
        "SCP"
      ],
      "figure_relations": [
        {
          "figure": "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap",
          "compatibility": "adaptable",
          "reason": "轨迹分组/lineage 标签可作为 UMAP 着色变量；现有模板不画 lineage 曲线。",
          "prerequisites": [
            "UMAP 坐标与 group 来自同一对象；cell_id 一致。",
            "group 为 cluster/lineage 分组；group_levels 由课题给出。"
          ],
          "adaptation": "导出 render-umap-groups.csv（group=cluster/lineage）；曲线需另建模板。",
          "evidence": [
            "methods/trajectory-inference.md#输出",
            "methods/scp-trajectory-velocity.md#知识关联检查",
            "methods/scp-trajectory-velocity.md#输出",
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
          "figure": "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap",
          "compatibility": "adaptable",
          "reason": "pseudotime 可作为 feature 长表画在 UMAP 上；模板不拟合轨迹。",
          "prerequisites": [
            "值与 UMAP 坐标来自同一细胞集合；cell_id 一致。",
            "value 的含义/单位明确；无 NA。"
          ],
          "adaptation": "导出 render-umap-feature-long.csv（feature=pseudotime, value=Lineage1）。",
          "evidence": [
            "methods/trajectory-inference.md#输出",
            "methods/scp-trajectory-velocity.md#知识关联检查",
            "methods/scp-trajectory-velocity.md#输出",
            "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap/spec.json",
            "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap/verify/verify.json"
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
          "reason": "pseudotime 按 cluster/lineage 分组的分布可用分组小提琴展示；模板不做轨迹或检验。",
          "prerequisites": [
            "同一 pseudotime/lineage 定义；celltype/group 标签一致。",
            "p/mean/SD 若展示，由分析阶段预计算；细胞级 p 不能当样本级推断。"
          ],
          "adaptation": "导出 render-grouped-values.csv（celltype/group, value=pseudotime）。",
          "evidence": [
            "methods/trajectory-inference.md#输出",
            "methods/scp-trajectory-velocity.md#知识关联检查",
            "methods/scp-trajectory-velocity.md#输出",
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
    "body": "# 拟时序与轨迹推断\n\n<!-- facts:start -->\n- 来源：https://github.com/zhanghao-njmu/scp（b9b0eb7a7bf2c2c4b2262e73e09d7ebd515c7da0）\n- 许可证：GPL-3\n- 引用：SCP: https://github.com/zhanghao-njmu/scp (commit b9b0eb7a7bf2c2c4b2262e73e09d7ebd515c7da0)\n- 标签：单细胞分析\n- 分析用途：轨迹与动态分析\n- 输入接口：未声明\n- 输出接口：未声明\n- 接口结构匹配的图（仅结构候选，未核实语义）：暂无\n- 接口结构匹配的下一步方法（仅结构候选，未核实语义）：暂无\n- 代码模板：[methods/trajectory-inference/code/analysis.R](/files/wiki/methods/trajectory-inference/code/analysis.R)\n\n- 方法配图关系（语义审查）：\n  - [[templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap|CNS 细胞类型 UMAP]]（ready）：需要适配（adaptable）；调用验证：not_run；范围：2026-10-23 只核对方法输出与模板接口；未运行真实课题分析→出图。\n    - 依据：轨迹分组/lineage 标签可作为 UMAP 着色变量；现有模板不画 lineage 曲线。；前提：UMAP 坐标与 group 来自同一对象；cell_id 一致。；group 为 cluster/lineage 分组；group_levels 由课题给出。；适配：导出 render-umap-groups.csv（group=cluster/lineage）；曲线需另建模板。\n    - 关系证据：methods/trajectory-inference.md#输出；methods/scp-trajectory-velocity.md#知识关联检查；methods/scp-trajectory-velocity.md#输出；templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap/spec.json；templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap/verify/verify.json；运行证据：无\n  - [[templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap|marker 特征 UMAP 小多图]]（ready）：需要适配（adaptable）；调用验证：not_run；范围：2026-10-23 只核对方法输出与模板接口；未运行真实课题分析→出图。\n    - 依据：pseudotime 可作为 feature 长表画在 UMAP 上；模板不拟合轨迹。；前提：值与 UMAP 坐标来自同一细胞集合；cell_id 一致。；value 的含义/单位明确；无 NA。；适配：导出 render-umap-feature-long.csv（feature=pseudotime, value=Lineage1）。\n    - 关系证据：methods/trajectory-inference.md#输出；methods/scp-trajectory-velocity.md#知识关联检查；methods/scp-trajectory-velocity.md#输出；templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap/spec.json；templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap/verify/verify.json；运行证据：无\n  - [[templates/2026-10-22-glaucoma-scrna__fig06-pathway-violin--violin|分组小提琴图（含统计标注）]]（ready）：需要适配（adaptable）；调用验证：not_run；范围：2026-10-23 只核对方法输出与模板接口；未运行真实课题分析→出图。\n    - 依据：pseudotime 按 cluster/lineage 分组的分布可用分组小提琴展示；模板不做轨迹或检验。；前提：同一 pseudotime/lineage 定义；celltype/group 标签一致。；p/mean/SD 若展示，由分析阶段预计算；细胞级 p 不能当样本级推断。；适配：导出 render-grouped-values.csv（celltype/group, value=pseudotime）。\n    - 关系证据：methods/trajectory-inference.md#输出；methods/scp-trajectory-velocity.md#知识关联检查；methods/scp-trajectory-velocity.md#输出；templates/2026-10-22-glaucoma-scrna__fig06-pathway-violin--violin/spec.json；templates/2026-10-22-glaucoma-scrna__fig06-pathway-violin--violin/verify/verify.json；运行证据：无\n<!-- facts:end -->\n\n## 用途\n\n在细胞群之间建立有序轨迹，给每个细胞一个 lineage 上的 pseudotime 和分支标签，用于描述分化、激活或损伤修复等连续过程。输出是模型推断的顺序，不是采样时间。\n\n## 原理与选择\n\nSlingshot 在嵌入空间对 cluster 建最小生成树，再拟合 lineage 曲线；Monocle2/3、PAGA、Palantir、WOT 等是其他实现，假设和输入不同。SCP `RunSlingshot` 封装 slingshot，需指定 `group.by`、`reduction`、`dims` 和可选起点/终点。轨迹方向依赖起点和 cluster 结构，换嵌入/分辨率可能改变结论。\n\n\n\n## 来源与实现选择\n\n| 策略 / 实现 | 原始来源 | 输入与目标 | 本库状态 |\n|---|---|---|---|\n| SCP `RunSlingshot` | [[methods/scp-trajectory-velocity]]；`SCP-local/R/SCP-analysis.R` | 嵌入 + cluster + 起点/终点；lineage/pseudotime | 已封装并 verified（80 细胞，CellType 分组） |\n| Monocle2 / Monocle3 / PAGA / Palantir / WOT | 同上 | 不同轨迹模型与输入 | 未实现、未运行；不能与 Slingshot 互换 |\n| 青光眼课题 | `source/` 中未发现独立轨迹脚本 | — | 不声称有独立课题实现 |\n## 适用\n\n- 有连续过程假设、相对稳定的嵌入和 cluster，且 cluster 能覆盖轨迹上的状态。\n- 起点/终点有生物学依据或明确说明是探索性选择。\n- 用于生成 pseudotime 供动态特征分析，而不是单独证明分化方向。\n\n## 不适用\n\n- 离散细胞类型、没有连续过程假设，或 cluster 主要由批次/技术因素驱动。\n- 把 pseudotime 当真实时间、把 lineage 当因果谱系；没有谱系追踪时不能证明祖先关系。\n- 只选一个起点/嵌入报告结果，不做敏感性分析。\n\n## 输入\n\nSeurat 对象、`group.by` cluster 列、`reduction`（如 UMAP/PCA）、`dims`、可选 `start`/`end`。每个细胞一行 pseudotime；cluster 标签和嵌入必须同源。\n\n## 怎么做\n\n1. 先确定轨迹假设和 cluster 分辨率；检查嵌入是否被批次主导。\n2. 指定起点/终点（或有依据地探索），运行 Slingshot；保留 lineage 曲线和 BranchID。\n3. 检查 pseudotime 与关键 marker 的单调性、lineage 是否覆盖预期状态；换嵌入/分辨率做敏感性分析。\n4. 轨迹结果再交给动态特征分析；不要用 pseudotime 反向证明 cluster 注释正确。\n5. Monocle2/3、PAGA 等分支未在本页实现，不能因 Slingshot 通过就声称支持。\n\n## 代码\n\n入口 `methods/trajectory-inference/code/analysis.R:run_trajectory_inference(srt, bundle, parameters)`，封装 SCP `RunSlingshot`。2026-10-23 在 `pancreas_sub` 80 细胞、CellType 分组、UMAP 1:2 上实际调用；封装与上游 `Lineage1`、`BranchID` 一致。scope 仅软件调用，起点和 cluster 结构是示例，不代表真实轨迹。\n\nMonocle2/Monocle3/PAGA 等分支未运行。\n\n## 输出\n\nSeurat metadata 增加 `Lineage1`（pseudotime）和 `BranchID`；`result@tools` 保存 Slingshot 对象/曲线。可导出 `cell_id, pseudotime, branch, umap_1, umap_2` 供模板；本页不强制 CSV。\n\n## 知识关联检查\n\n2026-10-23 检查了 UMAP 分组、特征 UMAP 和分组小提琴模板。cluster/lineage 可着色 UMAP，pseudotime 可作 feature 或分组分布；均为 adaptable。现有模板不画 lineage 曲线/箭头，不能把普通 UMAP 分组图当作轨迹图。动态特征分析见 [[methods/dynamic-feature-analysis]]。\n\n## 使用记录\n\n2026-10-23：在隔离 R 环境用 `pancreas_sub` 80 细胞实际运行 Slingshot 并与上游比较；未做真实轨迹方向论证。\n\n<!-- user:start -->\n<!-- user:end -->\n",
    "implementation_status": [
      {
        "id": "scp-slingshot",
        "title": "SCP RunSlingshot 封装",
        "state": "verified",
        "scope": "实际调用 SCP RunSlingshot：pancreas_sub 80 细胞，CellType 分组，UMAP 1:2；比较 pseudotime 与 BranchID。"
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
        "path": "interfaces/render-umap-feature-long.md",
        "title": "UMAP 坐标与特征长表",
        "type": "interface"
      },
      {
        "path": "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap.md",
        "title": "marker 特征 UMAP 小多图",
        "type": "template"
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
        "path": "methods/scp-trajectory-velocity.md",
        "title": "单细胞轨迹推断与 RNA 速度",
        "type": "method"
      },
      {
        "path": "interfaces/render-group-summaries.md",
        "title": "预计算分组分布摘要表",
        "type": "interface"
      }
    ],
    "gallery": null,
    "reuse": null,
    "input_contract": null,
    "figure_refs": [
      "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap.md",
      "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap.md",
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
        "method": "methods/trajectory-inference.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap.md",
        "method_title": "拟时序与轨迹推断",
        "figure_title": "CNS 细胞类型 UMAP",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "轨迹分组/lineage 标签可作为 UMAP 着色变量；现有模板不画 lineage 曲线。",
        "prerequisites": [
          "UMAP 坐标与 group 来自同一对象；cell_id 一致。",
          "group 为 cluster/lineage 分组；group_levels 由课题给出。"
        ],
        "adaptation": "导出 render-umap-groups.csv（group=cluster/lineage）；曲线需另建模板。",
        "evidence": [
          "methods/trajectory-inference.md#输出",
          "methods/scp-trajectory-velocity.md#知识关联检查",
          "methods/scp-trajectory-velocity.md#输出",
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
        "method": "methods/trajectory-inference.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap.md",
        "method_title": "拟时序与轨迹推断",
        "figure_title": "marker 特征 UMAP 小多图",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "pseudotime 可作为 feature 长表画在 UMAP 上；模板不拟合轨迹。",
        "prerequisites": [
          "值与 UMAP 坐标来自同一细胞集合；cell_id 一致。",
          "value 的含义/单位明确；无 NA。"
        ],
        "adaptation": "导出 render-umap-feature-long.csv（feature=pseudotime, value=Lineage1）。",
        "evidence": [
          "methods/trajectory-inference.md#输出",
          "methods/scp-trajectory-velocity.md#知识关联检查",
          "methods/scp-trajectory-velocity.md#输出",
          "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap/spec.json",
          "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap/verify/verify.json"
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
        "method": "methods/trajectory-inference.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig06-pathway-violin--violin.md",
        "method_title": "拟时序与轨迹推断",
        "figure_title": "分组小提琴图（含统计标注）",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "pseudotime 按 cluster/lineage 分组的分布可用分组小提琴展示；模板不做轨迹或检验。",
        "prerequisites": [
          "同一 pseudotime/lineage 定义；celltype/group 标签一致。",
          "p/mean/SD 若展示，由分析阶段预计算；细胞级 p 不能当样本级推断。"
        ],
        "adaptation": "导出 render-grouped-values.csv（celltype/group, value=pseudotime）。",
        "evidence": [
          "methods/trajectory-inference.md#输出",
          "methods/scp-trajectory-velocity.md#知识关联检查",
          "methods/scp-trajectory-velocity.md#输出",
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
    "path": "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot.md",
    "meta": {
      "type": "template",
      "id": "2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot",
      "title": "细胞类型 × 基因气泡点图",
      "status": "ready",
      "layouts": [
        "2026-10-22-glaucoma-scrna__fig03-topjournal-bubble"
      ],
      "panels": [
        "A"
      ],
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "chart_types": [
        "dotplot"
      ],
      "favorite": false,
      "keywords": [
        "GSE251716",
        "dotplot"
      ]
    },
    "body": "# 细胞类型 × 基因气泡点图\r\n\r\n![[templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot/preview.png]]\r\n\r\n<!-- facts:start -->\n- 来源版式：[[layouts/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble|顶刊样式气泡点图（GSE251716）]]\n- 面板（来源版式）：A\n- 语言：r\n- 标签：单细胞分析\n- 图型：[[chart-types/dotplot]]\n- 输入接口：[[interfaces/render-dotplot-long|细胞类型 × 基因点图表]]\n- 接口结构匹配的分析方法（仅结构候选，未核实语义）：暂无\n\n- 方法配图关系（语义审查）：\n  - [[methods/cell-type-annotation|细胞类型注释]]（draft）：需要适配（adaptable）；调用验证：not_run；范围：2026-10-23 只核对方法输出与模板接口；未运行真实课题分析→出图。\n    - 依据：预测类型的 marker 平均表达/阳性比例可整理成点图，检查注释是否合理；模板不重算统计。；前提：avg_expression 与 pct_expressed 由表达矩阵按预测标签计算；缩放方式说明。；group/feature 顺序由课题给出；target_group 只用于排序。；适配：导出 render-dotplot-long.csv（group, feature, avg_expression, pct_expressed, target_group）。\n    - 关系证据：methods/cell-type-annotation.md#输出；methods/scp-annotation-projection.md#知识关联检查；methods/scp-annotation-projection.md#输出；templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot/spec.json；templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot/verify/verify.json；运行证据：无\n  - [[methods/differential-expression|差异表达分析]]（draft）：需要适配（adaptable）；调用验证：not_run；范围：2026-10-23 只核对方法输出与模板接口；未运行真实课题分析→出图。\n    - 依据：DE 选出的 marker 可整理成 group/feature/avg_expression/pct_expressed，复用气泡点图；模板不重算 DE。；前提：avg_expression 与 pct_expressed 由表达矩阵按组计算，不能用 avg_log2FC 代替。；group/feature 顺序由课题给出；target_group 只用于排序。；适配：导出 render-dotplot-long.csv（group, feature, avg_expression, pct_expressed, target_group）。\n    - 关系证据：methods/differential-expression.md#输出；methods/scp-de-enrichment-dynamic.md#知识关联检查；methods/scp-de-enrichment-dynamic.md#输出；templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot/spec.json；templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot/verify/verify.json；运行证据：无\n<!-- facts:end -->\r\n\r\n## 适用\r\n\r\n细胞类型 × 基因的气泡点图：输入 `group, feature, avg_expression, pct_expressed`，可选 `target_group` 用于基因排序。画灰底黑框、底部细胞类型色块、旋转 x 标签、斜体基因名、Relative Expression 渐变和 Percentage Expressed 大小图例。组数由 `style.x_levels` 控制（示例固定 9 组），换数据必须覆盖或置空；基因数由数据识别。\r\n\r\n## 不适用\r\n\r\n没有平均表达/阳性比例表；需要差异检验或显著性标注；基因数过多导致 y 标签不可读；不能把颜色或气泡大小当统计显著性。`avg_expression` 若是 scaled data，必须与原始表达区分并在图注说明。\r\n\r\n## 知识关联检查\r\n\r\n2026-10-22 查过 [[methods/scrna-marker-annotation|M2 注释]] 和点图图型页。M2 产出 `render-dotplot-long` 所需的 group/feature/avg/pct 表；同一数据也可画 SCpubr 点图，但作者确认只保留本顶刊气泡样式。示例为合成数据；方法侧关系已登记为 adaptable；模板只读接口表，不重算分析。\r\n\r\n## 数据要求\r\n\n### dotplot（render-dotplot-long.csv）：细胞类型 × 基因的平均表达和阳性比例；target_group 仅用于基因排序 [[interfaces/render-dotplot-long|细胞类型 × 基因点图表]]\n\n| 列 | 类型 | 必需 | 含义 |\n|---|---|---|---|\n| group | str | 必需 | 细胞类型或分组；点图 x 轴 |\n| feature | str | 必需 | 基因/marker 名称；点图 y 轴 |\n| avg_expression | float | 必需 | 该组该基因的平均表达；缩放方式由课题说明 |\n| pct_expressed | float | 必需 | 该组该基因的阳性细胞百分比，0–100 |\n| target_group | str | 可选 | 该基因对应的目标细胞类型，可为空；仅用于基因排序 |\n\n### 可覆盖的 style\n\n- `font_family`：`\"sans\"`\n- `dpi`：`192`\n- `width_in`：`6`\n- `height_in`：`12`\n- `sizing`：`{\"mode\": \"adaptive\", \"base_width_in\": 3.0, \"per_x_in\": 0.3, \"base_height_in\": 2.0, \"per_y_in\": 0.2, \"min_width_in\": 6, \"min_height_in\": 5, \"base_label_chars\": 10, \"per_label_char_in\": 0.1, \"aspect\": null, \"max_width_in\": null, \"max_height_in\": null}`\n- `x_levels`：`[\"Muller_Glia\", \"Rod_Photoreceptor\", \"Bipolar\", \"Cone_Photoreceptor\", \"RGC_like\", \"RPE\", \"Vascular_Pericyte\", \"Amacrine\", \"Amacrine_Horizontal_like\"]`\n- `expr_limits`：`[0, 1]`\n- `expr_breaks`：`[0, 0.25, 0.5, 0.75, 1]`\n- `size_limits`：`[0, 100]`\n- `size_breaks`：`[25, 50, 75]`\n- `size_range`：`[1.2, 7.0]`\n- `panel_fill`：`\"#F2F2F2\"`\n- `italic_y`：`true`\n- `expr_palette`：`[\"#083B6F\", \"#3B8FC2\", \"#D9EEF4\", \"#F6F3EA\", \"#F07C56\", \"#8A001F\"]`\n- `x_colors`：`[\"#F2A000\", \"#37B7AE\", \"#13A25B\", \"#F0DB35\", \"#1C9AD6\", \"#D65F00\", \"#AEB0B4\", \"#C98CB7\", \"#E64B35\"]`\n\n## 使用记录\r\n\r\n2026-10-22 建模板；R 4.3.1 回放通过；preview 已生成。\r\n2026-10-22 作者确认模板可用；补 adaptive sizing，固定示例用 `example/style.json` 的 fixed 模式；`check-entry --record` 已更新。\r\n\r\n<!-- user:start -->\r\n<!-- user:end -->\r\n",
    "implementation_status": [],
    "backlinks": [
      {
        "path": "chart-types/dotplot.md",
        "title": "dotplot",
        "type": "chart-type"
      },
      {
        "path": "methods/differential-expression.md",
        "title": "差异表达分析",
        "type": "method"
      },
      {
        "path": "interfaces/render-dotplot-long.md",
        "title": "细胞类型 × 基因点图表",
        "type": "interface"
      },
      {
        "path": "methods/cell-type-annotation.md",
        "title": "细胞类型注释",
        "type": "method"
      },
      {
        "path": "layouts/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble.md",
        "title": "顶刊样式气泡点图（GSE251716）",
        "type": "layout"
      }
    ],
    "gallery": null,
    "reuse": {
      "sizing_declared": true,
      "mode": "adaptive",
      "profile": null
    },
    "input_contract": {
      "bindings": true,
      "tables": [
        {
          "key": "dotplot",
          "interface": "render-dotplot-long",
          "description": "细胞类型 × 基因的平均表达和阳性比例；target_group 仅用于基因排序",
          "required": true,
          "columns": [
            {
              "name": "group",
              "type": "str",
              "description": "细胞类型或分组；点图 x 轴",
              "required": true
            },
            {
              "name": "feature",
              "type": "str",
              "description": "基因/marker 名称；点图 y 轴",
              "required": true
            },
            {
              "name": "avg_expression",
              "type": "float",
              "description": "该组该基因的平均表达；缩放方式由课题说明",
              "required": true
            },
            {
              "name": "pct_expressed",
              "type": "float",
              "description": "该组该基因的阳性细胞百分比，0–100",
              "required": true
            },
            {
              "name": "target_group",
              "type": "str",
              "description": "该基因对应的目标细胞类型，可为空；仅用于基因排序",
              "required": false
            }
          ]
        }
      ]
    },
    "figure_refs": [],
    "preview": {
      "url": "/files/wiki/templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot/preview.png",
      "kind": "replay",
      "label": "模板回放"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "可用",
      "reason": "已确认可用；当前笔记与回放完整。",
      "templates": []
    },
    "relations": [
      {
        "method": "methods/cell-type-annotation.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot.md",
        "method_title": "细胞类型注释",
        "figure_title": "细胞类型 × 基因气泡点图",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "预测类型的 marker 平均表达/阳性比例可整理成点图，检查注释是否合理；模板不重算统计。",
        "prerequisites": [
          "avg_expression 与 pct_expressed 由表达矩阵按预测标签计算；缩放方式说明。",
          "group/feature 顺序由课题给出；target_group 只用于排序。"
        ],
        "adaptation": "导出 render-dotplot-long.csv（group, feature, avg_expression, pct_expressed, target_group）。",
        "evidence": [
          "methods/cell-type-annotation.md#输出",
          "methods/scp-annotation-projection.md#知识关联检查",
          "methods/scp-annotation-projection.md#输出",
          "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot/spec.json",
          "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot/verify/verify.json"
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
        "method": "methods/differential-expression.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot.md",
        "method_title": "差异表达分析",
        "figure_title": "细胞类型 × 基因气泡点图",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "DE 选出的 marker 可整理成 group/feature/avg_expression/pct_expressed，复用气泡点图；模板不重算 DE。",
        "prerequisites": [
          "avg_expression 与 pct_expressed 由表达矩阵按组计算，不能用 avg_log2FC 代替。",
          "group/feature 顺序由课题给出；target_group 只用于排序。"
        ],
        "adaptation": "导出 render-dotplot-long.csv（group, feature, avg_expression, pct_expressed, target_group）。",
        "evidence": [
          "methods/differential-expression.md#输出",
          "methods/scp-de-enrichment-dynamic.md#知识关联检查",
          "methods/scp-de-enrichment-dynamic.md#输出",
          "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot/spec.json",
          "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot/verify/verify.json"
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
    "path": "templates/2026-10-22-scp-example__fig09-bar--bar.md",
    "meta": {
      "type": "template",
      "id": "2026-10-22-scp-example__fig09-bar--bar",
      "title": "分组计数柱图",
      "status": "ready",
      "layouts": [
        "2026-10-22-scp-example__fig09-bar"
      ],
      "panels": [
        "A"
      ],
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "chart_types": [
        "bar"
      ],
      "favorite": false
    },
    "body": "# 分组计数柱图\n\n![[templates/2026-10-22-scp-example__fig09-bar--bar/preview.png]]\n\n<!-- facts:start -->\n- 来源版式：[[layouts/2026-10-22-scp-example__fig09-bar|分组计数柱图]]\n- 面板（来源版式）：A\n- 语言：r\n- 标签：单细胞分析\n- 图型：[[chart-types/bar]]\n- 输入接口：[[interfaces/render-cell-metadata|细胞级分组元数据表]]\n- 接口结构匹配的分析方法（仅结构候选，未核实语义）：暂无\n\n- 方法配图关系（语义审查）：\n  - 暂无已记录关系；接口或标签相同不代表语义已核实。\n<!-- facts:end -->\n\n## 适用\n\n读取 `render-cell-metadata` 的逐细胞分类表（每个细胞一行，`group` 与 `stat` 两个标签），在模板内按原 `StatPlot()` 的 `xtabs` 步骤计数，再复现 `plot_type = \"bar\"` 分支：`geom_col(width = 0.8, colour = \"black\", alpha = ...)`、stack/dodge 定位、柱内计数或百分比标签、`scale_fill_manual`、`theme_scp`。示例为 `pancreas_sub` 的 CellType × Phase，`stat_type = \"count\"`、默认 stack、`label = TRUE`、8×6 in @150 dpi。\n\n绘图核心来自 SCP v0.5.6（commit `b9b0eb7a7bf2c2c4b2262e73e09d7ebd515c7da0`，GPL >= 3）`StatPlot()` 的 bar 分支。组数 `n_group`、类别数 `n_stat` 与最长标签从数据读取，不写死示例的 5 组 × 3 类；`position`、`stat_type`、`label`、`flip` 由 style 显式给出。固定示例输出与画廊 source 逐字节一致（SHA256 `d9375658…`）；PNG 与 SVG 一致，PDF 仅尾部压缩流有差异（页面内容相同）。\n\n## 不适用\n\n- 只画 bar 单 panel；不能把 pie/rose/trend/area/dot 等其他 `CellStatPlot` 图型混进同一模板。\n- 只展示计数或组内比例，不替代统计检验；柱高不是效应量，误差棒/显著性需另配。\n- 输入必须逐细胞一行，`cell` 唯一；`group`/`stat` 的 NA 不是真实类别，当前 levels 检查在计数前拒绝 NA（`NA_stat` 不能保留 NA 水平）。\n- `group`/`stat` 的顺序由 `group_levels`/`stat_levels` 显式给出；显式 levels 漏掉任一观察值会报错。示例 CSV 的出现顺序与因子顺序不同，必须保留 style 中的 levels，否则轴序/图例会变。\n- 组数/类别数多或标签长时按 `sizing` 增宽/增高；设置 `max_width_in`/`max_height_in` 后超限会停止并报所需尺寸，不缩小字体、不隐藏类别。\n- 示例数据 `pancreas_sub` 不是病例/对照队列，不能据此作生物学结论。\n- 参考 panel（Example-2 第 2 格）与记录的 source 同为上游默认 stack；第 1 格是 dodge 变体，数据与配色相同但几何不同。模板通过 `position = \"dodge\"` 也支持后者，并已与上游逐字节对照。\n\n## 知识关联检查\n\n日期 2026-10-22；查过 methods（`scp-standard-workflow`、`scp-annotation-projection`、`scp-cellqc-doublet`、`scp-de-enrichment-dynamic`、`scp-visualization-interface`）与 templates（fig03 pie、fig04 rose、fig05 trend、fig06 area、fig07 dot、本模板）。\n\n- 候选方法：[[methods/scp-standard-workflow]] 与 [[methods/scp-annotation-projection]] 产出 celltype/cluster；[[methods/scp-cellqc-doublet]] 可提供 QC Pass/Fail；[[methods/scp-de-enrichment-dynamic]] 的 DE 结果可提供分组。它们需要在课题内把元数据整理成 `render-cell-metadata` 表（cell, group, stat），模板不重算分析。\n- 一方法多图：同一份细胞级元数据可驱动 bar/pie/rose/trend/area/dot 六种结构编码；bar 用共同零基线比较绝对量，pie/rose 用角度/半径编码比例，trend/area 用堆叠段沿有序轴展示构成，dot 用面积编码比例；它们不互相替代。\n- 一图多方法：任何产生「每个细胞一个 group 与一个 stat」标签的方法都可驱动本模板，不限于 SCP。\n- 来源 layout：[[layouts/2026-10-22-scp-example__fig09-bar|分组计数柱图来源]]；模板从 A panel 拆出。\n- 关系状态：已登记到 [[methods/scp-visualization-interface]] 的 `adaptable` 关系；模板读取 `render-cell-metadata`，验证状态 example。\n- 验证范围：固定 8×6@150 与画廊 source 逐字节一致；stack/dodge/count/percent/label/flip 六个变体与上游逐字节一致；adaptive 2×2 与 12×5、35 字符标签通过；`max_width_in`/`max_height_in` 正确拒绝；输入不变、异目录复制通过；PNG/SVG 一致，PDF 尾部压缩流不同。未验证 Seurat 元数据→CSV→模板的课题流水线，也不证明统计有效。\n\n## 数据要求\n\n### metadata（render-cell-metadata.csv）：每个细胞一行的 group/stat 元数据；模板按原 StatPlot 的 xtabs 计数步骤聚合成 group x stat 表 [[interfaces/render-cell-metadata|细胞级分组元数据表]]\n\n| 列 | 类型 | 必需 | 含义 |\n|---|---|---|---|\n| cell | str | 可选 | 细胞标识；同一图内唯一 |\n| group | str | 必需 | 分组或条件；每个细胞一个值；x 轴 |\n| stat | str | 必需 | 被统计的类别；每个细胞一个值；堆叠/扇区系列 |\n\n### 可覆盖的 style\n\n- `plot_type`：`\"bar\"`\n- `stat_type`：`\"count\"`\n- `position`：`\"stack\"`\n- `group_col`：`\"group\"`\n- `stat_col`：`\"stat\"`\n- `group_levels`：`[\"Ductal\", \"Ngn3 low EP\", \"Ngn3 high EP\", \"Pre-endocrine\", \"Endocrine\"]`\n- `stat_levels`：`[\"G1\", \"S\", \"G2M\"]`\n- `palette`：`\"Paired\"`\n- `palcolor`：`null`\n- `alpha`：`1`\n- `bg_col`：`null`\n- `bg_palette`：`\"Paired\"`\n- `bg_palcolor`：`null`\n- `bg_alpha`：`0.2`\n- `flip`：`false`\n- `label`：`true`\n- `label_size`：`3.5`\n- `label_fg`：`\"black\"`\n- `label_bg`：`\"white\"`\n- `label_bg_r`：`0.1`\n- `legend_title`：`\"Phase:\"`\n- `legend_position`：`\"right\"`\n- `legend_direction`：`\"vertical\"`\n- `xlab`：`\"CellType\"`\n- `ylab`：`\"Count\"`\n- `NA_stat`：`true`\n- `seed`：`11`\n- `dpi`：`150`\n- `width_in`：`8`\n- `height_in`：`6`\n- `sizing`：`{\"mode\": \"adaptive\", \"base_in\": 5.0, \"per_group_in\": 0.7, \"per_stat_in\": 0.25, \"base_height_in\": 4.6, \"min_width_in\": 6.0, \"min_height_in\": 3.5, \"base_label_chars\": 14, \"per_label_char_in\": 0.1, \"aspect\": 0.75, \"max_width_in\": null, \"max_height_in\": null}`\n\n## 使用记录\n\n2026-10-22 从 layout `2026-10-22-scp-example__fig09-bar` 的 A panel 拆出；原生调用 `CellStatPlot(pancreas_sub, stat.by = \"Phase\", group.by = \"CellType\", stat_type = \"count\", plot_type = \"bar\", label = TRUE)`。表半 `scp_stat_table()` 的 15 行计数表与上游 `p0$data` 在列、因子水平、行序和数值上一致（仅多 5 个 provenance 属性）；绘图半保留 bar 分支。固定 8×6@150 与画廊 source 逐字节一致，`verify-template` exit 0；方法关系登记在 [[methods/scp-visualization-interface]]。\n\n<!-- user:start -->\n<!-- user:end -->\n",
    "implementation_status": [],
    "backlinks": [
      {
        "path": "chart-types/bar.md",
        "title": "bar",
        "type": "chart-type"
      },
      {
        "path": "layouts/2026-10-22-scp-example__fig09-bar.md",
        "title": "分组计数柱图",
        "type": "layout"
      },
      {
        "path": "interfaces/render-cell-metadata.md",
        "title": "细胞级分组元数据表",
        "type": "interface"
      }
    ],
    "gallery": null,
    "reuse": {
      "sizing_declared": true,
      "mode": "adaptive",
      "profile": null
    },
    "input_contract": {
      "bindings": true,
      "tables": [
        {
          "key": "metadata",
          "interface": "render-cell-metadata",
          "description": "每个细胞一行的 group/stat 元数据；模板按原 StatPlot 的 xtabs 计数步骤聚合成 group x stat 表",
          "required": true,
          "columns": [
            {
              "name": "cell",
              "type": "str",
              "description": "细胞标识；同一图内唯一",
              "required": false
            },
            {
              "name": "group",
              "type": "str",
              "description": "分组或条件；每个细胞一个值；x 轴",
              "required": true
            },
            {
              "name": "stat",
              "type": "str",
              "description": "被统计的类别；每个细胞一个值；堆叠/扇区系列",
              "required": true
            }
          ]
        }
      ]
    },
    "figure_refs": [],
    "preview": {
      "url": "/files/wiki/templates/2026-10-22-scp-example__fig09-bar--bar/preview.png",
      "kind": "replay",
      "label": "模板回放"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "可用",
      "reason": "已确认可用；当前笔记与回放完整。",
      "templates": []
    },
    "relations": []
  }
];

export const REAL_PAGES: any[] = [
  {
    "path": "chart-types/area.md",
    "meta": {
      "type": "chart-type",
      "slug": "area",
      "title": "area"
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "chart-types/bar.md",
    "meta": {
      "type": "chart-type",
      "slug": "bar",
      "title": "bar"
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "chart-types/beeswarm.md",
    "meta": {
      "type": "chart-type",
      "slug": "beeswarm",
      "title": "beeswarm"
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "chart-types/boxplot.md",
    "meta": {
      "type": "chart-type",
      "slug": "boxplot",
      "title": "boxplot"
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "chart-types/chord.md",
    "meta": {
      "type": "chart-type",
      "slug": "chord",
      "title": "chord"
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "chart-types/density-scatter.md",
    "meta": {
      "type": "chart-type",
      "slug": "density-scatter",
      "title": "density-scatter"
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "chart-types/dot.md",
    "meta": {
      "type": "chart-type",
      "slug": "dot",
      "title": "dot"
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "chart-types/dotplot.md",
    "meta": {
      "type": "chart-type",
      "slug": "dotplot",
      "title": "dotplot"
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "chart-types/errorbar.md",
    "meta": {
      "type": "chart-type",
      "slug": "errorbar",
      "title": "errorbar"
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "chart-types/heatmap.md",
    "meta": {
      "type": "chart-type",
      "slug": "heatmap",
      "title": "heatmap"
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "chart-types/pie.md",
    "meta": {
      "type": "chart-type",
      "slug": "pie",
      "title": "pie"
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "chart-types/radial-bar.md",
    "meta": {
      "type": "chart-type",
      "slug": "radial-bar",
      "title": "radial-bar"
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "chart-types/ridge.md",
    "meta": {
      "type": "chart-type",
      "slug": "ridge",
      "title": "ridge"
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "chart-types/ring.md",
    "meta": {
      "type": "chart-type",
      "slug": "ring",
      "title": "ring"
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "chart-types/rose.md",
    "meta": {
      "type": "chart-type",
      "slug": "rose",
      "title": "rose"
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "chart-types/sankey.md",
    "meta": {
      "type": "chart-type",
      "slug": "sankey",
      "title": "sankey"
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "chart-types/stacked-bar-flow.md",
    "meta": {
      "type": "chart-type",
      "slug": "stacked-bar-flow",
      "title": "stacked-bar-flow"
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "chart-types/trend.md",
    "meta": {
      "type": "chart-type",
      "slug": "trend",
      "title": "trend"
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "chart-types/umap.md",
    "meta": {
      "type": "chart-type",
      "slug": "umap",
      "title": "umap"
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "chart-types/upset.md",
    "meta": {
      "type": "chart-type",
      "slug": "upset",
      "title": "upset"
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "chart-types/venn.md",
    "meta": {
      "type": "chart-type",
      "slug": "venn",
      "title": "venn"
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "chart-types/violin.md",
    "meta": {
      "type": "chart-type",
      "slug": "violin",
      "title": "violin"
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "chart-types/volcano.md",
    "meta": {
      "type": "chart-type",
      "slug": "volcano",
      "title": "volcano"
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "interfaces/regression-fold-metrics.md",
    "meta": {
      "type": "interface",
      "slug": "regression-fold-metrics",
      "title": "回归模型逐折评估指标表",
      "columns": {
        "model": {
          "type": "str",
          "description": "完整模型流程名称"
        },
        "repeat": {
          "type": "int",
          "description": "重复编号"
        },
        "fold": {
          "type": "int",
          "description": "验证折或随机划分编号"
        },
        "n_test": {
          "type": "int",
          "description": "本折验证样本数，不是独立重复次数"
        },
        "RMSE": {
          "type": "float",
          "description": "本折均方根误差，原目标单位"
        },
        "MAE": {
          "type": "float",
          "description": "本折平均绝对误差，原目标单位"
        },
        "R2": {
          "type": "float",
          "description": "1-SSE/SST；常量真实结局或不足2例时缺失"
        },
        "r": {
          "type": "float",
          "description": "Pearson相关；任一变量常量或不足2例时缺失"
        },
        "split_design": {
          "type": "str",
          "description": "原样保留上游验证设计"
        }
      }
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "interfaces/regression-predictions.md",
    "meta": {
      "type": "interface",
      "slug": "regression-predictions",
      "title": "回归模型逐样本验证预测表",
      "columns": {
        "sample_id": {
          "type": "str",
          "description": "课题内唯一的样本标识；重复测量仍需另有受试者分组"
        },
        "model": {
          "type": "str",
          "description": "模型或完整训练流程名称"
        },
        "repeat": {
          "type": "int",
          "description": "重采样重复编号，从1起；普通K折为1"
        },
        "fold": {
          "type": "int",
          "description": "本次重复内的验证折或划分编号，从1起"
        },
        "y_true": {
          "type": "float",
          "description": "该验证样本的真实连续结局"
        },
        "y_pred": {
          "type": "float",
          "description": "未使用该验证样本训练或调参的流程给出的预测"
        },
        "split_design": {
          "type": "str",
          "description": "kfold/repeated_kfold/group_kfold/time_series/repeated_holdout"
        }
      }
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "interfaces/render-box-summaries.md",
    "meta": {
      "type": "interface",
      "slug": "render-box-summaries",
      "title": "预计算分组箱线与均值表",
      "columns": {
        "category": {
          "type": "str",
          "description": "每类恰好一行；不能缺组"
        },
        "q1": {
          "type": "float",
          "description": "上游给定第一四分位数"
        },
        "median": {
          "type": "float",
          "description": "上游给定中位数"
        },
        "q3": {
          "type": "float",
          "description": "上游给定第三四分位数"
        },
        "low": {
          "type": "float",
          "description": "上游给定下须；规则由分析说明"
        },
        "high": {
          "type": "float",
          "description": "上游给定上须；规则由分析说明"
        },
        "mean": {
          "type": "float",
          "description": "上游给定均值；须与真实点使用同一数据来源"
        }
      }
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "interfaces/render-category-points.md",
    "meta": {
      "type": "interface",
      "slug": "render-category-points",
      "title": "分组数值与显式抖动表",
      "columns": {
        "category": {
          "type": "str",
          "description": "类别标识；与摘要表一一对应"
        },
        "value": {
          "type": "float",
          "description": "逐条结果值；采样单位/量纲由课题说明"
        },
        "jitter": {
          "type": "float",
          "description": "显式横向展示偏移，绝对值须小于0.5；不参与统计"
        }
      }
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "interfaces/render-cell-feature-values.md",
    "meta": {
      "type": "interface",
      "slug": "render-cell-feature-values",
      "title": "细胞级特征值长表",
      "columns": {
        "cell": {
          "type": "str",
          "description": "细胞标识；同一特征内唯一；每个细胞每个特征一行"
        },
        "feature": {
          "type": "str",
          "description": "基因或特征标识；一张图可含多个特征"
        },
        "value": {
          "type": "float",
          "description": "该细胞该特征的数值（表达/得分）；单位由上游定义"
        },
        "group": {
          "type": "str",
          "description": "密度分组的类别；每个细胞一个值"
        },
        "feature_order": {
          "type": "int",
          "description": "特征面板/行顺序；从 1 起"
        },
        "group_order": {
          "type": "int",
          "description": "组（山脊线）顺序；从 1 起"
        }
      }
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "interfaces/render-cell-linkage.md",
    "meta": {
      "type": "interface",
      "slug": "render-cell-linkage",
      "title": "细胞级多维流向长表",
      "columns": {
        "cell": {
          "type": "str",
          "description": "细胞标识；同一维度内唯一；每个细胞每个维度一行"
        },
        "dimension": {
          "type": "str",
          "description": "维度/注释名；如 CellType、Phase；显式顺序沿流向排列"
        },
        "category": {
          "type": "str",
          "description": "该维度下的类别；每个细胞每个维度一个值"
        },
        "dimension_order": {
          "type": "int",
          "description": "维度顺序；从 1 起；决定桑基/和弦的左右次序"
        }
      }
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "interfaces/render-cell-membership.md",
    "meta": {
      "type": "interface",
      "slug": "render-cell-membership",
      "title": "细胞级集合成员表",
      "columns": {
        "cell": {
          "type": "str",
          "description": "细胞标识；同一集合内唯一；每个细胞每个集合一行"
        },
        "set": {
          "type": "str",
          "description": "集合名；如 Ductal、G1S；顺序显式给出"
        },
        "member": {
          "type": "int",
          "description": "是否属于该集合；只接受 0 或 1"
        }
      }
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "interfaces/render-cell-metadata.md",
    "meta": {
      "type": "interface",
      "slug": "render-cell-metadata",
      "title": "细胞级分组元数据表",
      "columns": {
        "cell": {
          "type": "str",
          "description": "细胞标识；同一图内唯一",
          "required": false
        },
        "group": {
          "type": "str",
          "description": "分组或条件；每个细胞一个值；x 轴"
        },
        "stat": {
          "type": "str",
          "description": "被统计的类别；每个细胞一个值；堆叠/扇区系列"
        }
      }
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "interfaces/render-cell-proportions.md",
    "meta": {
      "type": "interface",
      "slug": "render-cell-proportions",
      "title": "细胞类型比例表",
      "columns": {
        "group": {
          "type": "str",
          "description": "样本或条件分组；x 轴"
        },
        "celltype": {
          "type": "str",
          "description": "细胞类型；堆叠/流带类别"
        },
        "proportion": {
          "type": "float",
          "description": "该组内该细胞类型的比例；每组应归一化到 1"
        }
      }
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "interfaces/render-correlation-heatmap.md",
    "meta": {
      "type": "interface",
      "slug": "render-correlation-heatmap",
      "title": "相似度矩阵长表",
      "columns": {
        "row": {
          "type": "str",
          "description": "行标签（查询细胞/组）；与 column 组成完整矩阵"
        },
        "column": {
          "type": "str",
          "description": "列标签（参考细胞/组）；与 row 组成完整矩阵"
        },
        "similarity": {
          "type": "float",
          "description": "已计算的相似度；模板不重算"
        },
        "row_group": {
          "type": "str",
          "description": "行分组注释；每个 row 一个值"
        },
        "column_group": {
          "type": "str",
          "description": "列分组注释；每个 column 一个值"
        },
        "row_order": {
          "type": "int",
          "description": "行顺序；从 1 起"
        },
        "column_order": {
          "type": "int",
          "description": "列顺序；从 1 起"
        }
      }
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "interfaces/render-de-results.md",
    "meta": {
      "type": "interface",
      "slug": "render-de-results",
      "title": "差异表达结果表",
      "columns": {
        "gene": {
          "type": "str",
          "description": "基因/特征标识；同一 group1 内唯一"
        },
        "group1": {
          "type": "str",
          "description": "比较组；一个模板文件只放一个 group1"
        },
        "group2": {
          "type": "str",
          "description": "参照组或 rest"
        },
        "avg_log2FC": {
          "type": "float",
          "description": "group1 相对 group2 的 log2 倍数变化"
        },
        "pct_1": {
          "type": "float",
          "description": "group1 中阳性细胞比例，0–1"
        },
        "pct_2": {
          "type": "float",
          "description": "group2 中阳性细胞比例，0–1"
        },
        "p_val": {
          "type": "float",
          "description": "原始 p 值"
        },
        "p_val_adj": {
          "type": "float",
          "description": "多重校正后的 p 值"
        }
      }
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "interfaces/render-dotplot-long.md",
    "meta": {
      "type": "interface",
      "slug": "render-dotplot-long",
      "title": "细胞类型 × 基因点图表",
      "columns": {
        "group": {
          "type": "str",
          "description": "细胞类型或分组；点图 x 轴"
        },
        "feature": {
          "type": "str",
          "description": "基因/marker 名称；点图 y 轴"
        },
        "avg_expression": {
          "type": "float",
          "description": "该组该基因的平均表达；缩放方式由课题说明"
        },
        "pct_expressed": {
          "type": "float",
          "description": "该组该基因的阳性细胞百分比，0–100"
        },
        "target_group": {
          "type": "str",
          "description": "该基因对应的目标细胞类型，可为空；仅用于基因排序",
          "required": false
        }
      }
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "interfaces/render-feature-heatmap.md",
    "meta": {
      "type": "interface",
      "slug": "render-feature-heatmap",
      "title": "特征×细胞表达矩阵长表",
      "columns": {
        "matrix": {
          "type": "str",
          "description": "矩阵/分组变量名；同一图可含多个 matrix"
        },
        "feature": {
          "type": "str",
          "description": "基因或特征标识；同一矩阵内唯一"
        },
        "cell": {
          "type": "str",
          "description": "细胞标识；同一矩阵内唯一；每个细胞每个特征一行"
        },
        "group": {
          "type": "str",
          "description": "细胞所属分组（列注释）；每个细胞一个值"
        },
        "value": {
          "type": "float",
          "description": "已按 exp_method 变换的表达值（如 zscore）；模板不重算变换"
        },
        "matrix_order": {
          "type": "int",
          "description": "矩阵显示顺序；从 1 起"
        },
        "feature_order": {
          "type": "int",
          "description": "特征行顺序；从 1 起；各矩阵需一致"
        },
        "cell_order": {
          "type": "int",
          "description": "细胞列顺序；从 1 起"
        },
        "group_order": {
          "type": "int",
          "description": "分组图例/注释顺序；从 1 起"
        }
      }
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "interfaces/render-group-heatmap.md",
    "meta": {
      "type": "interface",
      "slug": "render-group-heatmap",
      "title": "分组热图长表",
      "columns": {
        "matrix": {
          "type": "str",
          "description": "分组变量/矩阵名，如 CellType；同一 feature 可出现在多个矩阵"
        },
        "feature": {
          "type": "str",
          "description": "基因或元数据特征标识；同一矩阵内唯一"
        },
        "group": {
          "type": "str",
          "description": "列分组/细胞类型；同一矩阵内唯一"
        },
        "value": {
          "type": "float",
          "description": "聚合后的表达值，已按 exp_method 变换（如 zscore）"
        },
        "percent": {
          "type": "float",
          "description": "该组中 value > exp_cutoff 的细胞比例，0–1"
        },
        "matrix_order": {
          "type": "int",
          "description": "矩阵显示顺序，从 1 起"
        },
        "group_order": {
          "type": "int",
          "description": "同一矩阵内列顺序，从 1 起"
        },
        "feature_order": {
          "type": "int",
          "description": "行顺序，从 1 起；同一 feature 在各矩阵保持一致"
        }
      }
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "interfaces/render-group-summaries.md",
    "meta": {
      "type": "interface",
      "slug": "render-group-summaries",
      "title": "预计算分组分布摘要表",
      "columns": {
        "celltype": {
          "type": "str",
          "description": "细胞类型或类别；与值表一一对应"
        },
        "group": {
          "type": "str",
          "description": "比较组；与值表一一对应"
        },
        "mean": {
          "type": "float",
          "description": "上游给定的组内均值"
        },
        "sd": {
          "type": "float",
          "description": "上游给定的组内标准差"
        },
        "p_label": {
          "type": "str",
          "description": "上游给定的 p 值标签；模板不重算检验"
        },
        "p_y": {
          "type": "float",
          "description": "p 标签的 y 位置，由上游给定"
        },
        "mean_sd_label": {
          "type": "str",
          "description": "上游给定的 Mean/SD 文本标签"
        },
        "mean_y": {
          "type": "float",
          "description": "Mean/SD 标签的 y 位置，由上游给定"
        }
      }
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "interfaces/render-grouped-values.md",
    "meta": {
      "type": "interface",
      "slug": "render-grouped-values",
      "title": "分组细胞级数值表",
      "columns": {
        "celltype": {
          "type": "str",
          "description": "细胞类型或类别；x 轴"
        },
        "group": {
          "type": "str",
          "description": "比较组；用于小提琴/箱线/散点分组"
        },
        "value": {
          "type": "float",
          "description": "细胞级或样本级数值；采样单位由课题说明"
        }
      }
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "interfaces/render-marginal-bars.md",
    "meta": {
      "type": "interface",
      "slug": "render-marginal-bars",
      "title": "预计算边缘分布条表",
      "columns": {
        "orientation": {
          "type": "str",
          "description": "top或right，分别对应横轴或纵轴边缘"
        },
        "position": {
          "type": "float",
          "description": "条形中心坐标，单位与对应轴一致"
        },
        "height": {
          "type": "float",
          "description": "预先计算的非负条高，计数/密度含义由上游声明"
        },
        "width": {
          "type": "float",
          "description": "预先计算的正条宽，单位与对应轴一致"
        }
      }
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "interfaces/render-scatter-rgb.md",
    "meta": {
      "type": "interface",
      "slug": "render-scatter-rgb",
      "title": "配对数值散点的预设颜色表",
      "columns": {
        "x": {
          "type": "float",
          "description": "横轴数值；量纲由课题说明"
        },
        "y": {
          "type": "float",
          "description": "配对纵轴数值；1:1线仅在同量纲时使用"
        },
        "red": {
          "type": "int",
          "description": "预先给定的红通道0..255"
        },
        "green": {
          "type": "int",
          "description": "预先给定的绿通道0..255"
        },
        "blue": {
          "type": "int",
          "description": "预先给定的蓝通道0..255"
        }
      }
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "interfaces/render-umap-feature-long.md",
    "meta": {
      "type": "interface",
      "slug": "render-umap-feature-long",
      "title": "UMAP 坐标与特征长表",
      "columns": {
        "cell_id": {
          "type": "str",
          "description": "细胞标识；同一 feature 内唯一，唯一键为 (cell_id, feature)"
        },
        "umap_1": {
          "type": "float",
          "description": "UMAP 第一维坐标"
        },
        "umap_2": {
          "type": "float",
          "description": "UMAP 第二维坐标"
        },
        "group": {
          "type": "str",
          "description": "细胞类型或分组；用于背景点和目标群轮廓"
        },
        "feature": {
          "type": "str",
          "description": "基因/marker 名称"
        },
        "value": {
          "type": "float",
          "description": "该细胞在该 feature 上的表达值；0 表示不画前景点"
        }
      }
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "interfaces/render-umap-groups.md",
    "meta": {
      "type": "interface",
      "slug": "render-umap-groups",
      "title": "UMAP 坐标与分组表",
      "columns": {
        "cell_id": {
          "type": "str",
          "description": "细胞标识；同一图内唯一"
        },
        "umap_1": {
          "type": "float",
          "description": "UMAP 第一维坐标"
        },
        "umap_2": {
          "type": "float",
          "description": "UMAP 第二维坐标"
        },
        "group": {
          "type": "str",
          "description": "分组或细胞类型；用于着色、包络和标签"
        }
      }
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "interfaces/shap-samples.md",
    "meta": {
      "type": "interface",
      "slug": "shap-samples",
      "title": "SHAP 逐样本值表",
      "columns": {
        "feature": {
          "type": "str",
          "description": "特征名"
        },
        "shap": {
          "type": "float",
          "description": "该样本该特征的带符号 SHAP 值"
        },
        "feature_value": {
          "type": "float",
          "description": "该特征取值在解释样本内按最小–最大缩放到 0–1，用于着色；常量特征取 0"
        }
      }
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "interfaces/shap-summary.md",
    "meta": {
      "type": "interface",
      "slug": "shap-summary",
      "title": "SHAP 特征贡献汇总表",
      "columns": {
        "feature": {
          "type": "str",
          "description": "特征名"
        },
        "shap": {
          "type": "float",
          "description": "该特征在解释样本上的平均绝对 SHAP 值"
        },
        "percent": {
          "type": "float",
          "description": "平均绝对 SHAP 占筛选前全部特征的平均绝对 SHAP 之和的百分比，0–100"
        }
      }
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": null,
    "workflow": null,
    "relations": []
  },
  {
    "path": "layouts/2026-08-17-shap-feature-mechanism__fig01-shap-a-f.md",
    "meta": {
      "type": "layout",
      "id": "2026-08-17-shap-feature-mechanism__fig01-shap-a-f",
      "title": "双模型 SHAP 特征贡献组图",
      "status": "archived",
      "gallery_entry": "2026-08-17-shap-feature-mechanism/figures/fig01-shap-a-f",
      "gallery_version": 1,
      "language": "python",
      "panels": {
        "A": "bar",
        "B": "beeswarm",
        "C": "radial-bar",
        "D": "bar",
        "E": "beeswarm",
        "F": "radial-bar"
      },
      "chart_types": [
        "bar",
        "beeswarm",
        "radial-bar"
      ],
      "templates": [
        "2026-08-17-shap-feature-mechanism__fig01-shap-a-f--bar",
        "2026-08-17-shap-feature-mechanism__fig01-shap-a-f--beeswarm",
        "2026-08-17-shap-feature-mechanism__fig01-shap-a-f--radial-bar"
      ],
      "template_panels": {
        "2026-08-17-shap-feature-mechanism__fig01-shap-a-f--bar": [
          "A",
          "D"
        ],
        "2026-08-17-shap-feature-mechanism__fig01-shap-a-f--beeswarm": [
          "B",
          "E"
        ],
        "2026-08-17-shap-feature-mechanism__fig01-shap-a-f--radial-bar": [
          "C",
          "F"
        ]
      },
      "favorite": false,
      "tags": [
        "机器学习",
        "模型解释与特征重要性",
        "化学信息与QSAR"
      ],
      "archived_from": "ready",
      "keywords": [
        "SHAP",
        "LightGBM",
        "CatBoost",
        "pLC50",
        "AR-DBP",
        "QSAR"
      ]
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/gallery/2026-08-17-shap-feature-mechanism/figures/fig01-shap-a-f/source/fig01.png",
      "kind": "source",
      "label": "来源 panel · 只读溯源"
    },
    "workflow": {
      "stage": "archived",
      "queue": null,
      "label": "已归档",
      "reason": "已归档，不进入待办。",
      "templates": []
    },
    "relations": []
  },
  {
    "path": "layouts/2026-10-19-regression-stability__fig01-density-grid.md",
    "meta": {
      "type": "layout",
      "id": "2026-10-19-regression-stability__fig01-density-grid",
      "title": "六模型验证预测密度散点组图（整图存档）",
      "status": "archived",
      "gallery_entry": "2026-10-19-regression-stability/figures/fig01-density-grid",
      "gallery_version": 1,
      "language": "python",
      "tags": [
        "机器学习",
        "实验统计"
      ],
      "panels": {
        "A": "density-scatter",
        "B": "density-scatter",
        "C": "density-scatter",
        "D": "density-scatter",
        "E": "density-scatter",
        "F": "density-scatter"
      },
      "chart_types": [
        "density-scatter"
      ],
      "templates": [],
      "template_panels": {},
      "favorite": false,
      "archived_from": "pending_template",
      "keywords": [
        "regression",
        "cross-validation",
        "回归评估",
        "模型比较",
        "折外预测"
      ]
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/gallery/2026-10-19-regression-stability/figures/fig01-density-grid/source/fig01.png",
      "kind": "source",
      "label": "来源 panel · 只读溯源"
    },
    "workflow": {
      "stage": "archived",
      "queue": null,
      "label": "已归档",
      "reason": "已归档，不进入待办。",
      "templates": []
    },
    "relations": []
  },
  {
    "path": "layouts/2026-10-19-regression-stability__fig02-metric-boxplots.md",
    "meta": {
      "type": "layout",
      "id": "2026-10-19-regression-stability__fig02-metric-boxplots",
      "title": "多模型 RMSE、R² 与 MAE 箱线组图（整图存档）",
      "status": "archived",
      "gallery_entry": "2026-10-19-regression-stability/figures/fig02-metric-boxplots",
      "gallery_version": 1,
      "language": "python",
      "tags": [
        "机器学习",
        "实验统计"
      ],
      "panels": {
        "A": "boxplot",
        "B": "boxplot",
        "C": "boxplot"
      },
      "chart_types": [
        "boxplot"
      ],
      "templates": [],
      "template_panels": {},
      "favorite": false,
      "archived_from": "pending_template",
      "keywords": [
        "regression",
        "cross-validation",
        "回归评估",
        "模型比较",
        "折外预测"
      ]
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/gallery/2026-10-19-regression-stability/figures/fig02-metric-boxplots/source/fig02.png",
      "kind": "source",
      "label": "来源 panel · 只读溯源"
    },
    "workflow": {
      "stage": "archived",
      "queue": null,
      "label": "已归档",
      "reason": "已归档，不进入待办。",
      "templates": []
    },
    "relations": []
  },
  {
    "path": "layouts/2026-10-19-regression-stability__fig03-density-panel.md",
    "meta": {
      "type": "layout",
      "id": "2026-10-19-regression-stability__fig03-density-panel",
      "title": "六模型验证预测：密度散点与边缘分布",
      "status": "pending_template",
      "gallery_entry": "2026-10-19-regression-stability/figures/fig03-density-panel",
      "gallery_version": 1,
      "language": "python",
      "tags": [
        "机器学习",
        "实验统计"
      ],
      "panels": {
        "A": "density-scatter"
      },
      "chart_types": [
        "density-scatter"
      ],
      "templates": [
        "2026-10-19-regression-stability__fig03-density-panel--density-scatter"
      ],
      "template_panels": {
        "2026-10-19-regression-stability__fig03-density-panel--density-scatter": [
          "A"
        ]
      },
      "favorite": false,
      "signedoff_version": 1,
      "keywords": [
        "regression",
        "cross-validation",
        "回归评估",
        "模型比较",
        "折外预测"
      ]
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/gallery/2026-10-19-regression-stability/figures/fig03-density-panel/source/fig03.png",
      "kind": "source",
      "label": "来源 panel · 只读溯源"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "模板已就绪",
      "reason": "选定 panel 已由可用模板完整覆盖，来源不再计入待办；不表示另做了来源版式回放。",
      "templates": [
        "templates/2026-10-19-regression-stability__fig03-density-panel--density-scatter.md"
      ]
    },
    "relations": []
  },
  {
    "path": "layouts/2026-10-19-regression-stability__fig04-boxplot-panel.md",
    "meta": {
      "type": "layout",
      "id": "2026-10-19-regression-stability__fig04-boxplot-panel",
      "title": "多模型逐折指标：箱线、散点与均值",
      "status": "pending_template",
      "gallery_entry": "2026-10-19-regression-stability/figures/fig04-boxplot-panel",
      "gallery_version": 1,
      "language": "python",
      "tags": [
        "机器学习",
        "实验统计"
      ],
      "panels": {
        "A": "boxplot"
      },
      "chart_types": [
        "boxplot"
      ],
      "templates": [
        "2026-10-19-regression-stability__fig04-boxplot-panel--boxplot"
      ],
      "template_panels": {
        "2026-10-19-regression-stability__fig04-boxplot-panel--boxplot": [
          "A"
        ]
      },
      "favorite": false,
      "signedoff_version": 1,
      "keywords": [
        "regression",
        "cross-validation",
        "回归评估",
        "模型比较",
        "折外预测"
      ]
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/gallery/2026-10-19-regression-stability/figures/fig04-boxplot-panel/source/fig04.png",
      "kind": "source",
      "label": "来源 panel · 只读溯源"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "模板已就绪",
      "reason": "选定 panel 已由可用模板完整覆盖，来源不再计入待办；不表示另做了来源版式回放。",
      "templates": [
        "templates/2026-10-19-regression-stability__fig04-boxplot-panel--boxplot.md"
      ]
    },
    "relations": []
  },
  {
    "path": "layouts/2026-10-22-glaucoma-scrna__fig01-cns-umap.md",
    "meta": {
      "type": "layout",
      "id": "2026-10-22-glaucoma-scrna__fig01-cns-umap",
      "title": "CNS 细胞类型 UMAP（GSE251716）",
      "status": "pending_template",
      "gallery_entry": "2026-10-22-glaucoma-scrna/figures/fig01-cns-umap",
      "gallery_version": 1,
      "signedoff_version": 1,
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "panels": {
        "A": "umap"
      },
      "chart_types": [
        "umap"
      ],
      "templates": [
        "2026-10-22-glaucoma-scrna__fig01-cns-umap--umap"
      ],
      "template_panels": {
        "2026-10-22-glaucoma-scrna__fig01-cns-umap--umap": [
          "A"
        ]
      },
      "favorite": false,
      "keywords": [
        "GSE251716"
      ]
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/gallery/2026-10-22-glaucoma-scrna/figures/fig01-cns-umap/source/fig01.png",
      "kind": "source",
      "label": "来源 panel · 只读溯源"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "模板已就绪",
      "reason": "选定 panel 已由可用模板完整覆盖，来源不再计入待办；不表示另做了来源版式回放。",
      "templates": [
        "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap.md"
      ]
    },
    "relations": []
  },
  {
    "path": "layouts/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap.md",
    "meta": {
      "type": "layout",
      "id": "2026-10-22-glaucoma-scrna__fig02-marker-feature-umap",
      "title": "marker 特征 UMAP 小多图（GSE251716）",
      "status": "pending_template",
      "gallery_entry": "2026-10-22-glaucoma-scrna/figures/fig02-marker-feature-umap",
      "gallery_version": 1,
      "signedoff_version": 1,
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "panels": {
        "A": "umap"
      },
      "chart_types": [
        "umap"
      ],
      "templates": [
        "2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap"
      ],
      "template_panels": {
        "2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap": [
          "A"
        ]
      },
      "favorite": false,
      "keywords": [
        "GSE251716",
        "marker"
      ]
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/gallery/2026-10-22-glaucoma-scrna/figures/fig02-marker-feature-umap/source/fig02.png",
      "kind": "source",
      "label": "来源 panel · 只读溯源"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "模板已就绪",
      "reason": "选定 panel 已由可用模板完整覆盖，来源不再计入待办；不表示另做了来源版式回放。",
      "templates": [
        "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap.md"
      ]
    },
    "relations": []
  },
  {
    "path": "layouts/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble.md",
    "meta": {
      "type": "layout",
      "id": "2026-10-22-glaucoma-scrna__fig03-topjournal-bubble",
      "title": "顶刊样式气泡点图（GSE251716）",
      "status": "pending_template",
      "gallery_entry": "2026-10-22-glaucoma-scrna/figures/fig03-topjournal-bubble",
      "gallery_version": 1,
      "signedoff_version": 1,
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "panels": {
        "A": "dotplot"
      },
      "chart_types": [
        "dotplot"
      ],
      "templates": [
        "2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot"
      ],
      "template_panels": {
        "2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot": [
          "A"
        ]
      },
      "favorite": false,
      "keywords": [
        "GSE251716",
        "dotplot"
      ]
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/gallery/2026-10-22-glaucoma-scrna/figures/fig03-topjournal-bubble/source/fig03.png",
      "kind": "source",
      "label": "来源 panel · 只读溯源"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "模板已就绪",
      "reason": "选定 panel 已由可用模板完整覆盖，来源不再计入待办；不表示另做了来源版式回放。",
      "templates": [
        "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot.md"
      ]
    },
    "relations": []
  },
  {
    "path": "layouts/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow.md",
    "meta": {
      "type": "layout",
      "id": "2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow",
      "title": "细胞比例堆叠与流带（GSE251716）",
      "status": "pending_template",
      "gallery_entry": "2026-10-22-glaucoma-scrna/figures/fig04-cell-proportion-flow",
      "gallery_version": 1,
      "signedoff_version": 1,
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "panels": {
        "A": "stacked-bar-flow"
      },
      "chart_types": [
        "stacked-bar-flow"
      ],
      "templates": [
        "2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow"
      ],
      "template_panels": {
        "2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow": [
          "A"
        ]
      },
      "favorite": false,
      "keywords": [
        "GSE251716",
        "proportion"
      ]
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/gallery/2026-10-22-glaucoma-scrna/figures/fig04-cell-proportion-flow/source/fig04.png",
      "kind": "source",
      "label": "来源 panel · 只读溯源"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "模板已就绪",
      "reason": "选定 panel 已由可用模板完整覆盖，来源不再计入待办；不表示另做了来源版式回放。",
      "templates": [
        "templates/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow.md"
      ]
    },
    "relations": []
  },
  {
    "path": "layouts/2026-10-22-glaucoma-scrna__fig06-pathway-violin.md",
    "meta": {
      "type": "layout",
      "id": "2026-10-22-glaucoma-scrna__fig06-pathway-violin",
      "title": "分组小提琴与统计标注（GSE251716）",
      "status": "pending_template",
      "gallery_entry": "2026-10-22-glaucoma-scrna/figures/fig06-pathway-violin",
      "gallery_version": 1,
      "signedoff_version": 1,
      "language": "r",
      "tags": [
        "单细胞分析",
        "实验统计"
      ],
      "panels": {
        "A": "violin"
      },
      "chart_types": [
        "violin"
      ],
      "templates": [
        "2026-10-22-glaucoma-scrna__fig06-pathway-violin--violin"
      ],
      "template_panels": {
        "2026-10-22-glaucoma-scrna__fig06-pathway-violin--violin": [
          "A"
        ]
      },
      "favorite": false,
      "keywords": [
        "GSE251716",
        "pathway"
      ]
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/gallery/2026-10-22-glaucoma-scrna/figures/fig06-pathway-violin/source/fig06.png",
      "kind": "source",
      "label": "来源 panel · 只读溯源"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "模板已就绪",
      "reason": "选定 panel 已由可用模板完整覆盖，来源不再计入待办；不表示另做了来源版式回放。",
      "templates": [
        "templates/2026-10-22-glaucoma-scrna__fig06-pathway-violin--violin.md"
      ]
    },
    "relations": []
  },
  {
    "path": "layouts/2026-10-22-scp-example__fig01-volcano.md",
    "meta": {
      "type": "layout",
      "id": "2026-10-22-scp-example__fig01-volcano",
      "title": "火山图：Endocrine vs 其余细胞（SCP 示例）",
      "status": "pending_template",
      "gallery_entry": "2026-10-22-scp-example/figures/fig01-volcano",
      "gallery_version": 2,
      "signedoff_version": 2,
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "keywords": [
        "SCP",
        "pancreas_sub",
        "volcano",
        "DE"
      ],
      "panels": {
        "A": "volcano"
      },
      "chart_types": [
        "volcano"
      ],
      "templates": [
        "2026-10-22-scp-example__fig01-volcano--volcano"
      ],
      "template_panels": {
        "2026-10-22-scp-example__fig01-volcano--volcano": [
          "A"
        ]
      },
      "favorite": false
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/gallery/2026-10-22-scp-example/figures/fig01-volcano/source/fig01.png",
      "kind": "source",
      "label": "来源 panel · 只读溯源"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "模板已就绪",
      "reason": "选定 panel 已由可用模板完整覆盖，来源不再计入待办；不表示另做了来源版式回放。",
      "templates": [
        "templates/2026-10-22-scp-example__fig01-volcano--volcano.md"
      ]
    },
    "relations": []
  },
  {
    "path": "layouts/2026-10-22-scp-example__fig02-ring.md",
    "meta": {
      "type": "layout",
      "id": "2026-10-22-scp-example__fig02-ring",
      "title": "环形组成图（SCP 示例）",
      "status": "pending_template",
      "gallery_entry": "2026-10-22-scp-example/figures/fig02-ring",
      "gallery_version": 3,
      "signedoff_version": 3,
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "keywords": [
        "SCP",
        "pancreas_sub",
        "ring",
        "composition"
      ],
      "panels": {
        "A": "ring"
      },
      "chart_types": [
        "ring"
      ],
      "templates": [
        "2026-10-22-scp-example__fig02-ring--ring"
      ],
      "template_panels": {
        "2026-10-22-scp-example__fig02-ring--ring": [
          "A"
        ]
      },
      "favorite": false
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/gallery/2026-10-22-scp-example/figures/fig02-ring/source/fig02.png",
      "kind": "source",
      "label": "来源 panel · 只读溯源"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "模板已就绪",
      "reason": "选定 panel 已由可用模板完整覆盖，来源不再计入待办；不表示另做了来源版式回放。",
      "templates": [
        "templates/2026-10-22-scp-example__fig02-ring--ring.md"
      ]
    },
    "relations": []
  },
  {
    "path": "layouts/2026-10-22-scp-example__fig03-pie.md",
    "meta": {
      "type": "layout",
      "id": "2026-10-22-scp-example__fig03-pie",
      "title": "饼图组成（SCP 示例）",
      "status": "pending_template",
      "gallery_entry": "2026-10-22-scp-example/figures/fig03-pie",
      "gallery_version": 1,
      "signedoff_version": 1,
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "keywords": [
        "SCP",
        "pancreas_sub",
        "pie",
        "composition"
      ],
      "panels": {
        "A": "pie"
      },
      "chart_types": [
        "pie"
      ],
      "templates": [
        "2026-10-22-scp-example__fig03-pie--pie"
      ],
      "template_panels": {
        "2026-10-22-scp-example__fig03-pie--pie": [
          "A"
        ]
      },
      "favorite": false
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/gallery/2026-10-22-scp-example/figures/fig03-pie/source/fig03.png",
      "kind": "source",
      "label": "来源 panel · 只读溯源"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "模板已就绪",
      "reason": "选定 panel 已由可用模板完整覆盖，来源不再计入待办；不表示另做了来源版式回放。",
      "templates": [
        "templates/2026-10-22-scp-example__fig03-pie--pie.md"
      ]
    },
    "relations": []
  },
  {
    "path": "layouts/2026-10-22-scp-example__fig04-rose.md",
    "meta": {
      "type": "layout",
      "id": "2026-10-22-scp-example__fig04-rose",
      "title": "玫瑰图组成：计数 dodge（SCP 示例）",
      "status": "pending_template",
      "gallery_entry": "2026-10-22-scp-example/figures/fig04-rose",
      "gallery_version": 1,
      "signedoff_version": 1,
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "keywords": [
        "SCP",
        "pancreas_sub",
        "rose",
        "composition"
      ],
      "panels": {
        "A": "rose"
      },
      "chart_types": [
        "rose"
      ],
      "templates": [
        "2026-10-22-scp-example__fig04-rose--rose"
      ],
      "template_panels": {
        "2026-10-22-scp-example__fig04-rose--rose": [
          "A"
        ]
      },
      "favorite": false
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/gallery/2026-10-22-scp-example/figures/fig04-rose/source/fig04.png",
      "kind": "source",
      "label": "来源 panel · 只读溯源"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "模板已就绪",
      "reason": "选定 panel 已由可用模板完整覆盖，来源不再计入待办；不表示另做了来源版式回放。",
      "templates": [
        "templates/2026-10-22-scp-example__fig04-rose--rose.md"
      ]
    },
    "relations": []
  },
  {
    "path": "layouts/2026-10-22-scp-example__fig05-trend.md",
    "meta": {
      "type": "layout",
      "id": "2026-10-22-scp-example__fig05-trend",
      "title": "组成趋势图：计数（SCP 示例）",
      "status": "pending_template",
      "gallery_entry": "2026-10-22-scp-example/figures/fig05-trend",
      "gallery_version": 1,
      "signedoff_version": 1,
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "keywords": [
        "SCP",
        "pancreas_sub",
        "trend",
        "composition"
      ],
      "panels": {
        "A": "trend"
      },
      "chart_types": [
        "trend"
      ],
      "templates": [
        "2026-10-22-scp-example__fig05-trend--trend"
      ],
      "template_panels": {
        "2026-10-22-scp-example__fig05-trend--trend": [
          "A"
        ]
      },
      "favorite": false
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/gallery/2026-10-22-scp-example/figures/fig05-trend/source/fig05.png",
      "kind": "source",
      "label": "来源 panel · 只读溯源"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "模板已就绪",
      "reason": "选定 panel 已由可用模板完整覆盖，来源不再计入待办；不表示另做了来源版式回放。",
      "templates": [
        "templates/2026-10-22-scp-example__fig05-trend--trend.md"
      ]
    },
    "relations": []
  },
  {
    "path": "layouts/2026-10-22-scp-example__fig06-area.md",
    "meta": {
      "type": "layout",
      "id": "2026-10-22-scp-example__fig06-area",
      "title": "组成面积图：百分比（SCP 示例）",
      "status": "pending_template",
      "gallery_entry": "2026-10-22-scp-example/figures/fig06-area",
      "gallery_version": 1,
      "signedoff_version": 1,
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "keywords": [
        "SCP",
        "pancreas_sub",
        "area",
        "composition"
      ],
      "panels": {
        "A": "area"
      },
      "chart_types": [
        "area"
      ],
      "templates": [
        "2026-10-22-scp-example__fig06-area--area"
      ],
      "template_panels": {
        "2026-10-22-scp-example__fig06-area--area": [
          "A"
        ]
      },
      "favorite": false
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/gallery/2026-10-22-scp-example/figures/fig06-area/source/fig06.png",
      "kind": "source",
      "label": "来源 panel · 只读溯源"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "模板已就绪",
      "reason": "选定 panel 已由可用模板完整覆盖，来源不再计入待办；不表示另做了来源版式回放。",
      "templates": [
        "templates/2026-10-22-scp-example__fig06-area--area.md"
      ]
    },
    "relations": []
  },
  {
    "path": "layouts/2026-10-22-scp-example__fig07-dot.md",
    "meta": {
      "type": "layout",
      "id": "2026-10-22-scp-example__fig07-dot",
      "title": "组成点阵图（SCP 示例）",
      "status": "pending_template",
      "gallery_entry": "2026-10-22-scp-example/figures/fig07-dot",
      "gallery_version": 1,
      "signedoff_version": 1,
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "keywords": [
        "SCP",
        "pancreas_sub",
        "dot",
        "composition"
      ],
      "panels": {
        "A": "dot"
      },
      "chart_types": [
        "dot"
      ],
      "templates": [
        "2026-10-22-scp-example__fig07-dot--dot"
      ],
      "template_panels": {
        "2026-10-22-scp-example__fig07-dot--dot": [
          "A"
        ]
      },
      "favorite": false
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/gallery/2026-10-22-scp-example/figures/fig07-dot/source/fig07.png",
      "kind": "source",
      "label": "来源 panel · 只读溯源"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "模板已就绪",
      "reason": "选定 panel 已由可用模板完整覆盖，来源不再计入待办；不表示另做了来源版式回放。",
      "templates": [
        "templates/2026-10-22-scp-example__fig07-dot--dot.md"
      ]
    },
    "relations": []
  },
  {
    "path": "layouts/2026-10-22-scp-example__fig08-group-heatmap.md",
    "meta": {
      "type": "layout",
      "id": "2026-10-22-scp-example__fig08-group-heatmap",
      "title": "GroupHeatmap (CellType / SubCellType)",
      "status": "pending_template",
      "gallery_entry": "2026-10-22-scp-example/figures/fig08-group-heatmap",
      "gallery_version": 1,
      "signedoff_version": 1,
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "keywords": [
        "SCP",
        "pancreas_sub",
        "GroupHeatmap",
        "heatmap",
        "marker"
      ],
      "panels": {
        "A": "heatmap"
      },
      "chart_types": [
        "heatmap"
      ],
      "templates": [
        "2026-10-22-scp-example__fig08-group-heatmap--heatmap"
      ],
      "template_panels": {
        "2026-10-22-scp-example__fig08-group-heatmap--heatmap": [
          "A"
        ]
      },
      "favorite": false
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/gallery/2026-10-22-scp-example/figures/fig08-group-heatmap/source/fig08.png",
      "kind": "source",
      "label": "来源 panel · 只读溯源"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "模板已就绪",
      "reason": "选定 panel 已由可用模板完整覆盖，来源不再计入待办；不表示另做了来源版式回放。",
      "templates": [
        "templates/2026-10-22-scp-example__fig08-group-heatmap--heatmap.md"
      ]
    },
    "relations": []
  },
  {
    "path": "layouts/2026-10-22-scp-example__fig09-bar.md",
    "meta": {
      "type": "layout",
      "id": "2026-10-22-scp-example__fig09-bar",
      "title": "分组计数柱图",
      "status": "pending_template",
      "gallery_entry": "2026-10-22-scp-example/figures/fig09-bar",
      "gallery_version": 2,
      "signedoff_version": 2,
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "panels": {
        "A": "bar"
      },
      "chart_types": [
        "bar"
      ],
      "templates": [
        "2026-10-22-scp-example__fig09-bar--bar"
      ],
      "template_panels": {
        "2026-10-22-scp-example__fig09-bar--bar": [
          "A"
        ]
      },
      "favorite": false,
      "keywords": [
        "SCP",
        "pancreas_sub",
        "bar",
        "composition"
      ]
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/gallery/2026-10-22-scp-example/figures/fig09-bar/source/fig09.png",
      "kind": "source",
      "label": "来源 panel · 只读溯源"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "模板已就绪",
      "reason": "选定 panel 已由可用模板完整覆盖，来源不再计入待办；不表示另做了来源版式回放。",
      "templates": [
        "templates/2026-10-22-scp-example__fig09-bar--bar.md"
      ]
    },
    "relations": []
  },
  {
    "path": "layouts/2026-10-22-scp-example__fig10-sankey.md",
    "meta": {
      "type": "layout",
      "id": "2026-10-22-scp-example__fig10-sankey",
      "title": "分组流向桑基图",
      "status": "pending_template",
      "gallery_entry": "2026-10-22-scp-example/figures/fig10-sankey",
      "gallery_version": 1,
      "signedoff_version": 1,
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "panels": {
        "A": "sankey"
      },
      "chart_types": [
        "sankey"
      ],
      "templates": [
        "2026-10-22-scp-example__fig10-sankey--sankey"
      ],
      "template_panels": {
        "2026-10-22-scp-example__fig10-sankey--sankey": [
          "A"
        ]
      },
      "favorite": false,
      "keywords": [
        "SCP",
        "pancreas_sub",
        "sankey",
        "composition"
      ]
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/gallery/2026-10-22-scp-example/figures/fig10-sankey/source/fig10.png",
      "kind": "source",
      "label": "来源 panel · 只读溯源"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "模板已就绪",
      "reason": "选定 panel 已由可用模板完整覆盖，来源不再计入待办；不表示另做了来源版式回放。",
      "templates": [
        "templates/2026-10-22-scp-example__fig10-sankey--sankey.md"
      ]
    },
    "relations": []
  },
  {
    "path": "layouts/2026-10-22-scp-example__fig11-chord.md",
    "meta": {
      "type": "layout",
      "id": "2026-10-22-scp-example__fig11-chord",
      "title": "分组流向和弦图",
      "status": "pending_template",
      "gallery_entry": "2026-10-22-scp-example/figures/fig11-chord",
      "gallery_version": 1,
      "signedoff_version": 1,
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "panels": {
        "A": "chord"
      },
      "chart_types": [
        "chord"
      ],
      "templates": [
        "2026-10-22-scp-example__fig11-chord--chord"
      ],
      "template_panels": {
        "2026-10-22-scp-example__fig11-chord--chord": [
          "A"
        ]
      },
      "favorite": false,
      "keywords": [
        "SCP",
        "pancreas_sub",
        "chord",
        "composition"
      ]
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/gallery/2026-10-22-scp-example/figures/fig11-chord/source/fig11.png",
      "kind": "source",
      "label": "来源 panel · 只读溯源"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "模板已就绪",
      "reason": "选定 panel 已由可用模板完整覆盖，来源不再计入待办；不表示另做了来源版式回放。",
      "templates": [
        "templates/2026-10-22-scp-example__fig11-chord--chord.md"
      ]
    },
    "relations": []
  },
  {
    "path": "layouts/2026-10-22-scp-example__fig12-venn.md",
    "meta": {
      "type": "layout",
      "id": "2026-10-22-scp-example__fig12-venn",
      "title": "多集合交集维恩图",
      "status": "pending_template",
      "gallery_entry": "2026-10-22-scp-example/figures/fig12-venn",
      "gallery_version": 1,
      "signedoff_version": 1,
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "panels": {
        "A": "venn"
      },
      "chart_types": [
        "venn"
      ],
      "templates": [
        "2026-10-22-scp-example__fig12-venn--venn"
      ],
      "template_panels": {
        "2026-10-22-scp-example__fig12-venn--venn": [
          "A"
        ]
      },
      "favorite": false,
      "keywords": [
        "SCP",
        "pancreas_sub",
        "venn",
        "composition"
      ]
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/gallery/2026-10-22-scp-example/figures/fig12-venn/source/fig12.png",
      "kind": "source",
      "label": "来源 panel · 只读溯源"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "模板已就绪",
      "reason": "选定 panel 已由可用模板完整覆盖，来源不再计入待办；不表示另做了来源版式回放。",
      "templates": [
        "templates/2026-10-22-scp-example__fig12-venn--venn.md"
      ]
    },
    "relations": []
  },
  {
    "path": "layouts/2026-10-22-scp-example__fig13-upset.md",
    "meta": {
      "type": "layout",
      "id": "2026-10-22-scp-example__fig13-upset",
      "title": "多集合交集 UpSet 图",
      "status": "pending_template",
      "gallery_entry": "2026-10-22-scp-example/figures/fig13-upset",
      "gallery_version": 1,
      "signedoff_version": 1,
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "panels": {
        "A": "upset"
      },
      "chart_types": [
        "upset"
      ],
      "templates": [
        "2026-10-22-scp-example__fig13-upset--upset"
      ],
      "template_panels": {
        "2026-10-22-scp-example__fig13-upset--upset": [
          "A"
        ]
      },
      "favorite": false,
      "keywords": [
        "SCP",
        "pancreas_sub",
        "upset",
        "composition"
      ]
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/gallery/2026-10-22-scp-example/figures/fig13-upset/source/fig13.png",
      "kind": "source",
      "label": "来源 panel · 只读溯源"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "模板已就绪",
      "reason": "选定 panel 已由可用模板完整覆盖，来源不再计入待办；不表示另做了来源版式回放。",
      "templates": [
        "templates/2026-10-22-scp-example__fig13-upset--upset.md"
      ]
    },
    "relations": []
  },
  {
    "path": "layouts/2026-10-22-scp-example__fig14-feature-heatmap.md",
    "meta": {
      "type": "layout",
      "id": "2026-10-22-scp-example__fig14-feature-heatmap",
      "title": "特征表达热图",
      "status": "pending_template",
      "gallery_entry": "2026-10-22-scp-example/figures/fig14-feature-heatmap",
      "gallery_version": 1,
      "signedoff_version": 1,
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "panels": {
        "A": "heatmap"
      },
      "chart_types": [
        "heatmap"
      ],
      "templates": [
        "2026-10-22-scp-example__fig14-feature-heatmap--heatmap"
      ],
      "template_panels": {
        "2026-10-22-scp-example__fig14-feature-heatmap--heatmap": [
          "A"
        ]
      },
      "favorite": false,
      "keywords": [
        "SCP",
        "pancreas_sub",
        "heatmap",
        "feature"
      ]
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/gallery/2026-10-22-scp-example/figures/fig14-feature-heatmap/source/fig14.png",
      "kind": "source",
      "label": "来源 panel · 只读溯源"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "模板已就绪",
      "reason": "选定 panel 已由可用模板完整覆盖，来源不再计入待办；不表示另做了来源版式回放。",
      "templates": [
        "templates/2026-10-22-scp-example__fig14-feature-heatmap--heatmap.md"
      ]
    },
    "relations": []
  },
  {
    "path": "layouts/2026-10-22-scp-example__fig15-cell-cor-heatmap.md",
    "meta": {
      "type": "layout",
      "id": "2026-10-22-scp-example__fig15-cell-cor-heatmap",
      "title": "细胞相似度热图",
      "status": "pending_template",
      "gallery_entry": "2026-10-22-scp-example/figures/fig15-cell-cor-heatmap",
      "gallery_version": 1,
      "signedoff_version": 1,
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "panels": {
        "A": "heatmap"
      },
      "chart_types": [
        "heatmap"
      ],
      "templates": [
        "2026-10-22-scp-example__fig15-cell-cor-heatmap--heatmap"
      ],
      "template_panels": {
        "2026-10-22-scp-example__fig15-cell-cor-heatmap--heatmap": [
          "A"
        ]
      },
      "favorite": false,
      "keywords": [
        "SCP",
        "pancreas_sub",
        "heatmap",
        "similarity"
      ]
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/gallery/2026-10-22-scp-example/figures/fig15-cell-cor-heatmap/source/fig15.png",
      "kind": "source",
      "label": "来源 panel · 只读溯源"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "模板已就绪",
      "reason": "选定 panel 已由可用模板完整覆盖，来源不再计入待办；不表示另做了来源版式回放。",
      "templates": [
        "templates/2026-10-22-scp-example__fig15-cell-cor-heatmap--heatmap.md"
      ]
    },
    "relations": []
  },
  {
    "path": "layouts/2026-10-22-scp-example__fig16-cell-density.md",
    "meta": {
      "type": "layout",
      "id": "2026-10-22-scp-example__fig16-cell-density",
      "title": "分组表达密度图",
      "status": "pending_template",
      "gallery_entry": "2026-10-22-scp-example/figures/fig16-cell-density",
      "gallery_version": 1,
      "signedoff_version": 1,
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "panels": {
        "A": "ridge"
      },
      "chart_types": [
        "ridge"
      ],
      "templates": [
        "2026-10-22-scp-example__fig16-cell-density--ridge"
      ],
      "template_panels": {
        "2026-10-22-scp-example__fig16-cell-density--ridge": [
          "A"
        ]
      },
      "favorite": false,
      "keywords": [
        "SCP",
        "pancreas_sub",
        "ridge",
        "density"
      ]
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/gallery/2026-10-22-scp-example/figures/fig16-cell-density/source/fig16.png",
      "kind": "source",
      "label": "来源 panel · 只读溯源"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "模板已就绪",
      "reason": "选定 panel 已由可用模板完整覆盖，来源不再计入待办；不表示另做了来源版式回放。",
      "templates": [
        "templates/2026-10-22-scp-example__fig16-cell-density--ridge.md"
      ]
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
      "purposes": [
        "整合与批次校正"
      ],
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
  },
  {
    "path": "methods/cell-clustering.md",
    "meta": {
      "type": "method",
      "id": "cell-clustering",
      "title": "单细胞聚类分析",
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
      "purposes": [
        "降维与聚类"
      ],
      "summary": "在低维嵌入上构建邻居图并划分 cluster；cluster 是分析单位，不是细胞类型。",
      "data_contract": {
        "input": "已有 PCA/UMAP 嵌入的 Seurat 对象；dims、resolution、algorithm 显式。",
        "output": "每细胞 cluster 标签；cluster 不是细胞类型。"
      },
      "implementations": [
        {
          "id": "seurat-findclusters",
          "title": "SCP Standard_SCP 聚类分支",
          "language": "R",
          "entrypoint": "code/clustering.R:run_seurat_clustering",
          "dependencies": [
            "Seurat",
            "SeuratObject"
          ],
          "verification": "verification/seurat-findclusters.json"
        }
      ],
      "keywords": [
        "FindClusters",
        "Louvain",
        "Leiden",
        "resolution",
        "cluster",
        "SCP"
      ],
      "figure_relations": [
        {
          "figure": "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap",
          "compatibility": "adaptable",
          "reason": "cluster 标签可作为 UMAP 着色变量；模板不聚类。",
          "prerequisites": [
            "celltype 标签与 UMAP 坐标来自同一 Seurat 对象；cell_id 一致。",
            "group_levels 按注释顺序给出；不得把 cluster 编号直接当 celltype。"
          ],
          "adaptation": "导出 render-umap-groups.csv（group=cluster）；cluster 编号不是细胞类型。",
          "evidence": [
            "methods/cell-clustering.md#输出",
            "methods/scrna-marker-annotation.md#知识关联检查",
            "methods/scrna-marker-annotation.md#输出",
            "layouts/2026-10-22-glaucoma-scrna__fig01-cns-umap.md#适用",
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
          "reason": "按样本/条件统计 cluster 比例，检查组成；模板不做聚类或检验。",
          "prerequisites": [
            "每个 group 的比例归一化到 1；group/celltype 完整，无缺组。",
            "流带仅作视觉插值，不是统计估计或细胞轨迹。"
          ],
          "adaptation": "导出 render-cell-proportions.csv（group=样本, celltype=cluster, proportion）。",
          "evidence": [
            "methods/cell-clustering.md#输出",
            "methods/scrna-marker-annotation.md#知识关联检查",
            "methods/scrna-marker-annotation.md#输出",
            "layouts/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow.md#适用",
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
    "implementation_status": [
      {
        "id": "seurat-findclusters",
        "title": "SCP Standard_SCP 聚类分支",
        "state": "verified",
        "scope": "显式复用 SCP Standard_SCP 中的 FindNeighbors/FindClusters 聚类分支；与相同 Seurat 调用逐标签比较，不含预处理/降维。"
      }
    ],
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
        "method": "methods/cell-clustering.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap.md",
        "method_title": "单细胞聚类分析",
        "figure_title": "CNS 细胞类型 UMAP",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "cluster 标签可作为 UMAP 着色变量；模板不聚类。",
        "prerequisites": [
          "celltype 标签与 UMAP 坐标来自同一 Seurat 对象；cell_id 一致。",
          "group_levels 按注释顺序给出；不得把 cluster 编号直接当 celltype。"
        ],
        "adaptation": "导出 render-umap-groups.csv（group=cluster）；cluster 编号不是细胞类型。",
        "evidence": [
          "methods/cell-clustering.md#输出",
          "methods/scrna-marker-annotation.md#知识关联检查",
          "methods/scrna-marker-annotation.md#输出",
          "layouts/2026-10-22-glaucoma-scrna__fig01-cns-umap.md#适用",
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
        "method": "methods/cell-clustering.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow.md",
        "method_title": "单细胞聚类分析",
        "figure_title": "细胞比例堆叠流带图",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "按样本/条件统计 cluster 比例，检查组成；模板不做聚类或检验。",
        "prerequisites": [
          "每个 group 的比例归一化到 1；group/celltype 完整，无缺组。",
          "流带仅作视觉插值，不是统计估计或细胞轨迹。"
        ],
        "adaptation": "导出 render-cell-proportions.csv（group=样本, celltype=cluster, proportion）。",
        "evidence": [
          "methods/cell-clustering.md#输出",
          "methods/scrna-marker-annotation.md#知识关联检查",
          "methods/scrna-marker-annotation.md#输出",
          "layouts/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow.md#适用",
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
  },
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
      "purposes": [
        "预处理与质量控制"
      ],
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
    "implementation_status": [
      {
        "id": "scp-runcellqc",
        "title": "SCP RunCellQC 封装",
        "state": "verified",
        "scope": "实际调用 SCP RunCellQC 于 pancreas_sub 的 80 个细胞；比较封装与上游 CellQC、检查输入未变。"
      }
    ],
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
    "path": "methods/cell-type-annotation.md",
    "meta": {
      "type": "method",
      "id": "cell-type-annotation",
      "title": "细胞类型注释",
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
      "purposes": [
        "注释与参考映射"
      ],
      "summary": "综合参考标签与 marker 集合给细胞分配类型；SingleR 分支未运行，青光眼 marker 手工注释尚未函数化。",
      "data_contract": {
        "input": "query Seurat；参考标签分支需 reference Seurat + ref_group，marker 分支需预先定义的 marker→类型映射；同物种/同基因标识。",
        "output": "每细胞 predicted label 与分数（SingleR 成功时），或手工 marker 注释标签表；当前无已验证输出。"
      },
      "implementations": [
        {
          "id": "scp-singler",
          "title": "SCP RunSingleR 分支",
          "language": "R",
          "entrypoint": "code/analysis.R:run_cell_type_annotation",
          "dependencies": [
            "Seurat",
            "SingleR"
          ],
          "verification": "verification/scp-singler.json"
        }
      ],
      "keywords": [
        "SingleR",
        "marker",
        "cell type",
        "annotation",
        "参考注释",
        "手工注释",
        "SCP",
        "GSE251716"
      ],
      "figure_relations": [
        {
          "figure": "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap",
          "compatibility": "adaptable",
          "reason": "预测细胞类型可作为 UMAP 着色变量；模板不执行注释。",
          "prerequisites": [
            "预测标签与 UMAP 坐标来自同一查询对象；cell_id 一致。",
            "标签不是 cluster 编号；group_levels 按注释顺序给出。"
          ],
          "adaptation": "导出 render-umap-groups.csv（group=predicted celltype）。",
          "evidence": [
            "methods/cell-type-annotation.md#输出",
            "methods/scp-annotation-projection.md#知识关联检查",
            "methods/scp-annotation-projection.md#输出",
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
          "figure": "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap",
          "compatibility": "adaptable",
          "reason": "用 marker 表达检查预测标签是否落在对应群，可复用特征 UMAP 网格；模板不做注释或检验。",
          "prerequisites": [
            "marker 表达长表与 UMAP 坐标同源；cell_id 一致。",
            "每个 feature 至少有一个正表达细胞；目标类型在 group 中存在。"
          ],
          "adaptation": "导出 render-umap-feature-long.csv（cell_id, umap_1, umap_2, group, feature, value）。",
          "evidence": [
            "methods/cell-type-annotation.md#输出",
            "methods/scp-annotation-projection.md#知识关联检查",
            "methods/scp-annotation-projection.md#输出",
            "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap/spec.json",
            "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap/verify/verify.json"
          ],
          "verification": {
            "state": "not_run",
            "scope": "2026-10-23 只核对方法输出与模板接口；未运行真实课题分析→出图。",
            "evidence": []
          }
        },
        {
          "figure": "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot",
          "compatibility": "adaptable",
          "reason": "预测类型的 marker 平均表达/阳性比例可整理成点图，检查注释是否合理；模板不重算统计。",
          "prerequisites": [
            "avg_expression 与 pct_expressed 由表达矩阵按预测标签计算；缩放方式说明。",
            "group/feature 顺序由课题给出；target_group 只用于排序。"
          ],
          "adaptation": "导出 render-dotplot-long.csv（group, feature, avg_expression, pct_expressed, target_group）。",
          "evidence": [
            "methods/cell-type-annotation.md#输出",
            "methods/scp-annotation-projection.md#知识关联检查",
            "methods/scp-annotation-projection.md#输出",
            "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot/spec.json",
            "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot/verify/verify.json"
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
          "reason": "按样本/条件统计预测类型比例，检查注释组成；模板不做统计检验。",
          "prerequisites": [
            "每个 group 的比例归一化到 1；group 为样本/条件，celltype 为预测标签。",
            "比例是描述性；组间差异不能由该图直接推断。"
          ],
          "adaptation": "导出 render-cell-proportions.csv（group, celltype, proportion）。",
          "evidence": [
            "methods/cell-type-annotation.md#输出",
            "methods/scp-annotation-projection.md#知识关联检查",
            "methods/scp-annotation-projection.md#输出",
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
    "implementation_status": [
      {
        "id": "scp-singler",
        "title": "SCP RunSingleR 分支",
        "state": "not_run",
        "scope": "SCP RunSingleR 分支；本机 R 库无 SingleR。"
      }
    ],
    "figure_refs": [
      "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap.md",
      "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap.md",
      "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot.md",
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
        "method": "methods/cell-type-annotation.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap.md",
        "method_title": "细胞类型注释",
        "figure_title": "CNS 细胞类型 UMAP",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "预测细胞类型可作为 UMAP 着色变量；模板不执行注释。",
        "prerequisites": [
          "预测标签与 UMAP 坐标来自同一查询对象；cell_id 一致。",
          "标签不是 cluster 编号；group_levels 按注释顺序给出。"
        ],
        "adaptation": "导出 render-umap-groups.csv（group=predicted celltype）。",
        "evidence": [
          "methods/cell-type-annotation.md#输出",
          "methods/scp-annotation-projection.md#知识关联检查",
          "methods/scp-annotation-projection.md#输出",
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
        "method": "methods/cell-type-annotation.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap.md",
        "method_title": "细胞类型注释",
        "figure_title": "marker 特征 UMAP 小多图",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "用 marker 表达检查预测标签是否落在对应群，可复用特征 UMAP 网格；模板不做注释或检验。",
        "prerequisites": [
          "marker 表达长表与 UMAP 坐标同源；cell_id 一致。",
          "每个 feature 至少有一个正表达细胞；目标类型在 group 中存在。"
        ],
        "adaptation": "导出 render-umap-feature-long.csv（cell_id, umap_1, umap_2, group, feature, value）。",
        "evidence": [
          "methods/cell-type-annotation.md#输出",
          "methods/scp-annotation-projection.md#知识关联检查",
          "methods/scp-annotation-projection.md#输出",
          "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap/spec.json",
          "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap/verify/verify.json"
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
        "method": "methods/cell-type-annotation.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot.md",
        "method_title": "细胞类型注释",
        "figure_title": "细胞类型 × 基因气泡点图",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "预测类型的 marker 平均表达/阳性比例可整理成点图，检查注释是否合理；模板不重算统计。",
        "prerequisites": [
          "avg_expression 与 pct_expressed 由表达矩阵按预测标签计算；缩放方式说明。",
          "group/feature 顺序由课题给出；target_group 只用于排序。"
        ],
        "adaptation": "导出 render-dotplot-long.csv（group, feature, avg_expression, pct_expressed, target_group）。",
        "evidence": [
          "methods/cell-type-annotation.md#输出",
          "methods/scp-annotation-projection.md#知识关联检查",
          "methods/scp-annotation-projection.md#输出",
          "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot/spec.json",
          "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot/verify/verify.json"
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
        "method": "methods/cell-type-annotation.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow.md",
        "method_title": "细胞类型注释",
        "figure_title": "细胞比例堆叠流带图",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "按样本/条件统计预测类型比例，检查注释组成；模板不做统计检验。",
        "prerequisites": [
          "每个 group 的比例归一化到 1；group 为样本/条件，celltype 为预测标签。",
          "比例是描述性；组间差异不能由该图直接推断。"
        ],
        "adaptation": "导出 render-cell-proportions.csv（group, celltype, proportion）。",
        "evidence": [
          "methods/cell-type-annotation.md#输出",
          "methods/scp-annotation-projection.md#知识关联检查",
          "methods/scp-annotation-projection.md#输出",
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
  },
  {
    "path": "methods/differential-expression.md",
    "meta": {
      "type": "method",
      "id": "differential-expression",
      "title": "差异表达分析",
      "status": "draft",
      "tags": [
        "单细胞分析",
        "转录组"
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
      "purposes": [
        "差异与功能分析"
      ],
      "summary": "在明确对比组之间检验基因表达差异，输出效应量、p 值与阳性比例；细胞级 p 值不等于样本级推断。",
      "data_contract": {
        "input": "已标准化/注释的 Seurat 对象 + 分组列；比较组与参照组显式给出，组内细胞数足够。",
        "output": "SCP tools 中的 gene×contrast 表：gene、group1、group2、avg_log2FC、p_val、p_val_adj、pct.1、pct.2。"
      },
      "implementations": [
        {
          "id": "scp-detest",
          "title": "SCP RunDEtest 封装",
          "language": "R",
          "entrypoint": "code/analysis.R:run_differential_expression",
          "dependencies": [
            "Seurat",
            "BiocParallel"
          ],
          "verification": "verification/scp-detest.json"
        }
      ],
      "keywords": [
        "DE",
        "FindMarkers",
        "Wilcoxon",
        "avg_log2FC",
        "p_val_adj",
        "差异基因",
        "SCP"
      ],
      "figure_relations": [
        {
          "figure": "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot",
          "compatibility": "adaptable",
          "reason": "DE 选出的 marker 可整理成 group/feature/avg_expression/pct_expressed，复用气泡点图；模板不重算 DE。",
          "prerequisites": [
            "avg_expression 与 pct_expressed 由表达矩阵按组计算，不能用 avg_log2FC 代替。",
            "group/feature 顺序由课题给出；target_group 只用于排序。"
          ],
          "adaptation": "导出 render-dotplot-long.csv（group, feature, avg_expression, pct_expressed, target_group）。",
          "evidence": [
            "methods/differential-expression.md#输出",
            "methods/scp-de-enrichment-dynamic.md#知识关联检查",
            "methods/scp-de-enrichment-dynamic.md#输出",
            "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot/spec.json",
            "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot/verify/verify.json"
          ],
          "verification": {
            "state": "not_run",
            "scope": "2026-10-23 只核对方法输出与模板接口；未运行真实课题分析→出图。",
            "evidence": []
          }
        },
        {
          "figure": "templates/2026-10-22-scp-example__fig01-volcano--volcano",
          "compatibility": "adaptable",
          "reason": "DE 表可整理成 render-de-results，火山图模板消费该表；模板不重跑检验。",
          "prerequisites": [
            "group1 单一；pct_1/pct_2 为 0–1；p_val_adj >0；gene 组内唯一。",
            "模板不重跑 DE 或 p 值校正；阈值由 style 显式给出。"
          ],
          "adaptation": "从 AllMarkers 表导出 gene、avg_log2FC、p_val_adj 等字段到 render-de-results。",
          "evidence": [
            "methods/differential-expression.md#输出",
            "methods/scp-de-enrichment-dynamic.md#知识关联检查",
            "methods/scp-de-enrichment-dynamic.md#输出",
            "templates/2026-10-22-scp-example__fig01-volcano--volcano/spec.json",
            "templates/2026-10-22-scp-example__fig01-volcano--volcano/verify/verify.json"
          ],
          "verification": {
            "state": "not_run",
            "scope": "2026-10-23 只核对方法输出与模板接口；未运行真实课题分析→出图。",
            "evidence": []
          }
        }
      ]
    },
    "implementation_status": [
      {
        "id": "scp-detest",
        "title": "SCP RunDEtest 封装",
        "state": "verified",
        "scope": "实际调用 SCP RunDEtest：pancreas_sub 全数据，Ductal vs Endocrine，wilcox；比较封装与上游 AllMarkers 表。"
      }
    ],
    "figure_refs": [
      "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot.md",
      "templates/2026-10-22-scp-example__fig01-volcano--volcano.md"
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
        "method": "methods/differential-expression.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot.md",
        "method_title": "差异表达分析",
        "figure_title": "细胞类型 × 基因气泡点图",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "DE 选出的 marker 可整理成 group/feature/avg_expression/pct_expressed，复用气泡点图；模板不重算 DE。",
        "prerequisites": [
          "avg_expression 与 pct_expressed 由表达矩阵按组计算，不能用 avg_log2FC 代替。",
          "group/feature 顺序由课题给出；target_group 只用于排序。"
        ],
        "adaptation": "导出 render-dotplot-long.csv（group, feature, avg_expression, pct_expressed, target_group）。",
        "evidence": [
          "methods/differential-expression.md#输出",
          "methods/scp-de-enrichment-dynamic.md#知识关联检查",
          "methods/scp-de-enrichment-dynamic.md#输出",
          "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot/spec.json",
          "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot/verify/verify.json"
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
        "method": "methods/differential-expression.md",
        "figure": "templates/2026-10-22-scp-example__fig01-volcano--volcano.md",
        "method_title": "差异表达分析",
        "figure_title": "差异表达火山图",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "DE 表可整理成 render-de-results，火山图模板消费该表；模板不重跑检验。",
        "prerequisites": [
          "group1 单一；pct_1/pct_2 为 0–1；p_val_adj >0；gene 组内唯一。",
          "模板不重跑 DE 或 p 值校正；阈值由 style 显式给出。"
        ],
        "adaptation": "从 AllMarkers 表导出 gene、avg_log2FC、p_val_adj 等字段到 render-de-results。",
        "evidence": [
          "methods/differential-expression.md#输出",
          "methods/scp-de-enrichment-dynamic.md#知识关联检查",
          "methods/scp-de-enrichment-dynamic.md#输出",
          "templates/2026-10-22-scp-example__fig01-volcano--volcano/spec.json",
          "templates/2026-10-22-scp-example__fig01-volcano--volcano/verify/verify.json"
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
    "path": "methods/dimensionality-reduction.md",
    "meta": {
      "type": "method",
      "id": "dimensionality-reduction",
      "title": "单细胞降维分析",
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
      "purposes": [
        "降维与聚类"
      ],
      "summary": "在标准化/缩放后的表达上计算 PCA 与 UMAP，为聚类、可视化和轨迹提供低维表示。",
      "data_contract": {
        "input": "已标准化、选 HVF 并缩放的 Seurat 对象；features 或 reduction_use 显式。",
        "output": "PCA/UMAP 嵌入，每细胞一行坐标。"
      },
      "implementations": [
        {
          "id": "scp-dimreduction",
          "title": "SCP RunDimReduction 封装",
          "language": "R",
          "entrypoint": "code/analysis.R:run_dimensionality_reduction",
          "dependencies": [
            "Seurat",
            "SeuratObject"
          ],
          "verification": "verification/scp-dimreduction.json"
        }
      ],
      "keywords": [
        "PCA",
        "UMAP",
        "RunDimReduction",
        "HVF",
        "降维",
        "SCP"
      ],
      "figure_relations": [
        {
          "figure": "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap",
          "compatibility": "adaptable",
          "reason": "Standard_SCP 产出 StandardUMAP2D，可作为 UMAP 分组着色；模板只画表，不降维。",
          "prerequisites": [
            "坐标与 group 来自同一嵌入；cell_id 唯一；坐标无 NA。",
            "group 明确为 cluster 或 celltype；group_levels 由课题给出。"
          ],
          "adaptation": "导出 render-umap-groups.csv（cell_id, umap_1, umap_2, group）。",
          "evidence": [
            "methods/dimensionality-reduction.md#输出",
            "methods/scp-standard-workflow.md#知识关联检查",
            "methods/scp-standard-workflow.md#输出",
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
          "figure": "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap",
          "compatibility": "adaptable",
          "reason": "降维嵌入可与 marker 表达长表拼成特征 UMAP 网格；模板不重做降维或表达。",
          "prerequisites": [
            "UMAP 坐标与表达来自同一 Seurat 对象；cell_id 一致。",
            "目标细胞类型映射由注释步骤给出；每个 feature 至少有一个正表达细胞。"
          ],
          "adaptation": "导出 render-umap-feature-long.csv（cell_id, umap_1, umap_2, group, feature, value）。",
          "evidence": [
            "methods/dimensionality-reduction.md#输出",
            "methods/scp-standard-workflow.md#知识关联检查",
            "methods/scp-standard-workflow.md#输出",
            "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap/spec.json",
            "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap/verify/verify.json"
          ],
          "verification": {
            "state": "not_run",
            "scope": "2026-10-23 只核对方法输出与模板接口；未运行真实课题分析→出图。",
            "evidence": []
          }
        }
      ]
    },
    "implementation_status": [
      {
        "id": "scp-dimreduction",
        "title": "SCP RunDimReduction 封装",
        "state": "verified",
        "scope": "实际调用 SCP RunDimReduction：pancreas_sub 200 细胞，100 HVF、20 PC、UMAP；比较封装与上游 UMAP。"
      }
    ],
    "figure_refs": [
      "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap.md",
      "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap.md"
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
        "method": "methods/dimensionality-reduction.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap.md",
        "method_title": "单细胞降维分析",
        "figure_title": "CNS 细胞类型 UMAP",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "Standard_SCP 产出 StandardUMAP2D，可作为 UMAP 分组着色；模板只画表，不降维。",
        "prerequisites": [
          "坐标与 group 来自同一嵌入；cell_id 唯一；坐标无 NA。",
          "group 明确为 cluster 或 celltype；group_levels 由课题给出。"
        ],
        "adaptation": "导出 render-umap-groups.csv（cell_id, umap_1, umap_2, group）。",
        "evidence": [
          "methods/dimensionality-reduction.md#输出",
          "methods/scp-standard-workflow.md#知识关联检查",
          "methods/scp-standard-workflow.md#输出",
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
        "method": "methods/dimensionality-reduction.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap.md",
        "method_title": "单细胞降维分析",
        "figure_title": "marker 特征 UMAP 小多图",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "降维嵌入可与 marker 表达长表拼成特征 UMAP 网格；模板不重做降维或表达。",
        "prerequisites": [
          "UMAP 坐标与表达来自同一 Seurat 对象；cell_id 一致。",
          "目标细胞类型映射由注释步骤给出；每个 feature 至少有一个正表达细胞。"
        ],
        "adaptation": "导出 render-umap-feature-long.csv（cell_id, umap_1, umap_2, group, feature, value）。",
        "evidence": [
          "methods/dimensionality-reduction.md#输出",
          "methods/scp-standard-workflow.md#知识关联检查",
          "methods/scp-standard-workflow.md#输出",
          "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap/spec.json",
          "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap/verify/verify.json"
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
    "path": "methods/doublet-detection.md",
    "meta": {
      "type": "method",
      "id": "doublet-detection",
      "title": "双细胞检测",
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
      "purposes": [
        "预处理与质量控制"
      ],
      "summary": "按样本识别双细胞；scDblFinder 与 DoubletFinder 是不同算法，当前均未在本机跑通，保留来源与精确缺失原因。",
      "data_contract": {
        "input": "按样本的 Seurat 原始 counts；显式预期双细胞率；scDblFinder 或 DoubletFinder 分支及其预处理前提。",
        "output": "每细胞 doublet class/score（运行成功时）；当前两条路线均未产生结果。"
      },
      "implementations": [
        {
          "id": "scp-rundoublet",
          "title": "SCP RunDoubletCalling 的 scDblFinder 分支",
          "language": "R",
          "entrypoint": "code/analysis.R:run_doublet_detection",
          "dependencies": [
            "Seurat",
            "scDblFinder"
          ],
          "verification": "verification/scp-rundoublet.json"
        }
      ],
      "keywords": [
        "doublet",
        "scDblFinder",
        "DoubletFinder",
        "Scrublet",
        "DoubletDetection",
        "scds",
        "双细胞",
        "SCP"
      ],
      "figure_relations": [
        {
          "figure": "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap",
          "compatibility": "adaptable",
          "reason": "双细胞标签可作为 UMAP 着色变量检查分布；模板不检测双细胞。",
          "prerequisites": [
            "UMAP 坐标与 QC 标签来自同一 Seurat 对象；cell_id 一致。",
            "group_levels 显式给出；Pass/Fail 顺序固定。"
          ],
          "adaptation": "导出 render-umap-groups.csv（group=doublet class 或样本）；标签只作描述。",
          "evidence": [
            "methods/doublet-detection.md#输出",
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
          "reason": "按样本统计双细胞比例可复用比例图；模板不做双细胞检测或统计检验。",
          "prerequisites": [
            "每个 group 的 celltype 比例归一化到 1；group 为样本或条件，celltype 为 CellQC。",
            "组间比较只作描述，不能当样本级推断。"
          ],
          "adaptation": "导出 render-cell-proportions.csv（group=样本, celltype=doublet class, proportion）。",
          "evidence": [
            "methods/doublet-detection.md#输出",
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
        }
      ]
    },
    "implementation_status": [
      {
        "id": "scp-rundoublet",
        "title": "SCP RunDoubletCalling 的 scDblFinder 分支",
        "state": "not_run",
        "scope": "SCP RunDoubletCalling 的 scDblFinder 分支；本机 R 库无 scDblFinder。"
      }
    ],
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
        "method": "methods/doublet-detection.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap.md",
        "method_title": "双细胞检测",
        "figure_title": "CNS 细胞类型 UMAP",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "双细胞标签可作为 UMAP 着色变量检查分布；模板不检测双细胞。",
        "prerequisites": [
          "UMAP 坐标与 QC 标签来自同一 Seurat 对象；cell_id 一致。",
          "group_levels 显式给出；Pass/Fail 顺序固定。"
        ],
        "adaptation": "导出 render-umap-groups.csv（group=doublet class 或样本）；标签只作描述。",
        "evidence": [
          "methods/doublet-detection.md#输出",
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
        "method": "methods/doublet-detection.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow.md",
        "method_title": "双细胞检测",
        "figure_title": "细胞比例堆叠流带图",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "按样本统计双细胞比例可复用比例图；模板不做双细胞检测或统计检验。",
        "prerequisites": [
          "每个 group 的 celltype 比例归一化到 1；group 为样本或条件，celltype 为 CellQC。",
          "组间比较只作描述，不能当样本级推断。"
        ],
        "adaptation": "导出 render-cell-proportions.csv（group=样本, celltype=doublet class, proportion）。",
        "evidence": [
          "methods/doublet-detection.md#输出",
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
      }
    ]
  },
  {
    "path": "methods/dynamic-feature-analysis.md",
    "meta": {
      "type": "method",
      "id": "dynamic-feature-analysis",
      "title": "拟时序动态特征分析",
      "status": "draft",
      "tags": [
        "单细胞分析",
        "转录组"
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
      "purposes": [
        "轨迹与动态分析"
      ],
      "summary": "沿 pseudotime 拟合每个特征的平滑趋势，输出变化显著性、解释度和峰/谷时间。",
      "data_contract": {
        "input": "Seurat 对象 + pseudotime/lineage 列 + 候选 features；pseudotime 必须来自轨迹推断。",
        "output": "每 feature 的 GAM 表：features、exp_ncells、r.sq、dev.expl、peaktime、valleytime、pvalue、padjust。"
      },
      "implementations": [
        {
          "id": "scp-dynamicfeatures",
          "title": "SCP RunDynamicFeatures 封装",
          "language": "R",
          "entrypoint": "code/analysis.R:run_dynamic_feature_analysis",
          "dependencies": [
            "Seurat",
            "mgcv",
            "BiocParallel"
          ],
          "verification": "verification/scp-dynamicfeatures.json"
        }
      ],
      "keywords": [
        "GAM",
        "mgcv",
        "pseudotime",
        "dynamic features",
        "RunDynamicFeatures",
        "SCP"
      ],
      "figure_relations": [
        {
          "figure": "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap",
          "compatibility": "adaptable",
          "reason": "动态特征值可作为 feature 长表画在 UMAP 上；模板只画值，不拟合 GAM。",
          "prerequisites": [
            "值与 UMAP 坐标来自同一细胞集合；cell_id 一致。",
            "value 的含义/单位明确；无 NA。"
          ],
          "adaptation": "导出 render-umap-feature-long.csv（feature=基因/特征, value=表达或拟合值）。",
          "evidence": [
            "methods/dynamic-feature-analysis.md#输出",
            "methods/scp-de-enrichment-dynamic.md#知识关联检查",
            "methods/scp-de-enrichment-dynamic.md#输出",
            "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap/spec.json",
            "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap/verify/verify.json"
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
          "reason": "动态特征或 pseudotime 按 cluster/lineage 分组的分布可用分组小提琴展示；模板不做轨迹或检验。",
          "prerequisites": [
            "同一 pseudotime/lineage 定义；celltype/group 标签一致。",
            "p/mean/SD 若展示，由分析阶段预计算；细胞级 p 不能当样本级推断。"
          ],
          "adaptation": "导出 render-grouped-values.csv（group=cluster/lineage, value=特征值/pseudotime）。",
          "evidence": [
            "methods/dynamic-feature-analysis.md#输出",
            "methods/scp-trajectory-velocity.md#知识关联检查",
            "methods/scp-trajectory-velocity.md#输出",
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
    "implementation_status": [
      {
        "id": "scp-dynamicfeatures",
        "title": "SCP RunDynamicFeatures 封装",
        "state": "verified",
        "scope": "实际调用 SCP RunDynamicFeatures：pancreas_sub 80 细胞，显式 fixture pseudotime，Gcg/Krt19；比较 GAM 表。pseudotime 为软件夹具，不代表真实轨迹。"
      }
    ],
    "figure_refs": [
      "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap.md",
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
        "method": "methods/dynamic-feature-analysis.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap.md",
        "method_title": "拟时序动态特征分析",
        "figure_title": "marker 特征 UMAP 小多图",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "动态特征值可作为 feature 长表画在 UMAP 上；模板只画值，不拟合 GAM。",
        "prerequisites": [
          "值与 UMAP 坐标来自同一细胞集合；cell_id 一致。",
          "value 的含义/单位明确；无 NA。"
        ],
        "adaptation": "导出 render-umap-feature-long.csv（feature=基因/特征, value=表达或拟合值）。",
        "evidence": [
          "methods/dynamic-feature-analysis.md#输出",
          "methods/scp-de-enrichment-dynamic.md#知识关联检查",
          "methods/scp-de-enrichment-dynamic.md#输出",
          "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap/spec.json",
          "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap/verify/verify.json"
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
        "method": "methods/dynamic-feature-analysis.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig06-pathway-violin--violin.md",
        "method_title": "拟时序动态特征分析",
        "figure_title": "分组小提琴图（含统计标注）",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "动态特征或 pseudotime 按 cluster/lineage 分组的分布可用分组小提琴展示；模板不做轨迹或检验。",
        "prerequisites": [
          "同一 pseudotime/lineage 定义；celltype/group 标签一致。",
          "p/mean/SD 若展示，由分析阶段预计算；细胞级 p 不能当样本级推断。"
        ],
        "adaptation": "导出 render-grouped-values.csv（group=cluster/lineage, value=特征值/pseudotime）。",
        "evidence": [
          "methods/dynamic-feature-analysis.md#输出",
          "methods/scp-trajectory-velocity.md#知识关联检查",
          "methods/scp-trajectory-velocity.md#输出",
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
    "path": "methods/gene-set-enrichment.md",
    "meta": {
      "type": "method",
      "id": "gene-set-enrichment",
      "title": "基因集富集分析",
      "status": "draft",
      "tags": [
        "单细胞分析",
        "转录组"
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
      "purposes": [
        "差异与功能分析"
      ],
      "summary": "用显式基因列表和背景检验基因集过代表（ORA），GO/KEGG 是资源，GSEA 是另一种策略且本页未实现。",
      "data_contract": {
        "input": "geneID 向量（可选分组）+ 显式 TERM2GENE/TERM2NAME，或由 DE 表派生的基因列表；背景/物种/ID 类型明确。",
        "output": "每个基因集一行的 ORA 表：ID、Description、GeneRatio、BgRatio、pvalue、p.adjust、qvalue、geneID、Count。"
      },
      "implementations": [
        {
          "id": "scp-enrichment",
          "title": "SCP RunEnrichment 的 ORA 分支",
          "language": "R",
          "entrypoint": "code/analysis.R:run_gene_set_enrichment",
          "dependencies": [
            "clusterProfiler",
            "DOSE",
            "Seurat"
          ],
          "verification": "verification/scp-enrichment.json"
        }
      ],
      "keywords": [
        "ORA",
        "GSEA",
        "GO",
        "KEGG",
        "clusterProfiler",
        "enrichment",
        "基因集",
        "SCP"
      ],
      "figure_relations": []
    },
    "implementation_status": [
      {
        "id": "scp-enrichment",
        "title": "SCP RunEnrichment 的 ORA 分支",
        "state": "verified",
        "scope": "实际调用 SCP RunEnrichment 的 ORA 分支，显式 TERM2GENE/TERM2NAME（两个合成基因集），与上游结果表比较。"
      }
    ],
    "figure_refs": [],
    "preview": null,
    "workflow": {
      "stage": "method_confirm",
      "queue": "confirm",
      "label": "待你确认",
      "reason": "笔记与知识关联检查已填写，待作者核对。",
      "templates": []
    },
    "relations": []
  },
  {
    "path": "methods/gene-set-scoring.md",
    "meta": {
      "type": "method",
      "id": "gene-set-scoring",
      "title": "基因集与通路签名打分",
      "status": "draft",
      "tags": [
        "单细胞分析",
        "转录组"
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
      "purposes": [
        "差异与功能分析"
      ],
      "summary": "按命名基因集给每个细胞打相对签名分数，用于描述状态差异；分数不是通路活性或富集显著性。",
      "data_contract": {
        "input": "Seurat 对象 + 命名基因集列表；同一数据集、同一 assay/slot 内比较。",
        "output": "每细胞×基因集的相对分数（Seurat metadata）或长表；不产出富集 p 值。"
      },
      "implementations": [
        {
          "id": "scp-cellscoring",
          "title": "SCP CellScoring 的 Seurat/AddModuleScore 分支",
          "language": "R",
          "entrypoint": "code/analysis.R:run_gene_set_scoring",
          "dependencies": [
            "Seurat",
            "BiocParallel"
          ],
          "verification": "verification/scp-cellscoring.json"
        }
      ],
      "keywords": [
        "AddModuleScore",
        "AUCell",
        "UCell",
        "ssGSEA",
        "singscore",
        "pathway score",
        "SCP"
      ],
      "figure_relations": [
        {
          "figure": "templates/2026-10-22-glaucoma-scrna__fig06-pathway-violin--violin",
          "compatibility": "adaptable",
          "reason": "通路签名分数按细胞类型/组展示分布，可复用小提琴模板；模板不重算分数或检验。",
          "prerequisites": [
            "同一 pathway 定义和单位；celltype/group 标签一致。",
            "p/mean/SD 由分析阶段预计算并说明来源；细胞水平 p 仅作描述，不能当样本级推断。"
          ],
          "adaptation": "导出 render-grouped-values.csv 和可选的 render-group-summaries.csv；细胞级 p 只作描述。",
          "evidence": [
            "methods/gene-set-scoring.md#输出",
            "methods/scrna-pathway-signature-ensemble.md#知识关联检查",
            "methods/scrna-pathway-signature-ensemble.md#输出",
            "layouts/2026-10-22-glaucoma-scrna__fig06-pathway-violin.md#适用",
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
    "implementation_status": [
      {
        "id": "scp-cellscoring",
        "title": "SCP CellScoring 的 Seurat/AddModuleScore 分支",
        "state": "verified",
        "scope": "实际调用 SCP CellScoring 的 Seurat/AddModuleScore 分支，显式 name='X' 避开上游空 name 的列名缺陷；与上游分数比较。"
      }
    ],
    "figure_refs": [
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
        "method": "methods/gene-set-scoring.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig06-pathway-violin--violin.md",
        "method_title": "基因集与通路签名打分",
        "figure_title": "分组小提琴图（含统计标注）",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "通路签名分数按细胞类型/组展示分布，可复用小提琴模板；模板不重算分数或检验。",
        "prerequisites": [
          "同一 pathway 定义和单位；celltype/group 标签一致。",
          "p/mean/SD 由分析阶段预计算并说明来源；细胞水平 p 仅作描述，不能当样本级推断。"
        ],
        "adaptation": "导出 render-grouped-values.csv 和可选的 render-group-summaries.csv；细胞级 p 只作描述。",
        "evidence": [
          "methods/gene-set-scoring.md#输出",
          "methods/scrna-pathway-signature-ensemble.md#知识关联检查",
          "methods/scrna-pathway-signature-ensemble.md#输出",
          "layouts/2026-10-22-glaucoma-scrna__fig06-pathway-violin.md#适用",
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
    "path": "methods/reference-mapping.md",
    "meta": {
      "type": "method",
      "id": "reference-mapping",
      "title": "参考图谱映射",
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
      "purposes": [
        "注释与参考映射"
      ],
      "summary": "把查询细胞映射到参考标签并返回预测分数；Seurat 标签转移已验证，UMAP 投影分支未通过。",
      "data_contract": {
        "input": "query/reference Seurat 对象 + reference 标签列；reference 有 PCA，query/ref 共享特征。",
        "output": "每 query 细胞 predicted_id、max_score、margin；不包含 UMAP 投影（该分支未通过）。"
      },
      "implementations": [
        {
          "id": "seurat-label-transfer",
          "title": "Seurat 锚点标签转移分支",
          "language": "R",
          "entrypoint": "code/transfer.R:run_reference_label_transfer",
          "dependencies": [
            "Seurat",
            "SeuratObject"
          ],
          "verification": "verification/seurat-label-transfer.json"
        },
        {
          "id": "scp-runseuratmap",
          "title": "SCP RunSeuratMap UMAP 投影分支",
          "language": "R",
          "entrypoint": "code/analysis.R:run_reference_mapping",
          "dependencies": [
            "Seurat"
          ],
          "verification": "verification/scp-runseuratmap.json"
        }
      ],
      "keywords": [
        "reference mapping",
        "label transfer",
        "FindTransferAnchors",
        "TransferData",
        "Seurat",
        "SCP"
      ],
      "figure_relations": [
        {
          "figure": "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap",
          "compatibility": "adaptable",
          "reason": "查询细胞可按预测标签着色自身 UMAP；这不是参考 UMAP 投影，模板也不执行映射。",
          "prerequisites": [
            "预测标签与 UMAP 坐标来自同一查询对象；cell_id 一致。",
            "标签不是 cluster 编号；group_levels 按注释顺序给出。"
          ],
          "adaptation": "导出 render-umap-groups.csv（group=predicted label）；不得把查询 UMAP 说成参考投影。",
          "evidence": [
            "methods/reference-mapping.md#输出",
            "methods/scp-annotation-projection.md#知识关联检查",
            "methods/scp-annotation-projection.md#输出",
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
          "reason": "按样本统计预测标签比例，检查映射组成；模板不做映射或检验。",
          "prerequisites": [
            "每个 group 的比例归一化到 1；group 为样本/条件，celltype 为预测标签。",
            "比例是描述性；组间差异不能由该图直接推断。"
          ],
          "adaptation": "导出 render-cell-proportions.csv（group=样本, celltype=predicted label, proportion）。",
          "evidence": [
            "methods/reference-mapping.md#输出",
            "methods/scp-annotation-projection.md#知识关联检查",
            "methods/scp-annotation-projection.md#输出",
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
    "implementation_status": [
      {
        "id": "seurat-label-transfer",
        "title": "Seurat 锚点标签转移分支",
        "state": "verified",
        "scope": "从 SCP RunSeuratMap 提取 FindTransferAnchors + TransferData 标签转移分支；pancreas_sub 300 参考/700 查询，检查每细胞预测、顺序与 anchor 数。不包含 UMAP 投影。"
      },
      {
        "id": "scp-runseuratmap",
        "title": "SCP RunSeuratMap UMAP 投影分支",
        "state": "not_run",
        "scope": "SCP RunSeuratMap 的 UMAP 投影分支在 Seurat 5.6 下失败；标签转移另由 seurat-label-transfer 分支验证。"
      }
    ],
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
        "method": "methods/reference-mapping.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap.md",
        "method_title": "参考图谱映射",
        "figure_title": "CNS 细胞类型 UMAP",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "查询细胞可按预测标签着色自身 UMAP；这不是参考 UMAP 投影，模板也不执行映射。",
        "prerequisites": [
          "预测标签与 UMAP 坐标来自同一查询对象；cell_id 一致。",
          "标签不是 cluster 编号；group_levels 按注释顺序给出。"
        ],
        "adaptation": "导出 render-umap-groups.csv（group=predicted label）；不得把查询 UMAP 说成参考投影。",
        "evidence": [
          "methods/reference-mapping.md#输出",
          "methods/scp-annotation-projection.md#知识关联检查",
          "methods/scp-annotation-projection.md#输出",
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
        "method": "methods/reference-mapping.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow.md",
        "method_title": "参考图谱映射",
        "figure_title": "细胞比例堆叠流带图",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "按样本统计预测标签比例，检查映射组成；模板不做映射或检验。",
        "prerequisites": [
          "每个 group 的比例归一化到 1；group 为样本/条件，celltype 为预测标签。",
          "比例是描述性；组间差异不能由该图直接推断。"
        ],
        "adaptation": "导出 render-cell-proportions.csv（group=样本, celltype=predicted label, proportion）。",
        "evidence": [
          "methods/reference-mapping.md#输出",
          "methods/scp-annotation-projection.md#知识关联检查",
          "methods/scp-annotation-projection.md#输出",
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
  },
  {
    "path": "methods/regression-resampling-evaluation.md",
    "meta": {
      "type": "method",
      "id": "regression-resampling-evaluation",
      "title": "回归模型的重采样评估与折外预测",
      "status": "ready",
      "tags": [
        "机器学习",
        "实验统计"
      ],
      "inputs": [
        "regression-predictions"
      ],
      "outputs": [
        "regression-fold-metrics"
      ],
      "source": {
        "kind": "written",
        "gallery_entry": "2026-10-19-regression-stability/figures/fig03-density-panel"
      },
      "license": "none",
      "cite": [
        "原帖：Python机器学习AI，2026-10-19。https://mp.weixin.qq.com/s/LDPZ8guXNKnSRtjZC2YbNg",
        "scikit-learn: Cross-validation: evaluating estimator performance. https://scikit-learn.org/stable/modules/cross_validation.html",
        "scikit-learn: Nested versus non-nested cross-validation. https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html",
        "scikit-learn: Common pitfalls and recommended practices. https://scikit-learn.org/stable/common_pitfalls.html"
      ],
      "favorite": false,
      "figure_relations": [
        {
          "figure": "templates/2026-10-19-regression-stability__fig03-density-panel--density-scatter",
          "compatibility": "adaptable",
          "reason": "可用本绘图模板表达真实预测的配对分布，但需上游明确准备RGB/边缘表。",
          "prerequisites": [
            "连续结局且同一原始量纲；明确样本、模型、重复/折身份。",
            "需先确定密度/边缘分布策略与注释统计，不用估读颜色倒推真实频数。"
          ],
          "adaptation": "课题内准备坐标/RGB/边缘条及真实注释；不从估读点重建频数，密度算法仍需确认。",
          "evidence": [
            "methods/regression-resampling-evaluation.md#输入",
            "layouts/2026-10-19-regression-stability__fig03-density-panel.md#适用",
            "templates/2026-10-19-regression-stability__fig03-density-panel--density-scatter/spec.json",
            "templates/2026-10-19-regression-stability__fig03-density-panel--density-scatter/verify/function-verification.json"
          ],
          "verification": {
            "state": "not_run",
            "scope": "本轮只验证模板绘图与合成规模；未验证真实方法→准备表→出图流水线。",
            "evidence": []
          }
        },
        {
          "figure": "templates/2026-10-19-regression-stability__fig04-boxplot-panel--boxplot",
          "compatibility": "adaptable",
          "reason": "逐折指标可用于该单指标分组分布，需上游按已确认规则准备同源点与箱线摘要。",
          "prerequisites": [
            "同一验证方案、指标定义与单位；明确折间相关性。",
            "按已确认的箱体/须/均值规则产生一致结果，横向抖动仅作展示。"
          ],
          "adaptation": "课题内选定指标、明确采样单位/须规则、整理同源points/summaries；不自动新写统计算法。",
          "evidence": [
            "methods/regression-resampling-evaluation.md#输出",
            "layouts/2026-10-19-regression-stability__fig04-boxplot-panel.md#适用",
            "templates/2026-10-19-regression-stability__fig04-boxplot-panel--boxplot/spec.json",
            "templates/2026-10-19-regression-stability__fig04-boxplot-panel--boxplot/verify/function-verification.json"
          ],
          "verification": {
            "state": "not_run",
            "scope": "本轮只验证模板绘图与合成规模；未验证真实方法→准备表→出图流水线。",
            "evidence": []
          }
        }
      ],
      "keywords": [
        "regression",
        "cross-validation",
        "回归评估",
        "模型比较",
        "折外预测",
        "交叉验证"
      ],
      "method_kind": "analysis",
      "purposes": [
        "模型评价"
      ],
      "summary": "汇总已有折外回归预测，计算逐折 RMSE/MAE/R2/r；不训练模型、不生成重采样。",
      "data_contract": {
        "input": "折外预测表 regression-predictions：sample_id/model/repeat/fold/y_true/y_pred/split_design；一行一个验证样本。",
        "output": "逐折指标表：model/repeat/fold/n_test/RMSE/MAE/R2/r/split_design；另可输出描述性均值/SD。"
      },
      "implementations": [
        {
          "id": "summarize-predictions",
          "title": "折外预测指标汇总",
          "language": "Python",
          "entrypoint": "code/summarize_predictions.py:summarize",
          "dependencies": [
            "numpy",
            "pandas"
          ],
          "verification": "verification/summarize-predictions.json"
        }
      ]
    },
    "implementation_status": [
      {
        "id": "summarize-predictions",
        "title": "折外预测指标汇总",
        "state": "verified",
        "scope": "手算折外指标、常数预测 r 未定义、不修改输入、完整 coverage 拒绝。不包含训练或重采样。"
      }
    ],
    "figure_refs": [
      "layouts/2026-10-19-regression-stability__fig03-density-panel.md",
      "layouts/2026-10-19-regression-stability__fig04-boxplot-panel.md",
      "templates/2026-10-19-regression-stability__fig03-density-panel--density-scatter.md",
      "templates/2026-10-19-regression-stability__fig04-boxplot-panel--boxplot.md"
    ],
    "preview": null,
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "已验证实现",
      "reason": "笔记已确认；仅实现收据中列明的分支和范围通过验证。",
      "templates": []
    },
    "relations": [
      {
        "method": "methods/regression-resampling-evaluation.md",
        "figure": "templates/2026-10-19-regression-stability__fig03-density-panel--density-scatter.md",
        "method_title": "回归模型的重采样评估与折外预测",
        "figure_title": "密度散点与边缘分布",
        "method_status": "ready",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "可用本绘图模板表达真实预测的配对分布，但需上游明确准备RGB/边缘表。",
        "prerequisites": [
          "连续结局且同一原始量纲；明确样本、模型、重复/折身份。",
          "需先确定密度/边缘分布策略与注释统计，不用估读颜色倒推真实频数。"
        ],
        "adaptation": "课题内准备坐标/RGB/边缘条及真实注释；不从估读点重建频数，密度算法仍需确认。",
        "evidence": [
          "methods/regression-resampling-evaluation.md#输入",
          "layouts/2026-10-19-regression-stability__fig03-density-panel.md#适用",
          "templates/2026-10-19-regression-stability__fig03-density-panel--density-scatter/spec.json",
          "templates/2026-10-19-regression-stability__fig03-density-panel--density-scatter/verify/function-verification.json"
        ],
        "verification": {
          "state": "not_run",
          "scope": "本轮只验证模板绘图与合成规模；未验证真实方法→准备表→出图流水线。",
          "evidence": []
        },
        "target_kind": "template",
        "active": true
      },
      {
        "method": "methods/regression-resampling-evaluation.md",
        "figure": "templates/2026-10-19-regression-stability__fig04-boxplot-panel--boxplot.md",
        "method_title": "回归模型的重采样评估与折外预测",
        "figure_title": "箱线、散点与均值",
        "method_status": "ready",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "逐折指标可用于该单指标分组分布，需上游按已确认规则准备同源点与箱线摘要。",
        "prerequisites": [
          "同一验证方案、指标定义与单位；明确折间相关性。",
          "按已确认的箱体/须/均值规则产生一致结果，横向抖动仅作展示。"
        ],
        "adaptation": "课题内选定指标、明确采样单位/须规则、整理同源points/summaries；不自动新写统计算法。",
        "evidence": [
          "methods/regression-resampling-evaluation.md#输出",
          "layouts/2026-10-19-regression-stability__fig04-boxplot-panel.md#适用",
          "templates/2026-10-19-regression-stability__fig04-boxplot-panel--boxplot/spec.json",
          "templates/2026-10-19-regression-stability__fig04-boxplot-panel--boxplot/verify/function-verification.json"
        ],
        "verification": {
          "state": "not_run",
          "scope": "本轮只验证模板绘图与合成规模；未验证真实方法→准备表→出图流水线。",
          "evidence": []
        },
        "target_kind": "template",
        "active": true
      }
    ]
  },
  {
    "path": "methods/rna-velocity.md",
    "meta": {
      "type": "method",
      "id": "rna-velocity",
      "title": "RNA 速度分析",
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
      "purposes": [
        "轨迹与动态分析"
      ],
      "summary": "利用 spliced/unspliced 计数推断转录动态方向；当前 Python 后端缺失，函数保留但未运行。",
      "data_contract": {
        "input": "含 spliced/unspliced layers 的 Seurat 对象或 AnnData；同一细胞集合的剪接/未剪接计数。",
        "output": "velocity 图、latent time、velocity confidence（运行成功时）；当前未产生结果。"
      },
      "implementations": [
        {
          "id": "scp-scvelo",
          "title": "SCP RunSCVELO 分支",
          "language": "R",
          "entrypoint": "code/analysis.R:run_rna_velocity",
          "dependencies": [
            "Seurat",
            "reticulate",
            "scvelo"
          ],
          "verification": "verification/scp-scvelo.json"
        }
      ],
      "keywords": [
        "RNA velocity",
        "scVelo",
        "spliced",
        "unspliced",
        "latent time",
        "SCP"
      ],
      "figure_relations": []
    },
    "implementation_status": [
      {
        "id": "scp-scvelo",
        "title": "SCP RunSCVELO 分支",
        "state": "not_run",
        "scope": "SCP RunSCVELO 分支需要 reticulate 与 scvelo；本机未设置 RETICULATE_PYTHON，且未安装 scvelo/scanpy。"
      }
    ],
    "figure_refs": [],
    "preview": null,
    "workflow": {
      "stage": "method_confirm",
      "queue": "confirm",
      "label": "待你确认",
      "reason": "笔记与知识关联检查已填写，待作者核对。",
      "templates": []
    },
    "relations": []
  },
  {
    "path": "methods/scp-annotation-projection.md",
    "meta": {
      "type": "method",
      "id": "scp-annotation-projection",
      "title": "单细胞自动注释与参考投影",
      "status": "ready",
      "tags": [
        "单细胞分析"
      ],
      "keywords": [
        "SCP",
        "Seurat",
        "RunSingleR",
        "RunKNNPredict",
        "RunScmap",
        "RunKNNMap",
        "RunPCAMap",
        "RunSeuratMap",
        "RunSymphonyMap",
        "RunCSSMap",
        "SingleR",
        "scmap",
        "Symphony",
        "细胞类型注释",
        "参考投影"
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
      "summary": "SCP 自动注释与参考投影的原始脚本和作者实现记录；分析问题见细胞类型注释与参考映射家族。",
      "data_contract": {
        "input": "SCP/Seurat 查询与参考对象、作者提供的参考标签列；原脚本参数在 source/ 中。",
        "output": "原始 SCP 注释/投影对象与结果表；本页不重新运行，不产生新的分析结论。"
      }
    },
    "implementation_status": [],
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
    "implementation_status": [],
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
    "path": "methods/scp-de-enrichment-dynamic.md",
    "meta": {
      "type": "method",
      "id": "scp-de-enrichment-dynamic",
      "title": "单细胞差异表达、基因集富集与动态特征",
      "status": "ready",
      "tags": [
        "单细胞分析",
        "转录组"
      ],
      "keywords": [
        "SCP",
        "Seurat",
        "RunDEtest",
        "RunEnrichment",
        "RunGSEA",
        "RunDynamicFeatures",
        "RunDynamicEnrichment",
        "CellScoring",
        "FindExpressedMarkers",
        "GO",
        "KEGG",
        "GSEA",
        "GAM",
        "pseudotime"
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
      "summary": "SCP 差异表达、富集和动态特征的原始脚本与作者实现记录；分析问题见四个对应家族。",
      "data_contract": {
        "input": "Seurat 对象、分组列、基因集和 pseudotime；原脚本参数在 source/ 中。",
        "output": "SCP DE/富集/动态特征对象与表；本页不重新运行。"
      }
    },
    "implementation_status": [],
    "figure_refs": [
      "templates/2026-10-22-scp-example__fig01-volcano--volcano.md"
    ],
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
    "path": "methods/scp-integration.md",
    "meta": {
      "type": "method",
      "id": "scp-integration",
      "title": "单细胞多样本整合",
      "status": "ready",
      "tags": [
        "单细胞分析"
      ],
      "keywords": [
        "SCP",
        "Seurat",
        "Integration_SCP",
        "Harmony",
        "scVI",
        "MNN",
        "fastMNN",
        "Scanorama",
        "BBKNN",
        "CSS",
        "LIGER",
        "Conos",
        "ComBat",
        "批次校正"
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
      "summary": "SCP 单细胞多样本整合的原始脚本与作者实现记录；分析问题见批次整合家族。",
      "data_contract": {
        "input": "含 batch 列的 Seurat 对象或批次对象列表；原脚本参数在 source/ 中。",
        "output": "SCP 整合对象与嵌入；本页不重新运行。"
      }
    },
    "implementation_status": [],
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
    "path": "methods/scp-local-source.md",
    "meta": {
      "type": "method",
      "id": "scp-local-source",
      "title": "SCP 源码本地化",
      "status": "ready",
      "tags": [
        "单细胞分析"
      ],
      "keywords": [
        "SCP",
        "SingleCellPipeline",
        "源码本地化",
        "Seurat",
        "reticulate",
        "Rcpp",
        "GPL-3"
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
      "summary": "SCP v0.5.6 源码本地化与加载器资料；不是可执行分析，也不是独立方法家族。",
      "data_contract": {
        "input": "SCP v0.5.6 原始源码、DESCRIPTION 和依赖包。",
        "output": "可 source 的 SCP_local 环境、加载器和补丁说明；不产生分析结果。"
      }
    },
    "implementation_status": [],
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
    "implementation_status": [],
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
    "path": "methods/scp-trajectory-velocity.md",
    "meta": {
      "type": "method",
      "id": "scp-trajectory-velocity",
      "title": "单细胞轨迹推断与 RNA 速度",
      "status": "ready",
      "tags": [
        "单细胞分析"
      ],
      "keywords": [
        "SCP",
        "Seurat",
        "RunSlingshot",
        "RunMonocle2",
        "RunMonocle3",
        "RunPAGA",
        "RunSCVELO",
        "RunPalantir",
        "RunWOT",
        "RNA velocity",
        "pseudotime",
        "lineage",
        "PAGA"
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
      "summary": "SCP 轨迹与 RNA 速度的原始脚本和作者实现记录；分析问题见轨迹、速度和动态特征家族。",
      "data_contract": {
        "input": "Seurat 对象、UMAP、cluster/pseudotime 及 spliced/unspliced layers；原脚本参数在 source/ 中。",
        "output": "SCP 轨迹/速度对象与结果；本页不重新运行。"
      }
    },
    "implementation_status": [],
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
    "path": "methods/scp-visualization-interface.md",
    "meta": {
      "type": "method",
      "id": "scp-visualization-interface",
      "title": "SCP 绘图函数与图接口映射",
      "status": "ready",
      "tags": [
        "单细胞分析",
        "其他数据图"
      ],
      "keywords": [
        "SCP",
        "Seurat",
        "CellDimPlot",
        "FeatureDimPlot",
        "CellStatPlot",
        "FeatureStatPlot",
        "GroupHeatmap",
        "FeatureHeatmap",
        "CellCorHeatmap",
        "CellDensityPlot",
        "EnrichmentPlot",
        "GSEAPlot",
        "DynamicPlot",
        "DynamicHeatmap",
        "LineagePlot",
        "PAGAPlot",
        "VelocityPlot",
        "VolcanoPlot",
        "UMAP",
        "dotplot",
        "heatmap",
        "violin",
        "sankey"
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
      "summary": "SCP 绘图函数到 Wiki 图表接口的映射与适配资料；不是分析方法。",
      "data_contract": {
        "input": "SCP/Seurat 分析对象或已导出的表。",
        "output": "render-* 接口 CSV；适配层不重算分析或绘图统计。"
      },
      "implementations": [
        {
          "id": "scp-table-adapters",
          "title": "SCP/Seurat 表到 Wiki 接口适配层",
          "language": "R",
          "entrypoint": "code/scp_tables.R:scp_umap_groups",
          "dependencies": [],
          "verification": "verification/scp-table-adapters.json"
        }
      ]
    },
    "implementation_status": [
      {
        "id": "scp-table-adapters",
        "title": "SCP/Seurat 表到 Wiki 接口适配层",
        "state": "verified",
        "scope": "SCP/Seurat 导出表到 Wiki 绘图接口的适配层；20 个合成表检查。未验证 SCP 绘图函数视觉等价。"
      }
    ],
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
    "path": "methods/scrna-marker-annotation.md",
    "meta": {
      "type": "method",
      "id": "scrna-marker-annotation",
      "title": "单细胞标记基因注释与聚类检查",
      "status": "ready",
      "tags": [
        "单细胞分析"
      ],
      "inputs": [],
      "outputs": [],
      "source": {
        "kind": "project",
        "path": "E:\\青光眼单细胞\\annotation.R"
      },
      "license": "none",
      "cite": [],
      "favorite": false,
      "keywords": [
        "GSE251716",
        "细胞类型注释",
        "marker",
        "SCpubr",
        "UMAP",
        "点图",
        "单细胞"
      ],
      "method_kind": "technical",
      "summary": "青光眼 scRNA 课题的 marker 注释与聚类检查实现记录；分析问题见细胞类型注释与聚类家族。",
      "data_contract": {
        "input": "GSE251716 预处理后的 Seurat 对象、marker 列表和 cluster 标签。",
        "output": "作者脚本的 celltype 标签、marker 图和注释检查；本页不重新运行。"
      }
    },
    "implementation_status": [],
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
    "path": "methods/scrna-pathway-signature-ensemble.md",
    "meta": {
      "type": "method",
      "id": "scrna-pathway-signature-ensemble",
      "title": "单细胞通路签名打分与组间比较",
      "status": "ready",
      "tags": [
        "单细胞分析",
        "实验统计"
      ],
      "inputs": [],
      "outputs": [],
      "source": {
        "kind": "project",
        "path": "E:\\青光眼单细胞\\score_pathway_signatures.R"
      },
      "license": "none",
      "cite": [],
      "favorite": false,
      "keywords": [
        "GSE251716",
        "通路打分",
        "AUCell",
        "ssGSEA",
        "UCell",
        "singscore",
        "AddModuleScore",
        "热图",
        "小提琴图",
        "单细胞"
      ],
      "method_kind": "technical",
      "summary": "青光眼课题的通路签名打分与组间比较实现记录；五种分数相加是课题特定组合，不是通用标准。",
      "data_contract": {
        "input": "GSE251716 表达矩阵、GO/KEGG/标记基因集和细胞元数据。",
        "output": "作者脚本的 AddModuleScore/AUCell/ssGSEA/UCell/singscore 分数及求和；本页不重新运行。"
      }
    },
    "implementation_status": [],
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
    "path": "methods/scrna-preprocess-doublet-qc-harmony.md",
    "meta": {
      "type": "method",
      "id": "scrna-preprocess-doublet-qc-harmony",
      "title": "单细胞预处理、批次校正与聚类",
      "status": "ready",
      "tags": [
        "单细胞分析"
      ],
      "inputs": [],
      "outputs": [],
      "source": {
        "kind": "project",
        "path": "E:\\青光眼单细胞\\preprocess.R"
      },
      "license": "none",
      "cite": [],
      "favorite": false,
      "keywords": [
        "GSE251716",
        "Seurat",
        "DoubletFinder",
        "Harmony",
        "聚类",
        "质量控制",
        "单细胞"
      ],
      "method_kind": "workflow",
      "summary": "青光眼课题的预处理、QC、双细胞与 Harmony 组合流程记录；单步方法见对应家族。",
      "data_contract": {
        "input": "GSE251716 原始计数和样本元数据；流程参数在 source/ 中。",
        "output": "预处理 Seurat 对象、UMAP/cluster 和作者流程结果；本页不重新运行。"
      }
    },
    "implementation_status": [],
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
    "path": "methods/shap-explanation.md",
    "meta": {
      "type": "method",
      "id": "shap-explanation",
      "title": "基于 SHAP 的模型解释",
      "status": "ready",
      "tags": [
        "机器学习",
        "模型解释与特征重要性"
      ],
      "inputs": [],
      "outputs": [
        "shap-summary",
        "shap-samples"
      ],
      "source": {
        "kind": "post",
        "gallery_entry": "2026-08-17-shap-feature-mechanism/figures/fig01-shap-a-f"
      },
      "license": "none",
      "cite": [
        "Lundberg & Lee. A Unified Approach to Interpreting Model Predictions. NeurIPS, 2017.",
        "Lundberg et al. From local explanations to global understanding with explainable AI for trees. Nature Machine Intelligence, 2020.",
        "SHAP TreeExplainer official documentation. https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html",
        "SHAP LinearExplainer official documentation. https://shap.readthedocs.io/en/latest/generated/shap.LinearExplainer.html",
        "SHAP Explainer official documentation. https://shap.readthedocs.io/en/latest/generated/shap.Explainer.html"
      ],
      "favorite": false,
      "figure_relations": [
        {
          "figure": "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--bar",
          "compatibility": "direct",
          "reason": "特征级平均绝对 SHAP 及其占比对应汇总图契约。",
          "prerequisites": [
            "同一已明确模型输出、解释对象和背景定义；不可混合不同输出单位。",
            "使用真实 SHAP 表；示例估读/合成数据仅作画法参考。",
            "模板为历史固定尺寸实现；任意 n、长标签与配色须另查可读性，尚未迁移为自适应模板。"
          ],
          "adaptation": "",
          "evidence": [
            "methods/shap-explanation.md#输出",
            "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--bar/spec.json",
            "interfaces/shap-summary.md"
          ],
          "verification": {
            "state": "not_run",
            "scope": "本轮仅核对知识含义与现存契约，未做实际课题分析→出图联调。",
            "evidence": []
          }
        },
        {
          "figure": "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--beeswarm",
          "compatibility": "direct",
          "reason": "逐样本×特征的带符号 SHAP 和着色特征值对应蜂群图契约。",
          "prerequisites": [
            "同一已明确模型输出、解释对象和背景定义；不可混合不同输出单位。",
            "使用真实 SHAP 表；示例估读/合成数据仅作画法参考。",
            "模板为历史固定尺寸实现；任意 n、长标签与配色须另查可读性，尚未迁移为自适应模板。"
          ],
          "adaptation": "",
          "evidence": [
            "methods/shap-explanation.md#输出",
            "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--beeswarm/spec.json",
            "interfaces/shap-samples.md"
          ],
          "verification": {
            "state": "not_run",
            "scope": "本轮仅核对知识含义与现存契约，未做实际课题分析→出图联调。",
            "evidence": []
          }
        },
        {
          "figure": "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--radial-bar",
          "compatibility": "direct",
          "reason": "特征级平均绝对 SHAP 及其占比对应汇总图契约。",
          "prerequisites": [
            "同一已明确模型输出、解释对象和背景定义；不可混合不同输出单位。",
            "使用真实 SHAP 表；示例估读/合成数据仅作画法参考。",
            "模板为历史固定尺寸实现；任意 n、长标签与配色须另查可读性，尚未迁移为自适应模板。"
          ],
          "adaptation": "",
          "evidence": [
            "methods/shap-explanation.md#输出",
            "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--radial-bar/spec.json",
            "interfaces/shap-summary.md"
          ],
          "verification": {
            "state": "not_run",
            "scope": "本轮仅核对知识含义与现存契约，未做实际课题分析→出图联调。",
            "evidence": []
          }
        }
      ],
      "keywords": [
        "SHAP",
        "方法家族",
        "模型解释"
      ],
      "method_kind": "analysis",
      "purposes": [
        "模型解释"
      ],
      "summary": "对既定模型输出作 SHAP 归因，输出汇总表和逐样本贡献表；不训练、不划分数据。",
      "data_contract": {
        "input": "已拟合模型、背景 DataFrame、解释样本 DataFrame；特征列同名同序、有限数值。",
        "output": "样本×特征 SHAP 矩阵、summary 表（feature/shap/percent）、samples 长表；不产生训练或预测指标。"
      },
      "implementations": [
        {
          "id": "shap-explain-model",
          "title": "SHAP 纯函数封装",
          "language": "Python",
          "entrypoint": "code/explain_model.py:explain_model",
          "dependencies": [
            "shap",
            "numpy",
            "pandas"
          ],
          "verification": "verification/shap-explain-model.json"
        }
      ]
    },
    "implementation_status": [
      {
        "id": "shap-explain-model",
        "title": "SHAP 纯函数封装",
        "state": "verified",
        "scope": "解析线性模型 SHAP 精确解；检查 summary/samples 表、百分比、输入与模型未变、特征顺序保护。"
      }
    ],
    "figure_refs": [
      "layouts/2026-08-17-shap-feature-mechanism__fig01-shap-a-f.md",
      "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--bar.md",
      "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--beeswarm.md",
      "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--radial-bar.md"
    ],
    "preview": null,
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "已验证实现",
      "reason": "笔记已确认；仅实现收据中列明的分支和范围通过验证。",
      "templates": []
    },
    "relations": [
      {
        "method": "methods/shap-explanation.md",
        "figure": "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--bar.md",
        "method_title": "基于 SHAP 的模型解释",
        "figure_title": "SHAP 条形图（含环形 inset）",
        "method_status": "ready",
        "figure_status": "ready",
        "compatibility": "direct",
        "reason": "特征级平均绝对 SHAP 及其占比对应汇总图契约。",
        "prerequisites": [
          "同一已明确模型输出、解释对象和背景定义；不可混合不同输出单位。",
          "使用真实 SHAP 表；示例估读/合成数据仅作画法参考。",
          "模板为历史固定尺寸实现；任意 n、长标签与配色须另查可读性，尚未迁移为自适应模板。"
        ],
        "adaptation": "",
        "evidence": [
          "methods/shap-explanation.md#输出",
          "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--bar/spec.json",
          "interfaces/shap-summary.md"
        ],
        "verification": {
          "state": "not_run",
          "scope": "本轮仅核对知识含义与现存契约，未做实际课题分析→出图联调。",
          "evidence": []
        },
        "target_kind": "template",
        "active": true
      },
      {
        "method": "methods/shap-explanation.md",
        "figure": "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--beeswarm.md",
        "method_title": "基于 SHAP 的模型解释",
        "figure_title": "SHAP 蜂群图",
        "method_status": "ready",
        "figure_status": "ready",
        "compatibility": "direct",
        "reason": "逐样本×特征的带符号 SHAP 和着色特征值对应蜂群图契约。",
        "prerequisites": [
          "同一已明确模型输出、解释对象和背景定义；不可混合不同输出单位。",
          "使用真实 SHAP 表；示例估读/合成数据仅作画法参考。",
          "模板为历史固定尺寸实现；任意 n、长标签与配色须另查可读性，尚未迁移为自适应模板。"
        ],
        "adaptation": "",
        "evidence": [
          "methods/shap-explanation.md#输出",
          "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--beeswarm/spec.json",
          "interfaces/shap-samples.md"
        ],
        "verification": {
          "state": "not_run",
          "scope": "本轮仅核对知识含义与现存契约，未做实际课题分析→出图联调。",
          "evidence": []
        },
        "target_kind": "template",
        "active": true
      },
      {
        "method": "methods/shap-explanation.md",
        "figure": "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--radial-bar.md",
        "method_title": "基于 SHAP 的模型解释",
        "figure_title": "SHAP 环形贡献图",
        "method_status": "ready",
        "figure_status": "ready",
        "compatibility": "direct",
        "reason": "特征级平均绝对 SHAP 及其占比对应汇总图契约。",
        "prerequisites": [
          "同一已明确模型输出、解释对象和背景定义；不可混合不同输出单位。",
          "使用真实 SHAP 表；示例估读/合成数据仅作画法参考。",
          "模板为历史固定尺寸实现；任意 n、长标签与配色须另查可读性，尚未迁移为自适应模板。"
        ],
        "adaptation": "",
        "evidence": [
          "methods/shap-explanation.md#输出",
          "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--radial-bar/spec.json",
          "interfaces/shap-summary.md"
        ],
        "verification": {
          "state": "not_run",
          "scope": "本轮仅核对知识含义与现存契约，未做实际课题分析→出图联调。",
          "evidence": []
        },
        "target_kind": "template",
        "active": true
      }
    ]
  },
  {
    "path": "methods/trajectory-inference.md",
    "meta": {
      "type": "method",
      "id": "trajectory-inference",
      "title": "拟时序与轨迹推断",
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
      "purposes": [
        "轨迹与动态分析"
      ],
      "summary": "在低维嵌入上连接细胞群，推断 lineage 与 pseudotime；轨迹是模型假设，不是真实时间。",
      "data_contract": {
        "input": "Seurat 对象 + 稳定低维嵌入 + cluster 标签 + 起点/终点；cluster 是轨迹状态，不是细胞类型断言。",
        "output": "每细胞 lineage pseudotime 与 BranchID（Seurat metadata）；曲线对象在 tools。"
      },
      "implementations": [
        {
          "id": "scp-slingshot",
          "title": "SCP RunSlingshot 封装",
          "language": "R",
          "entrypoint": "code/analysis.R:run_trajectory_inference",
          "dependencies": [
            "Seurat",
            "slingshot"
          ],
          "verification": "verification/scp-slingshot.json"
        }
      ],
      "keywords": [
        "Slingshot",
        "pseudotime",
        "lineage",
        "Monocle",
        "PAGA",
        "轨迹",
        "SCP"
      ],
      "figure_relations": [
        {
          "figure": "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap",
          "compatibility": "adaptable",
          "reason": "轨迹分组/lineage 标签可作为 UMAP 着色变量；现有模板不画 lineage 曲线。",
          "prerequisites": [
            "UMAP 坐标与 group 来自同一对象；cell_id 一致。",
            "group 为 cluster/lineage 分组；group_levels 由课题给出。"
          ],
          "adaptation": "导出 render-umap-groups.csv（group=cluster/lineage）；曲线需另建模板。",
          "evidence": [
            "methods/trajectory-inference.md#输出",
            "methods/scp-trajectory-velocity.md#知识关联检查",
            "methods/scp-trajectory-velocity.md#输出",
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
          "figure": "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap",
          "compatibility": "adaptable",
          "reason": "pseudotime 可作为 feature 长表画在 UMAP 上；模板不拟合轨迹。",
          "prerequisites": [
            "值与 UMAP 坐标来自同一细胞集合；cell_id 一致。",
            "value 的含义/单位明确；无 NA。"
          ],
          "adaptation": "导出 render-umap-feature-long.csv（feature=pseudotime, value=Lineage1）。",
          "evidence": [
            "methods/trajectory-inference.md#输出",
            "methods/scp-trajectory-velocity.md#知识关联检查",
            "methods/scp-trajectory-velocity.md#输出",
            "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap/spec.json",
            "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap/verify/verify.json"
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
          "reason": "pseudotime 按 cluster/lineage 分组的分布可用分组小提琴展示；模板不做轨迹或检验。",
          "prerequisites": [
            "同一 pseudotime/lineage 定义；celltype/group 标签一致。",
            "p/mean/SD 若展示，由分析阶段预计算；细胞级 p 不能当样本级推断。"
          ],
          "adaptation": "导出 render-grouped-values.csv（celltype/group, value=pseudotime）。",
          "evidence": [
            "methods/trajectory-inference.md#输出",
            "methods/scp-trajectory-velocity.md#知识关联检查",
            "methods/scp-trajectory-velocity.md#输出",
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
    "implementation_status": [
      {
        "id": "scp-slingshot",
        "title": "SCP RunSlingshot 封装",
        "state": "verified",
        "scope": "实际调用 SCP RunSlingshot：pancreas_sub 80 细胞，CellType 分组，UMAP 1:2；比较 pseudotime 与 BranchID。"
      }
    ],
    "figure_refs": [
      "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap.md",
      "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap.md",
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
        "method": "methods/trajectory-inference.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap.md",
        "method_title": "拟时序与轨迹推断",
        "figure_title": "CNS 细胞类型 UMAP",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "轨迹分组/lineage 标签可作为 UMAP 着色变量；现有模板不画 lineage 曲线。",
        "prerequisites": [
          "UMAP 坐标与 group 来自同一对象；cell_id 一致。",
          "group 为 cluster/lineage 分组；group_levels 由课题给出。"
        ],
        "adaptation": "导出 render-umap-groups.csv（group=cluster/lineage）；曲线需另建模板。",
        "evidence": [
          "methods/trajectory-inference.md#输出",
          "methods/scp-trajectory-velocity.md#知识关联检查",
          "methods/scp-trajectory-velocity.md#输出",
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
        "method": "methods/trajectory-inference.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap.md",
        "method_title": "拟时序与轨迹推断",
        "figure_title": "marker 特征 UMAP 小多图",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "pseudotime 可作为 feature 长表画在 UMAP 上；模板不拟合轨迹。",
        "prerequisites": [
          "值与 UMAP 坐标来自同一细胞集合；cell_id 一致。",
          "value 的含义/单位明确；无 NA。"
        ],
        "adaptation": "导出 render-umap-feature-long.csv（feature=pseudotime, value=Lineage1）。",
        "evidence": [
          "methods/trajectory-inference.md#输出",
          "methods/scp-trajectory-velocity.md#知识关联检查",
          "methods/scp-trajectory-velocity.md#输出",
          "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap/spec.json",
          "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap/verify/verify.json"
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
        "method": "methods/trajectory-inference.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig06-pathway-violin--violin.md",
        "method_title": "拟时序与轨迹推断",
        "figure_title": "分组小提琴图（含统计标注）",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "pseudotime 按 cluster/lineage 分组的分布可用分组小提琴展示；模板不做轨迹或检验。",
        "prerequisites": [
          "同一 pseudotime/lineage 定义；celltype/group 标签一致。",
          "p/mean/SD 若展示，由分析阶段预计算；细胞级 p 不能当样本级推断。"
        ],
        "adaptation": "导出 render-grouped-values.csv（celltype/group, value=pseudotime）。",
        "evidence": [
          "methods/trajectory-inference.md#输出",
          "methods/scp-trajectory-velocity.md#知识关联检查",
          "methods/scp-trajectory-velocity.md#输出",
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
    "path": "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--bar.md",
    "meta": {
      "type": "template",
      "id": "2026-08-17-shap-feature-mechanism__fig01-shap-a-f--bar",
      "title": "SHAP 条形图（含环形 inset）",
      "status": "ready",
      "layouts": [
        "2026-08-17-shap-feature-mechanism__fig01-shap-a-f"
      ],
      "panels": [
        "A",
        "D"
      ],
      "language": "python",
      "chart_types": [
        "bar"
      ],
      "favorite": false,
      "tags": [
        "机器学习",
        "模型解释与特征重要性",
        "化学信息与QSAR"
      ],
      "keywords": [
        "SHAP",
        "LightGBM",
        "CatBoost",
        "pLC50",
        "AR-DBP",
        "QSAR"
      ]
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/wiki/templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--bar/preview.png",
      "kind": "replay",
      "label": "模板回放"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "可用",
      "reason": "已确认可用；当前笔记与回放完整。",
      "templates": []
    },
    "relations": [
      {
        "method": "methods/shap-explanation.md",
        "figure": "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--bar.md",
        "method_title": "基于 SHAP 的模型解释",
        "figure_title": "SHAP 条形图（含环形 inset）",
        "method_status": "ready",
        "figure_status": "ready",
        "compatibility": "direct",
        "reason": "特征级平均绝对 SHAP 及其占比对应汇总图契约。",
        "prerequisites": [
          "同一已明确模型输出、解释对象和背景定义；不可混合不同输出单位。",
          "使用真实 SHAP 表；示例估读/合成数据仅作画法参考。",
          "模板为历史固定尺寸实现；任意 n、长标签与配色须另查可读性，尚未迁移为自适应模板。"
        ],
        "adaptation": "",
        "evidence": [
          "methods/shap-explanation.md#输出",
          "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--bar/spec.json",
          "interfaces/shap-summary.md"
        ],
        "verification": {
          "state": "not_run",
          "scope": "本轮仅核对知识含义与现存契约，未做实际课题分析→出图联调。",
          "evidence": []
        },
        "target_kind": "template",
        "active": true
      }
    ]
  },
  {
    "path": "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--beeswarm.md",
    "meta": {
      "type": "template",
      "id": "2026-08-17-shap-feature-mechanism__fig01-shap-a-f--beeswarm",
      "title": "SHAP 蜂群图",
      "status": "ready",
      "layouts": [
        "2026-08-17-shap-feature-mechanism__fig01-shap-a-f"
      ],
      "panels": [
        "B",
        "E"
      ],
      "language": "python",
      "chart_types": [
        "beeswarm"
      ],
      "favorite": false,
      "tags": [
        "机器学习",
        "模型解释与特征重要性",
        "化学信息与QSAR"
      ],
      "keywords": [
        "SHAP",
        "LightGBM",
        "CatBoost",
        "pLC50",
        "AR-DBP",
        "QSAR"
      ]
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/wiki/templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--beeswarm/preview.png",
      "kind": "replay",
      "label": "模板回放"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "可用",
      "reason": "已确认可用；当前笔记与回放完整。",
      "templates": []
    },
    "relations": [
      {
        "method": "methods/shap-explanation.md",
        "figure": "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--beeswarm.md",
        "method_title": "基于 SHAP 的模型解释",
        "figure_title": "SHAP 蜂群图",
        "method_status": "ready",
        "figure_status": "ready",
        "compatibility": "direct",
        "reason": "逐样本×特征的带符号 SHAP 和着色特征值对应蜂群图契约。",
        "prerequisites": [
          "同一已明确模型输出、解释对象和背景定义；不可混合不同输出单位。",
          "使用真实 SHAP 表；示例估读/合成数据仅作画法参考。",
          "模板为历史固定尺寸实现；任意 n、长标签与配色须另查可读性，尚未迁移为自适应模板。"
        ],
        "adaptation": "",
        "evidence": [
          "methods/shap-explanation.md#输出",
          "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--beeswarm/spec.json",
          "interfaces/shap-samples.md"
        ],
        "verification": {
          "state": "not_run",
          "scope": "本轮仅核对知识含义与现存契约，未做实际课题分析→出图联调。",
          "evidence": []
        },
        "target_kind": "template",
        "active": true
      }
    ]
  },
  {
    "path": "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--radial-bar.md",
    "meta": {
      "type": "template",
      "id": "2026-08-17-shap-feature-mechanism__fig01-shap-a-f--radial-bar",
      "title": "SHAP 环形贡献图",
      "status": "ready",
      "layouts": [
        "2026-08-17-shap-feature-mechanism__fig01-shap-a-f"
      ],
      "panels": [
        "C",
        "F"
      ],
      "language": "python",
      "chart_types": [
        "radial-bar"
      ],
      "favorite": false,
      "tags": [
        "机器学习",
        "模型解释与特征重要性",
        "化学信息与QSAR"
      ],
      "keywords": [
        "SHAP",
        "LightGBM",
        "CatBoost",
        "pLC50",
        "AR-DBP",
        "QSAR"
      ]
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/wiki/templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--radial-bar/preview.png",
      "kind": "replay",
      "label": "模板回放"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "可用",
      "reason": "已确认可用；当前笔记与回放完整。",
      "templates": []
    },
    "relations": [
      {
        "method": "methods/shap-explanation.md",
        "figure": "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--radial-bar.md",
        "method_title": "基于 SHAP 的模型解释",
        "figure_title": "SHAP 环形贡献图",
        "method_status": "ready",
        "figure_status": "ready",
        "compatibility": "direct",
        "reason": "特征级平均绝对 SHAP 及其占比对应汇总图契约。",
        "prerequisites": [
          "同一已明确模型输出、解释对象和背景定义；不可混合不同输出单位。",
          "使用真实 SHAP 表；示例估读/合成数据仅作画法参考。",
          "模板为历史固定尺寸实现；任意 n、长标签与配色须另查可读性，尚未迁移为自适应模板。"
        ],
        "adaptation": "",
        "evidence": [
          "methods/shap-explanation.md#输出",
          "templates/2026-08-17-shap-feature-mechanism__fig01-shap-a-f--radial-bar/spec.json",
          "interfaces/shap-summary.md"
        ],
        "verification": {
          "state": "not_run",
          "scope": "本轮仅核对知识含义与现存契约，未做实际课题分析→出图联调。",
          "evidence": []
        },
        "target_kind": "template",
        "active": true
      }
    ]
  },
  {
    "path": "templates/2026-10-19-regression-stability__fig03-density-panel--density-scatter.md",
    "meta": {
      "type": "template",
      "id": "2026-10-19-regression-stability__fig03-density-panel--density-scatter",
      "title": "密度散点与边缘分布",
      "status": "ready",
      "layouts": [
        "2026-10-19-regression-stability__fig03-density-panel"
      ],
      "panels": [
        "A"
      ],
      "language": "python",
      "tags": [
        "机器学习",
        "实验统计"
      ],
      "chart_types": [
        "density-scatter"
      ],
      "favorite": false,
      "keywords": [
        "regression",
        "cross-validation",
        "回归评估",
        "模型比较",
        "折外预测"
      ]
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/wiki/templates/2026-10-19-regression-stability__fig03-density-panel--density-scatter/preview.png",
      "kind": "replay",
      "label": "模板回放"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "可用",
      "reason": "已确认可用；当前笔记与回放完整。",
      "templates": []
    },
    "relations": [
      {
        "method": "methods/regression-resampling-evaluation.md",
        "figure": "templates/2026-10-19-regression-stability__fig03-density-panel--density-scatter.md",
        "method_title": "回归模型的重采样评估与折外预测",
        "figure_title": "密度散点与边缘分布",
        "method_status": "ready",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "可用本绘图模板表达真实预测的配对分布，但需上游明确准备RGB/边缘表。",
        "prerequisites": [
          "连续结局且同一原始量纲；明确样本、模型、重复/折身份。",
          "需先确定密度/边缘分布策略与注释统计，不用估读颜色倒推真实频数。"
        ],
        "adaptation": "课题内准备坐标/RGB/边缘条及真实注释；不从估读点重建频数，密度算法仍需确认。",
        "evidence": [
          "methods/regression-resampling-evaluation.md#输入",
          "layouts/2026-10-19-regression-stability__fig03-density-panel.md#适用",
          "templates/2026-10-19-regression-stability__fig03-density-panel--density-scatter/spec.json",
          "templates/2026-10-19-regression-stability__fig03-density-panel--density-scatter/verify/function-verification.json"
        ],
        "verification": {
          "state": "not_run",
          "scope": "本轮只验证模板绘图与合成规模；未验证真实方法→准备表→出图流水线。",
          "evidence": []
        },
        "target_kind": "template",
        "active": true
      }
    ]
  },
  {
    "path": "templates/2026-10-19-regression-stability__fig04-boxplot-panel--boxplot.md",
    "meta": {
      "type": "template",
      "id": "2026-10-19-regression-stability__fig04-boxplot-panel--boxplot",
      "title": "箱线、散点与均值",
      "status": "ready",
      "layouts": [
        "2026-10-19-regression-stability__fig04-boxplot-panel"
      ],
      "panels": [
        "A"
      ],
      "language": "python",
      "tags": [
        "机器学习",
        "实验统计"
      ],
      "chart_types": [
        "boxplot"
      ],
      "favorite": false,
      "keywords": [
        "regression",
        "cross-validation",
        "回归评估",
        "模型比较",
        "折外预测"
      ]
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/wiki/templates/2026-10-19-regression-stability__fig04-boxplot-panel--boxplot/preview.png",
      "kind": "replay",
      "label": "模板回放"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "可用",
      "reason": "已确认可用；当前笔记与回放完整。",
      "templates": []
    },
    "relations": [
      {
        "method": "methods/regression-resampling-evaluation.md",
        "figure": "templates/2026-10-19-regression-stability__fig04-boxplot-panel--boxplot.md",
        "method_title": "回归模型的重采样评估与折外预测",
        "figure_title": "箱线、散点与均值",
        "method_status": "ready",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "逐折指标可用于该单指标分组分布，需上游按已确认规则准备同源点与箱线摘要。",
        "prerequisites": [
          "同一验证方案、指标定义与单位；明确折间相关性。",
          "按已确认的箱体/须/均值规则产生一致结果，横向抖动仅作展示。"
        ],
        "adaptation": "课题内选定指标、明确采样单位/须规则、整理同源points/summaries；不自动新写统计算法。",
        "evidence": [
          "methods/regression-resampling-evaluation.md#输出",
          "layouts/2026-10-19-regression-stability__fig04-boxplot-panel.md#适用",
          "templates/2026-10-19-regression-stability__fig04-boxplot-panel--boxplot/spec.json",
          "templates/2026-10-19-regression-stability__fig04-boxplot-panel--boxplot/verify/function-verification.json"
        ],
        "verification": {
          "state": "not_run",
          "scope": "本轮只验证模板绘图与合成规模；未验证真实方法→准备表→出图流水线。",
          "evidence": []
        },
        "target_kind": "template",
        "active": true
      }
    ]
  },
  {
    "path": "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap.md",
    "meta": {
      "type": "template",
      "id": "2026-10-22-glaucoma-scrna__fig01-cns-umap--umap",
      "title": "CNS 细胞类型 UMAP",
      "status": "ready",
      "layouts": [
        "2026-10-22-glaucoma-scrna__fig01-cns-umap"
      ],
      "panels": [
        "A"
      ],
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "chart_types": [
        "umap"
      ],
      "favorite": false,
      "keywords": [
        "GSE251716"
      ]
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/wiki/templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap/preview.png",
      "kind": "replay",
      "label": "模板回放"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "可用",
      "reason": "已确认可用；当前笔记与回放完整。",
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
        "method": "methods/cell-clustering.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap.md",
        "method_title": "单细胞聚类分析",
        "figure_title": "CNS 细胞类型 UMAP",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "cluster 标签可作为 UMAP 着色变量；模板不聚类。",
        "prerequisites": [
          "celltype 标签与 UMAP 坐标来自同一 Seurat 对象；cell_id 一致。",
          "group_levels 按注释顺序给出；不得把 cluster 编号直接当 celltype。"
        ],
        "adaptation": "导出 render-umap-groups.csv（group=cluster）；cluster 编号不是细胞类型。",
        "evidence": [
          "methods/cell-clustering.md#输出",
          "methods/scrna-marker-annotation.md#知识关联检查",
          "methods/scrna-marker-annotation.md#输出",
          "layouts/2026-10-22-glaucoma-scrna__fig01-cns-umap.md#适用",
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
        "method": "methods/cell-type-annotation.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap.md",
        "method_title": "细胞类型注释",
        "figure_title": "CNS 细胞类型 UMAP",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "预测细胞类型可作为 UMAP 着色变量；模板不执行注释。",
        "prerequisites": [
          "预测标签与 UMAP 坐标来自同一查询对象；cell_id 一致。",
          "标签不是 cluster 编号；group_levels 按注释顺序给出。"
        ],
        "adaptation": "导出 render-umap-groups.csv（group=predicted celltype）。",
        "evidence": [
          "methods/cell-type-annotation.md#输出",
          "methods/scp-annotation-projection.md#知识关联检查",
          "methods/scp-annotation-projection.md#输出",
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
        "method": "methods/dimensionality-reduction.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap.md",
        "method_title": "单细胞降维分析",
        "figure_title": "CNS 细胞类型 UMAP",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "Standard_SCP 产出 StandardUMAP2D，可作为 UMAP 分组着色；模板只画表，不降维。",
        "prerequisites": [
          "坐标与 group 来自同一嵌入；cell_id 唯一；坐标无 NA。",
          "group 明确为 cluster 或 celltype；group_levels 由课题给出。"
        ],
        "adaptation": "导出 render-umap-groups.csv（cell_id, umap_1, umap_2, group）。",
        "evidence": [
          "methods/dimensionality-reduction.md#输出",
          "methods/scp-standard-workflow.md#知识关联检查",
          "methods/scp-standard-workflow.md#输出",
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
        "method": "methods/doublet-detection.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap.md",
        "method_title": "双细胞检测",
        "figure_title": "CNS 细胞类型 UMAP",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "双细胞标签可作为 UMAP 着色变量检查分布；模板不检测双细胞。",
        "prerequisites": [
          "UMAP 坐标与 QC 标签来自同一 Seurat 对象；cell_id 一致。",
          "group_levels 显式给出；Pass/Fail 顺序固定。"
        ],
        "adaptation": "导出 render-umap-groups.csv（group=doublet class 或样本）；标签只作描述。",
        "evidence": [
          "methods/doublet-detection.md#输出",
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
        "method": "methods/reference-mapping.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap.md",
        "method_title": "参考图谱映射",
        "figure_title": "CNS 细胞类型 UMAP",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "查询细胞可按预测标签着色自身 UMAP；这不是参考 UMAP 投影，模板也不执行映射。",
        "prerequisites": [
          "预测标签与 UMAP 坐标来自同一查询对象；cell_id 一致。",
          "标签不是 cluster 编号；group_levels 按注释顺序给出。"
        ],
        "adaptation": "导出 render-umap-groups.csv（group=predicted label）；不得把查询 UMAP 说成参考投影。",
        "evidence": [
          "methods/reference-mapping.md#输出",
          "methods/scp-annotation-projection.md#知识关联检查",
          "methods/scp-annotation-projection.md#输出",
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
        "method": "methods/trajectory-inference.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig01-cns-umap--umap.md",
        "method_title": "拟时序与轨迹推断",
        "figure_title": "CNS 细胞类型 UMAP",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "轨迹分组/lineage 标签可作为 UMAP 着色变量；现有模板不画 lineage 曲线。",
        "prerequisites": [
          "UMAP 坐标与 group 来自同一对象；cell_id 一致。",
          "group 为 cluster/lineage 分组；group_levels 由课题给出。"
        ],
        "adaptation": "导出 render-umap-groups.csv（group=cluster/lineage）；曲线需另建模板。",
        "evidence": [
          "methods/trajectory-inference.md#输出",
          "methods/scp-trajectory-velocity.md#知识关联检查",
          "methods/scp-trajectory-velocity.md#输出",
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
      }
    ]
  },
  {
    "path": "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap.md",
    "meta": {
      "type": "template",
      "id": "2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap",
      "title": "marker 特征 UMAP 小多图",
      "status": "ready",
      "layouts": [
        "2026-10-22-glaucoma-scrna__fig02-marker-feature-umap"
      ],
      "panels": [
        "A"
      ],
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "chart_types": [
        "umap"
      ],
      "favorite": false,
      "keywords": [
        "GSE251716",
        "marker"
      ]
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/wiki/templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap/preview.png",
      "kind": "replay",
      "label": "模板回放"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "可用",
      "reason": "已确认可用；当前笔记与回放完整。",
      "templates": []
    },
    "relations": [
      {
        "method": "methods/cell-type-annotation.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap.md",
        "method_title": "细胞类型注释",
        "figure_title": "marker 特征 UMAP 小多图",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "用 marker 表达检查预测标签是否落在对应群，可复用特征 UMAP 网格；模板不做注释或检验。",
        "prerequisites": [
          "marker 表达长表与 UMAP 坐标同源；cell_id 一致。",
          "每个 feature 至少有一个正表达细胞；目标类型在 group 中存在。"
        ],
        "adaptation": "导出 render-umap-feature-long.csv（cell_id, umap_1, umap_2, group, feature, value）。",
        "evidence": [
          "methods/cell-type-annotation.md#输出",
          "methods/scp-annotation-projection.md#知识关联检查",
          "methods/scp-annotation-projection.md#输出",
          "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap/spec.json",
          "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap/verify/verify.json"
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
        "method": "methods/dimensionality-reduction.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap.md",
        "method_title": "单细胞降维分析",
        "figure_title": "marker 特征 UMAP 小多图",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "降维嵌入可与 marker 表达长表拼成特征 UMAP 网格；模板不重做降维或表达。",
        "prerequisites": [
          "UMAP 坐标与表达来自同一 Seurat 对象；cell_id 一致。",
          "目标细胞类型映射由注释步骤给出；每个 feature 至少有一个正表达细胞。"
        ],
        "adaptation": "导出 render-umap-feature-long.csv（cell_id, umap_1, umap_2, group, feature, value）。",
        "evidence": [
          "methods/dimensionality-reduction.md#输出",
          "methods/scp-standard-workflow.md#知识关联检查",
          "methods/scp-standard-workflow.md#输出",
          "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap/spec.json",
          "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap/verify/verify.json"
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
        "method": "methods/dynamic-feature-analysis.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap.md",
        "method_title": "拟时序动态特征分析",
        "figure_title": "marker 特征 UMAP 小多图",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "动态特征值可作为 feature 长表画在 UMAP 上；模板只画值，不拟合 GAM。",
        "prerequisites": [
          "值与 UMAP 坐标来自同一细胞集合；cell_id 一致。",
          "value 的含义/单位明确；无 NA。"
        ],
        "adaptation": "导出 render-umap-feature-long.csv（feature=基因/特征, value=表达或拟合值）。",
        "evidence": [
          "methods/dynamic-feature-analysis.md#输出",
          "methods/scp-de-enrichment-dynamic.md#知识关联检查",
          "methods/scp-de-enrichment-dynamic.md#输出",
          "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap/spec.json",
          "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap/verify/verify.json"
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
        "method": "methods/trajectory-inference.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap.md",
        "method_title": "拟时序与轨迹推断",
        "figure_title": "marker 特征 UMAP 小多图",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "pseudotime 可作为 feature 长表画在 UMAP 上；模板不拟合轨迹。",
        "prerequisites": [
          "值与 UMAP 坐标来自同一细胞集合；cell_id 一致。",
          "value 的含义/单位明确；无 NA。"
        ],
        "adaptation": "导出 render-umap-feature-long.csv（feature=pseudotime, value=Lineage1）。",
        "evidence": [
          "methods/trajectory-inference.md#输出",
          "methods/scp-trajectory-velocity.md#知识关联检查",
          "methods/scp-trajectory-velocity.md#输出",
          "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap/spec.json",
          "templates/2026-10-22-glaucoma-scrna__fig02-marker-feature-umap--umap/verify/verify.json"
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
    "path": "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot.md",
    "meta": {
      "type": "template",
      "id": "2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot",
      "title": "细胞类型 × 基因气泡点图",
      "status": "ready",
      "layouts": [
        "2026-10-22-glaucoma-scrna__fig03-topjournal-bubble"
      ],
      "panels": [
        "A"
      ],
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "chart_types": [
        "dotplot"
      ],
      "favorite": false,
      "keywords": [
        "GSE251716",
        "dotplot"
      ]
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/wiki/templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot/preview.png",
      "kind": "replay",
      "label": "模板回放"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "可用",
      "reason": "已确认可用；当前笔记与回放完整。",
      "templates": []
    },
    "relations": [
      {
        "method": "methods/cell-type-annotation.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot.md",
        "method_title": "细胞类型注释",
        "figure_title": "细胞类型 × 基因气泡点图",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "预测类型的 marker 平均表达/阳性比例可整理成点图，检查注释是否合理；模板不重算统计。",
        "prerequisites": [
          "avg_expression 与 pct_expressed 由表达矩阵按预测标签计算；缩放方式说明。",
          "group/feature 顺序由课题给出；target_group 只用于排序。"
        ],
        "adaptation": "导出 render-dotplot-long.csv（group, feature, avg_expression, pct_expressed, target_group）。",
        "evidence": [
          "methods/cell-type-annotation.md#输出",
          "methods/scp-annotation-projection.md#知识关联检查",
          "methods/scp-annotation-projection.md#输出",
          "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot/spec.json",
          "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot/verify/verify.json"
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
        "method": "methods/differential-expression.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot.md",
        "method_title": "差异表达分析",
        "figure_title": "细胞类型 × 基因气泡点图",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "DE 选出的 marker 可整理成 group/feature/avg_expression/pct_expressed，复用气泡点图；模板不重算 DE。",
        "prerequisites": [
          "avg_expression 与 pct_expressed 由表达矩阵按组计算，不能用 avg_log2FC 代替。",
          "group/feature 顺序由课题给出；target_group 只用于排序。"
        ],
        "adaptation": "导出 render-dotplot-long.csv（group, feature, avg_expression, pct_expressed, target_group）。",
        "evidence": [
          "methods/differential-expression.md#输出",
          "methods/scp-de-enrichment-dynamic.md#知识关联检查",
          "methods/scp-de-enrichment-dynamic.md#输出",
          "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot/spec.json",
          "templates/2026-10-22-glaucoma-scrna__fig03-topjournal-bubble--dotplot/verify/verify.json"
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
    "path": "templates/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow.md",
    "meta": {
      "type": "template",
      "id": "2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow",
      "title": "细胞比例堆叠流带图",
      "status": "ready",
      "layouts": [
        "2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow"
      ],
      "panels": [
        "A"
      ],
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "chart_types": [
        "stacked-bar-flow"
      ],
      "favorite": false,
      "keywords": [
        "GSE251716",
        "proportion"
      ]
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/wiki/templates/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow/preview.png",
      "kind": "replay",
      "label": "模板回放"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "可用",
      "reason": "已确认可用；当前笔记与回放完整。",
      "templates": []
    },
    "relations": [
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
      },
      {
        "method": "methods/cell-clustering.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow.md",
        "method_title": "单细胞聚类分析",
        "figure_title": "细胞比例堆叠流带图",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "按样本/条件统计 cluster 比例，检查组成；模板不做聚类或检验。",
        "prerequisites": [
          "每个 group 的比例归一化到 1；group/celltype 完整，无缺组。",
          "流带仅作视觉插值，不是统计估计或细胞轨迹。"
        ],
        "adaptation": "导出 render-cell-proportions.csv（group=样本, celltype=cluster, proportion）。",
        "evidence": [
          "methods/cell-clustering.md#输出",
          "methods/scrna-marker-annotation.md#知识关联检查",
          "methods/scrna-marker-annotation.md#输出",
          "layouts/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow.md#适用",
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
        "method": "methods/cell-type-annotation.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow.md",
        "method_title": "细胞类型注释",
        "figure_title": "细胞比例堆叠流带图",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "按样本/条件统计预测类型比例，检查注释组成；模板不做统计检验。",
        "prerequisites": [
          "每个 group 的比例归一化到 1；group 为样本/条件，celltype 为预测标签。",
          "比例是描述性；组间差异不能由该图直接推断。"
        ],
        "adaptation": "导出 render-cell-proportions.csv（group, celltype, proportion）。",
        "evidence": [
          "methods/cell-type-annotation.md#输出",
          "methods/scp-annotation-projection.md#知识关联检查",
          "methods/scp-annotation-projection.md#输出",
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
        "method": "methods/doublet-detection.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow.md",
        "method_title": "双细胞检测",
        "figure_title": "细胞比例堆叠流带图",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "按样本统计双细胞比例可复用比例图；模板不做双细胞检测或统计检验。",
        "prerequisites": [
          "每个 group 的 celltype 比例归一化到 1；group 为样本或条件，celltype 为 CellQC。",
          "组间比较只作描述，不能当样本级推断。"
        ],
        "adaptation": "导出 render-cell-proportions.csv（group=样本, celltype=doublet class, proportion）。",
        "evidence": [
          "methods/doublet-detection.md#输出",
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
        "method": "methods/reference-mapping.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig04-cell-proportion-flow--stacked-bar-flow.md",
        "method_title": "参考图谱映射",
        "figure_title": "细胞比例堆叠流带图",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "按样本统计预测标签比例，检查映射组成；模板不做映射或检验。",
        "prerequisites": [
          "每个 group 的比例归一化到 1；group 为样本/条件，celltype 为预测标签。",
          "比例是描述性；组间差异不能由该图直接推断。"
        ],
        "adaptation": "导出 render-cell-proportions.csv（group=样本, celltype=predicted label, proportion）。",
        "evidence": [
          "methods/reference-mapping.md#输出",
          "methods/scp-annotation-projection.md#知识关联检查",
          "methods/scp-annotation-projection.md#输出",
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
  },
  {
    "path": "templates/2026-10-22-glaucoma-scrna__fig06-pathway-violin--violin.md",
    "meta": {
      "type": "template",
      "id": "2026-10-22-glaucoma-scrna__fig06-pathway-violin--violin",
      "title": "分组小提琴图（含统计标注）",
      "status": "ready",
      "layouts": [
        "2026-10-22-glaucoma-scrna__fig06-pathway-violin"
      ],
      "panels": [
        "A"
      ],
      "language": "r",
      "tags": [
        "单细胞分析",
        "实验统计"
      ],
      "chart_types": [
        "violin"
      ],
      "favorite": false,
      "keywords": [
        "GSE251716",
        "pathway"
      ]
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/wiki/templates/2026-10-22-glaucoma-scrna__fig06-pathway-violin--violin/preview.png",
      "kind": "replay",
      "label": "模板回放"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "可用",
      "reason": "已确认可用；当前笔记与回放完整。",
      "templates": []
    },
    "relations": [
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
      },
      {
        "method": "methods/dynamic-feature-analysis.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig06-pathway-violin--violin.md",
        "method_title": "拟时序动态特征分析",
        "figure_title": "分组小提琴图（含统计标注）",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "动态特征或 pseudotime 按 cluster/lineage 分组的分布可用分组小提琴展示；模板不做轨迹或检验。",
        "prerequisites": [
          "同一 pseudotime/lineage 定义；celltype/group 标签一致。",
          "p/mean/SD 若展示，由分析阶段预计算；细胞级 p 不能当样本级推断。"
        ],
        "adaptation": "导出 render-grouped-values.csv（group=cluster/lineage, value=特征值/pseudotime）。",
        "evidence": [
          "methods/dynamic-feature-analysis.md#输出",
          "methods/scp-trajectory-velocity.md#知识关联检查",
          "methods/scp-trajectory-velocity.md#输出",
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
      },
      {
        "method": "methods/gene-set-scoring.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig06-pathway-violin--violin.md",
        "method_title": "基因集与通路签名打分",
        "figure_title": "分组小提琴图（含统计标注）",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "通路签名分数按细胞类型/组展示分布，可复用小提琴模板；模板不重算分数或检验。",
        "prerequisites": [
          "同一 pathway 定义和单位；celltype/group 标签一致。",
          "p/mean/SD 由分析阶段预计算并说明来源；细胞水平 p 仅作描述，不能当样本级推断。"
        ],
        "adaptation": "导出 render-grouped-values.csv 和可选的 render-group-summaries.csv；细胞级 p 只作描述。",
        "evidence": [
          "methods/gene-set-scoring.md#输出",
          "methods/scrna-pathway-signature-ensemble.md#知识关联检查",
          "methods/scrna-pathway-signature-ensemble.md#输出",
          "layouts/2026-10-22-glaucoma-scrna__fig06-pathway-violin.md#适用",
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
      },
      {
        "method": "methods/trajectory-inference.md",
        "figure": "templates/2026-10-22-glaucoma-scrna__fig06-pathway-violin--violin.md",
        "method_title": "拟时序与轨迹推断",
        "figure_title": "分组小提琴图（含统计标注）",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "pseudotime 按 cluster/lineage 分组的分布可用分组小提琴展示；模板不做轨迹或检验。",
        "prerequisites": [
          "同一 pseudotime/lineage 定义；celltype/group 标签一致。",
          "p/mean/SD 若展示，由分析阶段预计算；细胞级 p 不能当样本级推断。"
        ],
        "adaptation": "导出 render-grouped-values.csv（celltype/group, value=pseudotime）。",
        "evidence": [
          "methods/trajectory-inference.md#输出",
          "methods/scp-trajectory-velocity.md#知识关联检查",
          "methods/scp-trajectory-velocity.md#输出",
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
    "path": "templates/2026-10-22-scp-example__fig01-volcano--volcano.md",
    "meta": {
      "type": "template",
      "id": "2026-10-22-scp-example__fig01-volcano--volcano",
      "title": "差异表达火山图",
      "status": "ready",
      "layouts": [
        "2026-10-22-scp-example__fig01-volcano"
      ],
      "panels": [
        "A"
      ],
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "keywords": [
        "SCP",
        "pancreas_sub",
        "volcano",
        "DE"
      ],
      "chart_types": [
        "volcano"
      ],
      "favorite": false
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/wiki/templates/2026-10-22-scp-example__fig01-volcano--volcano/preview.png",
      "kind": "replay",
      "label": "模板回放"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "可用",
      "reason": "已确认可用；当前笔记与回放完整。",
      "templates": []
    },
    "relations": [
      {
        "method": "methods/differential-expression.md",
        "figure": "templates/2026-10-22-scp-example__fig01-volcano--volcano.md",
        "method_title": "差异表达分析",
        "figure_title": "差异表达火山图",
        "method_status": "draft",
        "figure_status": "ready",
        "compatibility": "adaptable",
        "reason": "DE 表可整理成 render-de-results，火山图模板消费该表；模板不重跑检验。",
        "prerequisites": [
          "group1 单一；pct_1/pct_2 为 0–1；p_val_adj >0；gene 组内唯一。",
          "模板不重跑 DE 或 p 值校正；阈值由 style 显式给出。"
        ],
        "adaptation": "从 AllMarkers 表导出 gene、avg_log2FC、p_val_adj 等字段到 render-de-results。",
        "evidence": [
          "methods/differential-expression.md#输出",
          "methods/scp-de-enrichment-dynamic.md#知识关联检查",
          "methods/scp-de-enrichment-dynamic.md#输出",
          "templates/2026-10-22-scp-example__fig01-volcano--volcano/spec.json",
          "templates/2026-10-22-scp-example__fig01-volcano--volcano/verify/verify.json"
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
    "path": "templates/2026-10-22-scp-example__fig02-ring--ring.md",
    "meta": {
      "type": "template",
      "id": "2026-10-22-scp-example__fig02-ring--ring",
      "title": "分组构成同心环图",
      "status": "ready",
      "layouts": [
        "2026-10-22-scp-example__fig02-ring"
      ],
      "panels": [
        "A"
      ],
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "keywords": [
        "SCP",
        "pancreas_sub",
        "ring",
        "composition"
      ],
      "chart_types": [
        "ring"
      ],
      "favorite": false
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/wiki/templates/2026-10-22-scp-example__fig02-ring--ring/preview.png",
      "kind": "replay",
      "label": "模板回放"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "可用",
      "reason": "已确认可用；当前笔记与回放完整。",
      "templates": []
    },
    "relations": []
  },
  {
    "path": "templates/2026-10-22-scp-example__fig03-pie--pie.md",
    "meta": {
      "type": "template",
      "id": "2026-10-22-scp-example__fig03-pie--pie",
      "title": "分组构成饼图",
      "status": "ready",
      "layouts": [
        "2026-10-22-scp-example__fig03-pie"
      ],
      "panels": [
        "A"
      ],
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "keywords": [
        "SCP",
        "pancreas_sub",
        "pie",
        "composition"
      ],
      "chart_types": [
        "pie"
      ],
      "favorite": false
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/wiki/templates/2026-10-22-scp-example__fig03-pie--pie/preview.png",
      "kind": "replay",
      "label": "模板回放"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "可用",
      "reason": "已确认可用；当前笔记与回放完整。",
      "templates": []
    },
    "relations": []
  },
  {
    "path": "templates/2026-10-22-scp-example__fig04-rose--rose.md",
    "meta": {
      "type": "template",
      "id": "2026-10-22-scp-example__fig04-rose--rose",
      "title": "分组构成玫瑰图",
      "status": "ready",
      "layouts": [
        "2026-10-22-scp-example__fig04-rose"
      ],
      "panels": [
        "A"
      ],
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "keywords": [
        "SCP",
        "pancreas_sub",
        "rose",
        "composition"
      ],
      "chart_types": [
        "rose"
      ],
      "favorite": false
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/wiki/templates/2026-10-22-scp-example__fig04-rose--rose/preview.png",
      "kind": "replay",
      "label": "模板回放"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "可用",
      "reason": "已确认可用；当前笔记与回放完整。",
      "templates": []
    },
    "relations": []
  },
  {
    "path": "templates/2026-10-22-scp-example__fig05-trend--trend.md",
    "meta": {
      "type": "template",
      "id": "2026-10-22-scp-example__fig05-trend--trend",
      "title": "分组构成趋势图",
      "status": "ready",
      "layouts": [
        "2026-10-22-scp-example__fig05-trend"
      ],
      "panels": [
        "A"
      ],
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "keywords": [
        "SCP",
        "pancreas_sub",
        "trend",
        "composition"
      ],
      "chart_types": [
        "trend"
      ],
      "favorite": false
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/wiki/templates/2026-10-22-scp-example__fig05-trend--trend/preview.png",
      "kind": "replay",
      "label": "模板回放"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "可用",
      "reason": "已确认可用；当前笔记与回放完整。",
      "templates": []
    },
    "relations": []
  },
  {
    "path": "templates/2026-10-22-scp-example__fig06-area--area.md",
    "meta": {
      "type": "template",
      "id": "2026-10-22-scp-example__fig06-area--area",
      "title": "分组构成面积图",
      "status": "ready",
      "layouts": [
        "2026-10-22-scp-example__fig06-area"
      ],
      "panels": [
        "A"
      ],
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "keywords": [
        "SCP",
        "pancreas_sub",
        "area",
        "composition"
      ],
      "chart_types": [
        "area"
      ],
      "favorite": false
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/wiki/templates/2026-10-22-scp-example__fig06-area--area/preview.png",
      "kind": "replay",
      "label": "模板回放"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "可用",
      "reason": "已确认可用；当前笔记与回放完整。",
      "templates": []
    },
    "relations": []
  },
  {
    "path": "templates/2026-10-22-scp-example__fig07-dot--dot.md",
    "meta": {
      "type": "template",
      "id": "2026-10-22-scp-example__fig07-dot--dot",
      "title": "分组构成点图",
      "status": "ready",
      "layouts": [
        "2026-10-22-scp-example__fig07-dot"
      ],
      "panels": [
        "A"
      ],
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "keywords": [
        "SCP",
        "pancreas_sub",
        "dot",
        "composition"
      ],
      "chart_types": [
        "dot"
      ],
      "favorite": false
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/wiki/templates/2026-10-22-scp-example__fig07-dot--dot/preview.png",
      "kind": "replay",
      "label": "模板回放"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "可用",
      "reason": "已确认可用；当前笔记与回放完整。",
      "templates": []
    },
    "relations": []
  },
  {
    "path": "templates/2026-10-22-scp-example__fig08-group-heatmap--heatmap.md",
    "meta": {
      "type": "template",
      "id": "2026-10-22-scp-example__fig08-group-heatmap--heatmap",
      "title": "分组热图（多分组注释）",
      "status": "ready",
      "layouts": [
        "2026-10-22-scp-example__fig08-group-heatmap"
      ],
      "panels": [
        "A"
      ],
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "chart_types": [
        "heatmap"
      ],
      "favorite": false
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/wiki/templates/2026-10-22-scp-example__fig08-group-heatmap--heatmap/preview.png",
      "kind": "replay",
      "label": "模板回放"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "可用",
      "reason": "已确认可用；当前笔记与回放完整。",
      "templates": []
    },
    "relations": []
  },
  {
    "path": "templates/2026-10-22-scp-example__fig09-bar--bar.md",
    "meta": {
      "type": "template",
      "id": "2026-10-22-scp-example__fig09-bar--bar",
      "title": "分组计数柱图",
      "status": "ready",
      "layouts": [
        "2026-10-22-scp-example__fig09-bar"
      ],
      "panels": [
        "A"
      ],
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "chart_types": [
        "bar"
      ],
      "favorite": false
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/wiki/templates/2026-10-22-scp-example__fig09-bar--bar/preview.png",
      "kind": "replay",
      "label": "模板回放"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "可用",
      "reason": "已确认可用；当前笔记与回放完整。",
      "templates": []
    },
    "relations": []
  },
  {
    "path": "templates/2026-10-22-scp-example__fig10-sankey--sankey.md",
    "meta": {
      "type": "template",
      "id": "2026-10-22-scp-example__fig10-sankey--sankey",
      "title": "分组流向桑基图",
      "status": "ready",
      "layouts": [
        "2026-10-22-scp-example__fig10-sankey"
      ],
      "panels": [
        "A"
      ],
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "chart_types": [
        "sankey"
      ],
      "favorite": false
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/wiki/templates/2026-10-22-scp-example__fig10-sankey--sankey/preview.png",
      "kind": "replay",
      "label": "模板回放"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "可用",
      "reason": "已确认可用；当前笔记与回放完整。",
      "templates": []
    },
    "relations": []
  },
  {
    "path": "templates/2026-10-22-scp-example__fig11-chord--chord.md",
    "meta": {
      "type": "template",
      "id": "2026-10-22-scp-example__fig11-chord--chord",
      "title": "分组流向和弦图",
      "status": "ready",
      "layouts": [
        "2026-10-22-scp-example__fig11-chord"
      ],
      "panels": [
        "A"
      ],
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "chart_types": [
        "chord"
      ],
      "favorite": false
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/wiki/templates/2026-10-22-scp-example__fig11-chord--chord/preview.png",
      "kind": "replay",
      "label": "模板回放"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "可用",
      "reason": "已确认可用；当前笔记与回放完整。",
      "templates": []
    },
    "relations": []
  },
  {
    "path": "templates/2026-10-22-scp-example__fig12-venn--venn.md",
    "meta": {
      "type": "template",
      "id": "2026-10-22-scp-example__fig12-venn--venn",
      "title": "多集合交集维恩图",
      "status": "ready",
      "layouts": [
        "2026-10-22-scp-example__fig12-venn"
      ],
      "panels": [
        "A"
      ],
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "chart_types": [
        "venn"
      ],
      "favorite": false
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/wiki/templates/2026-10-22-scp-example__fig12-venn--venn/preview.png",
      "kind": "replay",
      "label": "模板回放"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "可用",
      "reason": "已确认可用；当前笔记与回放完整。",
      "templates": []
    },
    "relations": []
  },
  {
    "path": "templates/2026-10-22-scp-example__fig13-upset--upset.md",
    "meta": {
      "type": "template",
      "id": "2026-10-22-scp-example__fig13-upset--upset",
      "title": "多集合交集 UpSet 图",
      "status": "ready",
      "layouts": [
        "2026-10-22-scp-example__fig13-upset"
      ],
      "panels": [
        "A"
      ],
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "chart_types": [
        "upset"
      ],
      "favorite": false
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/wiki/templates/2026-10-22-scp-example__fig13-upset--upset/preview.png",
      "kind": "replay",
      "label": "模板回放"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "可用",
      "reason": "已确认可用；当前笔记与回放完整。",
      "templates": []
    },
    "relations": []
  },
  {
    "path": "templates/2026-10-22-scp-example__fig14-feature-heatmap--heatmap.md",
    "meta": {
      "type": "template",
      "id": "2026-10-22-scp-example__fig14-feature-heatmap--heatmap",
      "title": "特征表达热图",
      "status": "ready",
      "layouts": [
        "2026-10-22-scp-example__fig14-feature-heatmap"
      ],
      "panels": [
        "A"
      ],
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "chart_types": [
        "heatmap"
      ],
      "favorite": false
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/wiki/templates/2026-10-22-scp-example__fig14-feature-heatmap--heatmap/preview.png",
      "kind": "replay",
      "label": "模板回放"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "可用",
      "reason": "已确认可用；当前笔记与回放完整。",
      "templates": []
    },
    "relations": []
  },
  {
    "path": "templates/2026-10-22-scp-example__fig15-cell-cor-heatmap--heatmap.md",
    "meta": {
      "type": "template",
      "id": "2026-10-22-scp-example__fig15-cell-cor-heatmap--heatmap",
      "title": "细胞相似度热图",
      "status": "ready",
      "layouts": [
        "2026-10-22-scp-example__fig15-cell-cor-heatmap"
      ],
      "panels": [
        "A"
      ],
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "chart_types": [
        "heatmap"
      ],
      "favorite": false
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/wiki/templates/2026-10-22-scp-example__fig15-cell-cor-heatmap--heatmap/preview.png",
      "kind": "replay",
      "label": "模板回放"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "可用",
      "reason": "已确认可用；当前笔记与回放完整。",
      "templates": []
    },
    "relations": []
  },
  {
    "path": "templates/2026-10-22-scp-example__fig16-cell-density--ridge.md",
    "meta": {
      "type": "template",
      "id": "2026-10-22-scp-example__fig16-cell-density--ridge",
      "title": "分组表达密度图",
      "status": "ready",
      "layouts": [
        "2026-10-22-scp-example__fig16-cell-density"
      ],
      "panels": [
        "A"
      ],
      "language": "r",
      "tags": [
        "单细胞分析"
      ],
      "chart_types": [
        "ridge"
      ],
      "favorite": false
    },
    "implementation_status": [],
    "figure_refs": [],
    "preview": {
      "url": "/files/wiki/templates/2026-10-22-scp-example__fig16-cell-density--ridge/preview.png",
      "kind": "replay",
      "label": "模板回放"
    },
    "workflow": {
      "stage": "complete",
      "queue": null,
      "label": "可用",
      "reason": "已确认可用；当前笔记与回放完整。",
      "templates": []
    },
    "relations": []
  }
];

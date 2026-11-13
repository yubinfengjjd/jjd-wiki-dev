# 课题本地状态与证据层

课题记录是执行现场：状态只写 `<课题>/wiki-use/_project/`，不调用 Wiki `save`，不复制数据进库。所有命令经 `wiki.py project <子命令> --root <课题>`；只读视图（status/check/impact/evaluate）不写状态，写命令在 help 里标明。

```text
<课题>/wiki-use/_project/
  project.json      唯一状态：revision、entities、objects、observations、routes、
                    tasks、artifacts、runs、decisions、authorizations、events
  summary.md        每次写入重建的接手摘要
  project.lock      单写者锁（无活动写者时可人工删除）
  routes/<id>.md    每条主线一张可读卡
  runs/<run_id>/    不可覆盖的运行收据
  lessons/          经验草稿位；lesson 记录存 project.json，待正式回存时再落成文件
  _quarantine/<时间戳>/  recover --clean-* 的隔离区（staging/ 保留暂存证据、
                    orphans/ 保留孤立收据；清理操作先取得写者锁互斥）
```

## 写语义

- 单写者：`project.lock`（O_EXCL）+ `expected_revision` 乐观并发；恢复清理（`recover --clean-*`）用同一把写者锁互斥——拿不到锁即拒绝，不在锁下另起第二把锁。整状态先校验再在锁内按序提交：调用方暂存的权威文件（run 收据）→ 派生物（summary、路线卡）→ `project.json`（权威提交点，最后）。任一失败点都保证状态与收据一致：收据改名失败则整体中止；summary/路线卡改名失败是可恢复的派生缺口——照常提交并在结果 `derived_warnings` 中显式报告，不谎报回滚；`project.json` 改名失败则按字节备份还原收据**和已发布的派生视图**——旧权威状态上绝不留下声称新修订完成的 summary/路线卡。
- `record-run` 收据先 `receipt.json.tmp` 暂存，随状态更新在同一锁事务内提交；修订号冲突等失败不会覆盖已有 running/completed 收据。不声称跨文件崩溃原子性，但所有已测写失败边界都保持权威文件与已发布视图一致。
- 重复 `completed` 运行按（任务、绑定实现、输入指纹、参数、实际命令、声明环境、登记代码引用）去重；仅当旧收据可解析**且结构完整**（本 run 的 run_id/task/status/inputs/outputs/checks 齐备）、登记了实际 `--code` 来源（implementation_id 是分支名不是当前代码哈希，单凭 id 不构成代码等价）、旧输出仍按指纹在位（**含指纹记录**——无哈希不等于哈希匹配）、输入指纹仍一致、且其产物未被显式标 stale/unknown 时才返回 `duplicate_of`。命令/环境/代码不同的修正是新计算，不是重复。
- `--in` 缺省沿用任务声明输入；显式给 `--in` 却漏掉已声明依赖会直接报错，不静默丢弃。`--param` 缺省沿用任务参数；与声明不一致时报错。
- 输出路径同一次运行内不得重复；输出不得与任何声明输入指向同一文件（输入被改写即拒登）。
- 载入 `project.json` 时校验嵌套记录形状（标量/畸形记录报字段级 WikiError），且记录的 `project_root` 必须与请求目录一致；复制/移动后的课题须显式 `project relocate`，不在旧根上静默核查。

## 命令一览

| 命令 | 写? | 说明 |
|---|---|---|
| `project init --root … [--id --title --data-root]` | 写 | 初始化；已存在 `_project` 不覆盖，报迁移。非拉丁目录名回退 `project-<根哈希>`，不撞 id |
| `project status` | 否 | 计数、pending、最近事件 |
| `project check` | 否 | 结构/引用/路径/指纹核查；产物新鲜度沿已声明依赖传递（上游 stale/unknown 会污染下游），任务给出 ok/at_risk/uncertain；有 config 时顺带核查 Wiki 引用 |
| `project impact --changed REF [--apply]` | 默认否 | 依赖影响：direct/indirect/tasks/unknown；`file:`/`object:`/`artifact:`/`run:` 按真实路径互为别名；`--apply` 把受影响产物标 stale/unknown 并按节点记录理由（含被覆盖说明）。变更分级：style 类输入（theme/标题/颜色等声明为仅样式）只触发渲染层任务，数据/权重/ROI/资源/代码变更触发计算层；混合路径按最高影响级归 compute，不降级 |
| `project record-run --run … --task … --status …` | 写 | 登记已执行运行；不执行命令 |
| `project add-data-root/add-entity/add-object/add-observation/add-route/add-task/add-decision/add-authorization/register-profile` | 写 | 登记各类记录；register-profile 绑定当时规格的版本与内容哈希 |
| `project evaluate [--profile id] [--subject REF]` | 否 | 领域前提评估（`rwiki/domain_profiles.yaml`）；`--subject` 把前提限定到一个 object/entity/task 上下文 |
| `project recover [--release-lock --clean-staging --clean-orphans]` | 写（缺省只读） | 中断恢复：报告锁（PID 活性按只读进程查询判定，权限不足/锁损坏/非正 PID 一律 unknown）、running 运行、暂存残留、孤立收据；无旗标不改任何字节。修复旗标要求锁主可验证地不活跃（live/unknown 拒绝），清理在写者锁内重读状态后走 `_quarantine/` 隔离区逐条可审计，不删证据 |
| `project add-lesson --id … --claim … --evidence REF… --applies-to … [--link --basis]` | 写 | 经验草稿（pending）：≥1 条已登记证据引用 + 显式适用范围必填；同命题+同范围+同链接自动合并证据（已评审草稿因新证据回到 pending、保留历史评审；无新证据的重复提交不动）；`--link` 指向已有记录/方法页，不另立家族 |
| `project lesson-review --id … --state … --by 署名 [--decision decision:id]` | 写 | 课题内评审处置；`accepted` 必须附已登记的 `decision:` 作者决策——只有实际作者决策能推向 accepted；accepted 仍是候选提案，正式落库走 Wiki 评审，测试/自动布尔不构成批准；deferred/rejected 永不进正式推荐 |
| `project relocate --root …` | 写 | 显式把状态根重定位到当前目录 |

引用写法：节点 `kind:id`（object/entity/artifact/observation/task/route/decision/authorization/lesson/run），文件 `file:<课题相对路径>`，外部 `external:<已登记数据根内绝对路径>`；裸 id 多处命中时报歧义。

## 判断轴互不授予

| 轴 | 取值 | 规则 |
|---|---|---|
| 声明依据 basis | `verified` / `author_stated` / `unknown` | `verified` 需当场可核对的真实证据；观察类 `verified` 未登记证据文件时按 author_stated 层对待；已登记证据缺失或字节变化时该记录直接失效；`about` 指向的对象/产物被替换或消失时该观察对**新版本**不构成当前证明（不据此称假，只是不再算现行证据）——文件指纹只证明材料完整，不证明科学内容 |
| 工作状态 | `planned/running/completed/failed/blocked/skipped` | `completed` 必须附实际命令 + ≥1 个存在的输出 + ≥1 项实际检查；退出码和调用方布尔不授予 |
| 产物新鲜度 | `current/stale/unknown` | 相对已登记输入指纹并经依赖传递；依赖未登记或不可解析 → `unknown`，不伪称精确跳过 |
| 实现/算法验证 | Wiki `verification/*.json` 轴 | 课题层不读不写，不互认 |
| 科学解释 | 另行审查 | 状态层没有任何字段授予科学有效性 |

对象另分三层语义：`native_type` 是声明的格式名；`inspected=True`（须带 `--adapter`）表示适配器确实打开解析过；接受一个文件名字符串从不声称已解析语义支持。

## 路径安全

- `file:`/对象 `path` 必须是课题相对路径：拒绝绝对路径、`..`、隐藏段、反斜杠、符号链接逃逸。
- `external:` 只允许落在作者用 `add-data-root` 登记的只读根内；**先拒相对输入再解析**，引用时校验边界（含盘符相对与 UNC）。
- 观察证据可引用 `external:<绝对路径>`（同样限已登记数据根内）。
- 证据、输出、对象 sha256 在登记与 check 时按当前字节核对；指纹分块流式读取（每次 1 MiB），登记时同时记 `bytes` 字节数，便于区分"无哈希记录"与"哈希相同"；文件存在不是科学验证。

## 运行登记的证据线

任务可带 `--stage <阶段名>`（与 profile 声明阶段自由对齐，非受控词表）标记所处分析阶段。

`record-run --status completed` 需要：`--command` 实际命令文本、`--out` 至少一个存在的课题相对输出（指纹入 artifact）、`--check` 至少一项实际检查。`--in` 支持任意已登记引用（代码/资源/权重/划分都应登记为依赖而非自由文本）；输入指纹写进收据，后续 `impact`/`check` 据此判断 stale。`--code` 登记本次实际使用的代码/清单/资源引用（可重复）：并入输入指纹与去重身份，是"相同计算"唯一可信的代码来源记录——不做命令文本的临时解析；**未登记 `--code` 的运行（含绑定实现的运行）永远不被静默复用**。`--param`/`--env` 记录 `k=v`。`--status` 其余值如实记录工作状态，不产生产物。同一输出路径被后续 run 覆盖时，旧产物标 stale（注明被覆盖），不产生同路径双活产物。

## 领域配置评估

`project evaluate` 对 `rwiki/domain_profiles.yaml` 中声明式 profile 做前提评估。每条前提给出 `satisfied`/`unsatisfied`/`unknown`/`conflicted`/`not_applicable` 及命中证据引用：

- **冲突**：同层正负观察并列时为 `conflicted`（两侧引用都保留），不是 satisfied；verified 负证据压过 author_stated 正证据；unknown 依据/取值的记录不构成权威否定。
- **范围**：不带 `--subject` 的评估只统计 `about=None` 的泛化观察——关于另一对象的观察不是全局证明；`--subject object:x`（或 entity/task 引用）把前提限定到一个一致上下文，互补元数据的无关对象不会拼成假完整数据集。
- **新鲜度**：对象/产物/观察证据命中前先做当前材料核对（与 `project check` 同一解析器）——文件缺失或指纹变化的登记项不再满足前提；存在但无指纹记录的材料是 `unhashed` 不是 `current`；观察证据字节变化的 `verified` 记录直接失效，不降格为 author_stated 真相；`about` 所指材料 stale/missing 的观察同样失去现行证明力；产物沿用 check 的依赖传递结果（`file:` 与 `artifact:` 同义）。无需调用方另跑人工预检。
- **条件前提**：前提可带 `when`/`unless` 子条件（如纯评价任务不强求权重、声明 ligand-only 不强求受体）。`when` 仅在其条件被**显式否定**（unsatisfied）时记 `not_applicable`；条件未知或冲突时前提照常保守评估，绝不豁免。`unless` 仅在条件显式满足时豁免。
- **阶段证据**：`stage_evidence` 逐阶段给出 `declared`/`recorded`/`not_recorded`——profile 声明的阶段名是声明；仅当有登记观察/任务声明了 `stage` 字段且其证据经当前材料核查（verified 观察须证据现行）才记 `recorded`。阶段名存在不等于阶段完成；记录存在不等于科学成立。任务/观察用 `add-task --stage`/`add-observation --stage` 登记阶段。
- **规格绑定**：报告含当前 `spec_sha256` 与登记的 `registration`；版本或哈希不一致时给出 warning，不静默沿用旧登记。

未知不是满足，也不是拒绝。profile 是规格不是可用性表；库外方法缺口只作为不可执行候选，详见 `discover-methods`。

## 恢复（recover）

`project recover` 缺省完全只读：报告 `project.lock` 的持有者 PID 与活性、running 运行、`.tmp` 暂存残留与 `runs/` 下未被**当前**状态引用的收据（注意：只核当前状态，不声称"从未被任何修订引用"）。PID 活性经只读进程查询判定；权限不足、锁不可读、JSON 损坏、PID 非正整数一律记 `unknown`，绝不当作无写者。

修复旗标在锁主可验证地不活跃之外一律拒绝，清理动作在写者锁内重读状态再分类（锁下重载避免把刚提交的收据误判为孤儿）：

- `--release-lock`：仅当锁主 PID 经只读查询确认不活跃才释放；释放前把锁当前字节/stat 与**探测前**记录的原始身份比对——探测期间被替换的锁（属于另一写者）拒绝释放。
- `--clean-staging`：把 `.tmp` 暂存残留移入 `_quarantine/<时间戳>/staging/`（不删）。
- `--clean-orphans`：把孤立收据目录移入 `_quarantine/<时间戳>/orphans/`（不删）。

所有清理目标必须在状态目录**内**且不是符号链接/接点；越界或逃逸路径拒绝。running 运行的处理是人工判断：recover 只报告，不自动改状态、不杀进程、不重启。

## 经验草稿（lessons）

课题中产生的可复用判断、失败模式与适配教训可登记为 lesson 草稿：`add-lesson` 要求 `--claim`（命题文本）、至少一条 `--evidence` 引用（`run:`/`observation:`/`decision:`/`artifact:` 等已登记记录）与显式 `--applies-to` 适用范围（无界命题不登记）；`--link` 指向已有记录或方法页 id（关联而非重述已有知识）。同命题+同范围+同链接的草稿自动合并证据引用、返回既有条目 id，不重复建条、不另立方法家族；已评审草稿因新证据回到 pending 并在 `previous_reviews` 保留带日期的原评审与当时证据范围，无新证据的重复提交不改变评审状态。

状态机：`pending`（草稿）→ `lesson-review` 可转 `deferred`（搁置）/`rejected`（否决）/`accepted`。所有评审须 `--by` 署名；`accepted` 另须 `--decision decision:<id>` 指向一条已登记的作者 decision 记录——代码路径不接受无决策记录的批准。deferred/rejected 永远不进正式推荐与回存提案；accepted 也只是"准备提交正式 Wiki 评审"的候选——正式知识落库仍走 Wiki 侧既有评审，测试布尔与自动状态不构成作者批准。

## 与旧 wiki-use 的关系

`wiki-use/<旧标识>/` 下的旧 context/mapping 目录在 `init` 时记入 `legacy_contexts`（仅引用、不迁移、不覆盖）。正式 `record-use` 仍走原有 Wiki 路径，两者不冲突。

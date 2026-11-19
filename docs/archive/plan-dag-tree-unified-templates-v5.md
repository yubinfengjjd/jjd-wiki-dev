# Research Wiki v5: DAG Asset Core + Composable Decision Trees + Unified Multi-Style Templates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` via **Orca Orchestration Task DAG (`orca orchestration run-create` / `task-create --deps` / `worker-start --agent antigravity --model gemini-4-hydrogen-high`)**. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate the contradictory L1/L2 recipe-vs-template split across Research Wiki, introduce multi-style swappable templates (`default` / `variant`) covering 100% of Cai et al. (2026) panels, bind semantic `method ↔ template` relations across all 11 canonical methods, and graft the composable `单细胞 × 空间转录组微环境` decision-tree subtree + Cai 2026 Case Card onto the existing `scrna-stepwise-playbook`.

**Architecture:** Decouple underlying storage from user-facing navigation into 4 clean pillars: (1) deduplicated canonical `methods/` (26 analysis families with swappable `implementations`, no paper workflows mixed into analysis families), (2) unified `templates/` (19 Cai 2026 native templates + reused library templates, annotated with `style_tier: default|variant` and `journal_style`, preserving 146 legacy `wiki/recipes/` on disk without broken links while unifying all docs/skills/UI copy to "绘图模板"), (3) composable domain decision trees (`scenarios/`) supporting multi-upstream convergence (`requires: [...]`) on DAG nodes while rendering cleanly as stepwise trees, and (4) isolated per-paper case cards (`projects/` + `gallery/` + read-only author `source/`).

**Tech Stack:** Python 3 (`rwiki` CLI + `pytest`), R 4.5.0 (`ggplot2`/`patchwork`/`ComplexHeatmap`/`circlize`), TypeScript + React + Vite (`开发/apps/web`), Git + Orca Orchestration CLI (`orca`).

**Spec:** `<dev_root>\docs\superpowers\specs\2026-11-19-dag-tree-unified-templates-v5-design.md` (captures the full multi-round Product Manager architecture discussion, 4-pillar DAG + Playbook + Unified Multi-Style Templates decisions, anti-paralysis `default`/`variant` rules, and concrete `QC → Integration → Annotation` + Cai 2026 Branch 7 plug-in walkthrough — every executor MUST read both this Spec and Plan).

## Global Constraints
- **Zero L1/L2 or 配方 split for new assets & UI copy:** All new visualizations live in `<vault_root>\wiki\templates\<short-slug>/`. Keep existing 146 files in `wiki/recipes/` intact on disk (no hard deletion, zero broken links), but remove contradictory "L1 配方 / L2 模板" wording from `AGENTS.md`, skills, and visible Web UI copy.
- **Strict Sequential R Execution (`一步一跑`):** Low-RAM Windows host. Run AT MOST ONE Rscript / `verify-template` process at a time; never run parallel R processes.
- **Honest Receipts:** Windows R 4.5.0 `rlang` exit-time `0xC0000005` (`3221225477`) occurs after writing valid PNG/PDF/SVG files. Never fake a receipt; verify written `figure.{png,pdf,svg}` existence/size and record teardown exit code honestly.
- **Valid `figure_relations` Schema (`rwiki/relations.py:86-148`):** Draft templates MUST use `compatibility: adaptable` (with non-empty `adaptation` string and `verification: {state: not_run, scope: "...", evidence: []}`), NEVER `compatibility: direct`.
- **Zero Machine Absolute Paths in Committed Wiki Files:** Never write `<drive>/`, `<drive>/`, `<drive>/` inside `<vault_root>\wiki\**` or `gallery\**` so `rwiki gh guard` stays `OK`.
- **Locked Assets (DO NOT MODIFY):** `<vault_root>\gallery\2026-11-19-cai-stromal-tme\**` and `<env_root>\sources\papers\2026-cai-stromal-tme\review\**`.
- **Orca Multi-Agent Ownership:** No two concurrent Orca workers may edit the same file. Enforce DAG dependencies via `orca orchestration task-create --deps`.

---

## Orca Multi-Agent Task DAG Topology

```text
Task 1 (Dev Core: schema + tests + skills) ──► Task 2 (Dev Web UI: unified copy + style_tier + 5th playbook) ──┐
                                                                                                              ├──► Task 6 (Final Verification Gate + Commit/Push)
Task 3 (Vault: 10 new + 9 existing templates, solo sequential R) ──► Task 4 (Vault: AGENTS.md + 11 methods figure_relations) ──► Task 5 (Vault: Playbooks + Project Case Card + Workflow Matrix) ──┘
```

- **Wave A (Parallel, Zero File Overlap):** `Task 1` (owns `<dev_root>\skills\**` + `tests\`) and `Task 3` (owns `<vault_root>\wiki\templates\**`, solo sequential R runner).
- **Wave B (Parallel after respective deps):** `Task 2` (owns `<dev_root>\apps\web\**`, deps: `[Task 1]`) and `Task 4` (owns `<vault_root>\wiki\AGENTS.md` + `wiki\methods\<11 canonical>.md` + `method-map.json`, deps: `[Task 3]`).
- **Wave C:** `Task 5` (owns `<vault_root>\wiki\scenarios\**` + `wiki\projects\2026-cai-stromal-tme.md` + `wiki\methods\breast-cancer-stromal-tme-workflow.md`, deps: `[Task 4]`).
- **Wave D:** `Task 6` (Coordinator / Verifier final cross-repo `lint`, `gh guard`, `pytest`, `npm run build`, `clean`, commit & push, deps: `[Task 2, Task 5]`).

---

### Task 1: Dev Core Schema (`style_tier`, `requires`) & Unified Skill Rules

**Files:**
- Modify: `<dev_root>\skills\research-wiki\rwiki\lint.py` (validate optional `style_tier` in `("default", "variant")` on `template`, optional `requires` string-list on `scenario.steps[*]`)
- Modify: `<dev_root>\skills\research-wiki\rwiki\catalog.py` (include optional `style_tier` and `journal_style` in template catalog record when present)
- Modify: `<dev_root>\skills\research-wiki\rwiki\server.py` (pass through `style_tier`, `journal_style` on template summaries and `requires` on playbook steps)
- Modify: `<dev_root>\skills\paper-replication\SKILL.md`
- Modify: `<dev_root>\skills\paper-replication\references\subagent-orchestration.md`
- Modify: `<dev_root>\skills\research-wiki\SKILL.md` (replace contradictory L1/L2 recipe-vs-template wording with unified template wording while noting legacy `recipes/` read-only archive)
- Create: `<dev_root>\skills\research-wiki\tests\test_v5_unified_schema.py`

**Interfaces:**
- Produces:
  - `template` frontmatter optional fields: `style_tier: "default" | "variant"`, `journal_style: str`
  - `scenario.steps[*]` optional field: `requires: list[str]` (multi-upstream convergence inputs)
  - Catalog JSONL & Server API expose `style_tier`, `journal_style`, and `requires` cleanly.

- [ ] **Step 1: Write failing unit tests in `tests/test_v5_unified_schema.py`**

```python
from pathlib import Path
from rwiki.lint import lint_wiki
from rwiki.config import Config

def test_template_style_tier_validation(tmp_path):
    # Verify lint accepts style_tier in ("default", "variant") and rejects invalid value "gold"
    ...

def test_scenario_step_requires_validation(tmp_path):
    # Verify lint accepts scenario step with requires: ["scrna-annotated-cells", "visium-spatial-object"]
    # and rejects non-list requires
    ...
```

- [ ] **Step 2: Run targeted pytest to confirm FAIL**

Run: `<python> -X utf8 -m pytest <dev_root>\skills\research-wiki\tests\test_v5_unified_schema.py -v`
Expected: FAIL because `style_tier` and `requires` validation are not yet wired.

- [ ] **Step 3: Implement minimal schema support in `lint.py`, `catalog.py`, `server.py`**
- In `lint.py`: validate `if "style_tier" in meta and meta["style_tier"] not in ("default", "variant"): errors.append(...)`; validate `scenario.steps[*].requires` is a list of non-empty strings when present.
- In `catalog.py`: preserve `style_tier` and `journal_style` in catalog entry dict for `type == "template"`.
- In `server.py`: pass `style_tier`, `journal_style`, and `requires` through page/playbook API payloads.

- [ ] **Step 4: Align `paper-replication` & `research-wiki` skill docs and mirror to `.claude` / `.codex`**
- Inspect current diff in `skills/paper-replication/*`, ensure unified template wording (`templates/` unified, `recipes/` legacy read-only archive, multi-style `default`/`variant`, 4-pillar DAG + Playbook + Case Card), mirror to `<user_home>\.claude\skills\` and `<user_home>\.codex\skills\`.

- [ ] **Step 5: Run full fast pytest suite**

Run: `<python> -X utf8 -m pytest <dev_root>\skills\research-wiki\tests -m "not r and not compose and not local" -q`
Expected: All tests PASS (0 failures).

---

### Task 2: Dev Web UI Unified Copy, Style-Tier Badges & 5th Spatial-TME Playbook DAG

**Files:**
- Modify: `<dev_root>\apps\web\src\api.ts` (add optional `style_tier?: 'default' | 'variant'`, `journal_style?: string`, `requires?: string[]`; change label `recipe: '历史归档模板'`)
- Modify: `<dev_root>\apps\web\src\components.tsx` (change `"配方"` display label to `"历史归档模板"` / `"绘图模板"`, keep status badges clean)
- Modify: `<dev_root>\apps\web\src\recipes.ts` (remove `"原样配方"` wording in UI labels)
- Modify: `<dev_root>\apps\web\src\views\RecipesView.tsx` (retitle H1 to `"历史归档模板（按方法域与分析方法组织）"`, remove L1 wording)
- Modify: `<dev_root>\apps\web\src\views\SourcesView.tsx` (replace `"L2 · 函数模板"` / `"L1 · 整模块配方"` with `"原生绘图模板"` / `"历史归档模板"`)
- Modify: `<dev_root>\apps\web\src\views\MethodsView.tsx`, `PageView.tsx`, `ResourcesView.tsx`, `ScenariosView.tsx`, `SearchView.tsx`, `FigureYaReview.tsx` (unify visible Chinese copy from `"配方"` to `"历史归档模板"` / `"绘图模板"` while preserving `#/recipes` routes & `type === 'recipe'` API checks)
- Modify: `<dev_root>\apps\web\src\views\PlaybooksView.tsx` (add 5th core playbook `'stromal-tme-scrna-st-playbook'` to `CORE_PLAYBOOK_META` and `CORE_PLAYBOOK_ORDER`, add Branch 7 spatial convergence node to `scrna-stepwise-playbook`, render `requires` convergence pill on DAG nodes, change `"参考源码配方"` to `"历史参考模板"`)
- Modify: `<dev_root>\apps\web\src\RelationList.tsx` / `views\MethodOverview.tsx` (display crisp `"主推默认"` / `"可切换画风"` badge when `style_tier` is present)

**Interfaces:**
- Consumes: Task 1 API fields `style_tier`, `journal_style`, `requires`.
- Produces: Clean built frontend bundle (`npm run build` in `<dev_root>\apps\web`).

- [ ] **Step 1: Update TypeScript types in `src/api.ts`**
- Add `style_tier?: 'default' | 'variant'; journal_style?: string;` to `PageSummary` / `TemplateMeta`, and `requires?: string[];` to `PlaybookStep`.
- Update `TYPE_LABELS.recipe` from `'配方'` to `'历史归档模板'`.

- [ ] **Step 2: Unify visible Chinese copy across the 11 UI view files**
- Replace all user-facing `"L1"` / `"L2"` / `"配方"` labels with `"绘图模板"` / `"历史归档模板"`. Do NOT rename TypeScript variables, API routes (`/api/recipes`), or hash routes (`#/recipes`).

- [ ] **Step 3: Add `stromal-tme-scrna-st-playbook` & `requires` convergence pill in `PlaybooksView.tsx` + `style_tier` badge in `RelationList.tsx`**
- Add `'stromal-tme-scrna-st-playbook'` to `CORE_PLAYBOOK_META` and `CORE_PLAYBOOK_ORDER` with its 6-stage DAG (`cell-type-annotation` + `spatial-transcriptomics-microenvironment` convergence -> `cell-proportion-composition` -> `gene-set-scoring`/`trajectory-inference` -> `immune-infiltration-tme` -> `cell-cell-communication`).
- Render a compact convergence tag (`多上游汇合: ...`) inside any DAG card where `step.requires?.length`.

- [ ] **Step 4: Build & verify zero TypeScript / Vite errors**

Run: `npm --prefix <dev_root>\apps\web run build`
Expected: Exit code 0, zero TS/Vite errors.

---

### Task 3: Vault — Complete & Sequentially Verify All 19 Cai 2026 Native Templates (10 New + 9 Tagged)

**Files:**
- Finalize 9 partial templates already scaffolded on disk under `<vault_root>\wiki\templates\`:
  1. `atlas-workflow-diagram` (`primary_method: batch-integration`, `style_tier: variant`, Fig 1A study schematic)
  2. `cellchat-signaling-ring` (`primary_method: cell-cell-communication`, `style_tier: variant`, SFig 5D 52-node VEGF circular signaling ring)
  3. `checkpoint-group-boxplot` (`primary_method: immune-infiltration-tme`, `style_tier: default`, Fig 3C multi-gene 2-group `#1D8A68/#D05810` Wilcoxon boxplot)
  4. `cluster-kegg-bars` (`primary_method: gene-set-enrichment`, `style_tier: variant`, SFig 4D/5C burgundy `#8E1D41` faceted horizontal KEGG bars + tip counts)
  5. `clustered-corr-boxes` (`primary_method: immune-infiltration-tme`, `style_tier: default`, Fig 3A symmetric clustered corrplot `+1` dark blue top / `-1` dark red bottom + diagonal black boxes)
  6. `diffusion-trajectory-overlay` (`primary_method: trajectory-inference`, `style_tier: default`, Fig 2F–I/4F–H/5F–H DiffusionMap/Slingshot + dual-module overlay)
  7. `spatial-coexpr-multichannel` (`primary_method: spatial-transcriptomics-microenvironment`, `style_tier: variant`, Fig 3E/6H/SFig 6B–C 2/4-channel spatial co-expression)
  8. `spatial-he-deconv-panel` (`primary_method: spatial-transcriptomics-microenvironment`, `style_tier: variant`, SFig 3B H&E histology paired with spatial signature deconvolution)
  9. `tissue-ratio-prop-combo` (`primary_method: cell-proportion-composition`, `style_tier: variant`, SFig 2A/4A/5A horizontal stacked tissue ratio + sample box/jitter + Wilcoxon stars)
- Create 10th new template:
  10. `stromal-hull-umap` (`primary_method: cell-type-annotation`, `style_tier: variant`, Fig 1D velvety UMAP with numbered centroids, red dashed group hulls `#D63A2F`, L-arrows, multi-column dot legend)
- Add `style_tier` & `journal_style: Cai2026-npjPO` frontmatter to the 9 already-committed Cai 2026 templates:
  - `spatial-feature-grid` (`default`), `roe-cox-heatmap` (`default`), `pathway-zscore-heatmap` (`default`), `cellchat-count-heatmap` (`variant`), `lr-bubble-matrix` (`default`), `lr-bipartite-bubble` (`variant`), `metabolism-lollipop-dotplot` (`default`), `pseudotime-branch-curves` (`variant`), `kegg-cluster-bubble` (`default`).

**Interfaces:**
- Produces: 19 complete native template packages under `<vault_root>\wiki\templates\<slug>\` each with valid `.md`, `spec.json`, portable `code/render.R` (zero hardcoded counts/paths), and rendered `verify/figure.{png,pdf,svg}`.

- [ ] **Step 1: Audit and complete `.md`, `spec.json`, `code/render.R` for all 9 partial templates + create `stromal-hull-umap`**
- Ensure every `.md` uses ONLY valid controlled-vocabulary `tags` (`rwiki/tags.py`), has complete `## 适用`, `## 不适用`, `## 知识关联检查` (explicitly noting its swappable style vs sibling templates), `## 数据要求`, `style_tier`, and `journal_style: Cai2026-npjPO`, with ZERO machine paths and ZERO L1/L2/"配方" wording.
- Ensure every `code/render.R` uses locked Cai 2026 hex palettes and adaptive group/gene counts.

- [ ] **Step 2: Add `style_tier` and `journal_style: Cai2026-npjPO` frontmatter to the 9 existing Cai 2026 `.md` files**

- [ ] **Step 3: Sequentially run `verify-template <slug>` ONE AT A TIME for all 10 new templates (`一步一跑`)**
- Run each template individually via:
  ```powershell
  $env:PYTHONPATH="<dev_root>\skills\research-wiki"
  <python> -X utf8 -c "import sys; from rwiki.cli import main; sys.exit(main(['verify-template', '<slug>']))"
  ```
- After EACH template, check `verify/figure.png`, `verify/figure.pdf`, `verify/figure.svg` exist and are > 1 KB. Record Windows R 4.5.0 exit-time `0xC0000005` honestly if encountered; never fake a receipt.

- [ ] **Step 4: Visually inspect representative `verify/figure.png` files via `read_file` to verify zero rendering glitches, overlaps, or clipping**

---

### Task 4: Vault — Clean `AGENTS.md` + Wire Semantic `figure_relations`, `next_steps` & `method-map.json` on All 11 Canonical Methods

**Files:**
- Modify: `<vault_root>\wiki\AGENTS.md` (clean top-to-bottom unification removing all 43 legacy L1/L2/配方 contradictions; codify 4-pillar DAG + Multi-Style Templates + Composable Decision Tree + Case Cards)
- Modify 11 canonical `analysis` method pages under `<vault_root>\wiki\methods\`:
  1. `batch-integration.md` -> `scrna-celltype-umap` (`default`), `stromal-hull-umap` (`variant`), `atlas-workflow-diagram` (`variant`)
  2. `cell-type-annotation.md` -> `scrna-celltype-umap` (`default`), `stromal-hull-umap` (`variant`), `scrna-feature-umap-grid` (`default`), `marker-bubble-dotplot` (`default`)
  3. `cell-proportion-composition.md` -> `cell-prop-flow-bar` (`default`), `roe-cox-heatmap` (`variant`), `tissue-ratio-prop-combo` (`variant`)
  4. `survival-prognosis-analysis.md` -> `roe-cox-heatmap` (`variant`)
  5. `differential-expression.md` -> keep existing + add `pathway-zscore-heatmap` (`variant`)
  6. `gene-set-scoring.md` -> `scrna-feature-umap-grid` (`default`), `pathway-zscore-heatmap` (`variant`), `metabolism-lollipop-dotplot` (`variant`)
  7. `gene-set-enrichment.md` -> `kegg-cluster-bubble` (`default`), `cluster-kegg-bars` (`variant`), `coexpr-module-enrich-bars` (`variant`), `metabolism-lollipop-dotplot` (`variant`)
  8. `trajectory-inference.md` -> add `DiffusionMap + Slingshot` implementation reference note + `figure_relations`: `diffusion-trajectory-overlay` (`default`), `pseudotime-branch-curves` (`variant`)
  9. `spatial-transcriptomics-microenvironment.md` -> `spatial-feature-grid` (`default`), `spatial-coexpr-multichannel` (`variant`), `spatial-he-deconv-panel` (`variant`)
  10. `cell-cell-communication.md` -> `lr-bubble-matrix` (`default`), `cellchat-count-heatmap` (`variant`), `lr-bipartite-bubble` (`variant`), `cellchat-signaling-ring` (`variant`), `cellchat-circos-multi` (`variant`)
  11. `immune-infiltration-tme.md` -> `clustered-corr-boxes` (`default`), `checkpoint-group-boxplot` (`default`), `lr-bipartite-bubble` (`variant`)
- Update `<vault_root>\wiki\method-map.json` via `rwiki map-method` for all 10 newly added templates.

**Interfaces:**
- Consumes: Task 3's 10 new template `.md` & `spec.json` files.
- Produces: Schema-valid `figure_relations` & `next_steps` on all 11 canonical methods (`compatibility: adaptable` for draft templates per `rwiki/relations.py:128-129`).

- [ ] **Step 1: Finalize `<vault_root>\wiki\AGENTS.md` with zero internal contradictions**
- Verify `grep` for `L1` / `L2` / `配方` in `AGENTS.md` ONLY appears in the single explicit historical-archive deprecation sentence (`recipes/` 为只读历史归档目录，不再新建或区分 L1/L2).

- [ ] **Step 2: Add schema-valid `figure_relations` & `next_steps` to all 11 canonical methods**
- Each `figure_relations` entry MUST include: `figure: templates/<slug>`, `compatibility: adaptable` (for draft templates), non-empty `reason` (mentioning `default` vs `variant` style role), `prerequisites: [...]`, non-empty `adaptation: "..."`, non-empty `evidence: ["methods/<id>.md#输出", "templates/<slug>/spec.json"]`, `verification: {state: not_run, scope: "...", evidence: []}`.

- [ ] **Step 3: Run `rwiki map-method` for all 10 new templates & refresh facts blocks**

Run: `<python> -X utf8 -c "import sys; from rwiki.cli import main; sys.exit(main(['save']))"` (or targeted `map-method` + `lint` check).
Expected: `spatial-transcriptomics-microenvironment.md` missing-template warning is GONE, and `figure_relations` produces 0 ERRORs.

---

### Task 5: Vault — Composable Decision Tree Subtree, Trunk Hook & Cai 2026 Case Card

**Files:**
- Create: `<vault_root>\wiki\scenarios\stromal-tme-scrna-st-playbook.md`
- Modify: `<vault_root>\wiki\scenarios\scrna-stepwise-playbook.md`
- Create: `<vault_root>\wiki\projects\2026-cai-stromal-tme.md`
- Modify: `<vault_root>\wiki\methods\breast-cancer-stromal-tme-workflow.md`

**Interfaces:**
- Consumes: Task 3 (all 19 Cai 2026 templates) and Task 4 (all 11 canonical methods with `figure_relations`).
- Produces: Composable spatial-stromal decision subtree hooked into main scRNA trunk + complete Cai 2026 project case card + 100% panel coverage matrix.

- [ ] **Step 1: Create `wiki/scenarios/stromal-tme-scrna-st-playbook.md`**
- Follow exact `scenario` frontmatter schema (`type: scenario`, `id: stromal-tme-scrna-st-playbook`, `title`, `picks` [ONLY `methods/` and `templates/`], `tags`, `keywords`, `summary`, `steps` with 6 DAG stages including `requires: ["scrna-annotated-cells", "visium-spatial-object"]` on convergence steps and multiple swappable templates per stage).
- Include clear Chinese decision-tree guidance explaining how future papers graft new branches onto this subtree.

- [ ] **Step 2: Graft Branch 7 (`branch-7-stromal-spatial-tme`) onto `wiki/scenarios/scrna-stepwise-playbook.md`**
- Preserve existing Steps 1–3 and Branches 1–6 intact; remove legacy `(L2)` text annotations in `picks`; add Cai 2026 swappable templates into Branches 1–6 (`roe-cox-heatmap`, `tissue-ratio-prop-combo`, `pathway-zscore-heatmap`, `kegg-cluster-bubble`, `cluster-kegg-bars`, `metabolism-lollipop-dotplot`, `diffusion-trajectory-overlay`, `pseudotime-branch-curves`, `cellchat-count-heatmap`, `lr-bubble-matrix`, `lr-bipartite-bubble`, `cellchat-signaling-ring`, `clustered-corr-boxes`, `checkpoint-group-boxplot`); add `branch-7-stromal-spatial-tme` (`requires: ["scrna-annotated-cells", "visium-spatial-object"]`) pointing to `scenarios/stromal-tme-scrna-st-playbook`!

- [ ] **Step 3: Create `wiki/projects/2026-cai-stromal-tme.md`**
- Follow exact `project` frontmatter (`type: project`, `slug: 2026-cai-stromal-tme`, `title`, `playbook: stromal-tme-scrna-st-playbook`, `status: active`, `templates` listing all 19 Cai 2026 + reused templates, `methods` listing all 11 canonical methods, `summary`).
- Write complete 6-stage research-path record (`【科学假设与目标】` → `【所用分析方法与可切换模板】` → `【核心生物学发现与小规模排坑】` → `【触发下一步分叉】`), explicitly recording excluded wet-lab Fig 3F–H and linking author read-only `source/`, 12-figure `code/`, and `gallery/2026-11-19-cai-stromal-tme/source.md`.

- [ ] **Step 4: Update `wiki/methods/breast-cancer-stromal-tme-workflow.md`**
- Add the complete **12-Figure × All-Panels → Swappable `wiki/templates/<slug>` Coverage Matrix** (covering 100% of all panels across Main Fig 1–6 [excl. 3F–H] & Supp Fig 1–6) and bidirectional wikilinks to `[[scenarios/stromal-tme-scrna-st-playbook]]`, `[[scenarios/scrna-stepwise-playbook]]`, and `[[projects/2026-cai-stromal-tme]]`.

---

### Task 6: Cross-Repo Verification Gate, Cleanup & Git Commit/Push

**Files:**
- Verify: `<dev_root>` & `<vault_root>`

- [ ] **Step 1: Rebuild Vault catalog & index**

Run: `<python> -X utf8 -c "import sys; sys.path.insert(0, r'<dev_root>\skills\research-wiki'); from rwiki.cli import main; sys.exit(main(['save']))"`

- [ ] **Step 2: Run Vault `rwiki lint` & `rwiki gh guard` & `rwiki clean --apply`**

Run:
```powershell
$env:PYTHONPATH="<dev_root>\skills\research-wiki"
<python> -X utf8 -c "import sys; from rwiki.cli import main; sys.exit(main(['lint']))"
<python> -X utf8 -c "import sys; from rwiki.cli import main; sys.exit(main(['gh', 'guard']))"
<python> -X utf8 -c "import sys; from rwiki.cli import main; sys.exit(main(['clean', '--apply']))"
```
Expected: `lint` exits 0 with **0 ERROR**; `gh guard` prints **`OK`**; `clean --apply` clears all empty R temp dirs.

- [ ] **Step 3: Run Dev repo `pytest` + `npm run build` final confirmation**

Run:
```powershell
<python> -X utf8 -m pytest <dev_root>\skills\research-wiki\tests -m "not r and not compose and not local" -q
npm --prefix <dev_root>\apps\web run build
```
Expected: Both exit 0.

- [ ] **Step 4: Coordinator independent review of `git diff`, then commit & push BOTH `<dev_root>` and `<vault_root>` to `origin/main`!**

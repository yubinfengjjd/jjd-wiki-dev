"""v2（2026-10-27）：来源登记、L0 目录、L1 配方、catalog/find/show/use、批量确认与许可托管块。

上游用本地 git 仓库替身（FigureYa 结构），不联网。运行配方的用例需要本机 Rscript 与 knitr/rmarkdown/jsonlite。
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import git_init, git_run, write_config, write_interface

RSCRIPT = Path("D:/R-4.5.0/bin/Rscript.exe")
needs_r = pytest.mark.skipif(not RSCRIPT.is_file(), reason="需要本机 Rscript")

SURV_RMD = """---
title: "FigureYaDemoSurv"
params:
  author: "tester"
---

## 需求描述 Requirement description

画两组生存曲线。

## 应用场景 Application scenario

比较高低风险组的总生存。

## 输入文件 Input file

- easy_input.csv，每行一个病人：time、status、group。

```{r}
source("install_dependencies.R")
x <- read.csv("easy_input.csv")
```

## 开始画图 Start drawing

```{r}
pdf("surv_plot.pdf")
plot(x$time, x$status)
invisible(dev.off())
plot(x$time, x$status)
```
"""

NEEDY_RMD = """---
title: "FigureYaDemoNeedy"
---

## 需求描述

需要一个不存在的包画火山图。

## 应用场景

差异基因展示。

```{r}
source("install_dependencies.R")
library(rwikiNoSuchPkgXyz)
```
"""


def deps_script(cran):
    return ("cran_packages <- c(" + ", ".join(f'"{name}"' for name in cran) + ")\n"
            "for (pkg in cran_packages) install.packages(pkg)\n")


@pytest.fixture
def upstream(tmp_path):
    repo = git_init(tmp_path / "upstream")
    surv = repo / "FigureYaDemoSurv"
    surv.mkdir()
    (surv / "FigureYaDemoSurv.Rmd").write_text(SURV_RMD, encoding="utf-8", newline="\n")
    (surv / "install_dependencies.R").write_text(deps_script(["stats"]), encoding="utf-8", newline="\n")
    (surv / "easy_input.csv").write_text("time,status,group\n1,1,A\n2,0,B\n3,1,A\n", encoding="utf-8")
    (surv / "FigureYaDemoSurv.html").write_text("<html>report</html>", encoding="utf-8")
    needy = repo / "FigureYaDemoNeedy"
    needy.mkdir()
    (needy / "FigureYaDemoNeedy.Rmd").write_text(NEEDY_RMD, encoding="utf-8", newline="\n")
    (needy / "install_dependencies.R").write_text(deps_script(["rwikiNoSuchPkgXyz"]), encoding="utf-8")
    (repo / "gallery_compress").mkdir()
    (repo / "gallery_compress/FigureYaDemoSurv.webp").write_bytes(b"RIFF0000WEBP")
    (repo / "README.md").write_text("# upstream\n", encoding="utf-8")
    git_run(repo, "add", "-A")
    git_run(repo, "commit", "-q", "-m", "upstream")
    return repo


@pytest.fixture
def v2(wiki_repo, tmp_path, upstream, monkeypatch):
    from rwiki.config import load_config
    from rwiki.sources import add_source, fetch_source, scan_source

    monkeypatch.delenv("RWIKI_AGENT", raising=False)
    config, config_path, vault = wiki_repo
    taxonomy = tmp_path / "taxonomy.yaml"
    taxonomy.write_text(json.dumps({"scenarios": {
        "survival-analysis": {"label": "生存分析", "aliases": ["生存曲线", "Kaplan-Meier"]},
        "transcriptomics": {"label": "转录组", "aliases": ["火山图"]}}}, ensure_ascii=False), encoding="utf-8")
    write_config(config_path, config.wiki_root, rscript_exe=str(RSCRIPT),
                 sources_root=str(tmp_path / "sources"), work_root=str(tmp_path / "work"),
                 r_libs=[str(tmp_path / "r-lib")])
    config = load_config(config_path)
    add_source(config, "demo", title="演示上游库", url=upstream.as_uri(), license="CC-BY-NC-SA-4.0",
               adapter="figureya", trusted=True, cite=["Demo et al. 2025"])
    fetch_source(config, "demo")
    scan_source(config, "demo")
    return config, vault


def test_save_commits_on_main(v2):
    config, vault = v2
    assert git_run(vault, "branch", "--show-current").strip() == "main"
    log = git_run(vault, "log", "--format=%s")
    assert "source add demo" in log and "source scan demo" in log
    assert git_run(vault, "status", "--porcelain", "--", "知识库").strip() == ""


def test_scan_builds_l0_catalog(v2):
    from rwiki.finder import load_catalog
    from rwiki.sources import read_items

    config, _ = v2
    items = {item["item"]: item for item in read_items(config, "demo")}
    assert set(items) == {"FigureYaDemoSurv", "FigureYaDemoNeedy"}
    surv = items["FigureYaDemoSurv"]
    assert surv["requirement"].startswith("画两组生存曲线")
    assert surv["scenario"].startswith("比较高低风险组")
    assert surv["inputs"][0]["file"] == "easy_input.csv"
    assert "surv_plot.pdf" in surv["outputs"]
    assert surv["recipe"] == "figureya-demosurv"
    assert "survival-analysis" in surv["tags"]
    assert items["FigureYaDemoNeedy"]["requires"][0] == "rwikiNoSuchPkgXyz"
    catalog = load_catalog(config)
    assert {record["id"] for record in catalog} == {"demo:FigureYaDemoSurv", "demo:FigureYaDemoNeedy"}
    assert all(record["level"] == "L0" for record in catalog)
    # Snapshot is outside the Wiki; only commit/items are recorded.
    page = (config.wiki_root / "sources/demo.md").read_text(encoding="utf-8")
    assert "L0 目录：2 项" in page and "<sources_root>/demo" in page


def test_find_and_show_l0(v2):
    from rwiki.finder import find, format_find, show

    config, _ = v2
    results = find(config, "生存曲线")
    assert results and results[0]["id"] == "demo:FigureYaDemoSurv"
    assert "→ wiki.py use demo:FigureYaDemoSurv" in format_find(results)
    detail = show(config, "demo:FigureYaDemoSurv")
    assert detail["level"] == "L0" and detail["promoted"] is None
    assert find(config, "完全不相关的词组xyz") == []


def test_promote_copies_and_tracks_licensed_source(v2):
    from rwiki.lint import lint
    from rwiki.pages import read_page

    config, vault = v2
    from rwiki.recipes import promote
    created = promote(config, "demo", ["FigureYaDemoSurv"],
                      {"FigureYaDemoSurv": {"title": "两组 KM 生存曲线", "chart_types": ["km-curve"],
                                            "tags": ["survival-analysis"], "unfit": "- 只有一组时不适用。"}})
    assert created == ["figureya-demosurv"]
    target = config.wiki_root / "recipes/figureya-demosurv"
    assert (target / "source/FigureYaDemoSurv.Rmd").read_text(encoding="utf-8") == SURV_RMD
    assert not (target / "source/FigureYaDemoSurv.html").exists()
    record = json.loads((target / "source.json").read_text(encoding="utf-8"))
    assert "FigureYaDemoSurv.html" in record["excluded"] and "easy_input.csv" in record["files"]
    meta, body = read_page(target.with_suffix(".md"))
    assert meta["status"] == "draft" and meta["title"] == "两组 KM 生存曲线"
    assert "CC BY-NC-SA 4.0" in body and "只有一组时不适用" in body
    ignore = (config.wiki_root / ".gitignore").read_text(encoding="utf-8")
    assert "/recipes/figureya-demosurv/source/" not in ignore
    tracked = git_run(vault, "ls-files", "--", "知识库/recipes")
    assert "source.json" in tracked and "FigureYaDemoSurv.Rmd" in tracked
    assert (config.wiki_root / "chart-types/km-curve.md").is_file()
    errors = [line for line in lint(config) if line.startswith("ERROR")]
    assert errors == []


def test_promote_is_all_or_nothing(v2):
    from rwiki.errors import WikiError
    from rwiki.recipes import promote

    config, vault = v2
    head = git_run(vault, "rev-parse", "HEAD").strip()
    with pytest.raises(WikiError):
        promote(config, "demo", ["FigureYaDemoSurv", "FigureYaMissing"])
    assert not (config.wiki_root / "recipes/figureya-demosurv.md").exists()
    assert git_run(vault, "rev-parse", "HEAD").strip() == head


@needs_r
def test_run_recipe_pass_receipt_and_confirm(v2):
    from rwiki.acceptance import ready_for_use
    from rwiki.finder import find
    from rwiki.pages import read_page
    from rwiki.recipes import promote, run_recipes
    from rwiki.templates import mark_ready_many
    from rwiki.workflow import workflow_snapshot

    config, vault = v2
    promote(config, "demo", ["FigureYaDemoSurv"], {"FigureYaDemoSurv": {"unfit": "- 只有一组时不适用。"}})
    [result] = run_recipes(config, ["figureya-demosurv"], timeout=300)
    assert result["state"] == "pass", result.get("error")
    assert result["scope"] == "as-is" and "surv_plot.pdf" in result["outputs"]
    assert result["figures"] and result["missing_outputs"] == []
    text = json.dumps(result, ensure_ascii=False)
    assert str(config.wiki_root) not in text and str(Path.home()) not in text
    page = config.wiki_root / "recipes/figureya-demosurv.md"
    assert (page.with_suffix("") / "preview.png").is_file()
    assert workflow_snapshot(config)["recipes/figureya-demosurv.md"]["queue"] == "confirm"
    assert find(config, "生存", runnable=True)[0]["id"] == "figureya-demosurv"
    mark_ready_many(config, ["figureya-demosurv"])
    assert read_page(page)[0]["status"] == "ready"
    assert ready_for_use(config, page)
    assert "最近运行：pass" in page.read_text(encoding="utf-8")


@needs_r
def test_missing_package_is_not_run(v2):
    from rwiki.recipes import promote, run_recipes
    from rwiki.workflow import workflow_snapshot

    config, _ = v2
    promote(config, "demo", ["FigureYaDemoNeedy"])
    [result] = run_recipes(config, ["figureya-demoneedy"], timeout=300)
    assert result["state"] == "not_run"
    assert result["missing_packages"] == ["rwikiNoSuchPkgXyz"]
    row = workflow_snapshot(config)["recipes/figureya-demoneedy.md"]
    assert row["label"] == "待装包" and "作者按批次批准" in row["reason"]


def test_batch_mark_ready_refuses_all_when_one_fails(v2):
    from rwiki.errors import WikiError
    from rwiki.pages import read_page
    from rwiki.recipes import promote
    from rwiki.templates import mark_ready_many

    config, _ = v2
    promote(config, "demo", ["FigureYaDemoSurv", "FigureYaDemoNeedy"])
    with pytest.raises(WikiError, match="全部未改动"):
        mark_ready_many(config, ["figureya-demosurv", "figureya-demoneedy"])
    for recipe_id in ("figureya-demosurv", "figureya-demoneedy"):
        assert read_page(config.wiki_root / f"recipes/{recipe_id}.md")[0]["status"] == "draft"


@needs_r
def test_use_copy_and_run_dir_new_data(v2, tmp_path):
    from rwiki.finder import use
    from rwiki.recipes import promote, run_dir

    config, vault = v2
    promote(config, "demo", ["FigureYaDemoSurv"])
    project = tmp_path / "project"
    project.mkdir()
    head = git_run(vault, "rev-parse", "HEAD").strip()
    result = use(config, "figureya-demosurv", project)
    copy = Path(result["copy"])
    assert copy == project / "wiki-use/figureya-demosurv"
    note = (copy / "RWIKI-USE.md").read_text(encoding="utf-8")
    assert "time、status、group" in note and "CC BY-NC-SA 4.0" in note
    origin = json.loads((copy / "rwiki-origin.json").read_text(encoding="utf-8"))
    assert origin["level"] == "L1" and "easy_input.csv" in origin["files"]
    assert git_run(vault, "rev-parse", "HEAD").strip() == head  # use never writes the Wiki
    (copy / "easy_input.csv").write_text("time,status,group\n5,1,A\n6,1,B\n7,0,B\n", encoding="utf-8")
    receipt = run_dir(config, copy, timeout=300)
    assert receipt["state"] == "pass", receipt.get("error")
    assert receipt["scope"] == "new-data" and receipt["changed_inputs"] == ["easy_input.csv"]
    assert list((copy / "rwiki-runs").glob("*.json"))
    assert (copy / "install_dependencies.R.rwiki-orig").is_file()


def test_use_l0_item_from_trusted_source(v2, tmp_path):
    from rwiki.errors import WikiError
    from rwiki.finder import use

    config, _ = v2
    project = tmp_path / "p2"
    project.mkdir()
    result = use(config, "demo:FigureYaDemoSurv", project, name="surv")
    copy = Path(result["copy"])
    assert (copy / "FigureYaDemoSurv.Rmd").is_file() and not (copy / "FigureYaDemoSurv.html").exists()
    assert json.loads((copy / "rwiki-origin.json").read_text(encoding="utf-8"))["level"] == "L0"
    with pytest.raises(WikiError, match="已存在"):
        use(config, "demo:FigureYaDemoSurv", project, name="surv")
    with pytest.raises(WikiError, match="不能在知识库内"):
        use(config, "demo:FigureYaDemoSurv", config.wiki_root / "recipes")


def test_restore_source_after_loss(v2):
    from rwiki.recipes import integrity_errors, promote, restore_source

    config, _ = v2
    promote(config, "demo", ["FigureYaDemoSurv"])
    page = config.wiki_root / "recipes/figureya-demosurv.md"
    shutil.rmtree(page.with_suffix("") / "source")
    assert integrity_errors(page)
    assert restore_source(config, "figureya-demosurv")["restored"] == 3
    assert integrity_errors(page) == []


def test_scenario_and_template_from_recipe_lint_clean(v2):
    from rwiki.facts import page_facts
    from rwiki.lint import lint
    from rwiki.pages import read_page, write_page
    from rwiki.recipes import promote
    from rwiki.store import save
    from rwiki.templates import scaffold_from_recipe

    config, _ = v2
    promote(config, "demo", ["FigureYaDemoSurv"])
    tid = scaffold_from_recipe(config, "figureya-demosurv", "km-curve", "KM 曲线")
    meta, _ = read_page(config.wiki_root / f"templates/{tid}.md")
    assert meta["sources"] == ["recipes/figureya-demosurv"] and meta["layouts"] == []
    assert meta["license"] == "CC-BY-NC-SA-4.0"
    # The agent's next step: declare the template's input table (here a minimal survival interface).
    write_interface(config.wiki_root, "survival-time-status",
                    {"time": {"type": "float", "description": "随访时间"},
                     "status": {"type": "int", "description": "事件 1/删失 0"}})
    spec_path = config.wiki_root / f"templates/{tid}/spec.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["tables"] = {"surv": {"interface": "survival-time-status", "description": "每行一个病人"}}
    spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    scenario = {"type": "scenario", "id": "clinical", "title": "临床预测与生存", "summary": "预后与生存",
                "tags": ["survival-analysis"], "keywords": ["生存"],
                "picks": [{"id": "recipes/figureya-demosurv", "note": "两组 KM"},
                          {"id": "demo:FigureYaDemoNeedy", "note": "L0 候选"}]}
    write_page(config.wiki_root / "scenarios/clinical.md", scenario,
               "# 临床预测与生存\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n## 什么时候用\n\n预后。\n\n"
               "## 首选组合\n\n见下表。\n\n## 注意\n\n比例风险假设。\n\n<!-- user:start -->\n<!-- user:end -->\n")
    save(config, "scenario clinical")
    facts = page_facts(config, scenario)
    assert "两组 KM" in facts and "L0" in facts
    ignore = (config.wiki_root / ".gitignore").read_text(encoding="utf-8")
    assert f"/templates/{tid}/code/" not in ignore
    errors = [line for line in lint(config) if line.startswith("ERROR")]
    assert errors == []
    from rwiki.finder import find
    assert find(config, "生存")[0]["id"] in ("figureya-demosurv", "demo:FigureYaDemoNeedy")
    # Knowledge code is tracked: a missing code directory is an error in CI too.
    shutil.rmtree(config.wiki_root / f"templates/{tid}/code")
    plain = [line for line in lint(config) if line.startswith(f"ERROR templates/{tid}.md")]
    assert plain and all("code/" in line for line in plain)
    ci = lint(config, ci=True)
    assert any(line.startswith(f"ERROR templates/{tid}.md") for line in ci)
    assert not any(line.startswith(f"LOCAL-ONLY templates/{tid}.md") for line in ci)


def test_scenario_pick_must_exist(v2):
    from rwiki.lint import lint
    from rwiki.pages import write_page
    from rwiki.store import save

    config, _ = v2
    write_page(config.wiki_root / "scenarios/bad.md",
               {"type": "scenario", "id": "bad", "title": "坏场景", "picks": ["recipes/nope"]},
               "# 坏场景\n\n<!-- facts:start -->\n<!-- facts:end -->\n\n<!-- user:start -->\n<!-- user:end -->\n")
    save(config, "bad scenario")
    assert any("场景首选条目不存在" in line for line in lint(config))


def test_restricted_dirs_cover_methods_recipes_templates(tmp_path):
    from rwiki.pages import write_page
    from rwiki.push_guard import restricted_dirs

    root = tmp_path / "wiki"
    write_page(root / "methods/m.md", {"type": "method", "id": "m", "license": "GPL-3.0"}, "# m\n")
    write_page(root / "methods/mit.md", {"type": "method", "id": "mit", "license": "MIT"}, "# mit\n")
    write_page(root / "recipes/r.md", {"type": "recipe", "id": "r", "license": "CC-BY-NC-SA-4.0"}, "# r\n")
    write_page(root / "recipes/ok.md", {"type": "recipe", "id": "ok", "license": "CC-BY-4.0"}, "# ok\n")
    write_page(root / "templates/t.md", {"type": "template", "id": "t", "license": "CC-BY-NC-4.0"}, "# t\n")
    assert restricted_dirs(root) == ["methods/m/code/", "methods/m/source/", "recipes/r/source/",
                                     "templates/t/code/", "templates/t/example/"]


def test_required_packages_follow_code_not_install_list():
    """FigureYa install lists sometimes name colours or data columns as packages ("blueviolet")."""
    from rwiki.adapters import declared_only, packages, required_packages

    script = deps_script(["ggplot2", "blueviolet", "phylum", "survminer"]) + \
        'bioc_packages <- c("limma")\n'
    rmd = ('```{r}\nsource("install_dependencies.R")\nlibrary(ggplot2)\n'
           'fit <- survminer::ggsurvplot(x)\ncol <- c("blueviolet")\nx <- limma:::internal\n'
           'base::paste("a")\n```\n')
    pkgs = packages(script, rmd)
    assert required_packages(pkgs) == ["ggplot2", "survminer", "limma"]
    assert declared_only(pkgs) == ["blueviolet", "phylum"]


@needs_r
def test_runner_knits_in_global_env(tmp_path):
    """survminer::ggsurvplot / rms::datadist look data up in the global environment."""
    runner = Path(__file__).resolve().parents[1] / "assets" / "rmd_knit_runner.R"
    shutil.copyfile(runner, tmp_path / "_rwiki_knit.R")
    (tmp_path / "demo.Rmd").write_text(
        "```{r}\nsv <- data.frame(x = 1:3)\nlook <- function() get('sv', envir = globalenv())\n"
        "stopifnot(nrow(look()) == 3)\n```\n", encoding="utf-8", newline="\n")
    result = subprocess.run([str(RSCRIPT), "--vanilla", "_rwiki_knit.R", "demo.Rmd", "out.md"],
                            cwd=tmp_path, capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert result.returncode == 0, result.stderr
    assert json.loads((tmp_path / "rwiki-session.json").read_text(encoding="utf-8"))["status"] == "ok"


WIKI_R_LIB = Path("E:/research-wiki-env/R-lib/figureya")


def _pdf_only_run(tmp_path, r_libs):
    from types import SimpleNamespace

    work = tmp_path / "work"
    work.mkdir()
    subprocess.run([str(RSCRIPT), "--vanilla", "-e", "pdf('only.pdf'); plot(1:3); invisible(dev.off())"],
                   cwd=work, check=True, capture_output=True)
    config = SimpleNamespace(rscript_exe=RSCRIPT, r_libs=r_libs, work_root=tmp_path / "wr")
    receipt = {"outputs": {"only.pdf": "x", "table.csv": "y"}, "expected_outputs": ["only.pdf"], "checks": []}
    return config, work, receipt


@needs_r
@pytest.mark.skipif(not (WIKI_R_LIB / "pdftools").is_dir(), reason="Wiki 专用库里没有 pdftools")
def test_pdf_only_module_gets_preview_from_first_page(tmp_path):
    """Upstream modules that only call pdf() still get a run picture: page 1 of the declared PDF."""
    from PIL import Image
    from rwiki.recipes import _pdf_fallback

    config, work, receipt = _pdf_only_run(tmp_path, [WIKI_R_LIB])
    picture, preview = _pdf_fallback(config, work, receipt)
    assert preview == {"from": "only.pdf", "page": 1, "kind": "pdf"}
    with Image.open(picture) as image:
        assert image.format == "PNG" and min(image.size) > 100
    assert receipt["checks"] == []


@needs_r
def test_pdf_preview_failure_is_recorded_not_fatal(tmp_path):
    from rwiki.recipes import _pdf_fallback

    config, work, receipt = _pdf_only_run(tmp_path, [tmp_path / "no-such-lib"])
    if any((Path(path) / "pdftools").is_dir() for path in subprocess.run(
            [str(RSCRIPT), "--vanilla", "-e", "cat(.Library, sep='\\n')"],
            capture_output=True, text=True).stdout.splitlines()):
        pytest.skip("R 自带库里已有 pdftools")
    assert _pdf_fallback(config, work, receipt) == (None, None)
    assert receipt["checks"] and "only.pdf 转预览图失败" in receipt["checks"][0]

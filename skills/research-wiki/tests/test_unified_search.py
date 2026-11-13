"""Unified retrieval must search author-independent knowledge and refresh evidence."""
import json
from pathlib import Path
from dataclasses import replace
import pytest
from rwiki.config import Config
from rwiki.pages import write_page
from rwiki import finder

@pytest.fixture
def config(tmp_path):
    wiki=tmp_path / "wiki"
    wiki.mkdir()
    taxonomy=tmp_path / "taxonomy.json"
    taxonomy.write_text('{"scenarios": {}}', encoding="utf-8")
    return Config(wiki, tmp_path / "gallery", taxonomy, Path("python"), Path("Rscript"), 8765,
                  work_root=tmp_path / "work", sources_root=tmp_path / "upstream")

def page(config, name, text, kind="method", **extra):
    folder={"method":"methods", "interface":"interfaces", "chart-type":"chart-types",
            "source":"sources", "scenario":"scenarios", "project":"projects"}.get(kind, kind+"s")
    path=config.wiki_root / folder / (name+".md")
    path.parent.mkdir(parents=True, exist_ok=True)
    meta={"type":kind,"id":name,"title":name,"status":"draft", **extra}
    write_page(path, meta, text)
    return path

def test_deep_sections_search_and_block_exclusions(config):
    from rwiki.search import search
    page(config,"deep", "## 原理\n稀有术语 pseudoreplication 同一样本内细胞不独立。\n"
         "<!-- user:start -->privatealpha<!-- user:end -->\n"
         "<!-- facts:start -->generatedomega<!-- facts:end -->")
    result=search(config,"pseudoreplication")
    assert result["results"][0]["id"]=="deep"
    assert result["results"][0]["match_section"]=="原理"
    assert "pseudoreplication" in result["results"][0]["snippet"]
    assert not search(config,"privatealpha")["results"]
    assert not search(config,"generatedomega")["results"]


def test_layout_reference_is_searchable_but_never_executable(config):
    from rwiki.search import search
    page(config, 'reference-figure', '## 适用\nrarelayoutterm', kind='layout')
    hit = search(config, 'rarelayoutterm')['results'][0]
    assert hit['kind'] == 'layout'
    assert not hit.get('usable')
    assert not search(config, 'rarelayoutterm', runnable=True)['results']

def test_all_knowledge_kinds_archived_and_removed(config):
    from rwiki.search import search
    for kind in ("method","interface","chart-type","source","scenario","project"):
        page(config,kind,"## 内涵\nuniqueterm", kind)
    page(config,"gone","## 原理\nuniqueterm", status="archived")
    found=search(config,"uniqueterm",limit=30)["results"]
    assert {r["kind"] for r in found}=={"method","interface","chart-type","source","scenario","project"}
    (config.wiki_root / "sources/figureya-curation.json").write_text(json.dumps(
        {"schema_version":1,"decisions":{"method":{"decision":"removed"}}}), encoding="utf-8")
    assert "method" not in {r["id"] for r in search(config,"uniqueterm",limit=30)["results"]}

def test_english_acronym_does_not_match_inside_word(config):
    from rwiki.search import search
    page(config,"coexpression","## 原理\ncoexpression prediction approximation")
    page(config,"precision","## 原理\nPR precision recall")
    assert [r["id"] for r in search(config,"PR")["results"]]==["precision"]

def test_finder_keeps_legacy_fields_and_new_evidence(config):
    page(config,"differential-expression","## 用途\n差异表达分析", title="差异表达分析")
    result=finder.find(config,"差异表达")
    assert result[0]["id"]=="differential-expression"
    assert {"use","level","why","match_section","snippet","asset_availability","evidence_state"} <= result[0].keys()

def test_incremental_index_updates_deletes_and_has_no_truth_cache(config, monkeypatch):
    from rwiki.search import search
    p=page(config,"mutable","## 原理\nfirstterm")
    first=search(config,"firstterm")
    second=search(config,"firstterm")
    assert second["index"]["reused"]>=1
    assert (config.work_root / "search/knowledge.json").is_file()
    cache=(config.work_root / "search/knowledge.json").read_text(encoding="utf-8")
    assert '"usable"' not in cache and '"run"' not in cache and '"evidence_state"' not in cache
    page(config,"mutable","## 原理\notherterm")
    assert not search(config,"firstterm")["results"]
    assert search(config,"otherterm")["index"]["reused"]>=1
    p.unlink()
    assert not search(config,"otherterm")["results"]

def test_current_evidence_changes_without_reindex(config,monkeypatch):
    from rwiki.search import search
    from rwiki import acceptance
    page(config,"fresh","## 用途\nrelevantterm")
    monkeypatch.setattr(acceptance,"ready_for_use",lambda *a,**k: True)
    assert search(config,"relevantterm",runnable=True)["results"]
    monkeypatch.setattr(acceptance,"ready_for_use",lambda *a,**k: False)
    assert not search(config,"relevantterm",runnable=True)["results"]

def test_source_scope_is_explicit_code_only_and_parent_kind(config):
    from rwiki.search import search
    p=page(config,"family","## 用途\n普通知识")
    source=p.with_suffix("") / "source"
    source.mkdir(parents=True)
    (source / "analysis.R").write_text("# exclusivecodeterm\nx <- 1",encoding="utf-8")
    (source / "private.csv").write_text("privatedataterm",encoding="utf-8")
    (source / "runs").mkdir()
    (source / "runs/log.py").write_text("privatelogterm",encoding="utf-8")
    assert not search(config,"exclusivecodeterm")["results"]
    hits=search(config,"exclusivecodeterm",scope="source")["results"]
    assert hits and hits[0]["kind"]=="method"
    assert hits[0]["source_path"].endswith("source/analysis.R")
    assert not search(config,"privatedataterm",scope="source")["results"]
    assert not search(config,"privatelogterm",scope="source")["results"]

def test_export_and_python_rank_parity(config):
    from rwiki.search import search, export_index, rank_export
    page(config,"de","## 用途\n差异表达 分析",title="差异表达")
    page(config,"pr","## 原理\nprecision recall PR")
    exported=export_index(config)
    for q in ("差异表达","PR"):
        assert [(r["id"],r["score"]) for r in rank_export(exported,q)] == [
            (r["id"],r["score"]) for r in search(config,q)["results"]]

def test_real_daily_questions_top_three(vault_root):
    from rwiki.search import search
    root=vault_root / "知识库"
    cfg=Config(root,vault_root / "画廊",Path("missing"),Path("python"),Path("Rscript"),8765,
               work_root=vault_root.parent / "research-wiki-env/work/rwiki-search-tests")
    assert "differential-expression" in [r["id"] for r in search(cfg,"我想做差异表达分析")["results"][:3]]
    assert "cell-type-annotation" in [r["id"] for r in search(cfg,"我想给细胞做注释")["results"][:3]]
    assert "cell-type-annotation" in [r["id"] for r in search(cfg,"判断每个细胞属于什么类型")["results"][:3]]


def test_api_returns_same_engine_envelope_and_rejects_bad_scope(config):
    from fastapi.testclient import TestClient
    from rwiki.server import create_app
    from rwiki.search import search
    page(config,"api","## 原理\nreliablekeyword")
    client=TestClient(create_app(config))
    r=client.get("/api/search",params={"q":"reliablekeyword"})
    assert r.status_code==200
    expected=search(config,"reliablekeyword")
    assert r.json()["results"]==expected["results"]
    assert {"results","coverage","index"} <= r.json().keys()
    assert client.get("/api/search",params={"q":"x","scope":"all"}).status_code==422
    assert client.get("/api/search",params={"q":" ","limit":0}).status_code==422


def test_light_assets_never_reuse_historical_pass(config,monkeypatch):
    from rwiki.search import search
    from rwiki import acceptance,asset_checkout
    page(config,"sparse","## 用途\nreliablekeyword")
    monkeypatch.setattr(acceptance,"ready_for_use",lambda *a,**k: True)
    monkeypatch.setattr(asset_checkout,"assets_state",lambda *a,**k: {"state":"not_downloaded","profile":"light","missing":["code/run.R"]})
    hit=search(config,"reliablekeyword")["results"][0]
    assert hit["usable"] is False and hit["asset_availability"]=="not_downloaded"
    assert hit["evidence_state"]=="not_downloaded"
    assert not search(config,"reliablekeyword",runnable=True)["results"]


def test_catalog_l0_survives_and_archived_source_is_excluded(config):
    from rwiki.search import search
    p=page(config,"public","## 这是什么\n公开来源","source",license="MIT",adapter="figureya")
    items=p.with_suffix("");items.mkdir()
    item={"id":"public:example","item":"example","title":"l0searchterm","requires":[],"inputs":[]}
    (items/"items.jsonl").write_text(json.dumps(item)+"\n",encoding="utf-8")
    result=search(config,"l0searchterm")["results"]
    assert result and result[0]["level"]=="L0" and result[0]["usable"] is False
    page(config,"public","## 这是什么\n公开来源","source",license="MIT",adapter="figureya",status="archived")
    assert not search(config,"l0searchterm")["results"]


def test_source_code_examples_are_searchable(config):
    from rwiki.search import search
    p=page(config,"family","## 用途\n知识")
    source=p.with_suffix("")/"source/examples";source.mkdir(parents=True)
    (source/"demo.R").write_text("legitimateexamplecode",encoding="utf-8")
    assert search(config,"legitimateexamplecode",scope="source")["results"]


def test_parity_fixture_still_matches_python():
    from rwiki.search import rank_export
    fixture=json.loads((Path(__file__).parent/"fixtures/search-parity.json").read_text(encoding="utf-8"))
    for case in fixture["cases"]:
        assert rank_export(fixture["index"],case["query"],**case["options"])==case["results"]


def test_corrupt_derivative_cache_is_rebuilt(config):
    from rwiki.search import search
    page(config,"recover","## 原理\nrecoverykeyword")
    path=config.work_root/"search/knowledge.json"
    path.parent.mkdir(parents=True)
    path.write_text("[]",encoding="utf-8")
    assert search(config,"recoverykeyword")["results"][0]["id"]=="recover"


def test_runnable_recipe_requires_current_as_is_receipt(config,monkeypatch):
    from rwiki.search import search
    from rwiki import acceptance,recipes
    page(config,"recipe","## 用途\nrecipekeyword",kind="recipe")
    monkeypatch.setattr(acceptance,"ready_for_use",lambda *a,**k: False)
    monkeypatch.setattr(recipes,"current_run",lambda *a,**k: {"state":"pass","scope":"new-data"})
    assert not search(config,"recipekeyword",runnable=True)["results"]
    monkeypatch.setattr(recipes,"current_run",lambda *a,**k: {"state":"pass","scope":"as-is"})
    assert search(config,"recipekeyword",runnable=True)["results"][0]["id"]=="recipe"


def test_layout_is_reference_knowledge_and_never_executable(config,monkeypatch):
    from rwiki.search import search
    from rwiki import acceptance
    page(config,"reference-layout","## 回答什么问题\nuniquelayoutknowledge",kind="layout",status="ready")
    monkeypatch.setattr(acceptance,"ready_for_use",lambda *a,**k: True)
    hits=search(config,"uniquelayoutknowledge")["results"]
    assert hits and hits[0]["kind"]=="layout"
    assert hits[0]["reference_only"] is True
    assert hits[0]["usable"] is False and hits[0]["evidence_state"]=="unverified"
    assert not search(config,"uniquelayoutknowledge",runnable=True)["results"]


def test_ordered_exact_phrase_bonus_is_bounded_and_respects_ascii_boundaries(config):
    from rwiki.search import search
    page(config,"a-reversed","## 原理\nbeta alpha",title="Order probe")
    page(config,"z-ordered","## 原理\nalpha beta",title="Order probe")
    page(config,"substring","## 原理\nunalpha betaextra alpha separately beta",title="Order probe")
    hits=search(config,'"alpha beta"')["results"]
    assert hits[0]["id"]=="z-ordered"
    assert any("精确短语" in why for why in hits[0]["why"])
    substring=next(r for r in hits if r["id"]=="substring")
    assert not any("精确短语" in why for why in substring["why"])
    from rwiki.search import export_index,rank_export
    index=export_index(config)
    without={**index,"ranking":{**index["ranking"],"phrase_weight":0}}
    plain=next(r for r in rank_export(without,'"alpha beta"') if r["id"]=="z-ordered")
    assert plain["score"] < hits[0]["score"] <= plain["score"]*1.500001


def upstream_catalog(config, modules):
    p=page(config,"public","## 这是什么\n公开来源",kind="source",snapshot="snap",adapter="figureya",license="MIT")
    p.with_suffix("").mkdir(exist_ok=True)
    items=[{"id":"public:"+name,"item":name,"title":title,"requires":[],"inputs":[]} for name,title in modules]
    (p.with_suffix("")/"items.jsonl").write_text("".join(json.dumps(i)+"\n" for i in items),encoding="utf-8")
    return config.sources_root/"snap"


def test_l0_availability_checks_actual_item_and_never_fetches(config,monkeypatch):
    from rwiki.search import search
    from rwiki import sources
    snapshot=upstream_catalog(config,[("Example","l0availabilityterm")])
    monkeypatch.setattr(sources,"fetch_source",lambda *a,**k: pytest.fail("search must never fetch"))
    missing=search(config,"l0availabilityterm")["results"][0]
    assert missing["asset_availability"]=="not_downloaded" and missing["usable"] is False
    module=snapshot/"Example";module.mkdir(parents=True)
    (module/"run.R").write_text("real downloaded code",encoding="utf-8")
    present=search(config,"l0availabilityterm")["results"][0]
    assert present["asset_availability"]=="available" and present["usable"] is False


def test_l0_sparse_omission_differs_from_unexpected_tracked_missing(config):
    from rwiki.search import search
    from conftest import git_init,git_run
    snapshot=upstream_catalog(config,[("Example","l0trackedterm")])
    git_init(snapshot)
    module=snapshot/"Example";module.mkdir()
    code=module/"run.R";code.write_text("code",encoding="utf-8")
    (snapshot/"README.md").write_text("description",encoding="utf-8")
    git_run(snapshot,"add","-A");git_run(snapshot,"commit","-qm","fixture")
    code.unlink()
    assert search(config,"l0trackedterm")["results"][0]["asset_availability"]=="missing"
    git_run(snapshot,"checkout","--","Example/run.R")
    git_run(snapshot,"sparse-checkout","set","--no-cone","README.md")
    assert search(config,"l0trackedterm")["results"][0]["asset_availability"]=="not_downloaded"


def test_upstream_source_respects_exact_removed_and_archived_module_paths(config):
    from rwiki.search import search
    snapshot=upstream_catalog(config,[("Gone","removeditemterm"),("GoneExtra","keptitemterm"),("Archived","archiveditemterm")])
    for name,word in [("Gone","gonecodeterm"),("GoneExtra","keptcodeterm"),("Archived","archivedcodeterm")]:
        module=snapshot/name;module.mkdir(parents=True)
        (module/"run.R").write_text(word,encoding="utf-8")
    assert search(config,"gonecodeterm",scope="source")["results"]
    (config.wiki_root/"sources/figureya-curation.json").write_text(json.dumps({"schema_version":1,"decisions":{"public:Gone":{"decision":"removed"}}}),encoding="utf-8")
    page(config,"custom-archived-slug","## 用途\narchiveditemterm",kind="recipe",status="archived",source={"id":"public","item":"Archived"})
    assert not search(config,"gonecodeterm",scope="source")["results"]
    assert not search(config,"archivedcodeterm",scope="source")["results"]
    retained=search(config,"keptcodeterm",scope="source")["results"]
    assert retained and retained[0]["source_path"].endswith("GoneExtra/run.R")
    assert not search(config,"removeditemterm")["results"]
    assert not search(config,"archiveditemterm")["results"]
    assert search(config,"keptitemterm")["results"]

"""Owner signoff covers the evidenced repair variant, never original source pass."""
import hashlib,json
from pathlib import Path
import pytest
from rwiki.config import Config
from rwiki.pages import read_page,write_page
from rwiki.errors import WikiError


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def put_json(path,value):path.write_text(json.dumps(value,ensure_ascii=False),encoding="utf-8")

@pytest.fixture
def repaired(tmp_path):
    root=tmp_path/"wiki";root.mkdir()
    cfg=Config(root,tmp_path/"gallery",tmp_path/"taxonomy.json",Path("python"),Path("Rscript"),8765,work_root=tmp_path/"work")
    page=root/"recipes/example.md";page.parent.mkdir()
    write_page(page,{"type":"recipe","id":"example","title":"repairprobeterm","status":"draft","license":"MIT"},
               "## 用途\nrepairprobeterm\n<!-- user:start -->作者原话<!-- user:end -->")
    asset=page.with_suffix("")
    for folder in ("source","runs","repair","repair-runs"):(asset/folder).mkdir(parents=True)
    (asset/"source/run.R").write_text("original failing source",encoding="utf-8")
    (asset/"repair/run.R").write_text("evidenced repaired variant",encoding="utf-8")
    (asset/"repair/input.csv").write_text("public fixture input",encoding="utf-8")
    original={"run.R":digest(asset/"source/run.R")}
    code={p.name:digest(p) for p in (asset/"repair").iterdir()}
    put_json(asset/"runs/20260101.json",{"schema_version":2,"kind":"run","id":"example","scope":"as-is","state":"fail","code":original})
    receipt={"schema_version":2,"kind":"run","id":"example","scope":"repair","state":"pass","exit_code":0,"code":code,"missing_outputs":[]}
    put_json(asset/"repair-runs/20260102.json",receipt)
    manifest={"schema_version":1,"kind":"recipe-repair","id":"example","execution_tree":"repair/","files":code,
              "latest_run":"repair-runs/20260102.json","latest_scope":"repair","latest_state":"pass"}
    put_json(asset/"repair.json",manifest)
    return cfg,page,asset


def workflow(repaired,monkeypatch):
    from rwiki import workflow as wf
    cfg,page,_=repaired
    monkeypatch.setattr(wf,"entry_errors",lambda *a,**k:["最近运行为 fail：original failure preserved"])
    return wf.workflow_snapshot(cfg)["recipes/example.md"]


def test_confirmation_creates_only_new_scope_record_and_preserves_original_fail(repaired,monkeypatch):
    from rwiki.repair_acceptance import record_repair_acceptance,validate_repair
    from rwiki.recipes import current_run
    from rwiki.finder import find
    cfg,page,asset=repaired
    before={p:p.read_bytes() for p in [page,*asset.rglob("*")] if p.is_file()}
    assert validate_repair(cfg,page)["valid"]
    assert not validate_repair(cfg,page,require_approval=True)["valid"]
    approval=record_repair_acceptance(cfg,page)
    assert approval["scope"]=="repair" and approval["owner_confirmed"] is True
    assert approval["owner_instruction"]=="全部改为通过"
    assert validate_repair(cfg,page,require_approval=True)["valid"]
    state=workflow(repaired,monkeypatch)
    assert state["stage"]=="repair_complete" and state["queue"] is None
    assert state["label"]=="修补版运行通过"
    assert all(word in state["reason"] for word in ("原样","source/","repair/"))
    assert read_page(page)[0]["status"]=="draft" and current_run(cfg,page)["state"]=="fail"
    assert not find(cfg,"repairprobeterm",runnable=True)
    assert all(p.read_bytes()==data for p,data in before.items())
    assert set(p for p in asset.rglob("*") if p.is_file())-set(before)=={asset/"repair-acceptance.json"}


@pytest.mark.parametrize("mutation",["code_changed","code_missing","input_missing","new_file","receipt_changed","receipt_fail","manifest_changed","receipt_path_escape"])
def test_changed_or_missing_evidence_invalidates_confirmation(repaired,monkeypatch,mutation):
    from rwiki.repair_acceptance import record_repair_acceptance,validate_repair
    cfg,page,asset=repaired
    record_repair_acceptance(cfg,page)
    if mutation=="code_changed":(asset/"repair/run.R").write_text("changed",encoding="utf-8")
    elif mutation=="code_missing":(asset/"repair/run.R").unlink()
    elif mutation=="input_missing":(asset/"repair/input.csv").unlink()
    elif mutation=="new_file":(asset/"repair/other.txt").write_text("new file",encoding="utf-8")
    elif mutation.startswith("receipt") and mutation!="receipt_path_escape":
        path=asset/"repair-runs/20260102.json";data=json.loads(path.read_text(encoding="utf-8"))
        data["state" if mutation=="receipt_fail" else "note"]="fail" if mutation=="receipt_fail" else "changed receipt bytes"
        put_json(path,data)
    else:
        path=asset/"repair.json";data=json.loads(path.read_text(encoding="utf-8"))
        data["latest_run" if mutation=="receipt_path_escape" else "note"]="../outside.json" if mutation=="receipt_path_escape" else "changed manifest"
        put_json(path,data)
    report=validate_repair(cfg,page,require_approval=True)
    assert not report["valid"] and report["errors"]
    assert workflow(repaired,monkeypatch)["stage"]=="recipe_work"


@pytest.mark.parametrize("mutation",["missing_receipt","failed_receipt","wrong_scope","stale_code"])
def test_signoff_cannot_create_pass_without_existing_current_pass(repaired,mutation):
    from rwiki.repair_acceptance import record_repair_acceptance
    cfg,page,asset=repaired
    path=asset/"repair-runs/20260102.json"
    if mutation=="missing_receipt":path.unlink()
    elif mutation=="stale_code":(asset/"repair/run.R").write_text("changed",encoding="utf-8")
    else:
        data=json.loads(path.read_text(encoding="utf-8"));data["scope" if mutation=="wrong_scope" else "state"]="as-is" if mutation=="wrong_scope" else "fail"
        put_json(path,data)
    with pytest.raises(WikiError):record_repair_acceptance(cfg,page)
    assert not (asset/"repair-acceptance.json").exists()


def test_valid_repair_without_owner_confirmation_stays_in_agent_queue(repaired,monkeypatch):
    assert workflow(repaired,monkeypatch)["stage"]=="recipe_work"
    assert not (repaired[2]/"repair-acceptance.json").exists()


def test_approval_flag_and_bound_receipt_hash_are_checked(repaired):
    from rwiki.repair_acceptance import record_repair_acceptance,validate_repair
    cfg,page,asset=repaired
    approval=record_repair_acceptance(cfg,page)
    approval["owner_confirmed"]=False
    put_json(asset/"repair-acceptance.json",approval)
    assert not validate_repair(cfg,page,require_approval=True)["valid"]


def test_hash_memo_lasts_only_for_current_read_session(repaired,monkeypatch):
    from rwiki import repair_acceptance as ra
    from rwiki.read_cache import read_session
    cfg,page,asset=repaired
    record=ra.record_repair_acceptance(cfg,page)
    calls=[];original=ra._hash_file
    def counting(path):calls.append(path);return original(path)
    monkeypatch.setattr(ra,"_hash_file",counting)
    with read_session():
        assert ra.validate_repair(cfg,page,require_approval=True)["valid"]
        initial=len(calls)
        assert ra.validate_repair(cfg,page,require_approval=True)["valid"]
        assert len(calls)==initial
    (asset/"repair/input.csv").unlink()
    with read_session():assert not ra.validate_repair(cfg,page,require_approval=True)["valid"]
    assert len(calls)>initial



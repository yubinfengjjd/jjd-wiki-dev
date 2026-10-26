import argparse
import json
import sys
from pathlib import Path

from .config import load_config
from .contact_sheet import contact_sheet
from .errors import WikiError
from .ingest import ingest_figure
from .interfaces import add_interface
from .methods import scaffold_method
from .lint import lint
from .layouts import render_layout, verify_layout
from .store import init, save
from .suggest import suggest, suggest_methods, suggest_pipeline
from .templates import attach_template, mark_ready, pending, render, scaffold_template, verify_template
from .usage import record_method_use, record_use


def serve(config, no_browser: bool) -> None:
    import asyncio
    import webbrowser

    import uvicorn

    from .server import create_app

    server = uvicorn.Server(uvicorn.Config(create_app(config), host="127.0.0.1", port=config.port))

    async def run_server():
        task = asyncio.create_task(server.serve())
        while not server.started and not task.done():
            await asyncio.sleep(0.05)
        if server.started and not no_browser:
            webbrowser.open(f"http://127.0.0.1:{config.port}/")
        await task

    asyncio.run(run_server())


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="科研知识库")
    result.add_argument("--config", type=Path, default=Path(__file__).resolve().parents[1] / "config.json")
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    ingest = commands.add_parser("ingest-figure")
    selection = ingest.add_mutually_exclusive_group(required=True)
    selection.add_argument("entry_id", nargs="?")
    selection.add_argument("--all", action="store_true")
    commands.add_parser("save").add_argument("message")
    commands.add_parser("lint")
    commands.add_parser("pending").add_argument('--json', action='store_true')
    checking = commands.add_parser('check-entry')
    checking.add_argument('entry_id')
    checking.add_argument('--record', action='store_true')
    commands.add_parser("serve").add_argument("--no-browser", action="store_true")
    for name in ("verify-template", "verify-layout", "mark-ready"):
        commands.add_parser(name).add_argument("entry_id")
    scaffold = commands.add_parser("scaffold-template")
    scaffold.add_argument("entry_id")
    scaffold.add_argument("--chart-type", required=True)
    scaffold.add_argument("--panels", required=True)
    scaffold.add_argument("--title", help="concise panel name; defaults to the chart type")
    interface = commands.add_parser("add-interface")
    interface.add_argument("slug")
    interface.add_argument("--title", required=True)
    interface.add_argument("--columns", type=Path, required=True)
    method = commands.add_parser("scaffold-method")
    method.add_argument("entry_id")
    method.add_argument("--title", required=True)
    method.add_argument("--license", required=True)
    source = method.add_mutually_exclusive_group(required=True)
    source.add_argument("--from-entry")
    source.add_argument("--from-path", type=Path)
    source.add_argument("--written", action="store_true")
    method.add_argument("--url")
    method.add_argument("--commit")
    attach = commands.add_parser("attach-template")
    attach.add_argument("entry_id")
    attach.add_argument("template_id")
    attach.add_argument("--panels", required=True)
    rendering = commands.add_parser("render")
    rendering.add_argument("entry_id")
    rendering.add_argument("--data", type=Path, required=True)
    rendering.add_argument("--out", type=Path, required=True)
    rendering.add_argument("--style", type=Path)
    rendering.add_argument("--bindings", type=Path,
                           help="显式映射外部文件/列；不提供时读取 <接口>.csv")
    layout_rendering = commands.add_parser("render-layout")
    layout_rendering.add_argument("entry_id")
    layout_rendering.add_argument("--data", type=Path, required=True)
    layout_rendering.add_argument("--out", type=Path, required=True)
    layout_rendering.add_argument("--style", type=Path)
    suggesting = commands.add_parser("suggest")
    suggesting.add_argument("--chart-type", nargs="+", action="extend", default=[])
    suggesting.add_argument("--columns")
    suggesting.add_argument("--q", default="")
    suggesting.add_argument("--limit", type=int, default=3)
    method_suggesting = commands.add_parser("suggest-methods")
    method_suggesting.add_argument("--q", default="")
    method_suggesting.add_argument("--columns")
    method_suggesting.add_argument("--limit", type=int, default=3)
    discovery = commands.add_parser("discover-methods",
                                    help="只读机会清单：规范 analysis 笔记及未验证分支；不放宽可执行门槛")
    discovery.add_argument("--q", default="")
    discovery.add_argument("--limit", type=int, default=20)
    pipeline = commands.add_parser("suggest-pipeline")
    pipeline.add_argument("--figure")
    pipeline.add_argument("--q", default="")
    sheet = commands.add_parser("contact-sheet")
    sheet.add_argument("entry_ids", nargs="+")
    sheet.add_argument("--out", type=Path, required=True)
    usage = commands.add_parser("record-use")
    usage.add_argument("entry_id")
    usage.add_argument("--project", required=True)
    usage.add_argument("--title", required=True)
    usage.add_argument("--output", required=True)
    usage.add_argument("--note")
    usage.add_argument("--method")
    m_usage = commands.add_parser(
        "record-method-use",
        help="登记一次已核实当前的分析型方法使用（不配图）；需 --project-root + --run 证据")
    m_usage.add_argument("--method", required=True)
    m_usage.add_argument("--project", required=True)
    m_usage.add_argument("--title", required=True)
    m_usage.add_argument("--project-root", type=Path, required=True,
                         help="含 wiki-use/_project 的课题根；run 证据由此核查")
    m_usage.add_argument("--run", required=True, help="已完成的 run id")
    m_usage.add_argument("--note")
    project = commands.add_parser(
        "project",
        help="课题本地状态：init/status/check/impact/record-run/add-*/evaluate；只写课题目录，不写 Wiki")
    project_sub = project.add_subparsers(dest="project_command", required=True)

    def with_root(sub):
        sub.add_argument("--root", type=Path, required=True, help="课题目录")
        return sub

    def kv(sub, name, help_text):
        sub.add_argument(name, action="append", default=[], metavar="KEY=VALUE",
                         help=help_text)

    p_init = with_root(project_sub.add_parser("init", help="初始化课题状态（写）"))
    p_init.add_argument("--id", help="稳定课题标识；默认取目录名安全化")
    p_init.add_argument("--title", help="课题标题")
    p_init.add_argument("--data-root", action="append", default=[],
                        help="登记的只读外部数据根，可重复")

    with_root(project_sub.add_parser("status", help="课题状态摘要（只读）"))
    with_root(project_sub.add_parser("check", help="结构/路径/证据核查（只读；未知前提保持 unknown）"))

    p_impact = with_root(project_sub.add_parser("impact", help="依赖影响分析（默认只读）"))
    p_impact.add_argument("--changed", action="append", required=True,
                          help="变化的引用：kind:id、file:path 或 external:path，可重复")
    p_impact.add_argument("--apply", action="store_true",
                          help="把影响结果写回产物新鲜度（写）")
    p_impact.add_argument("--reason", default="", help="--apply 时记录的原因")

    p_run = with_root(project_sub.add_parser("record-run", help="登记已实际执行的运行（写；不执行命令）"))
    p_run.add_argument("--run", required=True, help="run id")
    p_run.add_argument("--task", required=True, help="task id（须先 add-task）")
    p_run.add_argument("--status", required=True,
                       choices=("running", "completed", "failed", "blocked", "skipped"))
    p_run.add_argument("--command", dest="run_command", default="",
                       help="实际执行过的命令文本（completed 必填）")
    p_run.add_argument("--in", dest="inputs", action="append", default=None,
                       help="输入引用，可重复；缺省沿用任务已声明输入，且不得漏掉声明依赖")
    p_run.add_argument("--code", dest="code", action="append", default=[],
                       help="实际使用的代码/资源引用（file:/external:/object: 等），可重复；"
                            "记入指纹与去重身份，无任何代码来源登记时相同命令不会被静默复用")
    p_run.add_argument("--out", dest="outputs", action="append", default=[],
                       help="输出文件（课题相对路径），可重复；completed 至少一个且须存在")
    p_run.add_argument("--check", dest="checks", action="append", default=[],
                       help="实际检查项，可重复；completed 至少一个")
    kv(p_run, "--param", "运行参数 k=v，可重复")
    kv(p_run, "--env", "环境记录 k=v，可重复")
    p_run.add_argument("--note", help="备注")

    p_root = with_root(project_sub.add_parser("add-data-root", help="登记只读外部数据根（写）"))
    p_root.add_argument("--path", required=True)
    p_root.add_argument("--id", help="数据根 id")

    p_ent = with_root(project_sub.add_parser("add-entity", help="登记实体（写）"))
    p_ent.add_argument("--id", required=True)
    p_ent.add_argument("--kind", required=True, help="实体类型，如 sample/subject/gene")
    p_ent.add_argument("--count", type=int, help="数量（已知时）")
    p_ent.add_argument("--identity", help="身份/版本说明")
    kv(p_ent, "--prop", "属性 k=v，可重复")
    p_ent.add_argument("--basis", default="author_stated",
                       choices=("verified", "author_stated", "unknown"))
    p_ent.add_argument("--note")

    p_obj = with_root(project_sub.add_parser("add-object", help="登记原生对象/文件（写）"))
    p_obj.add_argument("--id", required=True)
    p_obj.add_argument("--kind", required=True, help="对象类型，自由命名")
    location = p_obj.add_mutually_exclusive_group(required=True)
    location.add_argument("--path", help="课题相对路径")
    location.add_argument("--external", help="已登记数据根内的绝对路径")
    p_obj.add_argument("--native-type", help="原生类型说明（如 SeuratObject/AnnData/网络对象）")
    p_obj.add_argument("--inspected", action="store_true",
                       help="声明对象已被适配器实际解析（需 --adapter）")
    p_obj.add_argument("--adapter", help="实际解析该对象的适配器名称")
    p_obj.add_argument("--entity", dest="entities", action="append", default=[],
                       help="关联实体引用，可重复")
    kv(p_obj, "--prop", "属性 k=v，可重复")
    p_obj.add_argument("--basis", default="author_stated",
                       choices=("verified", "author_stated", "unknown"),
                       help="verified 需要真实文件以记录指纹")
    p_obj.add_argument("--note")

    p_obs = with_root(project_sub.add_parser("add-observation", help="登记观察/前提声明（写）"))
    p_obs.add_argument("--id", required=True)
    p_obs.add_argument("--claim", required=True)
    p_obs.add_argument("--about", help="相关记录引用")
    p_obs.add_argument("--value", default="unknown", choices=("true", "false", "unknown"))
    p_obs.add_argument("--basis", default="unknown",
                       choices=("verified", "author_stated", "unknown"))
    p_obs.add_argument("--evidence", help="证据文件（课题相对路径）")
    p_obs.add_argument("--scope", help="证据实际支持的范围")
    p_obs.add_argument("--stage", help="声明归属的工作阶段（与 profile 阶段词对齐；非完成状态）")
    p_obs.add_argument("--note")

    p_route = with_root(project_sub.add_parser("add-route", help="登记研究主线（写）"))
    p_route.add_argument("--id", required=True)
    p_route.add_argument("--question", required=True)
    p_route.add_argument("--hypothesis")
    p_route.add_argument("--evidence", action="append", default=[], help="证据引用，可重复")
    p_route.add_argument("--gap", action="append", default=[], help="已知缺口，可重复")
    p_route.add_argument("--decision", default="pending",
                       choices=("pending", "chosen", "rejected"))
    p_route.add_argument("--basis", default="unknown",
                       choices=("verified", "author_stated", "unknown"))
    p_route.add_argument("--note")

    p_task = with_root(project_sub.add_parser("add-task", help="登记候选/执行任务（写）"))
    p_task.add_argument("--id", required=True)
    p_task.add_argument("--family", dest="family_id", help="规范方法页 id")
    p_task.add_argument("--implementation", dest="implementation_id", help="实现分支 id")
    p_task.add_argument("--purpose")
    p_task.add_argument("--role", default="exploratory", choices=("main", "exploratory", "support"))
    p_task.add_argument("--status", default="planned",
                        choices=("planned", "running", "completed", "failed", "blocked", "skipped"))
    p_task.add_argument("--in", dest="inputs", action="append", default=[],
                        help="输入引用，可重复")
    kv(p_task, "--param", "任务参数 k=v，可重复")
    p_task.add_argument("--authorization", help="authorization 引用")
    p_task.add_argument("--stage", help="声明归属的工作阶段（与 profile 阶段词对齐；非完成状态）")
    p_task.add_argument("--note")

    p_dec = with_root(project_sub.add_parser("add-decision", help="登记作者决定（写）"))
    p_dec.add_argument("--id", required=True)
    p_dec.add_argument("--kind", required=True,
                       choices=("route", "scope", "authorization", "budget", "other"))
    p_dec.add_argument("--text", required=True)
    p_dec.add_argument("--route", help="相关 route 引用")
    p_dec.add_argument("--supersedes", help="被取代的 decision 引用")
    p_dec.add_argument("--scope")
    p_dec.add_argument("--note")

    p_auth = with_root(project_sub.add_parser("add-authorization", help="登记执行约定/预算（写）"))
    p_auth.add_argument("--id", required=True)
    p_auth.add_argument("--scope", required=True)
    kv(p_auth, "--budget", "预算项 k=v，可重复")
    p_auth.add_argument("--decided-by", default="author")
    p_auth.add_argument("--note")

    p_prof = with_root(project_sub.add_parser("register-profile", help="登记所用领域配置版本（写）"))
    p_prof.add_argument("--id", required=True)
    p_prof.add_argument("--version", type=int, required=True)

    p_eval = with_root(project_sub.add_parser(
        "evaluate", help="领域前提评估（只读；未注册 profile 也可点名评估）"))
    p_eval.add_argument("--profile", help="领域 profile id；缺省时评估已登记的全部")
    p_eval.add_argument("--subject",
                        help="评估主体引用（object:/entity:/task:id）；限定前提在一致上下文中成立")

    with_root(project_sub.add_parser(
        "relocate", help="把复制/移动后的课题状态显式重定位到当前目录（写）"))

    p_rec = with_root(project_sub.add_parser(
        "recover", help="中断恢复检查（默认只读报告；修复动作需显式开关，"
                        "证据隔离至 _quarantine/ 不删除）"))
    p_rec.add_argument("--release-lock", action="store_true",
                       help="仅释放经只读探测证实无主且复核同一的 project.lock；"
                            "活动/未知/被替换锁一律拒绝")
    p_rec.add_argument("--clean-staging", action="store_true",
                       help="把未提交的 .tmp 暂存文件移入 _quarantine/staging/（不删除）")
    p_rec.add_argument("--clean-orphans", action="store_true",
                       help="把未被当前已提交状态引用的孤儿收据目录移入 "
                            "_quarantine/orphans/（核查范围=当前状态，不删除）")

    p_les = with_root(project_sub.add_parser(
        "add-lesson", help="登记有据可查的经验草稿（课题内提案，不进正式推荐）"))
    p_les.add_argument("--id", required=True)
    p_les.add_argument("--claim", required=True, help="经验命题文本")
    p_les.add_argument("--evidence", action="append", required=True,
                       help="证据引用 kind:id（run/observation/decision/artifact 等），可重复，至少一条")
    p_les.add_argument("--applies-to", required=True,
                       help="适用范围/失效边界（去重键的一部分；无界命题不收）")
    p_les.add_argument("--link", action="append", default=[],
                       help="关联已有知识：状态引用 kind:id 或方法页 id，可重复")
    p_les.add_argument("--basis", default="author_stated",
                       choices=("verified", "author_stated", "unknown"))
    p_les.add_argument("--note")

    p_rev = with_root(project_sub.add_parser(
        "lesson-review", help="对经验草稿作课题内评审处置（非正式 Wiki 回写）"))
    p_rev.add_argument("--id", required=True)
    p_rev.add_argument("--state", required=True,
                       choices=("pending", "deferred", "rejected", "accepted"))
    p_rev.add_argument("--by", required=True,
                       help="评审署名；测试评审须标明隔离夹具身份")
    p_rev.add_argument("--decision",
                       help="decision:<id>；--state accepted 必填——只有已登记的作者决策能把草稿推向 accepted")
    p_rev.add_argument("--note")
    return result


def _profile_spec_hash(profile_id: str) -> str | None:
    """Content hash of the spec about to be used, when the profile exists."""
    from .domain_profiles import load_profiles, profile_fingerprint
    spec = load_profiles().get(profile_id)
    return profile_fingerprint(spec) if spec else None


def _kv_pairs(values, what: str) -> dict:
    pairs = {}
    for item in values or []:
        key, sep, value = str(item).partition('=')
        if not sep or not key.strip():
            raise WikiError(f'{what} 须为 KEY=VALUE: {item}')
        pairs[key.strip()] = value
    return pairs


def _project_dispatch(args, config) -> None:
    from . import project_state as ps

    root = args.root
    verb = args.project_command
    if verb == 'init':
        state = ps.init_project(root, project_id=args.id, title=args.title,
                                data_roots=args.data_root or None)
        print(json.dumps({'project_id': state['project_id'], 'revision': state['revision'],
                          'state_dir': str(ps.state_dir(Path(root).resolve()))},
                         ensure_ascii=False, indent=2))
        return
    if verb == 'status':
        print(json.dumps(ps.project_status(root), ensure_ascii=False, indent=2))
        return
    if verb == 'check':
        print(json.dumps(ps.check_project(root, config), ensure_ascii=False, indent=2))
        return
    if verb == 'impact':
        report = ps.impact_analysis(root, args.changed)
        if args.apply:
            state = ps.mark_stale(root, report, reason=args.reason)
            report['applied'] = {'revision': state['revision'],
                                 'note': '受影响产物标 stale/unknown；未重算未删除'}
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    if verb == 'record-run':
        print(json.dumps(ps.record_run(
            root, args.run, args.task, status=args.status, command=args.run_command,
            inputs=args.inputs, outputs=args.outputs, checks=args.checks,
            code=args.code,
            params=_kv_pairs(args.param, '--param') or None,
            environment=_kv_pairs(args.env, '--env'),
            note=args.note), ensure_ascii=False, indent=2))
        return
    if verb == 'evaluate':
        from .domain_profiles import evaluate_profile, profile_ids
        state = ps.load_project(root)
        if args.profile:
            targets = [args.profile]
        else:
            targets = [item['id'] for item in state['profile_refs']] or profile_ids()
        print(json.dumps({pid: evaluate_profile(state, pid, subject=args.subject)
                          for pid in targets},
                         ensure_ascii=False, indent=2))
        return
    if verb == 'relocate':
        state = ps.relocate_project(root)
        print(json.dumps({'project_id': state['project_id'],
                          'project_root': state['project_root'],
                          'revision': state['revision']}, ensure_ascii=False, indent=2))
        return
    if verb == 'recover':
        print(json.dumps(ps.recover_project(
            root, release_lock=args.release_lock,
            clean_staging=args.clean_staging,
            clean_orphans=args.clean_orphans), ensure_ascii=False, indent=2))
        return
    if verb == 'add-lesson':
        print(json.dumps(ps.add_lesson(
            root, args.id, args.claim, evidence=args.evidence,
            applies_to=args.applies_to, links=args.link,
            basis=args.basis, note=args.note), ensure_ascii=False, indent=2))
        return
    if verb == 'lesson-review':
        state = ps.review_lesson(root, args.id, args.state, reviewed_by=args.by,
                                 note=args.note, decision=args.decision)
        print(json.dumps({'revision': state['revision'],
                          'event': state['events'][-1]},
                         ensure_ascii=False, indent=2))
        return
    mutate = {
        'add-data-root': lambda: ps.add_data_root(root, args.path, root_id=args.id),
        'add-entity': lambda: ps.add_entity(
            root, args.id, args.kind, count=args.count, identity=args.identity,
            properties=_kv_pairs(args.prop, '--prop'), basis=args.basis, note=args.note),
        'add-object': lambda: ps.add_object(
            root, args.id, args.kind, path=args.path, external=args.external,
            native_type=args.native_type, entities=args.entities, inspected=args.inspected,
            adapter=args.adapter,
            properties=_kv_pairs(args.prop, '--prop'), basis=args.basis, note=args.note),
        'add-observation': lambda: ps.add_observation(
            root, args.id, args.claim, about=args.about, value=args.value,
            basis=args.basis, evidence=args.evidence, scope=args.scope,
            stage=args.stage, note=args.note),
        'add-route': lambda: ps.add_route(
            root, args.id, args.question, hypothesis=args.hypothesis,
            evidence_refs=args.evidence, gaps=args.gap, decision=args.decision,
            basis=args.basis, note=args.note),
        'add-task': lambda: ps.add_task(
            root, args.id, family_id=args.family_id, implementation_id=args.implementation_id,
            purpose=args.purpose, role=args.role, status=args.status, inputs=args.inputs,
            params=_kv_pairs(args.param, '--param'), authorization=args.authorization,
            stage=args.stage, note=args.note),
        'add-decision': lambda: ps.add_decision(
            root, args.id, args.kind, args.text, scope=args.scope, route=args.route,
            supersedes=args.supersedes, note=args.note),
        'add-authorization': lambda: ps.add_authorization(
            root, args.id, args.scope, budget=_kv_pairs(args.budget, '--budget'),
            decided_by=args.decided_by, note=args.note),
        'register-profile': lambda: ps.register_profile(
            root, args.id, args.version, spec_sha256=_profile_spec_hash(args.id)),
    }
    state = mutate[verb]()
    print(json.dumps({'revision': state['revision'], 'event': state['events'][-1]},
                     ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        # 课题状态命令只依赖课题目录；check 有配置时才核查 Wiki 引用。
        config = (load_config(args.config)
                  if args.command != 'project' or args.config.is_file() else None)
        if args.command == "project":
            _project_dispatch(args, config)
            return 0
        elif args.command == "discover-methods":
            from .discovery import discover_methods
            print(json.dumps(discover_methods(config, args.q, args.limit),
                             ensure_ascii=False, indent=2))
        if args.command == "init":
            init(config)
        elif args.command == "ingest-figure":
            ingest_figure(config, args.entry_id)
        elif args.command == "save":
            save(config, args.message)
        elif args.command == "serve":
            serve(config, args.no_browser)
        elif args.command == "pending":
            if args.json:
                from .workflow import workflow_snapshot
                print(json.dumps([{'path': path, **item} for path, item in workflow_snapshot(config).items()
                                  if item['queue'] == 'agent'], ensure_ascii=False, indent=2))
            else:
                for entry_id in pending(config):
                    print(entry_id)
        elif args.command == 'check-entry':
            from .acceptance import acceptance_stale, entry_errors, record_acceptance
            from .pages import read_page, visual_path
            page = visual_path(config.wiki_root, args.entry_id)
            meta, _ = read_page(page)
            content_errors = entry_errors(config, page)
            stale = meta.get('status') == 'ready' and acceptance_stale(page)
            runtime_errors = []
            runtime_warnings = []
            if meta.get('type') in ('method', 'template'):
                from .runtime_contract import lint_manifest, read_manifest
                kind = 'method' if meta['type'] == 'method' else 'template'
                _, manifest_issues = read_manifest(page.with_suffix(''), meta['id'], kind)
                runtime_errors = manifest_issues
                if not manifest_issues:
                    runtime_warnings = lint_manifest(page.with_suffix(''), meta['id'], kind)
            errors = (content_errors + runtime_errors
                      + (['验收记录与当前内容不同，请核对后 --record'] if stale else []))
            from .method_taxonomy import missing_purpose
            warnings = (['purposes 缺失：请按分析用途分类；不影响已有状态，但不是完整分类']
                        if missing_purpose(meta) else []) + runtime_warnings
            report = {'page': page.relative_to(config.wiki_root).as_posix(), 'passed': not errors,
                      'errors': errors, 'warnings': warnings,
                      'scope': '结构和当前回放检查，不代替科学审查或作者确认'}
            if args.record and not content_errors and not runtime_errors:
                report['record'] = record_acceptance(config, page)
                report['passed'] = True
                report['errors'] = []
                save(config, f'acceptance check {args.entry_id}')
            print(json.dumps(report, ensure_ascii=False, indent=2))
            if errors and not (args.record and not content_errors and not runtime_errors):
                return 1
        elif args.command == "scaffold-template":
            scaffold_template(config, args.entry_id, args.chart_type,
                              args.panels.split(","), title=args.title)
        elif args.command == "add-interface":
            add_interface(config, args.slug, args.title, args.columns)
        elif args.command == "scaffold-method":
            scaffold_method(config, args.entry_id, args.title, args.license,
                            args.from_entry, args.from_path, args.url, args.commit, args.written)
        elif args.command == "attach-template":
            attach_template(config, args.entry_id, args.template_id, args.panels.split(","))
        elif args.command == "render":
            render(config, args.entry_id, args.data, args.out, args.style, args.bindings)
        elif args.command == "verify-template":
            verify_template(config, args.entry_id)
        elif args.command == "verify-layout":
            verify_layout(config, args.entry_id)
        elif args.command == "render-layout":
            render_layout(config, args.entry_id, args.data, args.out, args.style)
        elif args.command == "mark-ready":
            mark_ready(config, args.entry_id)
        elif args.command == "suggest":
            print(json.dumps(suggest(config, args.chart_type, args.columns,
                                     args.q, args.limit), ensure_ascii=False, indent=2))
        elif args.command == "suggest-pipeline":
            print(json.dumps(suggest_pipeline(config, args.figure, args.q),
                             ensure_ascii=False, indent=2))
        elif args.command == "suggest-methods":
            print(json.dumps(suggest_methods(config, args.q, args.columns, args.limit),
                             ensure_ascii=False, indent=2))
        elif args.command == "contact-sheet":
            print(contact_sheet(config, args.entry_ids, args.out))
        elif args.command == "record-use":
            record_use(config, args.entry_id, args.project, args.title, args.output, args.note,
                       args.method)
        elif args.command == "record-method-use":
            record_method_use(config, args.method, args.project, args.title,
                              project_root=args.project_root, run_id=args.run,
                              note=args.note)
        elif args.command == "lint":
            diagnostics = lint(config)
            for line in diagnostics:
                print(line)
            if any(line.startswith("ERROR ") for line in diagnostics):
                return 1
            print("OK")
    except WikiError as error:
        print(error, file=sys.stderr)
        return 1
    return 0

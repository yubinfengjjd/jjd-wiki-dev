import argparse
import json
import sys
from pathlib import Path

from .config import load_config, prepare_env
from .contact_sheet import contact_sheet
from .errors import WikiError
from .ingest import ingest_figure
from .interfaces import add_interface
from .methods import scaffold_method
from .lint import lint
from .layouts import render_layout, verify_layout
from .read_cache import read_session
from .store import init, save
from .suggest import format_next_steps, suggest, suggest_methods, suggest_next_steps, suggest_pipeline
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
    result.add_argument("--wiki-root", type=Path,
                        help="覆盖配置中的 wiki_root；优先于环境变量 RWIKI_WIKI_ROOT")
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    ingest = commands.add_parser("ingest-figure")
    selection = ingest.add_mutually_exclusive_group(required=True)
    selection.add_argument("entry_id", nargs="?")
    selection.add_argument("--all", action="store_true")
    commands.add_parser("save").add_argument("message")
    checkout = commands.add_parser('checkout', help='切换轻量或完整 Git 检出')
    checkout.add_argument('--profile', required=True, choices=('light', 'full'))
    assets = commands.add_parser('assets', help='显式获取条目资产，不安装依赖')
    assets_sub = assets.add_subparsers(dest='asset_command', required=True)
    assets_sub.add_parser('fetch').add_argument('entry_id')
    commands.add_parser("lint").add_argument(
        "--ci", action="store_true", help="被 git 忽略而缺失的引用报告为 LOCAL-ONLY，不计为错误")
    github = commands.add_parser("gh", help="本地推送前防泄漏与受保护字节核查")
    gh_sub = github.add_subparsers(dest="gh_command", required=True)
    guard = gh_sub.add_parser("guard", help="推送前防泄漏检查（纯本地，不需要 gh）")
    guard.add_argument("--range", dest="rev_range", help="检查的提交范围，如 origin/main..HEAD")
    guard.add_argument("--pre-push", nargs=2, metavar=("REMOTE", "URL"),
                       help="pre-push hook 入口：从标准输入读取待推送的 ref")
    guard.add_argument("--sync-ignore", action="store_true", help="重写知识库 .gitignore 的 GPL 托管块")
    gh_sub.add_parser("protect-baseline", help="生成或核验作者块字节基准（纯本地，不需要 gh）").add_argument(
        "--check", action="store_true", help="只核验，不写基准")
    # ---- v2（2026-10-27）：检索与调用、来源、配方
    finding = commands.add_parser("find", help="全文检索知识页面与 L0 目录；源码搜索需 --scope source")
    finding.add_argument("query", nargs="+")
    finding.add_argument("--kind", choices=("scenario", "template", "recipe", "method", "item", "source", "interface", "chart-type", "project", "layout"))
    finding.add_argument("--scope", choices=("knowledge", "source"), default="knowledge")
    finding.add_argument("--level", choices=("L0", "L1", "L2"))
    finding.add_argument("--runnable", action="store_true", help="只列可用模板与原样运行通过的配方")
    finding.add_argument("--limit", type=int, default=8)
    finding.add_argument("--json", action="store_true")
    showing = commands.add_parser("show", help="一个条目的用途、输入、许可、最近运行与下一步")
    showing.add_argument("entry_id", help="页面 id，或 L0 目录项 <来源>:<条目>")
    showing.add_argument("--json", action="store_true")
    using = commands.add_parser("use", help="把条目代码复制进课题 wiki-use/<名>/（不改 Wiki）")
    using.add_argument("entry_id")
    using.add_argument("--project", type=Path, required=True)
    using.add_argument("--name")
    source = commands.add_parser("source", help="来源登记：add / fetch / scan")
    source_sub = source.add_subparsers(dest="source_command", required=True)
    s_add = source_sub.add_parser("add")
    s_add.add_argument("source_id")
    s_add.add_argument("--title", required=True)
    s_add.add_argument("--url", required=True)
    s_add.add_argument("--license", required=True, help="SPDX 标识，如 CC-BY-NC-SA-4.0、MIT、GPL-3.0")
    s_add.add_argument("--adapter", required=True)
    s_add.add_argument("--trusted", action="store_true", help="白名单：按需获取不再逐次询问")
    s_add.add_argument("--cite", action="append", default=[])
    s_add.add_argument("--notice", default="", help="页面顶部的许可提示（缺省按许可证生成）")
    s_fetch = source_sub.add_parser("fetch")
    s_fetch.add_argument("source_id")
    s_fetch.add_argument("items", nargs="*")
    s_fetch.add_argument("--update", action="store_true", help="快照 commit 与来源页记录不同时，确认更新记录")
    source_sub.add_parser("scan").add_argument("source_id")
    promoting = commands.add_parser("promote", help="L0 → L1：上游条目原字节建为配方页（draft）")
    promoting.add_argument("source_id")
    promoting.add_argument("items", nargs="+")
    promoting.add_argument("--curation", type=Path,
                           help="JSON：{条目: {title, chart_types, tags}}，作者/agent 整理的中文名与分类")
    running = commands.add_parser("run", help="原样运行配方（Wiki 专用环境）或 use 生成的课题副本")
    running.add_argument("recipe_ids", nargs="*")
    running.add_argument("--dir", type=Path, help="use 生成的副本目录（收据写在副本 rwiki-runs/）")
    running.add_argument("--timeout", type=int, default=1200)
    running.add_argument("--jobs", type=int, default=1)
    restoring = commands.add_parser("restore", help="从来源快照按记录的 commit 取回配方原字节（source/ 不进 Git）")
    restoring.add_argument("recipe_ids", nargs="+")
    depending = commands.add_parser("deps", help="依赖检查；--install 只装进 config.r_libs[0]（作者按批次批准后）")
    depending.add_argument("ids", nargs="+", help="配方 id 或 <来源>:<条目>")
    depending.add_argument("--install", action="store_true")
    depending.add_argument("--github", action="store_true", help="同时安装声明的 GitHub 包")
    commands.add_parser("pending").add_argument('--json', action='store_true')
    checking = commands.add_parser('check-entry')
    checking.add_argument('entry_id')
    checking.add_argument('--record', action='store_true')
    commands.add_parser("serve").add_argument("--no-browser", action="store_true")
    for name in ("verify-template", "verify-layout"):
        commands.add_parser(name).add_argument("entry_id")
    commands.add_parser("mark-ready", help="作者确认；多个 id 时先全部核对，任一不通过则全部不改").add_argument(
        "entry_ids", nargs="+")
    scaffold = commands.add_parser("scaffold-template")
    scaffold.add_argument("entry_id", help="版式 id；--from-recipe 时为配方 id；--native 时为新模板 id")
    scaffold.add_argument("--chart-type", required=True)
    scaffold.add_argument("--panels", help="版式 panel 字母（从版式拆出时必填）")
    scaffold.add_argument("--from-recipe", action="store_true", help="v2：从 L1 配方开 L2 模板")
    scaffold.add_argument("--native", action="store_true", help="直接新建规范短 slug 原生模板（绑定 --primary-method）")
    scaffold.add_argument("--id", dest="template_id", help="配合 --from-recipe 使用，指定语义短 slug（替代旧的 <recipe>--<chart>）")
    scaffold.add_argument("--primary-method", help="关联的主分析方法 id（method_kind=analysis）")
    scaffold.add_argument("--sources", nargs="*", help="配合 --native 使用，来源页面列表")
    scaffold.add_argument("--language", choices=("python", "r"))
    scaffold.add_argument("--title", help="简明中文内容名")
    scaffold.add_argument("--dedup-note", default="", help="高相似既有条目时填写的差异保留说明")
    scaffold.add_argument("--force", action="store_true", help="强制跳过查重确认门槛")
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
    method.add_argument("--dedup-note", default="", help="高相似既有条目时填写的差异保留说明")
    method.add_argument("--force", action="store_true", help="强制跳过查重确认门槛")
    dedup_cmd = commands.add_parser("check-dup", help="入库前多维查重（方法域+图型+接口+标题语义）")
    dedup_cmd.add_argument("--kind", required=True, choices=("template", "method", "recipe"))
    dedup_cmd.add_argument("--id", dest="entry_id", default="")
    dedup_cmd.add_argument("--title", default="")
    dedup_cmd.add_argument("--primary-method", default="")
    dedup_cmd.add_argument("--methods", nargs="*", default=[])
    dedup_cmd.add_argument("--chart-type", dest="chart_types", nargs="*", default=[])
    dedup_cmd.add_argument("--interface", dest="interfaces", nargs="*", default=[])
    dedup_cmd.add_argument("--summary", default="")
    dedup_cmd.add_argument("--keyword", dest="keywords", nargs="*", default=[])
    dedup_cmd.add_argument("--journal-style", default="", help="目标期刊画风标识（用于区分多风格变体）")
    dedup_cmd.add_argument("--json", action="store_true")
    map_cmd = commands.add_parser("map-method", help="绑定模板 primary_method、更新 method-map.json 或体检方法域覆盖")
    map_cmd.add_argument("--template", dest="template_id")
    map_cmd.add_argument("--recipe", dest="recipe_id")
    map_cmd.add_argument("--primary-method")
    map_cmd.add_argument("--methods", nargs="*", default=[])
    map_cmd.add_argument("--unmapped", action="store_true")
    map_cmd.add_argument("--note", default="")
    map_cmd.add_argument("--audit", action="store_true", help="只读输出方法域整理全库体检报告")
    map_cmd.add_argument("--json", action="store_true")
    audit_cmd = commands.add_parser("curate-audit", help="只读审计方法-可视化覆盖率、断链、命名规范与重复簇")
    audit_cmd.add_argument("--json", action="store_true")
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
    next_cmd = commands.add_parser("next", help="查看当前方法/模板/接口的下一步生信分析导航")
    next_cmd.add_argument("node_id")
    next_cmd.add_argument("--q", default="")
    next_cmd.add_argument("--json", action="store_true")
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
        help="课题步进卡管理：list / show / add-step（读写 wiki/projects/<id>.md）",
    )
    project_sub = project.add_subparsers(dest="project_command", required=True)
    p_list = project_sub.add_parser("list", help="列出所有课题步进卡")
    p_list.add_argument("--json", action="store_true")

    p_show = project_sub.add_parser("show", help="查看单个课题步进卡")
    p_show.add_argument("project_id")
    p_show.add_argument("--json", action="store_true")

    p_step = project_sub.add_parser("add-step", help="追加一条 3 行课题步进记录")
    p_step.add_argument("project_id")
    p_step.add_argument("--title", required=True, help="步骤标题")
    p_step.add_argument("--templates", default="", help="所用分析/可视化模版")
    p_step.add_argument("--observation", default="", help="观察结果与排坑")
    p_step.add_argument("--next", dest="next_branch", default="", help="触发下一步分支")
    p_step.add_argument("--project-title", help="新建课题卡时的标题")
    p_step.add_argument("--json", action="store_true")

    paper = commands.add_parser("paper", help="文献复刻流水线：trace / fetch / parse / plan / publish / status")
    paper_sub = paper.add_subparsers(dest="paper_command", required=True)
    pp_trace = paper_sub.add_parser("trace", help="从二手推文/DOI/PMID/标题溯源原文献并初始化工作区")
    pp_trace.add_argument("--id", dest="paper_id", default="")
    pp_trace.add_argument("--query", default="")
    pp_trace.add_argument("--doi", default="")
    pp_trace.add_argument("--pmid", default="")
    pp_trace.add_argument("--pmcid", default="")
    pp_trace.add_argument("--url", dest="source_url", default="")
    pp_trace.add_argument("--post-file", type=Path)
    pp_trace.add_argument("--repo", dest="repo_url", default="")
    pp_trace.add_argument("--offline", action="store_true")
    pp_trace.add_argument("--json", action="store_true")

    pp_fetch = paper_sub.add_parser("fetch", help="下载 OA 全文 PDF（不绕过付费墙）或导入本地 PDF 与附加材料，并克隆开源代码仓")
    pp_fetch.add_argument("paper_id")
    pp_fetch.add_argument("--pdf", type=Path)
    pp_fetch.add_argument("--supp", action="append", type=Path, default=[], help="附加材料文件或目录（可重复传入）")
    pp_fetch.add_argument("--repo", dest="repo_url", default="")
    pp_fetch.add_argument("--no-clone", action="store_true")
    pp_fetch.add_argument("--json", action="store_true")

    pp_parse = paper_sub.add_parser("parse", help="解析 PDF Methods 与附加材料、剔除湿实验、提取图注与页面截图")
    pp_parse.add_argument("paper_id")
    pp_parse.add_argument("--no-render", action="store_true")
    pp_parse.add_argument("--max-render-pages", type=int, default=80)
    pp_parse.add_argument("--json", action="store_true")

    pp_plan = paper_sub.add_parser("plan", help="生成小规模数据降维计划、正文-附件映射、查重建议与全图复刻任务单")
    pp_plan.add_argument("paper_id")
    pp_plan.add_argument("--max-cells", type=int, default=2500)
    pp_plan.add_argument("--max-samples", type=int, default=120)
    pp_plan.add_argument("--include-supp", action="store_true", help="兼容参数；现默认已纳管附图")
    pp_plan.add_argument("--main-only", action="store_true", help="仅规划 Main Figures（排除附图）")
    pp_plan.add_argument("--json", action="store_true")

    pp_pub = paper_sub.add_parser("publish", help="将复刻串联流程及源码快照发布为 Wiki workflow 方法页")
    pp_pub.add_argument("paper_id")
    pp_pub.add_argument("--id", dest="workflow_id", required=True)
    pp_pub.add_argument("--title", required=True)
    pp_pub.add_argument("--tags", nargs="*", default=[])
    pp_pub.add_argument("--data-domains", nargs="*", default=[])
    pp_pub.add_argument("--derived-methods", nargs="*", default=[])
    pp_pub.add_argument("--derived-templates", nargs="*", default=[])
    pp_pub.add_argument("--scale-down-note", default="")
    pp_pub.add_argument("--dedup-note", default="")
    pp_pub.add_argument("--no-sync-code", action="store_true")
    pp_pub.add_argument("--force", action="store_true")
    pp_pub.add_argument("--json", action="store_true")

    pp_stat = paper_sub.add_parser("status", help="查看文献工作区进度")
    pp_stat.add_argument("paper_id", nargs="?", default="")
    pp_stat.add_argument("--json", action="store_true")

    clean_cmd = commands.add_parser("clean", help="盘点并清理过期临时目录、UI 冒烟目录与已退役探针残留")
    clean_cmd.add_argument("--apply", action="store_true", help="实际执行清理（默认仅 dry-run 预览）")
    clean_cmd.add_argument("--include-backups", action="store_true", help="一并清理 skill-backup/audit/maintenance 历史快照")
    clean_cmd.add_argument("--include-caches", action="store_true", help="一并清理仓库 .pytest_cache 与根目录 Rplots.pdf")
    clean_cmd.add_argument("--json", action="store_true")
    return result


def _project_dispatch(args, config) -> None:
    from .project_tracker import add_project_step, get_project, list_projects

    verb = args.project_command
    if verb == "list":
        items = list_projects(config)
        if args.json:
            _print({"projects": items})
        else:
            for item in items:
                print(f"{item['id']}  {item['title']}  ({len(item['steps'])} steps)")
        return
    if verb == "show":
        item = get_project(config, args.project_id)
        if args.json:
            _print(item)
        else:
            print(item["body"])
        return
    if verb == "add-step":
        updated = add_project_step(
            config,
            args.project_id,
            title=args.title,
            templates=args.templates,
            observation=args.observation,
            next_branch=args.next_branch,
            project_title=args.project_title,
            commit=True,
        )
        if args.json:
            _print(updated)
        else:
            last = updated["steps"][-1] if updated["steps"] else {}
            print(f"{updated['id']}: Step {last.get('step', '?')} {last.get('title', '')}")


def _gh_dispatch(args, config) -> int:
    from . import push_guard
    from .store import git

    verb = args.gh_command
    if verb == "protect-baseline":
        if not args.check:
            data = push_guard.write_baseline(config.wiki_root)
            print(f"已写入 {push_guard.BASELINE_FILE}：{len(data['files'])} 个文件")
            return 0
        problems = push_guard.check_baseline(config.wiki_root)
        for line in problems:
            print(line)
        if problems:
            return 1
        print("OK")
        return 0
    repo = Path(git(Path.cwd(), "rev-parse", "--show-toplevel").strip())
    if args.sync_ignore:
        changed = push_guard.sync_ignore(config.wiki_root)
        print("GPL 托管块已更新" if changed else "GPL 托管块无变化")
        if not (args.pre_push or args.rev_range):
            return 0
    rules = push_guard.load_rules(config, repo)
    if args.pre_push:
        return push_guard.pre_push(repo, args.pre_push[0], sys.stdin.read(), rules)
    # 未指定范围时检查所有尚未出现在任何远端的提交（首推前的干跑）。
    findings = push_guard.scan(repo, args.rev_range or "HEAD --not --remotes", rules)
    for finding in findings:
        print(push_guard.format_finding(finding))
    if findings:
        return 1
    print("OK")
    return 0


def _print(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _v2_dispatch(args, config) -> int:
    from . import finder, recipes, sources

    if args.command == "find":
        results = finder.find(config, " ".join(args.query), args.kind, args.level, args.runnable, args.limit, scope=args.scope)
        if args.json:
            _print(results)
        else:
            print(finder.format_find(results))
    elif args.command == "show":
        detail = finder.show(config, args.entry_id)
        if args.json:
            _print(detail)
        else:
            print(finder.format_show(detail))
    elif args.command == "use":
        _print(finder.use(config, args.entry_id, args.project, args.name))
    elif args.command == "source":
        if args.source_command == "add":
            page = sources.add_source(config, args.source_id, title=args.title, url=args.url,
                                      license=args.license, adapter=args.adapter, trusted=args.trusted,
                                      cite=args.cite, notice=args.notice)
            print(page.relative_to(config.wiki_root).as_posix())
        elif args.source_command == "fetch":
            _print(sources.fetch_source(config, args.source_id, args.items, args.update))
        else:
            _print(sources.scan_source(config, args.source_id))
    elif args.command == "promote":
        curation = json.loads(args.curation.read_text(encoding="utf-8")) if args.curation else {}
        _print(recipes.promote(config, args.source_id, args.items, curation))
    elif args.command == "run":
        if args.dir:
            if args.recipe_ids:
                raise WikiError("--dir 与配方 id 二选一")
            receipt = recipes.run_dir(config, args.dir, args.timeout)
            _print({key: receipt.get(key) for key in ("state", "scope", "duration_s", "missing_packages",
                                                       "error", "figures", "changed_inputs")})
            return 0 if receipt["state"] == "pass" else 1
        if not args.recipe_ids:
            raise WikiError("给出配方 id，或 --dir <use 副本>")
        results = recipes.run_recipes(config, args.recipe_ids, args.timeout, args.jobs)
        _print([{key: item.get(key) for key in ("id", "state", "duration_s", "missing_packages", "error")}
                for item in results])
        return 0 if all(item["state"] == "pass" for item in results) else 1
    elif args.command == "restore":
        _print([recipes.restore_source(config, recipe_id) for recipe_id in args.recipe_ids])
    elif args.command == "deps":
        _print(recipes.deps(config, args.ids, args.install, args.github))
    return 0


def utf8_streams() -> None:
    """stdout/stderr 统一 UTF-8 输出（Windows 管道缺省按 GBK 编码），已是 UTF-8 的不动。"""
    for stream in (sys.stdout, sys.stderr):
        encoding = (getattr(stream, "encoding", None) or "").replace("-", "").lower()
        if encoding != "utf8" and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    utf8_streams()
    args = parser().parse_args(argv)
    try:
        config = load_config(args.config, args.wiki_root)
        if config is not None:
            prepare_env(config)
        if args.command == 'checkout':
            from .asset_checkout import set_profile
            _print(set_profile(config, args.profile))
            return 0
        if args.command == 'assets':
            from .asset_checkout import fetch_assets
            _print(fetch_assets(config, args.entry_id))
            return 0
        if config is not None and args.command not in {
                'project', 'find', 'show', 'use', 'serve', 'lint', 'pending',
                'suggest', 'suggest-methods', 'suggest-pipeline', 'discover-methods',
                'next', 'contact-sheet', 'render', 'render-layout', 'check-entry',
                'check-dup', 'curate-audit', 'clean'} and not (args.command == 'map-method' and args.audit) and not (args.command == 'paper' and args.paper_command != 'publish'):
            from .asset_checkout import assert_writable
            # run --dir writes only the already copied project directory.
            if not (args.command == 'run' and getattr(args, 'dir', None)):
                assert_writable(config)
        if args.command == 'check-entry':
            from .asset_checkout import assets_state, assert_writable, profile
            if args.record:
                assert_writable(config)
            elif profile(config) == 'light':
                from .pages import visual_path
                _print({'page': args.entry_id, 'passed': None, 'evidence_state': 'not_checked',
                        'assets': assets_state(config, visual_path(config.wiki_root, args.entry_id)),
                        'scope': '轻量检出不进行科学或完整回放核查；请切换 full 后检查。'})
                return 0
        if args.command == "project":
            _project_dispatch(args, config)
            return 0
        if args.command == "clean":
            from .clean import clean_workspace
            res = clean_workspace(
                config,
                apply=args.apply,
                include_backups=args.include_backups,
                include_caches=args.include_caches,
            )
            _print(res) if getattr(args, "json", False) else print(json.dumps(res, ensure_ascii=False, indent=2))
            return 0
        if args.command == "paper":
            from . import paper as paper_mod
            verb = args.paper_command
            if verb == "trace":
                res = paper_mod.trace_paper(
                    config,
                    paper_id=args.paper_id,
                    query=args.query,
                    doi=args.doi,
                    pmid=args.pmid,
                    pmcid=args.pmcid,
                    source_url=args.source_url,
                    source_text_path=args.post_file,
                    repo_url=args.repo_url,
                    offline=args.offline,
                )
            elif verb == "fetch":
                res = paper_mod.fetch_paper(
                    config,
                    args.paper_id,
                    pdf_path=args.pdf,
                    supp_paths=args.supp or None,
                    repo_url=args.repo_url,
                    clone_repo=not args.no_clone,
                )
            elif verb == "parse":
                res = paper_mod.parse_paper_pdf(
                    config,
                    args.paper_id,
                    render_pages=not args.no_render,
                    max_render_pages=args.max_render_pages,
                )
            elif verb == "plan":
                res = paper_mod.build_plan(
                    config,
                    args.paper_id,
                    max_cells=args.max_cells,
                    max_samples=args.max_samples,
                    include_supp=not args.main_only,
                )
            elif verb == "publish":
                wid = paper_mod.publish_paper_workflow(
                    config,
                    args.paper_id,
                    workflow_id=args.workflow_id,
                    title=args.title,
                    tags=args.tags or None,
                    data_domains=args.data_domains or None,
                    derived_methods=args.derived_methods or None,
                    derived_templates=args.derived_templates or None,
                    scale_down_note=args.scale_down_note,
                    dedup_note=args.dedup_note,
                    sync_code=not args.no_sync_code,
                    force=args.force,
                )
                res = {"workflow_id": wid, "paper_id": args.paper_id}
            else:
                res = paper_mod.paper_status(config, args.paper_id)
            _print(res) if getattr(args, "json", False) else print(json.dumps(res, ensure_ascii=False, indent=2))
            return 0
        if args.command == "gh":
            return _gh_dispatch(args, config)
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
            from .naming import naming_audit_for_page
            warnings = (['purposes 缺失：请按分析用途分类；不影响已有状态，但不是完整分类']
                        if missing_purpose(meta) else []) + runtime_warnings + naming_audit_for_page(meta)
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
            if args.native:
                from .curation_workflow import scaffold_native_template
                if not args.primary_method:
                    raise WikiError("--native 新建原生模板必须指定 --primary-method <分析方法id>")
                if not args.title:
                    raise WikiError("--native 新建原生模板必须指定简洁中文 --title")
                scaffold_native_template(
                    config,
                    args.entry_id,
                    chart_type=args.chart_type,
                    title=args.title,
                    primary_method=args.primary_method,
                    language=args.language or "r",
                    sources=args.sources,
                    dedup_note=args.dedup_note,
                    force=args.force,
                )
            elif args.from_recipe:
                from .templates import scaffold_from_recipe
                scaffold_from_recipe(
                    config,
                    args.entry_id,
                    args.chart_type,
                    args.title,
                    args.language,
                    template_id=args.template_id,
                    primary_method=args.primary_method,
                    dedup_note=args.dedup_note,
                    force=args.force,
                )
            elif not args.panels:
                raise WikiError("从版式拆模板需要 --panels；从配方开模板用 --from-recipe；新建原生模板用 --native")
            else:
                scaffold_template(
                    config,
                    args.entry_id,
                    args.chart_type,
                    args.panels.split(","),
                    title=args.title,
                    primary_method=args.primary_method,
                    dedup_note=args.dedup_note,
                    force=args.force,
                )
        elif args.command in ("find", "show", "use", "source", "promote", "run", "restore", "deps"):
            return _v2_dispatch(args, config)
        elif args.command == "add-interface":
            add_interface(config, args.slug, args.title, args.columns)
        elif args.command == "scaffold-method":
            scaffold_method(
                config,
                args.entry_id,
                args.title,
                args.license,
                args.from_entry,
                args.from_path,
                args.url,
                args.commit,
                args.written,
                dedup_note=args.dedup_note,
                force=args.force,
            )
        elif args.command == "check-dup":
            from .dedup import check_duplicates
            report = check_duplicates(
                config,
                kind=args.kind,
                entry_id=args.entry_id,
                title=args.title,
                primary_method=args.primary_method,
                methods=args.methods,
                chart_types=args.chart_types,
                interfaces=args.interfaces,
                summary=args.summary,
                keywords=args.keywords,
                journal_style=args.journal_style,
            )
            if args.json:
                _print(report)
            elif not report["candidates"]:
                print("OK: 未发现高相似既有条目，可继续新建。")
            else:
                for cand in report["candidates"]:
                    print(f"[{cand['severity']}] {cand['kind']}/{cand['id']} 《{cand['title']}》 "
                          f"(score={cand['score']}): {'；'.join(cand['reasons'])}")
        elif args.command in ("map-method", "curate-audit"):
            from .curation_workflow import curate_audit, map_method
            if args.command == "curate-audit" or args.audit:
                report = curate_audit(config)
                if args.json:
                    _print(report)
                else:
                    print(f"分析方法: {report['methods_total']} | "
                          f"未映射配方: {report['unmapped_recipes_count']} | "
                          f"缺主方法模板: {len(report['templates_missing_primary_method'])} | "
                          f"无图方法: {len(report['methods_without_viz'])} | "
                          f"命名待清洗: {report['naming_hygiene_count']} | "
                          f"潜在重复簇: {report['duplicate_clusters_count']}")
                    for err in report["method_map_errors"]:
                        print(f"ERROR method-map: {err}")
            else:
                res = map_method(
                    config,
                    template_id=args.template_id,
                    recipe_id=args.recipe_id,
                    primary_method=args.primary_method,
                    methods=args.methods,
                    unmapped=args.unmapped,
                    note=args.note,
                )
                _print(res) if args.json else print(json.dumps(res, ensure_ascii=False))
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
            from .templates import mark_ready_many
            mark_ready_many(config, args.entry_ids)
        elif args.command == "suggest":
            print(json.dumps(suggest(config, args.chart_type, args.columns,
                                     args.q, args.limit), ensure_ascii=False, indent=2))
        elif args.command == "suggest-pipeline":
            print(json.dumps(suggest_pipeline(config, args.figure, args.q),
                             ensure_ascii=False, indent=2))
        elif args.command == "next":
            payload = suggest_next_steps(config, args.node_id, query=args.q)
            if args.json:
                _print(payload)
            else:
                print(format_next_steps(payload))
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
            with read_session():
                diagnostics = lint(config, ci=args.ci)
            for line in diagnostics:
                print(line)
            if any(line.startswith("ERROR ") for line in diagnostics):
                return 1
            print("OK")
    except WikiError as error:
        print(error, file=sys.stderr)
        return 1
    return 0

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
    result.add_argument("--wiki-root", type=Path,
                        help="覆盖配置中的 wiki_root；优先于环境变量 RWIKI_WIKI_ROOT")
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    ingest = commands.add_parser("ingest-figure")
    selection = ingest.add_mutually_exclusive_group(required=True)
    selection.add_argument("entry_id", nargs="?")
    selection.add_argument("--all", action="store_true")
    commands.add_parser("save").add_argument("message")
    commands.add_parser("lint").add_argument(
        "--ci", action="store_true", help="被 git 忽略而缺失的引用报告为 LOCAL-ONLY，不计为错误")
    github = commands.add_parser("gh", help="GitHub 结构化工作流（git 与 gh CLI 的薄封装）")
    gh_sub = github.add_subparsers(dest="gh_command", required=True)
    guard = gh_sub.add_parser("guard", help="推送前防泄漏检查（纯本地，不需要 gh）")
    guard.add_argument("--range", dest="rev_range", help="检查的提交范围，如 origin/main..HEAD")
    guard.add_argument("--pre-push", nargs=2, metavar=("REMOTE", "URL"),
                       help="pre-push hook 入口：从标准输入读取待推送的 ref")
    guard.add_argument("--sync-ignore", action="store_true", help="重写知识库 .gitignore 的 GPL 托管块")
    gh_sub.add_parser("protect-baseline", help="生成或核验作者块字节基准（纯本地，不需要 gh）").add_argument(
        "--check", action="store_true", help="只核验，不写基准")
    gh_sub.add_parser("tier", help="按改动路径与 .github/risk-tiers.json 计算风险档（纯本地，不需要 gh）").add_argument(
        "--range", dest="rev_range", required=True, help="比较范围，如 origin/main..HEAD")
    gh_sub.add_parser("preflight", help="只读检查 gh、账号、远端仓库、分支保护与待推送范围；有阻断项时退出 1")
    batch = gh_sub.add_parser("start-batch", help="从 origin/main 建长期分支与同名 Milestone")
    batch.add_argument("kind", help="project 或 ingest")
    batch.add_argument("name", help="批次名（小写 slug）")
    batch.add_argument("--title", required=True, help="中文标题，写入 Milestone 描述")
    batch.add_argument("--repo", required=True, choices=("dev", "vault"))
    task = gh_sub.add_parser("start-task", help="在批次的 Milestone 下建 Issue 并创建任务分支（需要 RWIKI_AGENT）")
    task.add_argument("batch")
    task.add_argument("stage", help="P0–P5 或 T<数字>")
    task.add_argument("topic", help="主题（小写 slug）")
    task.add_argument("--title", required=True, help="Issue 标题")
    task.add_argument("--worktree", action="store_true", help="在 worktree_root 下建独立 worktree（并行或 Obsidian 使用中时）")
    gh_sub.add_parser("finish-task", help="推送当前任务分支并开 PR 到所属长期分支").add_argument(
        "--local-report", type=Path, help="仅本地运行的检查摘要，填入 PR 的本地专属验证一栏")
    reviewing = gh_sub.add_parser("review", help="以 PR review（COMMENT）回帖 Codex 评审结论")
    reviewing.add_argument("pr", type=int)
    reviewing.add_argument("--verdict", required=True, choices=("pass", "changes"))
    reviewing.add_argument("--findings", type=Path, required=True, help="问题列表文件，每行一条")
    merging = gh_sub.add_parser("merge", help="合并门禁通过后合并 PR 并收尾（关闭 Issue、释放锁、清理分支）")
    merging.add_argument("pr", type=int)
    merging.add_argument("--plan", help="门禁不通过时回帖的修复计划")
    gh_sub.add_parser("close-batch", help="Milestone 内 Issue 全部关闭后开长期分支到 main 的 PR").add_argument("batch")
    migrating = gh_sub.add_parser("migrate-legacy", help="按 legacy-map.json 把旧任务书与遗留缺口迁到 Issue")
    migrating.add_argument("--map", dest="mapping", type=Path, required=True)
    migrating.add_argument("--dry-run", action="store_true", help="只输出计划，不写 GitHub 与文件")
    gh_sub.add_parser("bootstrap", help="首推：无 --confirm 时只读输出授权摘要；--confirm 时构造 main、建私有仓库并推送"
                      ).add_argument("--confirm", action="store_true",
                                     help="用户已明确授权：改名 master、构造并切到 main、建远端仓库、推送与配置")
    gh_sub.add_parser("install-hook", help="为仓库写 pre-push hook（调用 gh guard --pre-push；不需要 gh，可重复运行）"
                      ).add_argument("--repo", choices=("dev", "vault"),
                                     help="按 config.json 的 github.dev_root / vault_root 选仓库；缺省为当前目录所在仓库")
    # ---- v2（2026-10-27）：检索与调用、来源、配方
    finding = commands.add_parser("find", help="按场景/图型/关键词检索 L0–L2 条目（读 catalog.jsonl）")
    finding.add_argument("query", nargs="+")
    finding.add_argument("--kind", choices=("scenario", "template", "recipe", "method", "item"))
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
    scaffold.add_argument("entry_id", help="版式 id；--from-recipe 时为配方 id")
    scaffold.add_argument("--chart-type", required=True)
    scaffold.add_argument("--panels", help="版式 panel 字母（从版式拆出时必填）")
    scaffold.add_argument("--from-recipe", action="store_true", help="v2：从 L1 配方开 L2 模板")
    scaffold.add_argument("--language", choices=("python", "r"))
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


def _gh_dispatch(args, config) -> int:
    from . import ghflow, push_guard
    from .store import git

    verb = args.gh_command
    if verb == "tier":
        from . import risk
        print(json.dumps(risk.tier_report(Path(git(Path.cwd(), "rev-parse", "--show-toplevel").strip()),
                                          args.rev_range), ensure_ascii=False, indent=2))
        return 0
    if verb not in ("guard", "protect-baseline"):
        # finish-task、review、merge 作用于当前目录所在的检出（主检出或 worktree）。
        checkout = (lambda: Path(git(Path.cwd(), "rev-parse", "--show-toplevel").strip()))
        result = {
            "preflight": lambda: ghflow.preflight(config),
            "start-batch": lambda: ghflow.start_batch(config, args.kind, args.name, args.title, args.repo),
            "start-task": lambda: ghflow.start_task(config, args.batch, args.stage, args.topic, args.title,
                                                    args.worktree),
            "finish-task": lambda: ghflow.finish_task(config, checkout(), args.local_report),
            "review": lambda: ghflow.review(config, checkout(), args.pr, args.verdict, args.findings),
            "merge": lambda: ghflow.merge(config, checkout(), args.pr, args.plan),
            "close-batch": lambda: ghflow.close_batch(config, args.batch),
            "migrate-legacy": lambda: ghflow.migrate_legacy(config, args.mapping, args.dry_run),
            "bootstrap": lambda: ghflow.bootstrap(config, args.confirm, args.config),
            "install-hook": lambda: {"hook": str(ghflow.install_hook(
                ghflow.repo_root(config, args.repo) if args.repo else checkout(), args.config))},
        }[verb]()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if verb in ("preflight", "bootstrap") and result.get("blockers") else 0
    if args.gh_command == "protect-baseline":
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
        results = finder.find(config, " ".join(args.query), args.kind, args.level, args.runnable, args.limit)
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


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        # 课题状态命令只依赖课题目录；check 有配置时才核查 Wiki 引用。
        config = (load_config(args.config, args.wiki_root)
                  if args.command != 'project' or args.config.is_file() else None)
        if args.command == "project":
            _project_dispatch(args, config)
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
            if args.from_recipe:
                from .templates import scaffold_from_recipe
                scaffold_from_recipe(config, args.entry_id, args.chart_type, args.title, args.language)
            elif not args.panels:
                raise WikiError("从版式拆模板需要 --panels；从配方开模板用 --from-recipe")
            else:
                scaffold_template(config, args.entry_id, args.chart_type,
                                  args.panels.split(","), title=args.title)
        elif args.command in ("find", "show", "use", "source", "promote", "run", "restore", "deps"):
            return _v2_dispatch(args, config)
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
            from .templates import mark_ready_many
            mark_ready_many(config, args.entry_ids)
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

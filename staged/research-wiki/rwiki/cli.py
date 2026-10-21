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
from .suggest import suggest, suggest_pipeline
from .templates import attach_template, mark_ready, pending, render, scaffold_template, verify_template
from .usage import record_use


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
    commands.add_parser("pending")
    commands.add_parser("serve").add_argument("--no-browser", action="store_true")
    for name in ("verify-template", "verify-layout", "mark-ready"):
        commands.add_parser(name).add_argument("entry_id")
    scaffold = commands.add_parser("scaffold-template")
    scaffold.add_argument("entry_id")
    scaffold.add_argument("--chart-type", required=True)
    scaffold.add_argument("--panels", required=True)
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
    for name in ("render", "render-layout"):
        rendering = commands.add_parser(name)
        rendering.add_argument("entry_id")
        rendering.add_argument("--data", type=Path, required=True)
        rendering.add_argument("--out", type=Path, required=True)
        rendering.add_argument("--style", type=Path)
    suggesting = commands.add_parser("suggest")
    suggesting.add_argument("--chart-type", nargs="+", action="extend", default=[])
    suggesting.add_argument("--columns")
    suggesting.add_argument("--q", default="")
    suggesting.add_argument("--limit", type=int, default=3)
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
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        config = load_config(args.config)
        if args.command == "init":
            init(config)
        elif args.command == "ingest-figure":
            ingest_figure(config, args.entry_id)
        elif args.command == "save":
            save(config, args.message)
        elif args.command == "serve":
            serve(config, args.no_browser)
        elif args.command == "pending":
            for entry_id in pending(config):
                print(entry_id)
        elif args.command == "scaffold-template":
            scaffold_template(config, args.entry_id, args.chart_type, args.panels.split(","))
        elif args.command == "add-interface":
            add_interface(config, args.slug, args.title, args.columns)
        elif args.command == "scaffold-method":
            scaffold_method(config, args.entry_id, args.title, args.license,
                            args.from_entry, args.from_path, args.url, args.commit, args.written)
        elif args.command == "attach-template":
            attach_template(config, args.entry_id, args.template_id, args.panels.split(","))
        elif args.command == "render":
            render(config, args.entry_id, args.data, args.out, args.style)
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
        elif args.command == "contact-sheet":
            print(contact_sheet(config, args.entry_ids, args.out))
        elif args.command == "record-use":
            record_use(config, args.entry_id, args.project, args.title, args.output, args.note,
                       args.method)
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

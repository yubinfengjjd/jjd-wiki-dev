"""Standard JSON-RPC 2.0 stdio MCP Server for Research Wiki & Bio-Template Studio."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from rwiki.config import Config, load_config, prepare_env
from rwiki.errors import WikiError
from rwiki.finder import show as finder_show
from rwiki.project_tracker import add_project_step
from rwiki.search import search as wiki_search
from rwiki.studio import dispatch_studio, render_studio_code
from rwiki.suggest import suggest_next_steps

SERVER_INFO = {"name": "research-wiki-mcp", "version": "3.0.0"}
PROTOCOL_VERSION = "2024-11-05"

TOOLS: list[dict[str, Any]] = [
    {
        "name": "rwiki_next",
        "description": "查询生信方法/模板/接口的下一步分析分支、标准中间表与配套可视化模板。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "node_id": {"type": "string", "description": "当前方法、模板或接口 ID（如 cell-type-annotation）"},
                "query": {"type": "string", "description": "可选关键词过滤（如 拟时序、细胞比例）", "default": ""},
            },
            "required": ["node_id"],
        },
    },
    {
        "name": "rwiki_search",
        "description": "使用 SQLite FTS5 (BM25) 检索知识库页面、配方、模板与方法。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "检索关键词"},
                "kind": {"type": "string", "description": "可选类型过滤 (method/template/recipe/interface/scenario/project)"},
                "level": {"type": "string", "description": "可选级别过滤 (L0/L1/L2)"},
                "runnable": {"type": "boolean", "description": "仅返回可直接运行的条目", "default": False},
                "limit": {"type": "integer", "description": "最大返回条数", "default": 10},
                "scope": {"type": "string", "description": "knowledge 或 source", "default": "knowledge"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "rwiki_show",
        "description": "查看指定条目（模板、配方、方法、接口、场景或 L0 条目）的完整说明与输入输出。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entry_id": {"type": "string", "description": "条目 ID 或 <source>:<item>"},
            },
            "required": ["entry_id"],
        },
    },
    {
        "name": "rwiki_render_code",
        "description": "根据课题数据路径、列名映射 bindings 与参数 parameters 实时渲染 R/Python 代码。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "模板、配方或方法 ID"},
                "project_dir": {"type": "string", "default": ""},
                "data_file": {"type": "string", "default": ""},
                "bindings": {"type": "object", "default": {}},
                "parameters": {"type": "object", "default": {}},
            },
            "required": ["id"],
        },
    },
    {
        "name": "rwiki_dispatch",
        "description": "将渲染后的脚本、bindings.json 与最小资产闭包派发到目标课题目录 wiki-use/<id>/。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "模板、配方或方法 ID"},
                "project_dir": {"type": "string", "description": "目标课题目录绝对路径"},
                "data_file": {"type": "string", "default": ""},
                "bindings": {"type": "object", "default": {}},
                "parameters": {"type": "object", "default": {}},
                "code": {"type": "string", "description": "可选的自定义覆盖代码"},
            },
            "required": ["id", "project_dir"],
        },
    },
    {
        "name": "rwiki_add_project_step",
        "description": "向 wiki/projects/<project_id>.md 追加一条 3 行课题步进记录（所用模版/观察结果与排坑/触发下一步）。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "课题 slug ID"},
                "title": {"type": "string", "description": "步骤标题"},
                "templates": {"type": "string", "default": "", "description": "所用分析或可视化模版"},
                "observation": {"type": "string", "default": "", "description": "观察结果与排坑"},
                "next_branch": {"type": "string", "default": "", "description": "触发下一步分支"},
                "project_title": {"type": "string", "description": "新建课题卡时的标题"},
            },
            "required": ["project_id", "title"],
        },
    },
]


def call_tool(config: Config, name: str, arguments: dict[str, Any] | None = None) -> Any:
    args = dict(arguments or {})
    if name == "rwiki_next":
        return suggest_next_steps(config, str(args["node_id"]), query=str(args.get("query") or ""))
    if name == "rwiki_search":
        return wiki_search(
            config,
            str(args["query"]),
            kind=args.get("kind"),
            level=args.get("level"),
            runnable=bool(args.get("runnable", False)),
            limit=int(args.get("limit", 10)),
            scope=str(args.get("scope") or "knowledge"),
        )
    if name == "rwiki_show":
        return finder_show(config, str(args["entry_id"]))
    if name == "rwiki_render_code":
        return render_studio_code(
            config,
            entry_id=str(args.get("id") or args.get("entry_id")),
            project_dir=str(args.get("project_dir") or ""),
            data_file=str(args.get("data_file") or ""),
            bindings=args.get("bindings") or {},
            parameters=args.get("parameters") or {},
        )
    if name == "rwiki_dispatch":
        return dispatch_studio(
            config,
            entry_id=str(args.get("id") or args.get("entry_id")),
            project_dir=str(args["project_dir"]),
            data_file=str(args.get("data_file") or ""),
            bindings=args.get("bindings") or {},
            parameters=args.get("parameters") or {},
            code=args.get("code"),
        )
    if name == "rwiki_add_project_step":
        return add_project_step(
            config,
            str(args["project_id"]),
            title=str(args["title"]),
            templates=args.get("templates") or "",
            observation=str(args.get("observation") or ""),
            next_branch=str(args.get("next_branch") or ""),
            project_title=args.get("project_title"),
            commit=True,
        )
    raise WikiError(f"未知 MCP 工具: {name}")


def dispatch_mcp_request(config: Config, message: dict[str, Any]) -> dict[str, Any] | None:
    """Handle one JSON-RPC 2.0 MCP request; return None for notifications."""
    msg_id = message.get("id")
    method = str(message.get("method") or "")
    params = message.get("params") if isinstance(message.get("params"), dict) else {}

    if msg_id is None:
        # Notifications (e.g. notifications/initialized) do not receive a JSON-RPC response.
        return None

    try:
        if method == "initialize":
            result = {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": SERVER_INFO,
            }
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            tool_name = str(params.get("name") or "")
            tool_args = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
            try:
                payload = call_tool(config, tool_name, tool_args)
                result = {
                    "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, indent=2)}],
                    "structuredContent": payload,
                    "isError": False,
                }
            except (WikiError, KeyError, TypeError, ValueError) as exc:
                result = {
                    "content": [{"type": "text", "text": str(exc)}],
                    "isError": True,
                }
        else:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}
    except Exception as exc:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32603, "message": str(exc)},
        }


def serve_stdio(config: Config) -> int:
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        if line.lower().startswith("content-length:"):
            length = int(line.split(":", 1)[1].strip())
            # Read blank separator line and payload
            while True:
                sep = sys.stdin.readline()
                if not sep or sep.strip() == "":
                    break
            body = sys.stdin.read(length)
            if not body:
                break
            req = json.loads(body)
            resp = dispatch_mcp_request(config, req)
            if resp is not None:
                encoded = json.dumps(resp, ensure_ascii=False)
                sys.stdout.write(f"Content-Length: {len(encoded.encode('utf-8'))}\r\n\r\n{encoded}")
                sys.stdout.flush()
            continue

        req = json.loads(line)
        resp = dispatch_mcp_request(config, req)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Research Wiki MCP Server (stdio)")
    ap.add_argument("--config", type=Path, default=Path(__file__).resolve().parent / "config.json")
    ap.add_argument("--wiki-root", type=Path)
    args = ap.parse_args(argv)
    config = load_config(args.config, args.wiki_root)
    prepare_env(config)
    return serve_stdio(config)


if __name__ == "__main__":
    raise SystemExit(main())

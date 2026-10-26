"""测试用假 gh：从 FAKE_GH_STATE 读场景 JSON，把每次 argv 追加到 FAKE_GH_LOG。

只实现 ghflow 用到的子命令，输出与真实 gh 相同形状的 JSON；不访问网络。
场景结构：
{"login": "tester", "authenticated": true, "default_repo": "tester/research-wiki-vault",
 "remote_map": {"<origin url>": "owner/name"}, "clock": 0,
 "repos": {"owner/name": {"visibility": "PRIVATE", "protection_status": 403,
           "milestones": [], "issues": [], "prs": [], "labels": [], "secrets": [], "deploy_keys": []}}}
"""
import json
import os
import subprocess
import sys
from pathlib import Path

VALUE_OPTIONS = {"--title", "-t", "--body", "-b", "--body-file", "-F", "--milestone", "-m", "--label", "-l",
                 "--base", "-B", "--head", "-H", "--state", "-s", "--search", "-S", "--json", "--jq", "-q",
                 "--repo", "-R", "--method", "-X", "--field", "-f", "--raw-field", "--add-label",
                 "--remove-label", "--match-head-commit", "--limit", "-L", "--color", "-c", "--description",
                 "-d", "--header", "--hostname", "--author"}
NEVER_VALUE = {"--private", "--public", "--internal", "--force", "--merge", "--squash", "--rebase",
               "--delete-branch", "--read-only", "--paginate", "--approve", "--request-changes",
               "--draft", "--admin", "--auto"}
LIST_OPTIONS = {"--label", "--add-label", "--remove-label", "--field", "--raw-field", "-f"}
ALIASES = {"-t": "--title", "-b": "--body", "-m": "--milestone", "-l": "--label", "-B": "--base",
           "-s": "--state", "-S": "--search", "-q": "--jq", "-R": "--repo", "-X": "--method",
           "-f": "--field", "-L": "--limit", "-c": "--color", "-d": "--description"}


def fail(message: str, code: int = 1):
    print(message, file=sys.stderr)
    raise SystemExit(code)


def parse(argv: list[str], flags=()):
    """flags：本子命令中不带值的选项（如 pr review 的 --comment）。"""
    positional, options, index = [], {}, 0
    while index < len(argv):
        item = argv[index]
        if item.startswith("-") and len(item) > 1:
            name, eq, inline = item.partition("=")
            if eq and name.startswith("--"):
                value = inline
            elif name in flags or name in NEVER_VALUE or name not in VALUE_OPTIONS | {"--comment"}:
                options[ALIASES.get(name, name)] = True
                index += 1
                continue
            else:
                index += 1
                value = argv[index]
            key = ALIASES.get(name, name)
            if key in LIST_OPTIONS:
                options.setdefault(key, []).append(value)
            else:
                options[key] = value
        else:
            positional.append(item)
        index += 1
    return positional, options


def tick(state: dict) -> str:
    state["clock"] = state.get("clock", 0) + 1
    seconds = state["clock"]
    return f"2026-01-01T{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}Z"


def body_of(options: dict) -> str:
    if "--body-file" in options:
        source = options["--body-file"]
        return sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
    return options.get("--body", "")


def labels_of(values) -> list[str]:
    return [name for value in values or [] for name in value.split(",") if name]


def current_repo(state: dict, options: dict) -> str:
    if options.get("--repo"):
        return options["--repo"]
    url = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True).stdout.strip()
    return state.get("remote_map", {}).get(url, state.get("default_repo"))


def repo_state(state: dict, name: str) -> dict:
    if name not in state.get("repos", {}):
        fail(f"GraphQL: Could not resolve to a Repository with the name '{name}'. (repository)")
    return state["repos"][name]


def jq(data, expression: str):
    if expression == ".":
        return data
    for part in expression.lstrip(".").split("."):
        if part == "[]":
            continue
        if part.startswith("[]"):
            part = part[2:]
        data = [item[part] for item in data] if isinstance(data, list) else data[part]
    return data


def emit(data, options: dict) -> None:
    fields = options.get("--json")
    if isinstance(fields, str) and fields:
        names = fields.split(",")
        pick = (lambda item: {name: item.get(name) for name in names})
        data = [pick(item) for item in data] if isinstance(data, list) else pick(data)
    if options.get("--jq"):
        result = jq(data, options["--jq"])
        if isinstance(result, list):
            print("\n".join(str(item) for item in result))
        else:
            print(result if isinstance(result, str) else json.dumps(result, ensure_ascii=False))
        return
    print(json.dumps(data, ensure_ascii=False))


def next_number(repo: dict) -> int:
    return 1 + max([item["number"] for item in repo["issues"] + repo["prs"]] or [0])


def find(items: list[dict], number: str, what: str) -> dict:
    for item in items:
        if str(item["number"]) == str(number).lstrip("#"):
            return item
    fail(f"GraphQL: Could not resolve to an {what} with the number of {number}.")


def git_sha(ref: str) -> str:
    result = subprocess.run(["git", "rev-parse", ref], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else ""


def cmd_auth(state, args):
    if args[:1] != ["status"]:
        fail(f"假 gh 不支持: auth {' '.join(args)}")
    if not state.get("authenticated"):
        fail("You are not logged into any GitHub hosts. To log in, run: gh auth login")
    print(f"github.com\n  ✓ Logged in to github.com account {state['login']} (keyring)", file=sys.stderr)


def cmd_api(state, args):
    positional, options = parse(args)
    method = options.get("--method", "POST" if options.get("--field") or options.get("--raw-field") else "GET")
    endpoint = positional[0].split("?", 1)
    path, query = endpoint[0].strip("/"), dict(p.split("=", 1) for p in endpoint[1].split("&")) if len(endpoint) > 1 else {}
    fields = dict(item.split("=", 1) for item in options.get("--field", []) + options.get("--raw-field", []))
    if method == "GET":
        query.update(fields)
    name = current_repo(state, options)
    owner, _, repo_name = name.partition("/")
    path = path.replace("{owner}", owner).replace("{repo}", repo_name)
    if path == "user":
        return emit({"login": state["login"]}, options)
    parts = path.split("/")
    if parts[0] != "repos" or len(parts) < 3:
        fail(f"假 gh 不支持的 API: {path}")
    repo = repo_state(state, f"{parts[1]}/{parts[2]}")
    rest = parts[3:]
    if not rest:
        return emit({"full_name": f"{parts[1]}/{parts[2]}", "visibility": repo["visibility"].lower(),
                     "private": repo["visibility"] == "PRIVATE"}, options)
    if rest[:1] == ["branches"] and rest[-1] == "protection":
        status = repo.get("protection_status", 403)
        if status != 200:
            fail(f"gh: Upgrade to GitHub Pro or make this repository public to enable this feature. (HTTP {status})")
        repo.setdefault("protected", [])
        if method == "PUT" and rest[1] not in repo["protected"]:
            repo["protected"].append(rest[1])
        elif method != "PUT" and rest[1] not in repo["protected"]:
            fail("gh: Branch not protected (HTTP 404)")
        return emit({"url": f"https://api.github.com/{path}"}, options)
    if rest[:1] == ["milestones"]:
        if len(rest) == 1 and method == "GET":
            wanted = query.get("state", "open")
            return emit([m for m in repo["milestones"] if wanted == "all" or m["state"] == wanted], options)
        if len(rest) == 1 and method == "POST":
            milestone = {"number": 1 + max([m["number"] for m in repo["milestones"]] or [0]),
                         "title": fields["title"], "description": fields.get("description", ""),
                         "state": fields.get("state", "open")}
            repo["milestones"].append(milestone)
            return emit(milestone, options)
        milestone = find(repo["milestones"], rest[1], "Milestone")
        if method == "PATCH":
            milestone.update(fields)
        return emit(milestone, options)
    if rest == ["actions", "secrets"]:
        return emit({"total_count": len(repo["secrets"]), "secrets": [{"name": s} for s in repo["secrets"]]}, options)
    fail(f"假 gh 不支持的 API: {path}")


def cmd_repo(state, args):
    verb, rest = args[0], args[1:]
    positional, options = parse(rest)
    if verb == "view":
        name = positional[0] if positional else current_repo(state, options)
        repo = repo_state(state, name)
        owner, _, short = name.partition("/")
        return emit({"visibility": repo["visibility"], "nameWithOwner": name, "name": short,
                     "owner": {"login": owner}, "url": f"https://github.com/{name}"}, options)
    if verb == "create":
        name = positional[0] if "/" in positional[0] else f"{state['login']}/{positional[0]}"
        if name in state.setdefault("repos", {}):
            fail(f"GraphQL: Name already exists on this account (createRepository)")
        visibility = "PUBLIC" if options.get("--public") else "INTERNAL" if options.get("--internal") else "PRIVATE"
        state["repos"][name] = {"visibility": visibility, "protection_status": state.get("protection_status", 403),
                                "milestones": [], "issues": [], "prs": [], "labels": [], "secrets": [],
                                "deploy_keys": []}
        print(f"https://github.com/{name}")
        return
    if verb == "deploy-key" and positional[:1] == ["add"]:
        repo = repo_state(state, current_repo(state, options))
        repo["deploy_keys"].append({"key": Path(positional[1]).read_text(encoding="utf-8").strip(),
                                    "title": options.get("--title", ""), "read_only": bool(options.get("--read-only"))})
        return
    if verb == "deploy-key" and positional[:1] == ["list"]:
        return emit(repo_state(state, current_repo(state, options))["deploy_keys"], options)
    fail(f"假 gh 不支持: repo {' '.join(args)}")


def cmd_secret(state, args):
    verb, rest = args[0], args[1:]
    positional, options = parse(rest)
    repo = repo_state(state, current_repo(state, options))
    if verb == "set":
        if positional[0] not in repo["secrets"]:
            repo["secrets"].append(positional[0])
        if "--body" not in options:
            sys.stdin.read()
        return
    if verb == "list":
        return emit([{"name": name} for name in repo["secrets"]], options)
    fail(f"假 gh 不支持: secret {' '.join(args)}")


def cmd_label(state, args):
    verb, rest = args[0], args[1:]
    positional, options = parse(rest)
    repo = repo_state(state, current_repo(state, options))
    if verb == "create":
        existing = next((label for label in repo["labels"] if label["name"] == positional[0]), None)
        if existing and not options.get("--force"):
            fail(f"label with name \"{positional[0]}\" already exists; use `--force` to update its color and description")
        if existing:
            repo["labels"].remove(existing)
        repo["labels"].append({"name": positional[0], "color": options.get("--color", ""),
                               "description": options.get("--description", "")})
        return
    if verb == "list":
        return emit(repo["labels"], options)
    fail(f"假 gh 不支持: label {' '.join(args)}")


def issue_view(issue: dict) -> dict:
    return {**issue, "labels": [{"name": name} for name in issue["labels"]],
            "milestone": {"title": issue["milestone"]} if issue.get("milestone") else None}


def cmd_issue(state, args):
    verb, rest = args[0], args[1:]
    positional, options = parse(rest, flags=() if verb == "close" else ())
    name = current_repo(state, options)
    repo = repo_state(state, name)
    if verb == "create":
        milestone = options.get("--milestone")
        if milestone and not any(m["title"] == milestone for m in repo["milestones"]):
            fail(f"could not add to milestone '{milestone}': '{milestone}' not found")
        number = next_number(repo)
        repo["issues"].append({"number": number, "title": options["--title"], "body": body_of(options),
                               "state": "OPEN", "labels": labels_of(options.get("--label")),
                               "milestone": milestone, "comments": [],
                               "url": f"https://github.com/{name}/issues/{number}"})
        print(f"https://github.com/{name}/issues/{number}")
        return
    if verb == "list":
        wanted = options.get("--state", "open").upper()
        items = [issue for issue in repo["issues"]
                 if (wanted == "ALL" or issue["state"] == wanted)
                 and (not options.get("--milestone") or issue.get("milestone") == options["--milestone"])
                 and all(label in issue["labels"] for label in labels_of(options.get("--label")))
                 and (not options.get("--search") or options["--search"].strip('"') in issue["body"] + issue["title"])]
        return emit([issue_view(issue) for issue in items], options)
    issue = find(repo["issues"], positional[0], "Issue")
    if verb == "view":
        return emit(issue_view(issue), options)
    if verb == "close":
        if options.get("--comment") not in (None, True):
            issue["comments"].append({"body": options["--comment"], "createdAt": tick(state)})
        issue["state"] = "CLOSED"
        return
    if verb == "reopen":
        issue["state"] = "OPEN"
        return
    if verb == "comment":
        issue["comments"].append({"body": body_of(options), "createdAt": tick(state)})
        return
    if verb == "edit":
        issue["labels"] = [label for label in issue["labels"] + labels_of(options.get("--add-label"))
                           if label not in labels_of(options.get("--remove-label"))]
        issue["labels"] = list(dict.fromkeys(issue["labels"]))
        if "--body" in options or "--body-file" in options:
            issue["body"] = body_of(options)
        if "--milestone" in options:
            issue["milestone"] = options["--milestone"]
        if "--title" in options:
            issue["title"] = options["--title"]
        return
    fail(f"假 gh 不支持: issue {' '.join(args)}")


def cmd_pr(state, args):
    verb, rest = args[0], args[1:]
    positional, options = parse(rest, flags=("--comment",) if verb == "review" else ())
    name = current_repo(state, options)
    repo = repo_state(state, name)
    if verb == "create":
        head = options.get("--head") or subprocess.run(["git", "branch", "--show-current"],
                                                        capture_output=True, text=True).stdout.strip()
        if any(pr["headRefName"] == head and pr["state"] == "OPEN" for pr in repo["prs"]):
            fail(f"a pull request for branch \"{head}\" into branch \"{options['--base']}\" already exists")
        number = next_number(repo)
        repo["prs"].append({"number": number, "title": options.get("--title", head), "body": body_of(options),
                            "state": "OPEN", "headRefName": head, "baseRefName": options["--base"],
                            "headRefOid": state.get("pr_head_oid") or git_sha(head),
                            "reviews": [], "comments": [], "checks": list(state.get("default_checks", [])),
                            "mergeCommit": None, "url": f"https://github.com/{name}/pull/{number}"})
        print(f"https://github.com/{name}/pull/{number}")
        return
    if verb == "list":
        wanted = options.get("--state", "open").upper()
        items = [pr for pr in repo["prs"]
                 if (wanted == "ALL" or pr["state"] == wanted)
                 and (not options.get("--head") or pr["headRefName"] == options["--head"])
                 and (not options.get("--base") or pr["baseRefName"] == options["--base"])]
        return emit(items, options)
    pr = find(repo["prs"], positional[0], "PullRequest")
    if verb == "view":
        return emit(pr, options)
    if verb == "checks":
        checks = pr["checks"]
        if not checks:
            fail(f"no checks reported on the '{pr['headRefName']}' branch")
        emit(checks, options)
        buckets = {check["bucket"] for check in checks}
        if buckets & {"fail", "cancel"}:
            raise SystemExit(1)
        if "pending" in buckets:
            raise SystemExit(8)
        return
    if verb == "review":
        pr["reviews"].append({"body": body_of(options), "state": "COMMENTED", "submittedAt": tick(state),
                              "commit": {"oid": pr["headRefOid"]}, "author": {"login": state["login"]}})
        return
    if verb == "comment":
        pr["comments"].append({"body": body_of(options), "createdAt": tick(state),
                               "author": {"login": state["login"]}})
        return
    if verb == "merge":
        if pr["state"] != "OPEN":
            fail(f"Pull request #{pr['number']} was already merged or closed")
        expected = options.get("--match-head-commit")
        if expected and expected != pr["headRefOid"]:
            fail("GraphQL: Head branch was modified. Review and try the merge again. (mergePullRequest)")
        pr["state"] = "MERGED"
        pr["mergeCommit"] = {"oid": state.get("merge_oid", "f" * 40)}
        if options.get("--delete-branch"):
            state.setdefault("deleted_branches", []).append(pr["headRefName"])
        return
    if verb == "edit":
        if "--body" in options or "--body-file" in options:
            pr["body"] = body_of(options)
        return
    fail(f"假 gh 不支持: pr {' '.join(args)}")


COMMANDS = {"auth": cmd_auth, "api": cmd_api, "repo": cmd_repo, "secret": cmd_secret,
            "label": cmd_label, "issue": cmd_issue, "pr": cmd_pr}


def main(argv: list[str]) -> int:
    with open(os.environ["FAKE_GH_LOG"], "a", encoding="utf-8") as log:
        log.write(json.dumps(argv, ensure_ascii=False) + "\n")
    state_path = Path(os.environ["FAKE_GH_STATE"])
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if argv == ["--version"]:
        print("gh version 2.0.0-fake (2026-01-01)\nhttps://github.com/cli/cli/releases/tag/v2.0.0-fake")
        return 0
    if not argv or argv[0] not in COMMANDS:
        fail(f"假 gh 不支持: {' '.join(argv)}")
    try:
        COMMANDS[argv[0]](state, argv[1:])
    finally:
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main(sys.argv[1:]))

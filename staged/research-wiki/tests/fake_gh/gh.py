"""测试用假 gh：从 FAKE_GH_STATE 读场景 JSON，把每次 argv 追加到 FAKE_GH_LOG。

只实现 ghflow 用到的子命令，输出与真实 gh（2.103）相同形状的 JSON；不访问网络。
与真实 gh 一样拒绝未知参数（KNOWN_FLAGS，取自各子命令 --help）：报 unknown flag 并退出 1。
场景结构：
{"login": "tester", "authenticated": true, "default_repo": "tester/jjd-wiki",
 "remote_map": {"<origin url>": "owner/name"}, "clock": 0,
 "repos": {"owner/name": {"visibility": "PRIVATE", "protection_status": 403,
           "milestones": [], "issues": [], "prs": [], "labels": [], "secrets": [], "deploy_keys": []}}}
PR 另有 "labels"（名字列表）与 "timeline"（REST timeline 事件，可在场景中预置；pr edit 增删标签时追加
labeled/unlabeled 事件）。
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
                 "-d", "--header", "--hostname", "--author", "--input"}
NEVER_VALUE = {"--private", "--public", "--internal", "--force", "--merge", "--squash", "--rebase",
               "--delete-branch", "--allow-write", "--paginate", "--approve", "--request-changes",
               "--draft", "--admin", "--auto", "--slurp"}
# 各子命令接受的参数（gh 2.103 的 --help）；不在表中的参数与真实 gh 一样报 unknown flag。
REPO_FLAGS = {"--repo", "-R", "--help"}
FORMAT_FLAGS = {"--json", "--jq", "-q", "--template", "-t"}
BODY_FLAGS = {"--body", "-b", "--body-file", "-F"}
KNOWN_FLAGS = {
    "auth status": {"--active", "-a", "--hostname", "-h", "--jq", "--json", "--no-refresh", "--show-token", "-t",
                    "--template", "--help"},
    "api": {"--allow-escape-sequences", "--cache", "--field", "-F", "--header", "-H", "--hostname", "--include", "-i",
            "--input", "--jq", "-q", "--method", "-X", "--paginate", "--preview", "-p", "--raw-field", "-f", "--silent",
            "--slurp", "--template", "-t", "--verbose", "--help"},
    "repo view": {"--branch", "-b", "--web", "-w", "--help", *FORMAT_FLAGS},
    "repo create": {"--add-readme", "--clone", "-c", "--description", "-d", "--disable-issues", "--disable-wiki",
                    "--gitignore", "-g", "--homepage", "-h", "--include-all-branches", "--internal", "--license", "-l",
                    "--private", "--public", "--push", "--remote", "-r", "--source", "-s", "--team", "-t",
                    "--template", "-p", "--help"},
    "repo deploy-key add": {"--allow-write", "-w", "--title", "-t", *REPO_FLAGS},
    "repo deploy-key list": {*FORMAT_FLAGS, *REPO_FLAGS},
    "secret set": {"--app", "-a", "--body", "-b", "--env", "-e", "--env-file", "-f", "--no-repos-selected",
                   "--no-store", "--org", "-o", "--repos", "-r", "--user", "-u", "--visibility", "-v", *REPO_FLAGS},
    "secret list": {"--app", "-a", "--env", "-e", "--org", "-o", "--user", "-u", *FORMAT_FLAGS, *REPO_FLAGS},
    "label list": {"--limit", "-L", "--order", "--search", "-S", "--sort", "--web", "-w", *FORMAT_FLAGS, *REPO_FLAGS},
    "label create": {"--color", "-c", "--description", "-d", "--force", "-f", *REPO_FLAGS},
    "issue create": {"--assignee", "-a", "--attach", "--blocked-by", "--blocking", "--editor", "-e", "--label", "-l",
                     "--milestone", "-m", "--parent", "--project", "-p", "--recover", "--template", "-T", "--title",
                     "-t", "--type", "--web", "-w", *BODY_FLAGS, *REPO_FLAGS},
    "issue list": {"--app", "--assignee", "-a", "--author", "-A", "--label", "-l", "--limit", "-L", "--mention",
                   "--milestone", "-m", "--search", "-S", "--state", "-s", "--type", "--web", "-w", *FORMAT_FLAGS,
                   *REPO_FLAGS},
    "issue view": {"--comments", "-c", "--web", "-w", *FORMAT_FLAGS, *REPO_FLAGS},
    "issue edit": {"--add-assignee", "--add-label", "--add-project", "--attach", "--milestone", "-m",
                   "--remove-assignee", "--remove-label", "--remove-milestone", "--remove-project", "--title", "-t",
                   "--type", "--remove-type", *BODY_FLAGS, *REPO_FLAGS},
    "issue close": {"--comment", "-c", "--duplicate-of", "--reason", "-r", *REPO_FLAGS},
    "issue reopen": {"--comment", "-c", *REPO_FLAGS},
    "issue comment": {"--attach", "--edit-last", "--editor", "-e", "--web", "-w", *BODY_FLAGS, *REPO_FLAGS},
    "pr create": {"--assignee", "-a", "--attach", "--base", "-B", "--draft", "-d", "--dry-run", "--editor", "-e",
                  "--fill", "-f", "--fill-first", "--fill-verbose", "--head", "-H", "--label", "-l", "--milestone",
                  "-m", "--no-maintainer-edit", "--project", "-p", "--recover", "--reviewer", "-r", "--template",
                  "-T", "--title", "-t", "--web", "-w", *BODY_FLAGS, *REPO_FLAGS},
    "pr list": {"--app", "--assignee", "-a", "--author", "-A", "--base", "-B", "--draft", "-d", "--head", "-H",
                "--label", "-l", "--limit", "-L", "--search", "-S", "--state", "-s", "--web", "-w", *FORMAT_FLAGS,
                *REPO_FLAGS},
    "pr view": {"--comments", "-c", "--web", "-w", *FORMAT_FLAGS, *REPO_FLAGS},
    "pr checks": {"--fail-fast", "--interval", "-i", "--required", "--watch", "--web", "-w", *FORMAT_FLAGS,
                  *REPO_FLAGS},
    "pr review": {"--approve", "-a", "--comment", "-c", "--request-changes", "-r", *BODY_FLAGS, *REPO_FLAGS},
    "pr merge": {"--admin", "--author-email", "-A", "--auto", "--delete-branch", "-d", "--disable-auto",
                 "--match-head-commit", "--merge", "-m", "--rebase", "-r", "--squash", "-s", "--subject", "-t",
                 *BODY_FLAGS, *REPO_FLAGS},
    "pr comment": {"--attach", "--create-if-none", "--delete-last", "--edit-last", "--editor", "-e", "--web", "-w",
                   "--yes", *BODY_FLAGS, *REPO_FLAGS},
    "pr edit": {"--add-label", "--remove-label", "--base", "-B", "--title", "-t", *BODY_FLAGS, *REPO_FLAGS},
}
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


def command_path(argv: list[str]) -> str:
    if argv[0] == "api":
        return "api"
    return " ".join(argv[:3] if argv[:2] == ["repo", "deploy-key"] else argv[:2])


def check_flags(argv: list[str]) -> None:
    """与真实 gh（cobra）一样：子命令不认识的参数报错并退出 1，不执行任何操作。"""
    path = command_path(argv)
    known = KNOWN_FLAGS.get(path)
    if known is None:
        return
    takes_value = (VALUE_OPTIONS | ({"--comment"} if path != "pr review" else set())) - NEVER_VALUE
    rest, index = argv[len(path.split()):], 0
    while index < len(rest):
        item = rest[index]
        if item.startswith("-") and len(item) > 1:
            name, eq, _ = item.partition("=")
            if name not in known:
                detail = f"unknown flag: {name}" if name.startswith("--") else \
                    f"unknown shorthand flag: '{name[1:]}' in {name}"
                fail(f"{detail}\n\nUsage:  gh {path} [flags]")
            if not eq and name in takes_value:
                index += 1
        index += 1


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
    if len(rest) == 3 and rest[0] == "issues" and rest[2] == "timeline" and method == "GET":
        # PR 与 Issue 共用编号；事件形状同 REST：labeled/unlabeled（label、created_at）、
        # committed（sha、committer.date，无 created_at）、head_ref_force_pushed（created_at）。
        item = next((item for item in repo["prs"] + repo["issues"] if str(item["number"]) == rest[1]), None)
        if item is None:
            fail("gh: Not Found (HTTP 404)")
        timeline = item.get("timeline", [])
        return emit([timeline] if options.get("--slurp") else timeline, options)
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
        # gh 2.103：默认只读，--allow-write（-w）才给写权限。
        keys = repo_state(state, current_repo(state, options))["deploy_keys"]
        keys.append({"id": 1 + max([key.get("id", 0) for key in keys] or [0]),
                     "key": Path(positional[1]).read_text(encoding="utf-8").strip(),
                     "title": options.get("--title", ""), "created_at": tick(state),
                     "read_only": not (options.get("--allow-write") or options.get("-w"))})
        return
    if verb == "deploy-key" and positional[:1] == ["list"]:
        # 真实 gh：--json 不按字段筛选，原样输出 REST 形状（snake_case）；没有 key 时什么都不输出。
        keys = repo_state(state, current_repo(state, options))["deploy_keys"]
        if keys:
            print(json.dumps(keys, ensure_ascii=False))
        return
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


def pr_view(pr: dict) -> dict:
    """PR 的 labels 存为名字列表，输出为 gh 的 [{"name": …}] 形状。"""
    return {**pr, "labels": [{"name": name} for name in pr.get("labels", [])]}


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
                            "labels": labels_of(options.get("--label")), "timeline": [],
                            "mergeCommit": None, "url": f"https://github.com/{name}/pull/{number}"})
        print(f"https://github.com/{name}/pull/{number}")
        return
    if verb == "list":
        wanted = options.get("--state", "open").upper()
        items = [pr for pr in repo["prs"]
                 if (wanted == "ALL" or pr["state"] == wanted)
                 and (not options.get("--head") or pr["headRefName"] == options["--head"])
                 and (not options.get("--base") or pr["baseRefName"] == options["--base"])]
        return emit([pr_view(pr) for pr in items], options)
    pr = find(repo["prs"], positional[0], "PullRequest")
    if verb == "view":
        return emit(pr_view(pr), options)
    if verb == "checks":
        checks = pr["checks"]
        if not checks:
            fail(f"no checks reported on the '{pr['headRefName']}' branch")
        emit(checks, options)
        if options.get("--json"):
            return  # 真实 gh：--json 只导出并退出 0，失败与等待中只体现在 bucket
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
        # 默认等同快进合并：合并提交即 head，本地分支是它的祖先（after_task_merge 会核对）。
        pr["mergeCommit"] = {"oid": state.get("merge_oid", pr["headRefOid"])}
        if options.get("--delete-branch"):
            state.setdefault("deleted_branches", []).append(pr["headRefName"])
        return
    if verb == "edit":
        if "--body" in options or "--body-file" in options:
            pr["body"] = body_of(options)
        labels = pr.setdefault("labels", [])
        timeline = pr.setdefault("timeline", [])
        for label in labels_of(options.get("--remove-label")):
            if label in labels:
                labels.remove(label)
                timeline.append({"event": "unlabeled", "label": {"name": label}, "created_at": tick(state)})
        for label in labels_of(options.get("--add-label")):
            if label not in labels:
                labels.append(label)
                timeline.append({"event": "labeled", "label": {"name": label}, "created_at": tick(state)})
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
    check_flags(argv)
    try:
        COMMANDS[argv[0]](state, argv[1:])
    finally:
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main(sys.argv[1:]))

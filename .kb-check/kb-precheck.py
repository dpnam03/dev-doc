#!/usr/bin/env python3
"""kb-precheck.py — check dev-docs files against the Knowledge Base writing rules.

This tool is for the dev-docs repo. It never reads or writes the BS-Knowledge-Base repo or its PRs.
The only thing borrowed from the KB is the rule set: Foundation 0 (in ./foundation) and the
checker scripts, refreshed with sync.sh.

How it works: it builds a throwaway folder shaped like the KB (Foundation 0 + your file placed at
the destination path you give), runs the checks on it, then deletes it. The destination decides
which rules bind the file (layer, function folder, owner role).

Usage:
    # check files, keeping their names
    kb-precheck.py FILE [FILE ...] --to "2. Reference Library/Dev"

    # check ONE file under the name it will have after the move
    kb-precheck.py draft.md --as "2. Reference Library/Dev/Ref_Dev_git-flow_v1.0.md"

    # check every .md of PR #N of the dev-docs repo
    kb-precheck.py --dev-pr 1 --to "2. Reference Library/Dev" [--summary]

Exit code: 0 when nothing blocks, 1 when at least one blocking finding remains.
Findings marked `note` are advisory (readable-shape): they do not block.
Only .md files get content rules. Other formats are checked by file name only.
"""
import argparse
import collections
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, filename))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def git(repo, *args):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def build_sandbox():
    """A folder shaped like the KB, holding only Foundation 0 (the rule source)."""
    sb = tempfile.mkdtemp(prefix="kb-precheck-")
    f0 = os.path.join(sb, "0. Department Foundation")
    os.makedirs(f0)
    src = os.path.join(HERE, "foundation")
    for name in os.listdir(src):
        shutil.copy(os.path.join(src, name), f0)
    return sb


def export_dev_pr(repo, number, outdir):
    """Fetch PR #N of the dev-docs repo and write each .md it adds, changes or renames into
    outdir. Returns ({exported path: original path in the PR}, count of other changed files)."""
    ref = f"refs/precheck/devpr{number}"
    git(repo, "fetch", "--quiet", "origin", f"refs/pull/{number}/head:{ref}")
    base = git(repo, "merge-base", "origin/master", ref).strip()
    if git(repo, "rev-list", "--count", f"{base}..{ref}").strip() == "0":
        raise RuntimeError(f"PR #{number} adds no commits over origin/master: already merged?")
    raw = git(repo, "diff", "--name-only", "--diff-filter=AMR", "-z", base, ref)
    names = [n for n in raw.split("\0") if n]
    mds = [n for n in names if n.lower().endswith(".md")]
    shown = {}
    for n in mds:
        dest = os.path.join(outdir, f"{len(shown)}_{os.path.basename(n)}")
        data = subprocess.run(["git", "-C", repo, "show", f"{ref}:{n}"],
                              capture_output=True, check=True).stdout
        with open(dest, "wb") as fh:
            fh.write(data)
        shown[dest] = n
    return shown, len(names) - len(mds)


def check(a, ap, shown):
    kb_check = load("kb_check", "kb-check.py")
    pr_check = load("pr_check", "pr-check.py")  # holds the readable-shape runner

    pairs = []  # (source file, KB-relative destination)
    for f in a.files:
        if not os.path.isfile(f):
            ap.error(f"not a file: {f}")
        orig = shown.get(f, f)
        rel = a.as_path if a.as_path else os.path.join(a.to, os.path.basename(orig))
        pairs.append((f, rel.strip("/")))
    names = [rel for _, rel in pairs]
    dupes = [n for n, c in collections.Counter(names).items() if c > 1]
    if dupes:
        ap.error("two files share the name " + ", ".join(dupes) + ": rename one first")

    config = kb_check.load_config(HERE, os.path.join(HERE, "config.json"))
    # local-config.json holds dev-docs overrides (for example turning a rule off). sync.sh never
    # overwrites it, unlike config.json, which is a copy of the KB's.
    local = os.path.join(HERE, "local-config.json")
    if os.path.exists(local):
        over = json.load(open(local, encoding="utf-8"))
        config.setdefault("severity", {}).update(over.pop("severity", {}))
        config.update({k: v for k, v in over.items() if not k.startswith("_")})
    # `Linked from` names other KB docs. dev-docs has no KB to resolve them against.
    config.setdefault("severity", {})["C1-linkedfrom"] = "advisory"

    sandbox = build_sandbox()
    try:
        for src, rel in pairs:
            dest = os.path.join(sandbox, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy(src, dest)

        rules = kb_check.load_rules_from_foundation(sandbox)
        if not rules:
            print("error: Foundation 0 missing in .kb-check/foundation. Run .kb-check/sync.sh.",
                  file=sys.stderr)
            return 2
        checker = kb_check.Check(sandbox, config, rules)
        readable_hits = {}
        for src, rel in pairs:
            checker.run(rel)
            if (not a.no_readable and rel.lower().endswith(".md")
                    and kb_check.kind_of(rel) != "archive"
                    and os.path.basename(rel) not in config.get("templates", [])):
                text = open(os.path.join(sandbox, rel), encoding="utf-8", errors="replace").read()
                found, _ = pr_check.readable(sandbox, rel, text, config)
                readable_hits[rel] = found

        findings = list(checker.findings)
        for rel, found in readable_hits.items():
            for f in found:
                findings.append({
                    "file": rel, "line": f.get("line", 0), "id": "readable-" + f.get("rule", "?"),
                    "part": "read", "severity": "advisory", "message": f.get("what", ""),
                    "fix": pr_check.READABLE_FIX.get(f.get("rule"), ""),
                })
        blocking = [f for f in findings if f["severity"] == "blocking"]
        advisory = [f for f in findings if f["severity"] != "blocking"]

        if a.json:
            print(json.dumps({"pass": not blocking, "blocking": len(blocking),
                              "advisory": len(advisory), "rulesSource": checker.rules_source,
                              "findings": findings, "decisions": checker.decisions}))
            return 1 if blocking else 0

        by_file = collections.defaultdict(list)
        for f in findings:
            by_file[f["file"]].append(f)

        if a.summary:
            totals = collections.Counter()
            for src, rel in pairs:
                c = collections.Counter(f["id"] for f in by_file[rel] if f["severity"] == "blocking")
                totals.update(c)
                print(f"[{'FAIL' if c else 'OK  '}] {shown.get(src, src)}  "
                      f"({sum(c.values())} blocking)  " + " ".join(f"{i}:{n}" for i, n in sorted(c.items())))
            print("\nBy rule: " + ", ".join(f"{i}:{n}" for i, n in totals.most_common()))
        else:
            for src, rel in pairs:
                items = sorted(by_file[rel], key=lambda x: (x["severity"] != "blocking", x["line"]))
                nb = sum(1 for x in items if x["severity"] == "blocking")
                print(f"\n[{'FAIL' if nb else 'OK  '}] {shown.get(src, src)}\n       -> {rel}")
                for f in items:
                    tag = "FAIL" if f["severity"] == "blocking" else "note"
                    print(f"   {tag} {f['part']:<5} line {f['line']:>4}  {f['message']}")
                    if f.get("fix"):
                        print(f"        fix: {f['fix']}")
            for d in checker.decisions:
                print(f"\n[OWNR] {d['file']} line {d['line']}: {d['message']}")
        print(f"\n{len(pairs)} file(s) · {len(blocking)} blocking · {len(advisory)} advisory"
              f" · rules from {checker.rules_source}")
        print("RESULT: " + ("fix the FAIL items before moving the files." if blocking
                            else "files meet the KB rules."))
        return 1 if blocking else 0
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description="Check dev-docs files against the KB writing rules.")
    ap.add_argument("files", nargs="*", help="files in dev-docs to check")
    ap.add_argument("--to", help='KB folder the files will live in, e.g. "2. Reference Library/Dev"')
    ap.add_argument("--as", dest="as_path", help="full target path to check ONE file under (renames it)")
    ap.add_argument("--dev-pr", type=int, metavar="N",
                    help="check every .md of PR #N of the dev-docs repo (use with --to)")
    ap.add_argument("--dev-repo", default=os.path.join(HERE, ".."),
                    help="dev-docs checkout for --dev-pr (default: the repo holding .kb-check)")
    ap.add_argument("--summary", action="store_true",
                    help="print blocking counts per file and per rule, not every finding")
    ap.add_argument("--no-readable", action="store_true", help="skip the readable-shape check")
    ap.add_argument("--json", action="store_true", help="print one JSON line instead of the report")
    a = ap.parse_args()

    if a.dev_pr:
        if a.files or a.as_path or not a.to:
            ap.error("--dev-pr N takes no files and needs --to")
    else:
        if not a.files:
            ap.error("give at least one file, or --dev-pr N")
        if bool(a.to) == bool(a.as_path):
            ap.error("give exactly one of --to or --as")
        if a.as_path and len(a.files) != 1:
            ap.error("--as takes exactly one file")

    shown, tmp = {}, None
    try:
        if a.dev_pr:
            tmp = tempfile.mkdtemp(prefix="kb-precheck-devpr-")
            try:
                shown, other = export_dev_pr(os.path.abspath(a.dev_repo), a.dev_pr, tmp)
            except (RuntimeError, subprocess.CalledProcessError) as e:
                print(f"error: {e}", file=sys.stderr)
                return 2
            a.files = sorted(shown)
            print(f"dev-docs PR #{a.dev_pr}: {len(shown)} .md file(s) checked, {other} other "
                  f"changed file(s) (images, Office files, moves) not checked.")
            if not shown:
                return 0
        return check(a, ap, shown)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

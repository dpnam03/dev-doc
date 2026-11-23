#!/usr/bin/env python3
"""pr-check.py — check a pull request's KB docs and post what to fix as one PR comment.

Three checks run on every PR:

  1. Foundation 0 rules (kb-check.py) on every KB doc the PR adds, changes or renames.
  2. Other docs: references in docs this PR did NOT touch that this PR breaks — a renamed file,
     a removed doc, a renumbered section that another doc cites.
  3. Readable shape (readable-check.py, from the emma-readable skill): bullet, cell and paragraph
     size, lists glued into one line, ALL-CAPS emphasis, long bold runs, history in the body.

What counts against the author. A finding is the author's when the file is new, or the finding
sits on a line the PR changed, or it is a whole-doc rule (header, filename, changelog order) whose
count went up, or a length that grew. A Section C2 version bump is compared with its previous
version, not treated as a new file. Anything else was there before the PR; it is counted, not
blamed.

Blocking. Foundation 0 findings that are the author's, and references broken in other docs, turn
the check red. Section B4 blocks once Foundation 0 states its caps in words (v2.3 does). Readable findings are advisory until their rules are written into Foundation 0
(set "readable_severity" in config.json to "blocking" to change that).

Decisions for the Owner. What the Owner confirms by approving the PR is listed at the top of the
comment, not as a finding: every declared Section B4 exception and every advisory Section A3
Owner-role finding in the docs the PR touches, the Section C2.2 bump class of each changed Live
doc (header-only, body edit, or section added or removed, against the version change), and each
changed .xlsx or .docx with its companion changelog line.

Bump class. A body edit with no version bump must be bumped, or the changelog must say why it is
cosmetic. A section added or removed with only a minor bump is a suggestion: it looks major. A
changed .xlsx or .docx whose companion changelog file gained no line must be fixed.

Usage:
    pr-check.py --base <sha> --head <sha> [--pr N --comment] [--repo .]
    pr-check.py --base origin/master --head HEAD          # run locally before opening a PR
"""
import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
MARKER = "<!-- kb-pr-check -->"
FILE_LEVEL = {"C1-missing", "C1-order", "C1-owner", "A3-owner-role", "C1-reviewed", "C1-cadence", "C1-version",
              "C1-status", "C1-folder", "C1-linkedfrom", "C3-pattern", "C3-topic", "C3-version",
              "C3-ext", "C6-archived", "B2-title", "B2-header", "B2-purpose", "B2-changelog",
              "B4-exception", "B5-mixed"}
MAX_PER_FILE = 30

READABLE_FIX = {
    "bullet": "Bullet runs over 320 characters or 2 sentences. Split it, or make it a short "
              "paragraph.",
    "marker": "Doubled bullet marker `- -`. Use one.",
    "cell": "Table cell over 600 characters. Move the detail out of the table.",
    "paragraph": "Over 4,000 characters in one block — a wall of text. Split it.",
    "br": "`<br>` inside text. Many viewers drop it. Use a list or separate rows.",
    "options": "An (a) … (b) run inside one cell. Use a list or separate rows.",
    "words": "Hedge phrase. State the rule, or drop it.",
    "history": "Version note, date or marker glyph in the body. History belongs in the changelog.",
    "caps": "ALL-CAPS word that is not an acronym. Write it in normal case.",
    "bold": "Bold run over 6 words. Bold marks a label, not a sentence (Foundation 0 Section B3).",
    "clause": "Bullet starts with (i) or (a). State the item plainly.",
    "quote-join": "Two quote lines with no blank `>` line between. They show as one paragraph.",
    "list-line": "A list written on one line. Put each item on its own line.",
    "prose-join": "Two text lines with no blank line between. Markdown joins them into one "
                  "paragraph. Add a blank line, or join them.",
    "budget": "Section over its word budget.",
}


def load_kb_check():
    spec = importlib.util.spec_from_file_location("kb_check", os.path.join(HERE, "kb-check.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


KB = load_kb_check()


def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def changed_files(repo, base, head):
    """[(status, path, old_path)] for KB files the PR touches."""
    out = []
    raw = git(repo, "diff", "--name-status", "--find-renames", "-z", f"{base}...{head}")
    parts = raw.split("\0")
    i = 0
    while i < len(parts) and parts[i]:
        st = parts[i]
        if st.startswith(("R", "C")):
            old, new = parts[i + 1], parts[i + 2]
            out.append((st[0], new, old))
            i += 3
        else:
            out.append((st[0], parts[i + 1], None))
            i += 2
    return [(s, p, o) for s, p, o in out if is_kb_path(p) or (o and is_kb_path(o))]


def is_kb_path(p):
    return p.split("/")[0] in KB.LAYER_FOLDERS or p.startswith("KB_Plan")


VERSION_RE = re.compile(r"_v\d+\.\d+(?=\.[A-Za-z0-9]+$)")


def previous_version(repo, base, path):
    """The file a new file is a version bump of, or None.

    Section C2 makes every content edit a version bump: a new file with the bumped version in
    its name, and the old file moved to 4. Archive/. To git that is a new file, so without this
    every bump would blame its author for the whole doc. The previous version is the file at the
    base in the same folder whose name differs only in the version.
    """
    folder, name = os.path.split(path)
    stem = VERSION_RE.sub("", name)
    if stem == name:
        return None
    listing = git(repo, "ls-tree", "--name-only", f"{base}:{folder}" if folder else base,
                  check=False)
    cands = []
    for n in listing.split("\n"):
        m = re.search(r"_v(\d+)\.(\d+)\.[A-Za-z0-9]+$", n)
        if n and n != name and m and VERSION_RE.sub("", n) == stem:
            cands.append(((int(m.group(1)), int(m.group(2))), n))
    if not cands:
        return None
    best = max(cands)[1]
    return os.path.join(folder, best) if folder else best


def changed_lines(repo, base, head, path, old=None):
    """Line numbers in the head version that the PR added or changed.

    `old` is the file's path at the base when it differs (a rename or a version bump). The two
    versions are compared directly, because a path-filtered diff shows a renamed file as new.
    """
    if old and old != path:
        raw = git(repo, "diff", "-U0", f"{base}:{old}", f"{head}:{path}", check=False)
    else:
        raw = git(repo, "diff", "-U0", f"{base}...{head}", "--", path, check=False)
    lines = set()
    for m in re.finditer(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", raw, re.M):
        start, n = int(m.group(1)), int(m.group(2) or 1)
        lines.update(range(start, start + n))
    return lines


def show(repo, ref, path):
    r = subprocess.run(["git", "-C", repo, "show", f"{ref}:{path}"], capture_output=True)
    if r.returncode != 0:
        return None
    return r.stdout.decode("utf-8", errors="replace")


def export_tree(repo, ref):
    d = tempfile.mkdtemp(prefix="kb-base-")
    a = subprocess.run(["git", "-C", repo, "archive", ref], capture_output=True)
    if a.returncode != 0:
        raise RuntimeError(a.stderr.decode())
    subprocess.run(["tar", "-x", "-C", d], input=a.stdout, check=True)
    return d


def run_kb(repo_dir, config, rules, relpaths, text_for=None, decisions=None):
    c = KB.Check(repo_dir, config, rules)
    for rel in relpaths:
        text = text_for(rel) if text_for else None
        if text_for and text is None:
            continue
        if text is None and not os.path.exists(os.path.join(repo_dir, rel)):
            continue
        c.run(rel, text=text)
    if decisions is not None:
        decisions += c.decisions
    return c.findings


# ---------------------------------------------------------------- readable layer

def readable(repo, rel, text, config):
    """Run the emma-readable shape check on one doc. The header table and changelog are blanked
    first (keeping line numbers): the header's `Last reviewed | date` row is a required C1 field,
    not history in the body, and the changelog is where history belongs. For the same reason a
    standalone changelog file skips the history rule."""
    lines = text.split("\n")
    _, start, end = KB.parse_header(lines)
    if start is not None:
        for i in range(max(0, start - 1), end + 1):
            lines[i] = ""
    for i, ln in enumerate(lines):
        h = KB.HEADING_RE.match(ln)
        if h and KB.demark(h.group(2)).lower() in ("changelog", "change log"):
            for j in range(i, len(lines)):
                lines[j] = ""
            break
    tmp = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
    tmp.write("\n".join(lines))
    tmp.close()
    cmd = [sys.executable, os.path.join(HERE, "readable-check.py"), tmp.name, "--json",
           "--banned", os.path.join(HERE, "readable-banned.txt")]
    allow = config.get("readable_allow_caps", [])
    if allow:
        cmd += ["--allow-caps", ",".join(allow)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    os.unlink(tmp.name)
    try:
        res = json.loads(r.stdout.strip().split("\n")[-1])
    except (ValueError, IndexError):
        return [], {}
    drop = set(config.get("readable_skip_rules", ["sentence"]))
    if KB.is_changelog_file(rel):
        drop.add("history")  # a changelog file is history by design
    found = [f for f in res.get("findings", []) if f.get("rule") not in drop]
    counts = {k: v for k, v in res.get("perRule", {}).items() if k not in drop}
    return found, counts


def length_key(f):
    """Which span a B4 finding measures: one OM section by title, or the whole body."""
    m = re.match(r"Section `(.+?)` runs", f["message"])
    return m.group(1) if m else "<body>"


def length_words(f):
    m = re.search(r"runs (\d+) words", f["message"])
    return int(m.group(1)) if m else 0


# ---------------------------------------------------------------- bump class (C2.2)

BINARY_EXT = (".xlsx", ".docx")
SECTION_NO_RE = re.compile(r"^(?:Part\s+[A-Z]\b\s*[—–:-]?\s*|"
                           r"(?:(?:Stage|Step|Phase|Section)\s+)?[A-Z]?\d+(?:\.\d+)*\.?\s+)")
COMPANION_RE = re.compile(r"^(.+)-changelog_v\d+\.\d+\.md$", re.I)


def finding(config, path, line, rule_id, message, fix):
    """A finding in kb-check's shape, for rules only a PR diff can test."""
    part, rule, fails = KB.RULES[rule_id]
    sev = config.get("severity", {}).get(rule_id) or KB.DEFAULT_SEVERITY.get(rule_id, "blocking")
    if KB.kind_of(path) == "plan" and sev == "blocking":
        sev = "advisory"  # README: plan files are not KB docs
    return {"file": path, "line": line, "id": rule_id, "part": part, "rule": rule,
            "fails": fails, "message": message, "fix": fix, "severity": sev}


def split_doc(text):
    """(header, body, changelog) of a doc, each as (line number, line) pairs. The header is the
    title and the 7-field table; the changelog runs from the last Changelog heading to the end."""
    lines = text.split("\n")
    _, _, end = KB.parse_header(lines)
    first = (end + 1) if end is not None else 0
    cl = len(lines)
    for i in range(first, len(lines)):
        h = KB.HEADING_RE.match(lines[i])
        if h and KB.demark(h.group(2)).lower() in ("changelog", "change log"):
            cl = i
    num = list(enumerate(lines, 1))
    return num[:first], num[first:cl], num[cl:]


def norm(part):
    """The lines of a part with whitespace collapsed and blank lines dropped."""
    return [" ".join(ln.split()) for _, ln in part if ln.strip()]


def sections(body):
    """[(number, title key, line, heading as written)] for the body's headings below the title."""
    out = []
    for n, ln in body:
        h = KB.HEADING_RE.match(ln)
        if h and len(h.group(1)) > 1:
            text = KB.demark(h.group(2))
            m = SECTION_NO_RE.match(text)
            num = " ".join(m.group(0).split()).rstrip(".:—–- ") if m else None
            title = " ".join(text[m.end() if m else 0:].split())
            out.append((num, title.lower(), n, " ".join(text.split())))
    return out


def unmatched(old, new):
    """(added, removed) sections. A section matches by title first, so a renumbered section is
    not new; then, among the rest, by number, so a renamed section is not new either. A section
    inserted ahead of others that were renumbered still counts as added."""
    old_left, added = list(old), []
    for s in new:
        hit = next((o for o in old_left if o[1] == s[1]), None)
        if hit:
            old_left.remove(hit)
        else:
            added.append(s)
    for s in list(added):
        hit = next((o for o in old_left if s[0] and o[0] == s[0]), None)
        if hit:
            old_left.remove(hit)
            added.remove(s)
    return added, old_left


def version_of(text, path):
    """(major, minor) from the header's Version field, or from the filename."""
    v = KB.parse_header(text.split("\n"))[0].get("Version", "")
    m = re.match(r"v(\d+)\.(\d+)$", v.strip()) or re.search(r"_v(\d+)\.(\d+)\.[A-Za-z0-9]+$", path)
    return (int(m.group(1)), int(m.group(2))) if m else None


def vstr(v):
    return f"v{v[0]}.{v[1]}" if v else "no version"


def classify_doc(config, path, old, new):
    """Section C2.2 on one changed Live doc: what the diff looks like, and what that needs.
    Returns (findings, decision message)."""
    oh, ob, oc = split_doc(old)
    nh, nb, nc = split_doc(new)
    ov, nv = version_of(old, path), version_of(new, path)
    bump = ("none" if ov == nv or not (ov and nv) else
            "major" if nv[0] > ov[0] else "minor" if nv > ov else "none")
    bumped = f"{bump} bump {vstr(ov)} to {vstr(nv)}" if bump != "none" else f"no bump ({vstr(nv)})"
    if norm(ob) == norm(nb):
        if norm(oh) == norm(nh) and norm(oc) == norm(nc):
            return [], f"Whitespace only: no bump needed. {bumped.capitalize()}."
        what = "Header only" if norm(oc) == norm(nc) else "Header or changelog only"
        return [], f"{what}, no content change: no bump needed. {bumped.capitalize()}."

    added, removed = unmatched(sections(ob), sections(nb))
    old_body = set(norm(ob))
    first = next((n for n, ln in nb if ln.strip() and " ".join(ln.split()) not in old_body),
                 nb[0][0] if nb else None)
    fs = []
    if added or removed:
        moved = "; ".join(x for x in (
            "added: " + ", ".join(f"`{t[3]}`" for t in added) if added else "",
            "removed: " + ", ".join(f"`{t[3]}`" for t in removed) if removed else "") if x)
        kind = f"Section added or removed ({moved})"
        line = added[0][2] if added else first
    else:
        kind, line = "Body edit", first

    if bump == "none":
        old_cl = set(norm(oc))
        rows = [ln for _, ln in nc if ln.strip().startswith("|")
                and " ".join(ln.split()) not in old_cl
                and KB.DATE_RE.match(ln.strip().strip("|").split("|")[0].strip())]
        if rows:
            cells = [c.strip() for c in rows[0].strip().strip("|").split("|")]
            said = cells[2] if len(cells) > 2 else rows[0].strip()
            return fs, (f"{kind}, {bumped}. The changelog says it is cosmetic: \"{said}\". "
                        f"Approving confirms it needs no bump.")
        fs.append(finding(config, path, line, "C2-bump",
                          "C2.2: content edit needs a minor bump, or say in the changelog why it "
                          "is cosmetic",
                          (f"Bump to v{nv[0]}.{nv[1] + 1}: a new file, the old one moved to "
                           f"`4. Archive/` (Section C2)." if nv else "Bump the minor version.")
                          + " If it is a typo, formatting or link fix (Section C4), add a "
                          "changelog row at this version saying so."))
        return fs, f"{kind}, {bumped}: needs a minor bump or a cosmetic changelog row (below)."
    if (added or removed) and bump == "minor":
        fs.append(finding(config, path, line, "C2-major",
                          f"C2.2: looks major. {kind} with only a {bumped}.",
                          f"Bump to v{nv[0] + 1}.0 (Section C4), or keep the minor bump if the "
                          f"Owner agrees it is not a new section."))
        return fs, f"{kind}, {bumped}: looks major (Section C4). Approving confirms minor."
    return fs, f"{kind}, {bumped}: matches Section C2.2."


def companion_of(repo, head, path):
    """The changelog file that records a workbook's or Word file's changes: in the same folder,
    named for the longest stem the binary's name starts with, such as
    Ref_BA_presales-questionnaire-changelog_v1.0.md for Ref_BA_presales-questionnaire-template."""
    folder, name = os.path.split(path)
    stem = VERSION_RE.sub("", name).rsplit(".", 1)[0]
    listing = git(repo, "ls-tree", "--name-only", f"{head}:{folder}" if folder else head,
                  check=False)
    best = None
    for n in listing.split("\n"):
        m = COMPANION_RE.match(n)
        if m and stem.startswith(m.group(1)) and (not best or len(m.group(1)) > len(best[0])):
            best = (m.group(1), n)
    return os.path.join(folder, best[1]) if best else None


def companion_lines(repo, base, head, comp, old_of):
    """Text lines the PR added to a companion changelog file, the ones under a version heading
    such as `v1.1 — 2026-10-11` first. Headings and table rules are not lines of their own."""
    was = show(repo, base, old_of.get(comp, comp)) or ""
    had = {" ".join(ln.split()) for ln in was.split("\n")}
    under, other, in_version = [], [], False
    for ln in (show(repo, head, comp) or "").split("\n"):
        h = KB.HEADING_RE.match(ln)
        if h:
            in_version = bool(KB.VERSION_HEADING_RE.match(KB.demark(h.group(2))))
            continue
        if not ln.strip() or set(ln.strip()) <= set("|:- ") or " ".join(ln.split()) in had:
            continue
        (under if in_version else other).append(ln.strip())
    return under + other


def bump_checks(repo, base, head, files, old_of, config):
    """C2.2 bump class for each changed Live doc, and a changelog line for each changed binary.
    Returns (findings, decisions); every decision names what the Owner confirms by approving."""
    findings, decisions = [], []
    skip = config.get("templates", []) + config.get("ignore", [])
    for s, path, _ in files:
        if s not in ("M", "R", "B") or KB.kind_of(path) == "archive" \
                or os.path.basename(path) in skip:
            continue
        if path.lower().endswith(BINARY_EXT):
            comp = companion_of(repo, head, path)
            name = os.path.basename(path)
            new = companion_lines(repo, base, head, comp, old_of) if comp else []
            if comp and new:
                decisions.append(dict(finding(config, path, None, "C2-binary", "", ""), message=(
                    f"`{name}` changed. Its changelog `{os.path.basename(comp)}` adds: "
                    f"\"{new[0][:160]}\". Approving confirms the line matches the "
                    f"change.")))
                continue
            where = (f"its changelog `{os.path.basename(comp)}` gained no line" if comp
                     else "it has no companion changelog file in its folder")
            findings.append(finding(
                config, path, None, "C2-binary", f"`{name}` changed and {where}.",
                f"Add a line for this change to `{os.path.basename(comp)}`, even when it is "
                f"cosmetic, so the Owner can confirm it." if comp else
                f"Add a changelog file beside it, named `{VERSION_RE.sub('', name).rsplit('.', 1)[0]}"
                f"-changelog_v1.0.md`, with a line for this change."))
            decisions.append(dict(findings[-1], message=f"`{name}` changed with no changelog "
                                  f"line (must fix below)."))
            continue
        if not path.endswith(".md") or KB.kind_of(path) != "doc" or KB.is_changelog_file(path):
            continue  # a changelog file is the history itself; its workbook is judged above
        old, new = show(repo, base, old_of.get(path, path)), show(repo, head, path)
        if old is None or new is None:
            continue
        if KB.parse_header(new.split("\n"))[0].get("Status", "").strip() != "Live":
            continue
        fs, msg = classify_doc(config, path, old, new)
        findings += fs
        decisions.append(dict(finding(config, path, fs[0]["line"] if fs else None,
                                      "C2-bump", msg, ""), id="C2.2-class"))
    return findings, decisions


# ---------------------------------------------------------------- the PR

def check_pr(repo, base, head):
    # Compare against where the branch started, not the base branch's tip. If master moved on
    # after the PR opened, the tip carries other people's changes, and the author would be
    # blamed for them.
    base = git(repo, "merge-base", base, head).strip()
    config = KB.load_config(repo, None)
    rules = KB.load_rules_from_foundation(repo)
    files = changed_files(repo, base, head)
    # A new file that is a version bump is compared with its previous version (status "B").
    files = [("B", p, previous_version(repo, base, p))
             if s == "A" and KB.kind_of(p) != "archive" and previous_version(repo, base, p)
             else (s, p, o) for s, p, o in files]
    touched = {p for _, p, _ in files} | {o for _, _, o in files if o}
    head_paths = [p for s, p, _ in files if s != "D"]

    head_decisions = []
    head_findings = run_kb(repo, config, rules, head_paths, decisions=head_decisions)
    base_tree = export_tree(repo, base)
    try:
        base_rules = KB.load_rules_from_foundation(base_tree) or rules
        old_of = {p: (o or p) for s, p, o in files if s in ("M", "R", "B")}

        def base_text(rel):
            return show(repo, base, old_of[rel]) if rel in old_of else None

        base_findings = run_kb(base_tree, config, base_rules, list(old_of), text_for=base_text)

        # References in docs this PR did not touch, broken by this PR.
        others = [p for p in KB.kb_files(repo) if p not in touched]
        xref_ids = ("XREF-missing", "XREF-section", "C1-linkedfrom")

        def key(f):
            return (f["file"], f["id"], f["message"])

        before = {key(f) for f in run_kb(base_tree, config, base_rules, others)
                  if f["id"] in xref_ids}
        broken = [f for f in run_kb(repo, config, rules, others)
                  if f["id"] in xref_ids and f["severity"] == "blocking" and key(f) not in before]
    finally:
        shutil.rmtree(base_tree, ignore_errors=True)

    status = {p: s for s, p, _ in files}
    yours, earlier = [], []
    for path in head_paths:
        fs = [f for f in head_findings if f["file"] == path]
        if status[path] == "A":
            yours += fs
            continue
        lines = changed_lines(repo, base, head, path, old_of.get(path))
        base_counts = {}
        for f in base_findings:
            if f["file"] == path:
                base_counts[f["id"]] = base_counts.get(f["id"], 0) + 1
        head_counts = {}
        for f in fs:
            head_counts[f["id"]] = head_counts.get(f["id"], 0) + 1
        base_len = {length_key(f): length_words(f) for f in base_findings
                    if f["file"] == path and f["id"].startswith("B4")}
        for f in fs:
            mine = f["line"] in lines
            if f["id"].startswith("B4"):
                # Length got worse: a section newly over its cap, or one already over that grew.
                was = base_len.get(length_key(f))
                mine = was is None or length_words(f) > was
                if mine and was is not None:
                    f = dict(f, message=f"{f['message']} It grew from {was} words in this PR.")
            elif f["id"] in FILE_LEVEL:
                mine = head_counts[f["id"]] > base_counts.get(f["id"], 0)
                if status[path] == "R":
                    # A rename chose this filename. A move into 4. Archive/ only added the C6
                    # suffix to the old name, so only C6 is the author's there. A C2 bump ("B")
                    # keeps the old name, so its filename findings are inherited.
                    if KB.kind_of(path) == "archive":
                        mine = mine if f["id"].startswith("C3") else f["id"].startswith("C6")
                    elif f["id"].startswith(("C3", "C6")):
                        mine = True
            (yours if mine else earlier).append(f)

    # Decisions for the Owner: each declared B4 exception and each advisory A3 Owner-role finding
    # in a touched doc, the author's or not. The Owner confirms them by approving. An A3 finding
    # the config turns to blocking stays a must-fix as well.
    owner_role = [f for f in head_findings if f["id"] == "A3-owner-role"]
    decisions = head_decisions + owner_role
    yours = [f for f in yours if f["id"] != "A3-owner-role" or f["severity"] == "blocking"]
    earlier = [f for f in earlier if f["id"] != "A3-owner-role"]

    # Section C2.2 from the diff: the bump class of each changed Live doc, and a changelog line
    # for each changed workbook or Word file. Each is a decision for the Owner; what the diff
    # cannot accept on its own is also the author's finding.
    bump_findings, bump_decisions = bump_checks(repo, base, head, files, old_of, config)
    yours += bump_findings
    decisions += bump_decisions

    # Readable layer, on the same changed docs.
    r_yours, r_earlier = [], 0
    for path in head_paths:
        if not path.endswith(".md") or KB.kind_of(path) == "archive":
            continue
        if os.path.basename(path) in config.get("templates", []) + config.get("ignore", []):
            continue
        text = open(os.path.join(repo, path), encoding="utf-8", errors="replace").read()
        found, counts = readable(repo, path, text, config)
        if status[path] == "A":
            r_yours += [dict(f, file=path) for f in found]
            continue
        lines = changed_lines(repo, base, head, path, old_of.get(path))
        for f in found:
            if f.get("line") in lines:
                r_yours.append(dict(f, file=path))
            else:
                r_earlier += 1

    rsev = config.get("readable_severity", "advisory")
    blocking = [f for f in yours if f["severity"] == "blocking"] + broken
    if rsev == "blocking":
        blocking += r_yours
    return {
        "files": files, "yours": yours, "earlier": earlier, "broken": broken,
        "decisions": decisions,
        "readable": r_yours, "readable_earlier": r_earlier, "readable_severity": rsev,
        "rules_source": (rules or {}).get("source"), "pass": not blocking,
        "blocking": len(blocking),
    }


# ---------------------------------------------------------------- the comment

def md_escape(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


def render(res, server=None, repo_slug=None, head=None):
    out = [MARKER]
    yours_block = [f for f in res["yours"] if f["severity"] == "blocking"]
    yours_note = [f for f in res["yours"] if f["severity"] != "blocking"]
    n_files = len([1 for s, _, _ in res["files"] if s != "D"])

    def link(path, line):
        if server and repo_slug and head and line:
            from urllib.parse import quote
            return f"[{line}]({server}/{repo_slug}/src/commit/{head}/{quote(path)}#L{line})"
        return str(line or "—")

    out += decisions_block(res.get("decisions", []), link)

    if res["pass"] and not yours_note and not res["readable"]:
        out.append(f"**KB check: pass.** {n_files} doc{'s' if n_files != 1 else ''} checked "
                   f"against Foundation 0. Nothing to fix.")
        if res["earlier"] or res["readable_earlier"]:
            out.append("")
            out.append(f"{len(res['earlier']) + res['readable_earlier']} findings sit on lines "
                       f"this PR did not change. They were there before, so they are not yours "
                       f"to fix here.")
        out.append(footer(res))
        return "\n".join(out)

    head_line = ("**KB check: fix before merge.**" if not res["pass"]
                 else "**KB check: pass, with notes.**")
    out.append(f"{head_line} {res['blocking']} must be fixed"
               + (f", {len(yours_note) + len(res['readable'])} are suggestions." if
                  (yours_note or res["readable"]) else "."))
    out.append("")
    out.append("Each row names the line, the rule it breaks, and the fix. Push a new commit and "
               "this comment updates itself.")

    if yours_block:
        out.append("")
        out.append("### Must fix — Foundation 0")
        out += table(yours_block, link)

    if res["broken"]:
        out.append("")
        out.append("### Must fix — this PR breaks other docs")
        out.append("")
        out.append("These docs are not in this PR, but they cite something this PR renames, "
                   "removes or renumbers.")
        out += table(res["broken"], link)

    if yours_note:
        out.append("")
        out.append("### Suggestions — Foundation 0")
        out += table(yours_note, link)

    if res["readable"]:
        out.append("")
        word = "Must fix" if res["readable_severity"] == "blocking" else "Suggestions"
        out.append(f"### {word} — readable shape")
        out.append("")
        out.append("From the emma-readable standard. These rules are not in Foundation 0 yet, "
                   "so they do not block the merge.") if res["readable_severity"] != "blocking" \
            else None
        rows = [{"file": f["file"], "line": f.get("line"), "part": f.get("rule"),
                 "message": f.get("what", ""), "fix": READABLE_FIX.get(f.get("rule"), "")}
                for f in res["readable"]]
        out += table(rows, link)

    if res["earlier"] or res["readable_earlier"]:
        out.append("")
        out.append(f"{len(res['earlier']) + res['readable_earlier']} more findings sit on lines "
                   f"this PR did not change. They were there before, so they are not yours to fix "
                   f"here.")
    out.append(footer(res))
    return "\n".join(o for o in out if o is not None)


DECISION_LABEL = {"B4-exception": "B4 exception declared", "A3-owner-role": "Owner role (A3)",
                  "C2.2-class": "Bump class (C2.2)", "C2-binary": "Binary change (C2)"}


def decisions_block(decisions, link):
    """What the Owner confirms by approving: declared B4 exceptions, A3 Owner-role findings,
    the bump class of each changed Live doc, and each changed binary."""
    if not decisions:
        return []
    rows = ["### Decisions for the Owner", "",
            "Approving this PR confirms these. To reject one, request changes and say which.", "",
            "| File | Line | Decision | What the Owner confirms |",
            "| :--- | :--- | :--- | :--- |"]
    for f in sorted(decisions, key=lambda x: (x["file"], x["id"], x.get("line") or 0)):
        rows.append(f"| {md_escape(os.path.basename(f['file']))} | {link(f['file'], f.get('line'))} "
                    f"| {DECISION_LABEL.get(f['id'], f['id'])} | {md_escape(f['message'])} |")
    return rows + ["", "---", ""]


def table(findings, link):
    rows = []
    by_file = {}
    for f in findings:
        by_file.setdefault(f["file"], []).append(f)
    for path in sorted(by_file):
        fs = sorted(by_file[path], key=lambda x: (x.get("line") or 0))
        rows.append("")
        rows.append(f"**{os.path.basename(path)}**")
        rows.append("")
        rows.append("| Line | Rule | What is wrong | Fix |")
        rows.append("| :--- | :--- | :--- | :--- |")
        for f in fs[:MAX_PER_FILE]:
            rows.append(f"| {link(path, f.get('line'))} | {md_escape(f.get('part', ''))} | "
                        f"{md_escape(f.get('message', ''))} | {md_escape(f.get('fix', ''))} |")
        if len(fs) > MAX_PER_FILE:
            rows.append(f"| | | and {len(fs) - MAX_PER_FILE} more of the same kind | "
                        f"Run the check locally to see all. |")
    return rows


def footer(res):
    src = res.get("rules_source") or "Foundation 0"
    return ("\n---\n"
            f"<sub>Rules read from `{src}` in this branch. To run the same check before you push: "
            "`python3 .kb-ci/pr-check.py --base origin/master --head HEAD`</sub>")


# ---------------------------------------------------------------- gitea

def api(method, url, token, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"token {token}", "Content-Type": "application/json",
        "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode()
        return json.loads(raw) if raw else None


def post_comment(server, slug, pr, token, body):
    base = f"{server.rstrip('/')}/api/v1/repos/{slug}"
    existing = None
    page = 1
    while True:
        cs = api("GET", f"{base}/issues/{pr}/comments?page={page}&limit=50", token) or []
        for c in cs:
            if MARKER in (c.get("body") or ""):
                existing = c
        if len(cs) < 50:
            break
        page += 1
    if existing:
        api("PATCH", f"{base}/issues/comments/{existing['id']}", token, {"body": body})
        return f"updated comment {existing['id']}"
    c = api("POST", f"{base}/issues/{pr}/comments", token, {"body": body})
    return f"posted comment {c.get('id') if c else '?'}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", required=True)
    ap.add_argument("--pr", type=int)
    ap.add_argument("--comment", action="store_true", help="post or update the PR comment")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    repo = os.path.abspath(a.repo)

    res = check_pr(repo, a.base, a.head)
    server = os.environ.get("GITHUB_SERVER_URL", "").rstrip("/")
    slug = os.environ.get("GITHUB_REPOSITORY", "")
    head_sha = git(repo, "rev-parse", a.head).strip()
    body = render(res, server or None, slug or None, head_sha)

    print(body)
    print(json.dumps({"pass": res["pass"], "blocking": res["blocking"],
                      "yours": len(res["yours"]), "broken": len(res["broken"]),
                      "yoursIds": sorted(f["id"] for f in res["yours"]),
                      "readable": len(res["readable"]), "earlier": len(res["earlier"]),
                      "decisions": len(res["decisions"]),
                      "decisionIds": sorted(f["id"] for f in res["decisions"])}))

    if a.comment:
        token = os.environ.get("KB_BOT_TOKEN") or os.environ.get("GITEA_TOKEN") \
            or os.environ.get("GITHUB_TOKEN")
        if not (token and server and slug and a.pr):
            print("comment skipped: token, server, repository or PR number missing",
                  file=sys.stderr)
        else:
            try:
                print(post_comment(server, slug, a.pr, token, body), file=sys.stderr)
            except urllib.error.HTTPError as e:
                # A fork's token cannot write. The check result still stands; the log has it.
                print(f"comment failed: HTTP {e.code} {e.reason}. The report is above.",
                      file=sys.stderr)
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())

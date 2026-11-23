#!/usr/bin/env python3
"""kb-check.py — check a KB document against Foundation 0 — How this KB Works.

Every check below states a rule from Foundation 0 and the condition that fails it, per Section B6.
No check invents a rule. Where Foundation 0 is silent, the check is advisory, never blocking.

The rules live in Foundation 0 in this repository, not in this file. When Foundation 0 changes,
`--rules` re-reads the parts that are machine-readable from it (the Review cadence values, the
Status values, the Layer and Function name lists, the banned and hedging word lists), so the
checker cannot drift from the document the way an embedded ruleset does.

Usage:
    kb-check.py <file.md> [<file.md> ...] [--config .kb-ci/config.json] [--repo .] [--json]
    kb-check.py --all [--repo .]
    kb-check.py --selftest

Output: a plain table, then ONE JSON line {"pass", "blocking", "advisory", "findings": [...]}.
Exit 0 when no blocking finding, 1 otherwise.
"""
import argparse
import datetime
import json
import os
import re
import sys

# ---------------------------------------------------------------- rule text

RULES = {
    "C1-missing":    ("C1", "Every KB doc starts with a 7-field table at the top.",
                      "A required field is absent."),
    "C1-order":      ("C1", "The header table carries the 7 fields in the order Foundation 0 lists.",
                      "A field is out of order."),
    "C1-owner":      ("C1/A3", "Owner is one named human, rendered as Name — Role.",
                      "Owner names a role alone, a team, or carries no role."),
    "A3-owner-role": ("A3", "The Owner's role is the one A3 names for the doc's folder: DiM/DM for "
                      "Foundation, Shared and Archive; the Function Lead for a function folder.",
                      "The role after the em-dash is not that folder's approver."),
    "C1-reviewed":   ("C1", "Last reviewed is YYYY-MM-DD.",
                      "The value is not a date in that form."),
    "C1-cadence":    ("C1", "Review cadence is one of the permitted values.",
                      "The value is outside that list."),
    "C1-version":    ("C1", "Version is vX.Y.",
                      "The value carries anything else, such as a status word."),
    "C1-status":     ("C1", "Status is Draft, Live or Archive.",
                      "The value is outside that list."),
    "C1-folder":     ("C1", "Status must match the folder the doc lives in.",
                      "A Live doc sits in Archive, an Archive doc sits in a KB layer, or a Draft "
                      "sits inside a KB folder at all (C2 puts drafts outside KB folders)."),
    "C1-linkedfrom": ("C1", "Linked from names inbound KB docs.",
                      "A named doc does not exist in this repository."),
    "C3-pattern":    ("C3.1", "Filename is [Layer]_[Function]_[Section]_[Topic]_v[Version].[ext].",
                      "A slot is missing or malformed."),
    "C3-topic":      ("C3.1", "Topic is a kebab-case slug: lowercase, hyphens, no spaces, "
                      "no underscores, no capitals.",
                      "The topic slot carries a capital, a space or an underscore."),
    "C3-version":    ("C3.1", "Version uses a dot, not an underscore.",
                      "The version slot is not vX.Y."),
    "C3-ext":        ("C3.1", "Extension is one of md, docx, xlsx, pdf, html.",
                      "The extension is outside that list."),
    "C6-archived":   ("C6", "An archived file carries the suffix _ARCHIVED_YYYY-MM-DD.",
                      "A file in 4. Archive/ has no such suffix."),
    "B1-sentence":   ("B1", "Maximum sentence length is 28 words.",
                      "A sentence runs over 28 words."),
    "B1-paragraph":  ("B1", "One idea per paragraph. Maximum 5 sentences per paragraph.",
                      "A paragraph runs over 5 sentences."),
    "B1-hedging":    ("B1", "No hedging words: typically, generally, usually, often, may, might, "
                      "could. Use must, is, does, will.",
                      "A hedging word appears in the body."),
    "B1-banned":     ("B1", "No corporate-speak. Banned: leverage, synergy, holistic, robust, "
                      "best-in-class, seamless, empower, utilize.",
                      "A banned word appears in the body."),
    "B2-title":      ("B2", "Part 1 is the title, one line.",
                      "The doc opens with something other than a single top-level heading."),
    "B2-header":     ("B2", "Part 2 is the header table.",
                      "The 7-field table is not the first thing after the title."),
    "B2-purpose":    ("B2", "Part 3 is a purpose paragraph of 2 to 4 sentences.",
                      "The paragraph after the header table runs outside 2 to 4 sentences."),
    "B2-numbered":   ("B2", "Body sections are numbered 1, 2, 3, with subsections 1.1, 1.2.",
                      "A body section heading carries no number."),
    "B2-depth":      ("B2", "Numbered sections go no deeper than three levels.",
                      "A heading number carries four or more parts."),
    "B2-changelog":  ("B2/C5", "The changelog is a table at the bottom, newest entry on top.",
                      "The changelog is absent, is not last, or its dates do not descend."),
    "B3-section":    ("B3", "Refer by section number or doc name. Do not use the symbol §.",
                      "The symbol § appears."),
    "B3-bare-url":   ("B3", "Never paste a bare URL without the doc name.",
                      "A raw http or https URL appears outside a Markdown link."),
    "B4-exception":  ("B4", "A doc over its cap declares the exception under Purpose: the cap it "
                      "exceeds, which exception applies, and the sections that carry the data.",
                      "A doc over its cap carries no such declaration."),
    "C2-bump":       ("C2.2", "A content edit bumps the minor version. A typo, formatting or link "
                      "fix needs no bump (C4).",
                      "The body changed, the version did not, and the changelog says nothing."),
    "C2-major":      ("C2.2", "A new or removed section bumps the major version (C4).",
                      "A section was added or removed with only a minor bump."),
    "C2-binary":     ("C2/C5", "A workbook or Word file records each change in its companion "
                      "changelog file.",
                      "The file changed and its changelog file gained no line."),
    "B5-mixed":      ("B5", "Do not mix English and Vietnamese in the same doc.",
                      "Vietnamese-only characters appear in an English doc."),
    "XREF-missing":  ("B3", "A cross-reference names a doc that the reader can find.",
                      "The named doc does not exist in this repository."),
    "XREF-section":  ("B3", "Refer by section number: the section must exist in the named doc.",
                      "The named doc has no section with that number."),
}

# Values Foundation 0 permits. Read from the live Foundation 0 when --rules finds it.
CADENCES = ["Monthly", "Quarterly", "Semi-annual", "Annual", "On change"]
STATUSES = ["Draft", "Live", "Archive"]
LAYERS = ["Foundation", "OM", "Ref", "Onboard", "Archive"]
FUNCTIONS = ["PM", "Dev", "QC", "BA", "CRO", "Sales", "Mkt", "Tech", "Shared"]
EXTENSIONS = ["md", "docx", "xlsx", "pdf", "html"]
HEADER_FIELDS = ["Owner", "Audience", "Last reviewed", "Review cadence", "Version",
                 "Linked from", "Status"]
HEDGING = ["typically", "generally", "usually", "often", "may", "might", "could"]
BANNED = ["leverage", "synergy", "holistic", "robust", "best-in-class", "seamless", "empower",
          "utilize", "utilise", "utilization", "utilisation"]

# The same word in another spelling or form. Not a new rule: Foundation 0 bans the word.
SPELLING_VARIANTS = {"utilize": ["utilise", "utilization", "utilisation", "utilizes", "utilised",
                                 "utilized"],
                     "leverage": ["leverages", "leveraged", "leveraging"],
                     "empower": ["empowers", "empowered", "empowering"]}

SENTENCE_MAX = 28
PARAGRAPH_MAX_SENTENCES = 5
# Rules that advise until the owner sets them to blocking in config.json "severity". A3 is
# advisory first (PLAN D1): the BA headers name a PIC until a human sets the BA Lead (T4b).
# C2-major only looks major from the diff; the Owner decides (PLAN Section 3.1).
DEFAULT_SEVERITY = {"A3-owner-role": "advisory", "C2-major": "advisory"}

# Foundation 0 A3: the Owner by doc location. Read from the live Foundation 0 when it is found.
A3_OWNERS = {
    "Foundation": "DiM/DM",
    "Function Operating Manual": "Relevant Function Lead",
    "Reference Library / Shared": "DiM/DM",
    "Reference Library / per-function": "Relevant Function Lead",
    "Reference Library / Tech": "Architect Lead",
    "Onboarding Hub": "Relevant Function Lead",
    "Archive": "DiM/DM",
}

# Foundation 0 B4 states the caps in pages. A page is not countable in Markdown, so the config
# carries the word equivalent. Until the owner sets it, B4 findings are advisory.
DEFAULT_CAPS = {"Foundation": 3000, "OM": 1500, "Ref": 2000}

VIET_RE = re.compile(
    "[ăâđêôơưĂÂĐÊÔƠƯ]|[àáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữự"
    "ỳýỷỹỵÀÁẢÃẠẰẮẲẴẶẦẤẨẪẬÈÉẺẼẸỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌỒỐỔỖỘỜỚỞỠỢÙÚỦŨỤỪỨỬỮỰỲÝỶỸỴ]")
BARE_URL_RE = re.compile(r"(?<![\(<\[])\bhttps?://[^\s\)\]<>|]+")
LINK_TEXT_URL_RE = re.compile(r"\[(https?://[^\]]+)\]\(")
TOKEN_REF_RE = re.compile(r"\b((?:Foundation|OM|Ref|Onboard)_[A-Za-z0-9_.\-]*?_v\d+\.\d+)")
PROSE_REF_RE = re.compile(r"Reference Library\s*[—–-]\s*(" + "|".join(FUNCTIONS) +
                          r")\s*:\s*([^.\n|]{3,60})")
FOUNDATION_REF_RE = re.compile(r"\bFoundation (\d+)\b")
# "OM_BA Section 3.6" · "OM_BA 4.5" · "Foundation 0 Section C3" · "Foundation 0 B6"
SECTION_REF_RE = re.compile(r"\b(OM_[A-Z][A-Za-z]+|Foundation \d+)(?: [Ss]ections?)? "
                            r"([A-Z]?\d+(?:\.\d+)*)\b")
# [Layer]_[Function]_[Section]_[Topic]_v[Version].[ext]
FILENAME_RE = re.compile(r"^(?P<layer>[A-Za-z]+)_(?P<rest>.+)_v(?P<ver>[0-9]+\.[0-9]+)"
                         r"(?P<arch>_ARCHIVED_\d{4}-\d{2}-\d{2})?\.(?P<ext>[A-Za-z0-9]+)$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SECTION_SLOT_RE = re.compile(r"^s\d+(\.\d+)?$")
KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
# 1 · 1.1 · 1.1.1 — the letter-led scheme Foundation 0 itself uses (Part A · A1 · B7.2), and a
# number after a word (Part 1 · Stage 2). B3 cites "Section A5", so each is a number a reader can
# cite. A heading with no number at all is the finding.
NUMBERED_RE = re.compile(r"^(?:Part [A-Z]\b|(?:(?:Part|Stage|Step|Phase|Section)\s+)?"
                         r"([A-Z]?\d+(?:\.\d+)*)[.)]?(?:\s|$))")
EXAMPLE_LEAD_RE = re.compile(r"^\s*(?:[-*]\s*)?(?:examples?|for example|e\.g\.)\b[^.]*:?\s*$", re.I)

LAYER_FOLDERS = {
    "0. Department Foundation": "Foundation",
    "1. Function Operating Manuals": "OM",
    "2. Reference Library": "Ref",
    "3. Onboarding Hub": "Onboard",
    "4. Archive": "Archive",
}


# ---------------------------------------------------------------- helpers

def load_rules_from_foundation(repo):
    """Re-read the machine-readable lists from the live Foundation 0, so they cannot go stale."""
    found = None
    folder = os.path.join(repo, "0. Department Foundation")
    if os.path.isdir(folder):
        for name in sorted(os.listdir(folder)):
            if name.startswith("Foundation_s0_how-this-kb-works_v") and name.endswith(".md"):
                found = os.path.join(folder, name)
    if not found:
        return None
    text = open(found, encoding="utf-8").read()
    out = {"source": os.path.basename(found)}

    def schema_row(field):
        # The schema tables list permitted values joined by " · ". A doc's own header row
        # (| Status | Live |) carries one value and no separator, so requiring it skips that row.
        for m in re.finditer(r"^\|\s*" + re.escape(field) + r"\s*\|\s*([^|]*·[^|]*)\|",
                             text, re.M):
            vals = [v.strip().rstrip("\\").strip() for v in m.group(1).split("·")]
            vals = [v for v in vals if v]
            if vals:
                return vals
        return None

    for key, field in (("cadences", "Review cadence"), ("statuses", "Status"),
                       ("layers", "Layer"), ("functions", "Function")):
        vals = schema_row(field)
        if vals and all(re.match(r"^[A-Za-z][A-Za-z \-]*$", v) for v in vals):
            out[key] = vals
    m = re.search(r"Banned words:\s*([^.]+)\.", text)
    if m:
        vals = [re.sub(r"\s*\(.*$", "", v).strip().strip("\"'") for v in m.group(1).split(",")]
        vals = [v for v in vals if re.match(r"^[a-z][a-z\-]*$", v)]
        if vals:
            out["banned"] = vals
    # B4 caps: | Foundation doc | 3,000 words |  (or "6 pages" up to v2.2)
    b4 = re.search(r"^## B4\..*?(?=^## )", text, re.M | re.S)
    if b4:
        kinds = {"foundation doc": "Foundation", "operating manual section": "OM",
                 "reference library entry": "Ref"}
        caps, units = {}, set()
        for m in re.finditer(r"^\|\s*([^|]+?)\s*\|\s*([\d,]+)\s*(words|pages)\s*\|", b4.group(0),
                             re.M | re.I):
            k = kinds.get(m.group(1).strip().lower())
            if k:
                caps[k] = int(m.group(2).replace(",", ""))
                units.add(m.group(3).lower())
        if caps and len(units) == 1:
            out["caps"], out["caps_unit"] = caps, units.pop()
    m = re.search(r"No hedging words:\s*([^.]+)\.", text)
    if m:
        vals = [v.strip() for v in m.group(1).split(",") if v.strip()]
        if vals:
            out["hedging"] = vals
    # A3 owners: | Reference Library / Shared | DiM/DM |
    a3 = re.search(r"^## A3\..*?(?=^## )", text, re.M | re.S)
    if a3:
        owners = {}
        for m in re.finditer(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$", a3.group(0), re.M):
            loc, who = re.sub(r"\s*/\s*", " / ", demark(m.group(1))), demark(m.group(2))
            if set(loc) <= set(": -") or loc.lower() == "doc location":
                continue
            owners[loc] = who
        if owners:
            out["a3_owners"] = owners
    return out


def strip_code(lines):
    """Blank fenced code blocks so they are not read as prose."""
    out, fence = [], False
    for ln in lines:
        if ln.lstrip().startswith("```"):
            fence = not fence
            out.append("")
            continue
        out.append("" if fence else ln)
    return out


def split_sentences(text):
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\b(e\.g|i\.e|etc|vs|Mr|Ms|Dr|No|Sections?|v\d)\.", r"\1<DOT>", text)
    parts = re.split(r"(?<=[.!?])\s+", text)
    out = []
    for p in parts:
        p = p.replace("<DOT>", ".").strip()
        if p:
            out.append(p)
    return out


def word_count(text):
    return len([w for w in re.split(r"\s+", text.strip()) if w])


def demark(text):
    """Strip emphasis and backslash escapes: '**Owner**' -> 'Owner', '1\\.' -> '1.'."""
    text = re.sub(r"\\([\\`*_{}\[\]()#+\-.!&])", r"\1", text)
    return re.sub(r"\*+|_{2,}", "", text).strip()


def is_word_list(line, words):
    """A line naming 3+ of the listed words defines or quotes them; it does not use them."""
    low = line.lower()
    return sum(1 for w in words if re.search(r"\b" + re.escape(w.lower()) + r"\b", low)) >= 3


# "robust" · “usually” — a quoted word or example is mentioned, not used.
QUOTED_RE = re.compile(r'"[^"\n]*"|“[^”\n]*”')
# "vague adjectives (fast, seamless, robust)" · "Ambiguous quantifiers: most, some, usually"
MENTION_LIST_RE = re.compile(r"\(([^()|]*)\)|:\s*([^.;:()|]*)")


def mask_mentions(line):
    """Blank the words a line mentions rather than uses: quoted text, and a list of three or more
    short items inside brackets or after a colon. Both name the words as examples."""
    out = QUOTED_RE.sub(lambda m: " " * len(m.group(0)), line)

    def blank_list(m):
        body = m.group(1) if m.group(1) is not None else m.group(2)
        items = [re.sub(r"^(?:and|or)\s+", "", x.strip()) for x in body.split(",")]
        items = [x for x in items if x]
        if len(items) >= 3 and all(word_count(x) <= 3 for x in items):
            return m.group(0).replace(body, " " * len(body))
        return m.group(0)

    return MENTION_LIST_RE.sub(blank_list, out)


CHANGELOG_FILE_RE = re.compile(r"(?:^|[_-])changelog_v\d", re.I)
VERSION_HEADING_RE = re.compile(r"^v\d+(?:\.\d+)*\b")


def role_matches(role, expected):
    """Does an Owner role name the approver A3 expects? A qualifier in brackets is dropped, so
    `BA Lead (acting)` names the BA Lead and `BA (PIC)` names a BA, not the lead."""
    r = re.sub(r"\s+", " ", re.sub(r"\([^)]*\)", " ", demark(role))).strip().lower()
    e = expected.lower()
    if e == "dim/dm":
        return r in ("dim/dm", "division manager")
    m = re.match(r"^(.+?) lead$", e)
    if m:
        # PM Lead · PM/PMA Lead · BA Functional Lead · BE Dev Lead
        return bool(re.search(r"(?:^|\s)" + re.escape(m.group(1)) +
                              r"(?:/[a-z]+)?\s+(?:functional\s+|function\s+)?lead\b", r))
    return r == e


def is_changelog_file(relpath):
    """A standalone changelog, such as Ref_BA_presales-questionnaire-changelog_v1.0.md. It keeps
    the release history of a file that cannot carry its own (a workbook), so the whole doc is the
    changelog: its version headings (`v1.0 — 2026-09-15`) need no number, and it needs no
    changelog table of its own. Every other rule applies."""
    return bool(CHANGELOG_FILE_RE.search(os.path.basename(relpath)))


def kind_of(relpath):
    """Which Foundation 0 rules bind this file.

    archive  — 4. Archive/. C6 freezes content, so only the filename is checked.
    plan     — *_plan_* and KB_Plan_*. The README says plan files are not KB docs, so every
               finding is advisory.
    template — listed in config. A placeholder header is by design, so only the filename.
    doc      — everything else in a KB layer.
    """
    name = os.path.basename(relpath)
    if relpath.split("/")[0] == "4. Archive":
        return "archive"
    if "_plan_" in name or name.startswith("KB_Plan"):
        return "plan"
    return "doc"


def parse_header(lines):
    """Return (fields dict, first_line, last_line) for the leading 7-field table."""
    fields, start, end = {}, None, None
    for i, ln in enumerate(lines[:60]):
        m = re.match(r"^\|\s*([^|]+?)\s*\|\s*(.*?)\s*\|\s*$", ln)
        if not m:
            if start is not None and not ln.strip().startswith("|"):
                break
            continue
        # Docs converted from .docx bold the keys (| **Owner** |) and escape punctuation.
        key, val = demark(m.group(1)), demark(m.group(2))
        if set(key) <= set(": -") or set(val) <= set(": -"):
            continue
        if key.lower() in ("field", "fields"):
            start = i if start is None else start
            continue
        if start is None:
            start = i
        end = i
        fields[key] = val
    return fields, start, end


def body_span(lines):
    """Lines after the header table, with code fences blanked."""
    _, _, end = parse_header(lines)
    first = (end + 1) if end is not None else 0
    return first, strip_code(lines)


def iter_paragraphs(lines, first):
    """Yield (line_no, text) for prose paragraphs — not tables, headings, bullets."""
    buf, buf_start = [], None
    for i in range(first, len(lines)):
        ln = lines[i]
        s = ln.strip()
        is_prose = s and not s.startswith(("|", "#", "-", "*", ">", "1.", "2.", "3.")) \
            and not re.match(r"^\d+[.)]\s", s)
        if is_prose:
            if buf_start is None:
                buf_start = i + 1
            buf.append(s)
        else:
            if buf:
                yield buf_start, " ".join(buf)
            buf, buf_start = [], None
    if buf:
        yield buf_start, " ".join(buf)


def iter_cells(lines, first):
    for i in range(first, len(lines)):
        s = lines[i].strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if all(set(c) <= set(": -") for c in cells if c):
            continue
        for c in cells:
            if c:
                yield i + 1, c


def doc_type(relpath):
    top = relpath.split("/")[0]
    return LAYER_FOLDERS.get(top)


def index_repo(repo):
    """Map every file's basename (and stem) to its path, for cross-reference resolution."""
    idx = {}
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in (".git", ".kb-ci", ".gitea", ".github")]
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), repo)
            idx.setdefault(f, []).append(rel)
            idx.setdefault(os.path.splitext(f)[0], []).append(rel)
    return idx


# ---------------------------------------------------------------- the checks

class Check:
    def __init__(self, repo, config, rules=None):
        self.repo = repo
        self.config = config
        self.index = index_repo(repo)
        self.findings = []
        # What the Owner confirms by approving, not a finding: a declared B4 exception.
        self.decisions = []
        self.current_kind = "doc"
        r = rules or {}
        self.cadences = r.get("cadences", CADENCES)
        self.statuses = r.get("statuses", STATUSES)
        self.layers = r.get("layers", LAYERS)
        self.functions = r.get("functions", FUNCTIONS)
        self.hedging = r.get("hedging", HEDGING)
        self.banned = list(r.get("banned", BANNED))
        for w in list(self.banned):
            for v in SPELLING_VARIANTS.get(w, []):
                if v not in self.banned:
                    self.banned.append(v)
        self.rules_source = r.get("source")
        self.caps_from_foundation = r.get("caps") if r.get("caps_unit") == "words" else None
        self.a3_owners = r.get("a3_owners", A3_OWNERS)

    def add(self, path, line, rule_id, message, fix, severity=None):
        part, rule, fails = RULES[rule_id]
        sev = severity or self.config.get("severity", {}).get(rule_id) \
            or DEFAULT_SEVERITY.get(rule_id, "blocking")
        if sev == "off":
            return
        if self.current_kind == "plan" and sev == "blocking":
            sev = "advisory"  # README: plan files are not KB docs
        self.findings.append({
            "file": path, "line": line, "id": rule_id, "part": part,
            "rule": rule, "fails": fails, "message": message, "fix": fix, "severity": sev,
        })

    # -- filename -------------------------------------------------

    def check_filename(self, relpath):
        name = os.path.basename(relpath)
        if name in self.config.get("ignore", []):
            return
        in_archive = relpath.split("/")[0] == "4. Archive"
        m = FILENAME_RE.match(name)
        if not m:
            self.add(relpath, 0, "C3-pattern", f"`{name}` does not match the C3.1 pattern.",
                     "Rename to [Layer]_[Function]_[Section]_[Topic]_v[Version].[ext].")
            return
        layer, rest, ext = m.group("layer"), m.group("rest"), m.group("ext").lower()
        if layer not in self.layers and not name.startswith("KB_Plan"):
            self.add(relpath, 0, "C3-pattern",
                     f"Layer slot `{layer}` is not one of {', '.join(self.layers)}.",
                     "Use a permitted layer name.")
        if ext not in EXTENSIONS:
            self.add(relpath, 0, "C3-ext", f"Extension `.{ext}` is not permitted.",
                     f"Use one of {', '.join('.' + e for e in EXTENSIONS)}.")
        if in_archive and not m.group("arch"):
            self.add(relpath, 0, "C6-archived", f"`{name}` carries no _ARCHIVED_YYYY-MM-DD suffix.",
                     "Add the archive date suffix per C6.")
        slots = rest.split("_")
        if layer == "Foundation":
            # Foundation omits Function. Expect [Section]_[Topic].
            if slots and SECTION_SLOT_RE.match(slots[0]):
                topic_parts = slots[1:]
            else:
                topic_parts = slots
        else:
            if slots and slots[0] in self.functions:
                slots = slots[1:]
            elif not name.startswith("KB_Plan"):
                self.add(relpath, 0, "C3-pattern",
                         f"No Function slot in `{name}`. Expected one of "
                         f"{', '.join(self.functions)}.",
                         "Add the function slot after the layer.")
            topic_parts = slots[1:] if (slots and SECTION_SLOT_RE.match(slots[0])) else slots
        topic = "_".join(topic_parts)
        if not topic:
            self.add(relpath, 0, "C3-pattern", f"No Topic slot in `{name}`.",
                     "Add a kebab-case topic slug before the version.")
        elif not KEBAB_RE.match(topic):
            self.add(relpath, 0, "C3-topic", f"Topic `{topic}` is not kebab-case.",
                     "Lowercase it and join words with hyphens.")

    # -- header ---------------------------------------------------

    def check_header(self, relpath, lines):
        fields, start, end = parse_header(lines)
        present = [k for k in fields if k in HEADER_FIELDS]
        if not present:
            self.add(relpath, 1, "C1-missing", "No 7-field header table found.",
                     "Draft from the published doc template; do not write the header from scratch.")
            return fields
        for f in HEADER_FIELDS:
            if f not in fields:
                self.add(relpath, (start or 0) + 1, "C1-missing", f"Header field `{f}` is absent.",
                         f"Add a `{f}` row to the header table.")
        if present != [f for f in HEADER_FIELDS if f in fields]:
            self.add(relpath, (start or 0) + 1, "C1-order",
                     f"Header fields run {', '.join(present)}.",
                     f"Reorder to {', '.join(HEADER_FIELDS)}.")

        owner = fields.get("Owner", "")
        if owner and ("—" not in owner and "–" not in owner and " - " not in owner):
            self.add(relpath, (start or 0) + 1, "C1-owner",
                     f"Owner reads `{owner}` with no role after an em-dash.",
                     "Render it as Name — Role, for example Emma Nguyen — DiM/DM.")
        elif owner:
            role = re.split(r"\s*(?:—|–| - )\s*", owner, maxsplit=1)[1].strip()
            where, expected = self.expected_owner(relpath)
            if expected and not role_matches(role, expected):
                self.add(relpath, (start or 0) + 1, "A3-owner-role",
                         f"Owner role `{role}` is not the approver Foundation 0 Section A3 "
                         f"names for {where}: {expected}.",
                         f"Name the {expected} as Owner. A person sets it: Section A5 bars the "
                         "AI Agent from changing the Owner role.")

        rev = fields.get("Last reviewed", "")
        if rev and not DATE_RE.match(rev):
            self.add(relpath, (start or 0) + 1, "C1-reviewed",
                     f"Last reviewed reads `{rev}`.", "Write it as YYYY-MM-DD.")

        cad = fields.get("Review cadence", "")
        if cad and cad not in self.cadences:
            self.add(relpath, (start or 0) + 1, "C1-cadence",
                     f"Review cadence reads `{cad}`.",
                     f"Use one of {', '.join(self.cadences)}.")

        ver = fields.get("Version", "")
        if ver and not re.match(r"^v\d+\.\d+$", ver):
            self.add(relpath, (start or 0) + 1, "C1-version",
                     f"Version reads `{ver}`.",
                     "Write it as vX.Y. A status word belongs in the Status field.")

        status = fields.get("Status", "")
        if status and status not in self.statuses:
            self.add(relpath, (start or 0) + 1, "C1-status",
                     f"Status reads `{status}`.", f"Use one of {', '.join(self.statuses)}.")
        elif status:
            top = relpath.split("/")[0]
            in_kb = top in LAYER_FOLDERS
            in_archive = top == "4. Archive"
            if status == "Live" and in_archive:
                self.add(relpath, (start or 0) + 1, "C1-folder",
                         "Status is Live but the doc sits in 4. Archive/.",
                         "Set Status to Archive, or move the file out of Archive.")
            if status == "Archive" and in_kb and not in_archive:
                self.add(relpath, (start or 0) + 1, "C1-folder",
                         f"Status is Archive but the doc sits in {top}/.",
                         "Move the file to 4. Archive/ with the C6 suffix.")
            if status == "Draft" and in_kb:
                self.add(relpath, (start or 0) + 1, "C1-folder",
                         f"Status is Draft but the doc sits in {top}/.",
                         "C2 puts drafts outside KB folders. Promote it to Live, or move it out.")

        linked = fields.get("Linked from", "")
        if linked and linked.lower() not in ("(none — entry point of the kb)", "(none)", "none", "-"):
            for ref in TOKEN_REF_RE.findall(linked):
                if not self.resolve_token(ref):
                    self.add(relpath, (start or 0) + 1, "C1-linkedfrom",
                             f"Linked from names `{ref}`, which is not in this repository.",
                             "Correct the name, or remove the row.")
        return fields

    def expected_owner(self, relpath):
        """(A3 location, approver role) for a doc's folder, or (None, None) when A3 cannot tell."""
        parts = relpath.split("/")
        top = parts[0]
        fn = parts[1] if len(parts) > 2 else None
        if top == "0. Department Foundation":
            loc = "Foundation"
        elif top == "4. Archive":
            loc = "Archive"
        elif top == "1. Function Operating Manuals":
            loc = "Function Operating Manual"
        elif top == "2. Reference Library" and fn in ("Shared", "Tech"):
            loc = f"Reference Library / {fn}"
        elif top == "2. Reference Library":
            loc = "Reference Library / per-function"
        elif top == "3. Onboarding Hub":
            loc = "Onboarding Hub"
        else:
            return None, None
        who = self.a3_owners.get(loc)
        if not who:
            return None, None
        if who.lower().startswith("relevant "):
            # "Relevant Function Lead": the lead of the function the folder names.
            if not fn or fn == "Shared":
                return None, None
            return f"{loc} ({fn})", f"{fn} Lead"
        return loc, who

    # -- structure ------------------------------------------------

    def check_structure(self, relpath, lines, fields):
        # B2 says the title is one line. It does not say which markup: a `# heading` and a
        # bold line (the form .docx conversion produces) are both one line.
        first_content = next((i for i, ln in enumerate(lines) if ln.strip()), 0)
        t = lines[first_content].strip()
        if not (t.startswith("# ") or re.match(r"^\*\*[^*].*\*\*$", t)):
            self.add(relpath, first_content + 1, "B2-title",
                     "The doc does not open with a single title line.",
                     "Open with `# <Doc> — <Topic>`.")

        _, start, end = parse_header(lines)
        if end is None:
            return
        # purpose paragraph
        purpose = None
        for ln_no, text in iter_paragraphs(lines, end + 1):
            purpose = (ln_no, text)
            break
        if purpose:
            n = len(split_sentences(purpose[1]))
            if n < 2 or n > 4:
                self.add(relpath, purpose[0], "B2-purpose",
                         f"The purpose paragraph runs {n} sentence{'s' if n != 1 else ''}.",
                         "Write it in 2 to 4 sentences. If it cannot be done in 4, split the doc.")

        # Purpose holds B2 part 3 and Changelog the last part; B2 allows References after the
        # body (Foundation 0 v2.3). None of them is a numbered body section.
        tail_ok = [t.lower() for t in self.config.get("allow_unnumbered",
                                                      ["purpose", "references", "changelog",
                                                       "change log"])]
        headings = []
        for i in range(end + 1, len(lines)):
            m = HEADING_RE.match(lines[i])
            if m:
                headings.append((i + 1, len(m.group(1)), demark(m.group(2))))
        cl_file = is_changelog_file(relpath)
        for ln_no, level, text in headings:
            clean = re.sub(r"[`]", "", text).strip()
            if clean.lower() in tail_ok:
                continue
            if cl_file and VERSION_HEADING_RE.match(clean):
                continue
            nm = NUMBERED_RE.match(clean)
            if not nm:
                self.add(relpath, ln_no, "B2-numbered",
                         f"Section heading `{clean}` carries no number.",
                         "Number body sections 1, 2, 3 with subsections 1.1, 1.2.")
            elif nm.group(1) and len(nm.group(1).split(".")) > 3:
                self.add(relpath, ln_no, "B2-depth",
                         f"Heading number `{nm.group(1)}` runs four levels deep.",
                         "Go no deeper than three levels.")

        if not cl_file:
            self.check_changelog(relpath, lines, headings)

    def check_changelog(self, relpath, lines, headings):
        cl = [h for h in headings if h[2].strip().lower() in ("changelog", "change log")]
        if not cl:
            self.add(relpath, len(lines), "B2-changelog", "No changelog table found.",
                     "Add a changelog table at the bottom, newest entry on top.")
            return
        ln_no = cl[-1][0]
        if headings and headings[-1][0] != ln_no:
            later = [h for h in headings if h[0] > ln_no]
            self.add(relpath, ln_no, "B2-changelog",
                     f"The changelog is followed by `{later[0][2]}`.",
                     "Put the changelog last.")
        dates = []
        for i in range(ln_no, len(lines)):
            s = lines[i].strip()
            if not s.startswith("|"):
                continue
            cells = [c.strip() for c in s.strip("|").split("|")]
            if cells and DATE_RE.match(cells[0]):
                dates.append((i + 1, cells[0]))
        for (l1, d1), (l2, d2) in zip(dates, dates[1:]):
            if d1 < d2:
                self.add(relpath, l2, "B2-changelog",
                         f"Changelog entry {d2} sits below {d1}.",
                         "Put the newest entry on top.")
                break

    # -- writing --------------------------------------------------

    def check_writing(self, relpath, lines):
        first, body = body_span(lines)
        seen_sent = 0
        for ln_no, text in iter_paragraphs(body, first):
            sents = split_sentences(text)
            if len(sents) > PARAGRAPH_MAX_SENTENCES:
                self.add(relpath, ln_no, "B1-paragraph",
                         f"Paragraph runs {len(sents)} sentences.",
                         "Split it. One idea per paragraph, 5 sentences at most.")
            for s in sents:
                n = word_count(s)
                if n > SENTENCE_MAX and seen_sent < self.config.get("max_report_per_rule", 25):
                    seen_sent += 1
                    self.add(relpath, ln_no, "B1-sentence",
                             f"Sentence runs {n} words: \"{s[:70].strip()}…\"",
                             "Split it. 28 words is the cap.")
        for ln_no, cell in iter_cells(body, first):
            for s in split_sentences(cell):
                n = word_count(s)
                if n > SENTENCE_MAX and seen_sent < self.config.get("max_report_per_rule", 25):
                    seen_sent += 1
                    self.add(relpath, ln_no, "B1-sentence",
                             f"Table cell sentence runs {n} words: \"{s[:70].strip()}…\"",
                             "Split it. 28 words is the cap.")

        pinned = self.config.get("pinned", [])
        for i in range(first, len(body)):
            raw = body[i]
            s = raw
            for p in pinned:
                s = s.replace(p, " ")
            s = re.sub(r"`[^`]*`", " ", s)
            low = mask_mentions(s).lower()
            # A line that lists the words (B1's own rule, a weak-word list) names them, not uses them.
            if is_word_list(s, self.hedging) or is_word_list(s, self.banned):
                low = ""
            for w in self.hedging:
                if re.search(r"\b" + re.escape(w.lower()) + r"\b", low):
                    self.add(relpath, i + 1, "B1-hedging",
                             f"Hedging word `{w}`.",
                             "Replace it with must, is, does or will.")
                    break
            for w in self.banned:
                if re.search(r"\b" + re.escape(w.lower()) + r"\b", low):
                    self.add(relpath, i + 1, "B1-banned", f"Banned word `{w}`.",
                             "Use a plain word. For utilize, use `use`.")
                    break
            if "§" in raw:
                self.add(relpath, i + 1, "B3-section", "The symbol § appears.",
                         "Write `Section 4.4` or the doc name instead.")
            flagged = False
            for u in BARE_URL_RE.findall(s):
                if f"]({u}" in raw or f"<{u}" in raw:
                    continue
                self.add(relpath, i + 1, "B3-bare-url", f"Bare URL `{u[:60]}`.",
                         "Hyperlink the doc name instead of pasting the URL.")
                flagged = True
                break
            # B3: the visible text is the doc name. A link that shows the URL as its text is
            # still a bare URL to the reader: [https://x](https://x).
            lt = LINK_TEXT_URL_RE.search(raw)
            if lt and not flagged:
                self.add(relpath, i + 1, "B3-bare-url",
                         f"Link text is the URL itself: `{lt.group(1)[:60]}`.",
                         "Make the visible text the doc or page name.")

        viet = [i + 1 for i in range(first, len(body)) if VIET_RE.search(body[i])]
        if viet:
            self.add(relpath, viet[0], "B5-mixed",
                     f"Vietnamese characters on {len(viet)} line{'s' if len(viet) > 1 else ''} "
                     f"(first at line {viet[0]}).",
                     "Add an English gloss, or move the content to a Vietnamese-only doc.")

    # -- length ---------------------------------------------------

    def check_length(self, relpath, lines, fields):
        kind = doc_type(relpath)
        if kind in (None, "Archive", "Onboard"):
            return
        # B4 names Foundation 0 as exempt by scope.
        if os.path.basename(relpath).startswith("Foundation_s0_"):
            return
        # Foundation 0 B4 sets the caps. When it states them in words, the check can count them
        # and B4 blocks. When it states pages (Foundation 0 up to v2.2), Markdown cannot count
        # pages, so the config's word equivalents apply and B4 only advises.
        if self.caps_from_foundation:
            caps, sev = self.caps_from_foundation, None
        else:
            caps, sev = self.config.get("caps", DEFAULT_CAPS), "advisory"
        cap = caps.get(kind)
        if not cap:
            return
        first, body = body_span(lines)
        # B4 counts the body: from the end of the header table to the changelog, without code.
        end = len(body)
        for i in range(first, len(body)):
            h = HEADING_RE.match(body[i])
            if h and demark(h.group(2)).lower() in ("changelog", "change log"):
                end = i
                break

        def count(a, b):
            return sum(word_count(re.sub(r"[|#*`>-]", " ", ln)) for ln in body[a:b])

        # An Operating Manual's cap is per section: each numbered top-level section on its own.
        spans = [(first, end, None)]
        if kind == "OM":
            heads = []
            for i in range(first, end):
                h = HEADING_RE.match(body[i])
                if h:
                    nm = NUMBERED_RE.match(demark(h.group(2)))
                    if nm and nm.group(1) and "." not in nm.group(1).rstrip("."):
                        heads.append((i, len(h.group(1)), demark(h.group(2))))
            if heads:
                top = min(lv for _, lv, _ in heads)
                heads = [(i, t) for i, lv, t in heads if lv == top]
                spans = [(i, heads[k + 1][0] if k + 1 < len(heads) else end, t)
                         for k, (i, t) in enumerate(heads)]

        # The declaration sits under Purpose: before the first numbered body section.
        pre_end = next((i for i in range(first, end) if HEADING_RE.match(body[i]) and
                        NUMBERED_RE.match(demark(HEADING_RE.match(body[i]).group(2)))), end)
        purpose = " ".join(body[first:min(pre_end, first + 40)])
        declared = "b4" in purpose.lower()
        declaration = " ".join(s for s in split_sentences(demark(purpose))
                               if "b4" in s.lower() or "reference data" in s.lower()
                               or re.match(r"^sections? \d", s.lower()))

        for a, b, title in spans:
            words = count(a, b)
            if words <= cap:
                continue
            where = f"Section `{title}` runs" if title else "Body runs"
            if declared:
                # B4 lets the author declare it; the Owner confirms it by approving (PLAN 3.1).
                self.decisions.append({
                    "file": relpath, "line": a + 1, "id": "B4-exception", "part": "B4",
                    "message": f"{where} {words} words against a cap of {cap}. Declared under "
                               f"Purpose: \"{declaration}\"",
                })
            else:
                self.add(relpath, a + 1, "B4-exception",
                         f"{where} {words} words against a cap of {cap} and declares no exception.",
                         "Split the doc, or, if the length is reference data, declare the "
                         "exception under Purpose: the cap, the exception, the sections.",
                         severity=sev)

    # -- cross-references -----------------------------------------

    def resolve_token(self, token):
        if token in self.index:
            return True
        base = re.sub(r"_v\d+\.\d+$", "", token)
        for key in self.index:
            if key.startswith(base + "_v") or key == base:
                return True
        return False

    def section_numbers(self, doc):
        """Numbers of the sections in the doc a reference names, or None if no such doc."""
        cache = self.__dict__.setdefault("_sections", {})
        if doc in cache:
            return cache[doc]
        target = None
        if doc.startswith("Foundation "):
            n = doc.split()[1]
            cands = [k for k in self.index if k.startswith(f"Foundation_s{n}_") and k.endswith(".md")]
        else:
            cands = [k for k in self.index if k.startswith(doc + "_v") and k.endswith(".md")]
        for c in sorted(cands):
            for rel in self.index[c]:
                if not rel.startswith("4. Archive"):
                    target = rel
        if not target:
            cache[doc] = None
            return None
        text = open(os.path.join(self.repo, target), encoding="utf-8", errors="replace").read()
        nums = set()
        for ln in text.split("\n"):
            h = HEADING_RE.match(ln)
            if h:
                m = NUMBERED_RE.match(demark(h.group(2)))
                if m and m.group(1):
                    nums.add(m.group(1).rstrip("."))
        cache[doc] = (target, nums)
        return cache[doc]

    def check_xrefs(self, relpath, lines):
        first, body = body_span(lines)
        self_stem = os.path.splitext(os.path.basename(relpath))[0]
        seen = set()
        in_example = False
        for i in range(first, len(body)):
            raw = body[i]
            h = HEADING_RE.match(raw)
            if h:
                in_example = "example" in h.group(2).lower()
            elif EXAMPLE_LEAD_RE.match(raw):
                in_example = True
            if in_example:
                continue  # a filename shown to illustrate the pattern is not a reference
            for m in TOKEN_REF_RE.finditer(raw):
                token = m.group(1)
                if token in seen or token == self_stem:
                    continue
                seen.add(token)
                if not self.resolve_token(token):
                    # A token with its extension attached reads as a filename shown in prose;
                    # one without reads as a reference to a doc. Only the second blocks.
                    illustration = re.match(r"\.(md|docx|xlsx|pdf|html)\b", raw[m.end():])
                    self.add(relpath, i + 1, "XREF-missing",
                             f"Names `{token}`, which is not in this repository.",
                             "Correct the name, or add the doc before merging this one.",
                             severity="advisory" if illustration else None)
            for doc, sec in SECTION_REF_RE.findall(raw):
                key = f"{doc}§{sec}"
                if key in seen:
                    continue
                seen.add(key)
                res = self.section_numbers(doc)
                if not res:
                    continue  # the doc itself is missing; the doc-level check reports that
                target, nums = res
                if not any(n == sec or n.startswith(sec + ".") for n in nums):
                    self.add(relpath, i + 1, "XREF-section",
                             f"Cites `{doc} Section {sec}`, but {os.path.basename(target)} has no "
                             f"section {sec}.",
                             "Correct the number, or restore the section in the cited doc.")
            for n in FOUNDATION_REF_RE.findall(raw):
                key = f"Foundation s{n}"
                if key in seen:
                    continue
                seen.add(key)
                if not any(k.startswith(f"Foundation_s{n}_") for k in self.index):
                    self.add(relpath, i + 1, "XREF-missing",
                             f"Names `Foundation {n}`, which has no section file in this "
                             f"repository.", "Correct the number, or add the doc first.",
                             severity="advisory")
            for fn, title in PROSE_REF_RE.findall(raw):
                title = re.split(r"[\"“(]|\*\*", title)[0].strip().rstrip(":")
                if not title or not title[0].isupper():
                    continue  # prose describing the library, not a doc name
                words = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-").split("-")
                if words and words[0] == fn.lower():
                    words = words[1:]  # "BA: BA Judgement Patterns" -> judgement-patterns
                slug = "-".join(w for w in words if w)
                key = f"{fn}:{slug}"
                if key in seen or not slug:
                    continue
                seen.add(key)
                prefix = f"ref_{fn.lower()}_"
                hit = any(k.lower().startswith(prefix) and slug in k.lower() for k in self.index)
                if not hit:
                    self.add(relpath, i + 1, "XREF-missing",
                             f"Names `Reference Library — {fn}: {title.strip()}`, which has no "
                             f"matching entry in this repository.",
                             "Correct the name, add the entry, or say it is not written yet.",
                             severity="advisory")

    # -- driver ---------------------------------------------------

    def run(self, relpath, text=None):
        """Check one file. `text` overrides the disk copy (used to check a base version)."""
        name = os.path.basename(relpath)
        if name in self.config.get("ignore", []):
            return
        self.current_kind = kind_of(relpath)
        if name in self.config.get("templates", []):
            self.current_kind = "template"
        if not name.startswith("KB_Plan"):  # README names KB_Plan as the root plan artifact
            self.check_filename(relpath)
        if not relpath.lower().endswith(".md"):
            return
        if self.current_kind in ("archive", "template"):
            return  # C6 freezes archived content; a template's placeholders are by design
        if text is None:
            path = os.path.join(self.repo, relpath)
            try:
                text = open(path, encoding="utf-8", errors="replace").read()
            except OSError as e:
                self.add(relpath, 0, "C1-missing", f"Cannot read the file: {e}",
                         "Check the file is committed.")
                return
        lines = text.split("\n")
        fields = self.check_header(relpath, lines)
        self.check_structure(relpath, lines, fields)
        self.check_writing(relpath, lines)
        self.check_length(relpath, lines, fields)
        self.check_xrefs(relpath, lines)


# ---------------------------------------------------------------- cli

def kb_files(repo):
    out = []
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in (".git", ".kb-ci", ".gitea", ".github")]
        for f in sorted(files):
            if f.startswith("."):
                continue
            rel = os.path.relpath(os.path.join(root, f), repo)
            top = rel.split("/")[0]
            if top in LAYER_FOLDERS or rel.startswith("KB_Plan"):
                out.append(rel)
    return sorted(out)


def load_config(repo, path):
    default = {"ignore": ["README.md"], "severity": {}, "caps": DEFAULT_CAPS, "pinned": []}
    p = path or os.path.join(repo, ".kb-ci", "config.json")
    if os.path.exists(p):
        try:
            default.update(json.load(open(p, encoding="utf-8")))
        except (OSError, ValueError) as e:
            print(f"warning: cannot read {p}: {e}", file=sys.stderr)
    return default


def selftest():
    import tempfile
    bad = """# Bad doc

| Field | Value |
| :---- | :---- |
| Owner | BA Team |
| Audience | BA |
| Last reviewed | 22/08/2026 |
| Review cadence | When needed |
| Version | v1.0 Live |
| Linked from | (none) |
| Status | Live |

This doc leverages a robust approach.

## Part one

Teams may utilize this. See § 4. More at https://example.com/page and it usually works.
"""
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "2. Reference Library", "BA"))
    rel = "2. Reference Library/BA/Ref_BA_Bad_Topic_v1.0.md"
    open(os.path.join(d, rel), "w", encoding="utf-8").write(bad)
    c = Check(d, load_config(d, None))
    c.run(rel)
    got = sorted({f["id"] for f in c.findings})
    want = ["B1-banned", "B1-hedging", "B2-changelog", "B2-numbered", "B2-purpose",
            "B3-bare-url", "B3-section", "C1-cadence", "C1-owner", "C1-reviewed", "C1-version",
            "C3-topic"]
    missing = [w for w in want if w not in got]

    # Cases each fixed after a false result on the real repository. Each must hold.
    cases = []

    def case(name, doc, rel, expect_ids, forbid_ids, foundation=None, extra=None):
        dd = tempfile.mkdtemp()
        os.makedirs(os.path.join(dd, os.path.dirname(rel)), exist_ok=True)
        open(os.path.join(dd, rel), "w", encoding="utf-8").write(doc)
        if foundation:
            f0 = os.path.join(dd, "0. Department Foundation")
            os.makedirs(f0, exist_ok=True)
            open(os.path.join(f0, "Foundation_s0_how-this-kb-works_v9.9.md"), "w",
                 encoding="utf-8").write(foundation)
        cc = Check(dd, load_config(dd, None), load_rules_from_foundation(dd))
        cc.run(rel)
        ids = {f["id"] for f in cc.findings if f["severity"] == "blocking"}
        ok_ = all(e in ids for e in expect_ids) and not any(x in ids for x in forbid_ids)
        if extra:
            ok_ = ok_ and extra(cc)
        cases.append({"case": name, "pass": ok_, "got": sorted(ids)})

    hdr = ("| **Field** | **Value** |\n| --- | --- |\n| **Owner** | Emma Nguyen — DiM/DM |\n"
           "| **Audience** | All |\n| **Last reviewed** | 2026-05-06 |\n"
           "| **Review cadence** | Annual |\n| **Version** | v1.1 |\n"
           "| **Linked from** | (none) |\n| **Status** | Live |\n\n")
    good_tail = "\n## Changelog\n\n| Date | Version | Change | By |\n| :- | :- | :- | :- |\n" \
                "| 2026-05-06 | v1.1 | Edit. | Emma Nguyen — DiM/DM |\n"
    # bold keys, bold title, escaped heading numbers, letter numbering: all compliant
    case("docx-converted form is compliant",
         "**Foundation 1 — Tool Boundary**\n\n" + hdr +
         "This doc sets the tool boundary. Every editor reads it.\n\n"
         "# 1\\. Scope\n\nText here.\n\n## A1. Letter numbering\n\nText.\n\n"
         "## Part 2. Word-led number\n\nText.\n\n### Stage 1. Word-led sub\n\nText.\n" + good_tail,
         "0. Department Foundation/Foundation_s1_tool-boundary_v1.1.md",
         [], ["C1-missing", "B2-title", "B2-numbered", "C1-cadence"])
    # link whose text is the URL
    case("link text that is a URL is a bare URL",
         "# T — X\n\n" + hdr + "Purpose one. Purpose two.\n\n## 1. Body\n\n"
         "Raise a ticket at [https://service.example.vn](https://service.example.vn) now.\n"
         + good_tail,
         "2. Reference Library/BA/Ref_BA_link-test_v1.1.md", ["B3-bare-url"], [])
    # filenames under an Examples line are illustrations, not references
    case("example filenames are not references",
         "# T — X\n\n" + hdr + "Purpose one. Purpose two.\n\n## 1. Naming\n\nExamples:\n\n"
         "- `OM_Dev_plan_v0.1.md` — a plan file.\n" + good_tail,
         "2. Reference Library/BA/Ref_BA_naming-test_v1.1.md", [], ["XREF-missing"])
    # a line listing the hedging words defines them
    case("a word list names the words, it does not use them",
         "# T — X\n\n" + hdr + "Purpose one. Purpose two.\n\n## 1. Words\n\n"
         "Do not write typically, generally, usually, often, may, might or could.\n" + good_tail,
         "2. Reference Library/BA/Ref_BA_words-test_v1.1.md", [], ["B1-hedging"])
    # a quoted word, or one in a short list after a colon or in brackets, is an example
    case("quoted and listed example words are mentions, not uses",
         "# T — X\n\n" + hdr + "Purpose one. Purpose two.\n\n## 1. Words\n\n"
         "| 6 | Fails when it uses vague adjectives (fast, user-friendly, seamless, robust). |\n\n"
         "- Ambiguous quantifiers: most, many, several, some, sometimes, usually, normally\n"
         "- Replace \"robust\" with a number.\n" + good_tail,
         "2. Reference Library/BA/Ref_BA_mention-test_v1.1.md", [], ["B1-hedging", "B1-banned"])
    case("a used banned or hedging word is still a finding",
         "# T — X\n\n" + hdr + "Purpose one. Purpose two.\n\n## 1. Words\n\n"
         "- Open-ended lists: etc. and so on. These usually hide a requirement.\n"
         "- Build a robust import (one file per run).\n" + good_tail,
         "2. Reference Library/BA/Ref_BA_use-test_v1.1.md", ["B1-hedging", "B1-banned"], [])
    # a standalone changelog file is the changelog: version headings, no own changelog table
    changelog_doc = ("# T — Changelog\n\n" + hdr + "Every released version, newest first. "
                     "Add a row before release.\n\n## 1. Release history\n\n"
                     "### v1.1 — 2026-09-15\n\nFirst release.\n\n"
                     "### v1.0 — 2026-08-21\n\nDraft.\n")
    case("a changelog file needs no numbered version headings or changelog table", changelog_doc,
         "2. Reference Library/BA/Ref_BA_workbook-changelog_v1.1.md", [],
         ["B2-numbered", "B2-changelog"])
    case("a changelog file still numbers its other headings",
         changelog_doc + "\n## Notes\n\nText.\n",
         "2. Reference Library/BA/Ref_BA_workbook-changelog_v1.1.md", ["B2-numbered"], [])
    case("version headings in a normal doc still need a number", changelog_doc,
         "2. Reference Library/BA/Ref_BA_workbook-history_v1.1.md", ["B2-numbered",
                                                                     "B2-changelog"], [])
    # a heading with no number at all is still a finding
    case("an unnumbered heading is a finding",
         "# T — X\n\n" + hdr + "Purpose one. Purpose two.\n\n## 1. Body\n\nText.\n\n"
         "## Payments\n\nText.\n" + good_tail,
         "2. Reference Library/BA/Ref_BA_heading-test_v1.1.md", ["B2-numbered"], [])
    # B4: caps stated in words in Foundation 0 block; caps stated in pages only advise
    f0 = lambda unit: ("## B4. Length limits\n\n| Doc type | Maximum length |\n| :- | :- |\n"
                       f"| Foundation doc | 3,000 {unit} |\n| Operating Manual section | 1,500 {unit} |\n"
                       f"| Reference Library entry | 2,000 {unit} |\n\n## B5. Language\n")
    long_para = ("Word " * 11 + "end. ") * 40          # ~480 words
    long_ref = "# T — X\n\n" + hdr + "Purpose one. Purpose two.\n\n## 1. Body\n\n" + \
        "\n\n".join([long_para] * 5) + "\n" + good_tail   # ~2,400 words
    case("B4 blocks a Ref entry over a word cap stated in Foundation 0", long_ref,
         "2. Reference Library/BA/Ref_BA_long-test_v1.1.md", ["B4-exception"], [],
         foundation=f0("words"))
    # A declared exception is the Owner's to confirm on the PR: no finding, no reviewer line.
    clean_para = ("Word " * 11 + "end. ") * 5          # 60 words, 5 sentences
    clean_ref = ("# T — X\n\n" + hdr + "Purpose one. Purpose two.\n\n<DECLARE>## 1. Data\n\n" +
                 "\n\n".join([clean_para] * 40) + "\n" + good_tail)   # 2,400 words
    declared_ref = clean_ref.replace(
        "<DECLARE>", "This entry exceeds the 2,000-word cap in Foundation 0 Section B4. The pure "
        "reference data exception applies. Section 1 carries the data.\n\n")
    shared = "2. Reference Library/Shared/Ref_Shared_long-test_v1.1.md"
    case("B4 passes a declared exception with no finding, for the Owner to confirm", declared_ref,
         shared, [], ["B4-exception"], foundation=f0("words"),
         extra=lambda cc: cc.findings == []
         and [d["id"] for d in cc.decisions] == ["B4-exception"]
         and "pure reference data exception applies" in cc.decisions[0]["message"])
    case("B4 fails the same doc with no declaration", clean_ref.replace("<DECLARE>", ""),
         shared, ["B4-exception"], [], foundation=f0("words"),
         extra=lambda cc: cc.decisions == [])
    case("B4 only advises while Foundation 0 states pages", long_ref,
         "2. Reference Library/BA/Ref_BA_long-test_v1.1.md", [], ["B4-exception"],
         foundation=f0("pages"))
    om_sections = ("# OM — X\n\n" + hdr + "Purpose one. Purpose two.\n\n" +
                   "".join(f"## {n}. Part {n}\n\n{long_para}\n\n{long_para}\n\n" for n in (1, 2, 3))
                   + good_tail)                          # 3 sections of ~960 words each
    case("B4 counts an OM per section, not per file", om_sections,
         "1. Function Operating Manuals/BA/OM_BA_test-om_v1.1.md", [], ["B4-exception"],
         foundation=f0("words"))
    case("B4 blocks one OM section over its cap",
         om_sections.replace("## 2. Part 2\n\n", "## 2. Part 2\n\n" + long_para + "\n\n" +
                             long_para + "\n\n"),
         "1. Function Operating Manuals/BA/OM_BA_test-om_v1.1.md", ["B4-exception"], [],
         foundation=f0("words"))
    # A3: the Owner's role against the folder's approver. Advisory, never blocking.
    def a3(*want):
        return lambda cc: sorted(f["severity"] for f in cc.findings
                                 if f["id"] == "A3-owner-role") == list(want)
    body = "Purpose one. Purpose two.\n\n## 1. Body\n\nText.\n" + good_tail
    owned = lambda who: "# T — X\n\n" + hdr.replace("Emma Nguyen — DiM/DM", who) + body
    case("A3 advises when a function doc's Owner is a PIC, not the Function Lead",
         owned("Edel — BA (PIC)"), "2. Reference Library/BA/Ref_BA_owner-test_v1.1.md",
         [], ["A3-owner-role"], extra=a3("advisory"))
    case("A3 accepts the Function Lead, acting or not",
         owned("Emma Nguyen — BA Lead (acting)"),
         "1. Function Operating Manuals/BA/OM_BA_owner-test_v1.1.md", [], [], extra=a3())
    case("A3 advises when a function doc names the DiM/DM, not the Function Lead",
         owned("Emma Nguyen — DiM/DM"), "1. Function Operating Manuals/PM/OM_PM_owner-test_v1.1.md",
         [], ["A3-owner-role"], extra=a3("advisory"))
    case("A3 wants the DiM/DM for Shared and Foundation docs",
         owned("Hieu Dang — Architect Lead"), "2. Reference Library/Shared/Ref_Shared_owner-test_v1.1.md",
         [], ["A3-owner-role"], extra=a3("advisory"))
    case("A3 accepts the DiM/DM on a Foundation doc",
         owned("Emma Nguyen — DiM/DM").replace("# T — X", "# Foundation 1 — X"),
         "0. Department Foundation/Foundation_s1_owner-test_v1.1.md", [], [], extra=a3())
    case("A3 reads the owners from Foundation 0",
         owned("Hieu Dang — Architect Lead"), "2. Reference Library/Shared/Ref_Shared_owner-test_v1.1.md",
         [], [], extra=a3(),
         foundation="## A3. Ownership rules\n\n| Doc location | Owner |\n| :- | :- |\n"
                    "| Foundation | DiM/DM |\n| Reference Library / Shared | Architect Lead |\n\n"
                    "## A4. Master Index\n")

    # B2: a References section after the body is allowed unnumbered
    case("an unnumbered References section is allowed",
         "# T — X\n\n" + hdr + "Purpose one. Purpose two.\n\n## 1. Body\n\nText.\n\n"
         "## References\n\n1. A source.\n" + good_tail,
         "2. Reference Library/BA/Ref_BA_refs-test_v1.1.md", [], ["B2-numbered"])
    # a missing real reference still blocks
    case("a missing real reference blocks",
         "# T — X\n\n" + hdr + "Purpose one. Purpose two.\n\n## 1. Refs\n\n"
         "See `Ref_BA_does-not-exist_v1.0` for the method.\n" + good_tail,
         "2. Reference Library/BA/Ref_BA_xref-test_v1.1.md", ["XREF-missing"], [])

    ok = not missing and all(c["pass"] for c in cases)
    print(json.dumps({"stage": "SELFTEST", "pass": ok, "found": got, "missing": missing,
                      "cases": cases}))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--config")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    repo = os.path.abspath(a.repo)
    config = load_config(repo, a.config)
    rules = load_rules_from_foundation(repo)
    c = Check(repo, config, rules)
    targets = kb_files(repo) if (a.all or not a.files) else [
        os.path.relpath(os.path.abspath(f), repo) for f in a.files]
    for rel in targets:
        if os.path.exists(os.path.join(repo, rel)):
            c.run(rel)

    blocking = [f for f in c.findings if f["severity"] == "blocking"]
    advisory = [f for f in c.findings if f["severity"] == "advisory"]
    if not a.json:
        by_file = {}
        for f in c.findings:
            by_file.setdefault(f["file"], []).append(f)
        for f in c.decisions:
            by_file.setdefault(f["file"], []).append(dict(f, severity="decide"))
        for path in sorted(by_file):
            print(f"\n{path}")
            for f in sorted(by_file[path], key=lambda x: (x["severity"], x["line"])):
                tag = {"blocking": "FAIL", "decide": "OWNR"}.get(f["severity"], "note")
                print(f"  {tag} {f['part']:<6} line {f['line']:>4}  {f['message']}")
        print(f"\nchecked {len(targets)} files · {len(blocking)} blocking · "
              f"{len(advisory)} advisory · {len(c.decisions)} for the Owner to confirm"
              + (f" · rules read from {c.rules_source}" if c.rules_source else ""))
    print(json.dumps({"pass": not blocking, "blocking": len(blocking),
                      "advisory": len(advisory), "checked": len(targets),
                      "rulesSource": c.rules_source, "findings": c.findings,
                      "decisions": c.decisions}))
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())

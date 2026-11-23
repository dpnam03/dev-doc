#!/usr/bin/env python3
"""readable-check.py — measure how readable a Markdown document is, by shape. 0 model tokens.

Why: a document that is too long, written in long sentences, with lists glued into paragraphs and
jargon the reader does not need, costs every reader (person or model) time on every read. The
Project Beta Screens & Flows spec paid for that for weeks (46,000 words, sentences of 30–100 words,
bullets that were paragraphs). This script counts the shapes that make a document hard to read, so
a rewrite has a number to move and a gate has a number to hold.

It measures shape, not sense. A short sentence can still be wrong. The reader brief is the catch.

Rules (each counted on the body, fenced code and front matter skipped):
  sentence     a sentence over 40 words (`--max-sentence`); sentences over 25 are counted too
  bullet       a bullet over 320 bytes or more than 2 sentences
  marker       a doubled bullet marker `- - `
  cell         a table cell over 600 bytes
  paragraph    a paragraph (or cell) over 4,000 bytes — one wall in a rendered doc
  br           a `<br>` (many renderers drop it; it hides a list inside a cell)
  options      an option run "(a) … (b)" inside one table cell
  words        a banned word — jargon, tooling or history words the reader does not need
               (`--banned <file>`, one word or regex per line; see references/banned-words.md)
  history      a version note, date-after-name, or marker glyph in the body (⟳ ⬆ ⛔ ⚠ ⭐)
  caps         an ALL-CAPS word of 4+ letters outside the allow-list (`--allow-caps`)
  bold         a bold run over 6 words (bold marks a label, never a sentence)
  clause       a bullet that starts with a clause marker (i), (a), (x)
  quote-join   two text lines inside one blockquote with no blank `>` line between — they render
               as ONE paragraph (the "rung ladder" case)
  list-line    a list written on one line: 3+ bold labels or 4+ " · " joins in one paragraph
  prose-join   two prose lines with no blank line between — Markdown joins them into one paragraph
  budget       a section over its word budget, and the whole body over the total
               (`--budget <json>`: {"total": N, "sections": {"heading prefix": N}})

Pinned copy (`--pinned <file>`): strings listed there (one per line, in quotes) are blanked before
`words` and `caps` read a line, so quoted product copy that carries a banned word is not a finding.

Usage:
    readable-check.py <doc.md> [--prev <older doc.md>] [--budget <json>] [--banned <file>]
                      [--pinned <file>] [--allow-caps WORD,WORD] [--sections] [--top N]
                      [--start-at "## 0."] [--stop-at "## Change log"] [--blocking] [--growth-cap 2] [--json]
    readable-check.py --selftest

Output: a plain table with --sections / --top, then ONE JSON line
  {"pass","count","perRule","words","wordsBySection","prevCount","grew","findings":[first 40]}.
--blocking: with --prev, red when any rule's count grew or the body grew more than --growth-cap %;
without --prev, red when count > 0. Exit 0 green, 1 red.
"""
import argparse
import json
import os
import re
import sys

SENTENCE_MAX = 40
SENTENCE_NOTE = 25
BULLET_BYTES = 320
BULLET_SENTENCES = 2
CELL_BYTES = 600
PARA_BYTES = 4000
BOLD_WORDS = 6
LIST_LINE_BYTES = 200   # a labelled list glued into one line counts only when the line is long
FINDINGS_MAX = 40
GROWTH_MIN_WORDS = 2000

RULES = ["sentence", "bullet", "marker", "cell", "paragraph", "br", "options", "words", "history",
         "caps", "bold", "clause", "quote-join", "list-line", "prose-join", "budget"]

DEFAULT_CAPS = set("MVP POST GET PUT API URL PDF CSV HTML JSON CSS DOM PNG JPG SKU SEO FAQ CTA FAB TBD "
                   "WCAG HIG UUID HTTP HTTPS SSH SQL OAUTH TODO README STAR EARS CICD".split())
DEFAULT_BANNED = [
    # loop / tooling words
    r"\bworking default\b", r"\bwireframe", r"\blo-fi\b", r"\bfleet\b", r"\bsidecar", r"\bcanonical",
    r"\bverbatim\b", r"\bre-?cut\b", r"\bclause", r"\bhermetic", r"\baffordance", r"\bthis round\b",
    r"\bRULED\b", r"\bthe runner\b", r"\bthe lane\b", r"\bthe cut\b", r"\bthe plane\b",
    # history words that belong in a change log
    r"\bsupersed(es|ed)\b", r"\bpromoted\b", r"\badopted v\d",
]
HISTORY_RES = [
    ("version note", re.compile(r"\(v\d+\.\d+[^)]{0,60}\)")),
    ("version ref", re.compile(r"(?<![(*\w])\bv\d+\.\d{2,}\b")),
    ("name + date", re.compile(r"\b[A-Z][a-z]+\b[^\d\n]{0,12}20\d\d-\d\d-\d\d\b")),
    ("marker glyph", re.compile("[⟳⬆⛔⚠⭐]")),
]

CODE_RE = re.compile(r"`[^`\n]*`")
URL_RE = re.compile(r"https?://\S+")
LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
KEEP_DOT_RE = re.compile(r"§\d+(?:\.\d+)*[a-z]?|\bv\d+\.\d+(?:\.\d+)?|\b(?:e\.g|i\.e|vs|etc|cf|no|approx)\.|\b\d+\.\d+", re.I)
DOT = "․"
SENT_SPLIT_RE = re.compile(r"(?:(?<=[.!?])|(?<=[.!?][)\"”'\]]))\s+")
BULLET_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")
LABEL_RE = re.compile(r"^\s*\*\*[^*]+\*\*[.:]?\s*")  # a leading bold label is not a sentence
DOUBLE_MARKER_RE = re.compile(r"^\s*- - ")
CLAUSE_RE = re.compile(r"^\s*(?:(?:[-*+]\s+|\d+[.)]\s+)+)\*{0,2}\((?:[ivx]+|[a-z])\)")
TABLE_SEP_RE = re.compile(r"^\|?\s*:?-{3,}")
OPT_RE = re.compile(r"\(a\).*?\(b\)")
CAPS_RE = re.compile(r"(?<![\w-])[A-Z]{4,}(?![\w-])")
HEAD_RE = re.compile(r"^(#{1,6})\s+(.*)$")
QUOTE_RE = re.compile(r"^>\s?(.*)$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
DOT_JOIN_RE = re.compile(r" · ")


def strip_inline(s):
    s = CODE_RE.sub(" ", s)
    s = URL_RE.sub(" ", s)
    s = LINK_RE.sub(r"\1", s)
    s = s.replace("**", "")
    return s


def sentences(text):
    t = KEEP_DOT_RE.sub(lambda m: m.group(0).replace(".", DOT), strip_inline(text))
    parts = [p.strip() for p in SENT_SPLIT_RE.split(t) if re.search(r"\w", p)]
    return [p.replace(DOT, ".") for p in parts]


def words(text):
    t = strip_inline(text)
    return len([w for w in re.findall(r"\S+", t) if re.search(r"[A-Za-z0-9]", w)])


def load_list(path):
    out = []
    if not path:
        return out
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- "):
            line = line[2:].strip()
        m = re.match(r'^["“](.*)["”]\s*(?:·.*)?$', line)
        out.append(m.group(1) if m else line)
    return out


def blank_pinned(line, pinned):
    for p in pinned:
        for form in (f'"{p}"', f"“{p}”", f"`{p}`", f"**{p}**", p):
            if form in line:
                line = line.replace(form, " ")
    return line


def body_lines(text, stop_at, start_at=None):
    """Return [(lineno, line)] of the body: front matter and fenced code skipped, from --start-at to --stop-at."""
    lines = text.split("\n")
    out = []
    in_fence = False
    i = 0
    if lines and lines[0].strip() == "---":
        j = 1
        while j < len(lines) and lines[j].strip() != "---":
            j += 1
        i = j + 1
    if start_at:
        for n in range(i, len(lines)):
            if lines[n].strip().lower().startswith(start_at.strip().lower()):
                i = n
                break
    for n in range(i, len(lines)):
        ln = lines[n]
        if FENCE_RE.match(ln):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if stop_at and ln.strip().lower().startswith(stop_at.strip().lower()):
            break
        out.append((n + 1, ln))
    return out


def check(text, budget=None, banned=None, pinned=None, allow_caps=None, stop_at=None, top_level=6, start_at=None):
    banned_res = [re.compile(b, re.I) for b in (banned if banned is not None else DEFAULT_BANNED)]
    pinned = pinned or []
    allow = set(DEFAULT_CAPS) | set(allow_caps or [])
    lines = body_lines(text, stop_at, start_at)
    findings = []
    per = {r: 0 for r in RULES}
    measures = {"sentences": 0, "sentencesOver25": 0, "words": 0}
    words_by_section = {}
    section = "(top)"
    n_top = top_level

    def add(rule, ln, what):
        per[rule] += 1
        findings.append({"rule": rule, "line": ln, "what": what[:160]})

    # pass 1 — per-line rules
    prev_kind = None  # 'prose' | 'other' | 'blank' | 'quote-text' | 'quote-blank'
    para_buf = []
    para_start = None

    def flush_para():
        nonlocal para_buf, para_start
        if para_buf:
            txt = "\n".join(para_buf)
            if len(txt.encode()) > PARA_BYTES:
                add("paragraph", para_start, f"paragraph of {len(txt.encode())} bytes")
            # list written on one line
            for k, l in enumerate(para_buf):
                if len(l.encode()) > LIST_LINE_BYTES and (len(BOLD_RE.findall(l)) >= 3 or len(DOT_JOIN_RE.findall(l)) >= 4):
                    add("list-line", para_start + k, "a list written as one line (3+ bold labels or 4+ ' · ')")
        para_buf = []
        para_start = None

    for ln, raw in lines:
        m = HEAD_RE.match(raw)
        if m:
            flush_para()
            if len(m.group(1)) <= n_top:
                section = m.group(2).strip()
            prev_kind = "other"
            continue
        stripped = raw.strip()
        if not stripped:
            flush_para()
            prev_kind = "blank"
            continue
        # words per section (count every body line)
        w = words(raw)
        measures["words"] += w
        words_by_section[section] = words_by_section.get(section, 0) + w
        line = blank_pinned(raw, pinned)
        plain = strip_inline(line)
        # history + banned words + markers
        for name, rx in HISTORY_RES:
            for _ in rx.finditer(line):
                add("history", ln, f"{name}: {stripped[:80]}")
        for rx in banned_res:
            for hit in rx.finditer(plain):
                add("words", ln, f"banned word '{hit.group(0)}'")
        if "<br" in raw.lower():
            add("br", ln, "<br> in the source")
        # emphasis
        for cap in CAPS_RE.findall(plain):
            if cap not in allow:
                add("caps", ln, f"ALL-CAPS '{cap}'")
        for b in BOLD_RE.findall(line):
            if len(b.split()) > BOLD_WORDS:
                add("bold", ln, f"bold run of {len(b.split())} words")
        # sentences (a table row is read cell by cell)
        is_table = stripped.startswith("|")
        pieces = [c.strip() for c in stripped.strip("|").split("|")] if is_table else [raw]
        for piece in pieces:
            sents = sentences(piece)
            measures["sentences"] += len(sents)
            for s in sents:
                sw = len(s.split())
                if sw > SENTENCE_NOTE:
                    measures["sentencesOver25"] += 1
                if sw > SENTENCE_MAX:
                    add("sentence", ln, f"{sw} words: {s[:70]}…")
        # shapes
        is_quote = stripped.startswith(">")
        is_bullet = bool(BULLET_RE.match(raw))
        if is_table:
            flush_para()
            if not TABLE_SEP_RE.match(stripped):
                cells = [c.strip() for c in stripped.strip("|").split("|")]
                for c in cells:
                    if len(c.encode()) > CELL_BYTES:
                        add("cell", ln, f"cell of {len(c.encode())} bytes: {c[:60]}…")
                    if len(c.encode()) > PARA_BYTES:
                        add("paragraph", ln, f"cell of {len(c.encode())} bytes")
                    if OPT_RE.search(c):
                        add("options", ln, "option run (a) … (b) inside a cell")
                    if "<br" in c.lower():
                        pass
            prev_kind = "other"
            continue
        if is_quote:
            flush_para()
            inner = QUOTE_RE.match(stripped).group(1).strip()
            if inner and not HEAD_RE.match(inner) and not BULLET_RE.match(inner) and not inner.startswith("|"):
                if prev_kind == "quote-text":
                    add("quote-join", ln, "two blockquote text lines with no blank '>' line between")
                prev_kind = "quote-text"
            else:
                prev_kind = "quote-blank" if not inner else "other"
            continue
        if is_bullet:
            flush_para()
            if DOUBLE_MARKER_RE.match(raw):
                add("marker", ln, "doubled bullet marker '- - '")
            if CLAUSE_RE.match(raw):
                add("clause", ln, "bullet starts with a clause marker (i) / (a)")
            body = BULLET_RE.sub("", raw, count=1)
            bl = len(body.strip().encode())
            bs = len(sentences(LABEL_RE.sub("", body, count=1)))
            if bl > BULLET_BYTES or bs > BULLET_SENTENCES:
                add("bullet", ln, f"bullet of {bl} bytes / {bs} sentences")
            if bl > LIST_LINE_BYTES and len(BOLD_RE.findall(body)) >= 3:
                add("list-line", ln, "a list written as one bullet (3+ bold labels in one long bullet)")
            prev_kind = "other"
            continue
        # prose line
        if prev_kind == "prose":
            add("prose-join", ln, "two prose lines with no blank line between — they render as one paragraph")
        if para_start is None:
            para_start = ln
        para_buf.append(raw)
        prev_kind = "prose"
    flush_para()

    # budget
    total_budget = None
    if budget:
        total_budget = budget.get("total")
        for key, lim in (budget.get("sections") or {}).items():
            got = 0
            for sec, cnt in words_by_section.items():
                if sec.startswith(key):
                    got += cnt
            if got > lim:
                add("budget", 0, f"section '{key}' {got} / {lim} words")
        if total_budget and measures["words"] > total_budget:
            add("budget", 0, f"body {measures['words']} / {total_budget} words")
    count = sum(per.values())
    return {"count": count, "perRule": per, "measures": measures, "words": measures["words"],
            "wordsBySection": words_by_section, "findings": findings}


def print_sections(res, budget):
    rows = []
    for sec, w in res["wordsBySection"].items():
        lim = ""
        if budget:
            for key, l in (budget.get("sections") or {}).items():
                if sec.startswith(key):
                    lim = l
        rows.append((w, lim, sec))
    rows.sort(reverse=True)
    print(f"{'words':>7} | {'budget':>6} | section")
    for w, lim, sec in rows:
        flag = " OVER" if lim != "" and w > lim else ""
        print(f"{w:>7} | {str(lim):>6} | {sec}{flag}")
    print(f"{res['words']:>7} | {str(budget.get('total','')) if budget else '':>6} | TOTAL")


def print_top(res, n):
    print(f"rule        count")
    for r in RULES:
        if res["perRule"][r]:
            print(f"{r:<11} {res['perRule'][r]}")
    print("--- first findings")
    for f in res["findings"][:n]:
        print(f"L{f['line']:<5} {f['rule']:<11} {f['what']}")


SELFTEST_DOC = """# Title

## 1. Rules

This is a short rule. Another short one.
This line joins the one above.

- one rule per bullet, short
- - doubled marker here
- (i) a clause marker
- this bullet is long enough to fail: it has three sentences. Here is the second. And the third sentence makes it over the limit of two sentences per bullet.

> **Rung 1** first rung text
> **Rung 2** second rung text

**Label one** does this and that and more of it · **Label two** does that and this and more of it again · **Label three** does the other thing and then some more words to pass the two-hundred-byte line.

| a | b |
|---|---|
| short | (a) one option (b) another option |

This is a sentence that goes on and on and on and on and on and on and on and on and on and on and on and on and on and on and on and on and on and on and on and on and on words.

The canonical wireframe sidecar (v0.93, Emma 2026-09-24) is the WORKING DEFAULT and the FLEET.

## Change log

- everything here is skipped: (a) … (b) canonical canonical
"""


def selftest():
    res = check(SELFTEST_DOC, budget={"total": 50, "sections": {"1. Rules": 20}}, stop_at="## Change log")
    per = res["perRule"]
    expect = {"prose-join": 1, "marker": 1, "clause": 1, "bullet": 1, "quote-join": 1, "list-line": 1,
              "options": 1, "sentence": 1, "budget": 2}
    ok = all(per[k] >= v for k, v in expect.items()) and per["words"] >= 3 and per["caps"] >= 2 and per["history"] >= 2
    clean = check("# T\n\n## 1. A\n\nOne short rule.\n\n- one bullet\n")
    ok = ok and clean["count"] == 0
    label = check("# T\n\n## 1. A\n\n- **Option.** One way to meet the requirement. Configuration, extension, custom build, or a process change.\n")
    label3 = check("# T\n\n## 1. A\n\n- **Option.** One way. A second way. A third way.\n")
    ok = ok and label["perRule"].get("bullet", 0) == 0 and label3["perRule"].get("bullet", 0) == 1
    print(json.dumps({"stage": "SELFTEST", "pass": ok, "perRule": per, "clean": clean["count"],
                      "labelBullet": label["perRule"].get("bullet", 0), "label3Bullet": label3["perRule"].get("bullet", 0)}))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("doc", nargs="?")
    ap.add_argument("--prev")
    ap.add_argument("--budget")
    ap.add_argument("--banned")
    ap.add_argument("--pinned")
    ap.add_argument("--allow-caps", default="")
    ap.add_argument("--start-at", default=None, help='heading text where the body starts, e.g. "## 0." (the header before it is skipped)')
    ap.add_argument("--stop-at", default=None, help='heading text where the body ends, e.g. "## Change log"')
    ap.add_argument("--top-level", type=int, default=6, help="deepest heading level that names a section in the word table (6 = nearest heading of any level)")
    ap.add_argument("--sections", action="store_true")
    ap.add_argument("--top", type=int, default=0)
    ap.add_argument("--blocking", action="store_true")
    ap.add_argument("--growth-cap", type=float, default=2.0)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if not a.doc:
        ap.error("doc is required")
    budget = json.load(open(a.budget, encoding="utf-8")) if a.budget else None
    banned = load_list(a.banned) if a.banned else None
    pinned = load_list(a.pinned) if a.pinned else []
    allow = [w.strip() for w in a.allow_caps.split(",") if w.strip()]
    text = open(a.doc, encoding="utf-8").read()
    res = check(text, budget, banned, pinned, allow, a.stop_at, a.top_level, a.start_at)
    prev = None
    if a.prev:
        prev = check(open(a.prev, encoding="utf-8").read(), budget, banned, pinned, allow, a.stop_at, a.top_level, a.start_at)
    grew = []
    growth_pct = None
    if prev:
        for r in RULES:
            if res["perRule"][r] > prev["perRule"][r]:
                grew.append(r)
        if prev["words"] >= GROWTH_MIN_WORDS:
            growth_pct = round(100.0 * (res["words"] - prev["words"]) / prev["words"], 2)
    if a.blocking:
        ok = (not grew and (growth_pct is None or growth_pct <= a.growth_cap)) if prev else res["count"] == 0
    else:
        ok = True
    if a.sections and not a.json:
        print_sections(res, budget)
    if a.top and not a.json:
        print_top(res, a.top)
    out = {"stage": "READABLE", "pass": ok, "count": res["count"], "perRule": res["perRule"],
           "words": res["words"], "sentences": res["measures"]["sentences"],
           "sentencesOver25": res["measures"]["sentencesOver25"],
           "prevCount": prev["count"] if prev else None, "prevWords": prev["words"] if prev else None,
           "grew": grew, "growthPct": growth_pct,
           "wordsBySection": res["wordsBySection"] if a.json else None,
           "findings": res["findings"][:FINDINGS_MAX],
           "blindSpot": "shape only: a short sentence can still be wrong, a plain word can still be the wrong word; "
                        "the reader brief is the catch for meaning"}
    if not a.json:
        out.pop("wordsBySection")
    print(json.dumps(out, ensure_ascii=False))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

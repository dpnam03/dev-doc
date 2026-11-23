**Foundation 0 — How this KB Works**

| Field | Value |
| :---- | :---- |
| Owner | Emma Nguyen — DiM/DM |
| Audience | All Services Department editors |
| Last reviewed | 2026-10-18 |
| Review cadence | Quarterly |
| Version | v3.0 |
| Linked from | (none — entry point of the KB) |
| Status | Live |

This document is the entry point of the BSS All Services Department Knowledge Base (KB). It defines who owns what, how every Live doc must read, and how every Live doc is structured, named, versioned, and retired.

Read this document before you author or edit any KB doc.

# Part A — Governance Overview

## A1. What this KB is

One Knowledge Base for the whole All Services Department, shared across PM, Dev, QC, BA, CRO, Sales, and Marketing. It tells you how we work day-to-day and where to find what you need.

Read it before you ask someone. Write to it when you learn something worth keeping.

The KB's source of truth is Google Drive. Every member reads and authors KB content there; no other platform substitutes for Drive as the source of truth.

The KB is version-controlled in a Gitea repository (`git.bssdev.cloud/bssdev03/BS-Knowledge-Base`). Editors draft, review, and version documents in git; a scheduled task then syncs each approved version to Google Drive. Git is the version-control source that feeds Drive; Google Drive remains the source of truth.

## A2. Five-layer structure

| Layer | Owner | Contents |
| :---- | :---- | :---- |
| 0\. Department Foundation | DiM/DM | Cross-functional rules, lifecycle, RACI, governance. |
| 1\. Function Operating Manuals | Function Lead | How each function operates day-to-day. One manual per function. |
| 2\. Reference Library | Mixed: Shared \= DiM/DM; per-function \= Function Lead; Tech \= Architect Lead | Templates, tool guides, lookups. |
| 3\. Onboarding Hub | Function Lead | Onboarding paths per function. |
| 4\. Archive | DiM/DM | Read-only. Superseded docs only. |

## A3. Ownership rules

Every Live doc has one named human owner. Not a role alone. Not a team.

| Doc location | Owner |
| :---- | :---- |
| Foundation | DiM/DM |
| Function Operating Manual | Relevant Function Lead |
| Reference Library / Shared | DiM/DM |
| Reference Library / per-function | Relevant Function Lead |
| Reference Library / Tech | Architect Lead |
| Onboarding Hub | Relevant Function Lead |
| Archive | DiM/DM |

The Owner field is rendered as `<Name> — <Role>`. When the person in the role changes, the AI Agent updates the name on every doc owned by that role on its next nightly run. The role anchor remains the same; only the name updates. A doc with no owner is non-compliant. The AI Agent flags it nightly.

## A4. Master Index

The Master Index is a Google Sheet. Every Live and Archived doc is one row. It is the system of record for KB metadata — ownership, lifecycle stage, review dates, version, status.

The AI Agent reads and queries the entire KB, not just the Master Index. The Index exists because some questions — "what does Dev own?", "what is overdue?", "which docs cite Foundation 6?" — need a structured table to answer reliably. Free-form Docs cannot.

Rule: metadata about a doc lives in the Master Index. Content lives in the Doc itself.

| Aspect | Value |
| :---- | :---- |
| Format | Google Sheet |
| Maintained by | AI Agent (read access to KB folder, write access to this sheet) |
| Refresh cadence | Daily |
| Columns | Doc title · Layer · Function · Owner · Audience · Last reviewed · Review cadence · Version · Status · Days since last review · Overdue flag |

## A5. AI Agent permissions

An AI service account holds read access to all KB folders and write access to the Master Index. Permissions:

| Action | Allowed |
| :---- | :---- |
| Read any KB doc | Yes |
| Maintain Master Index | Yes |
| Write metadata in a Live doc (Last reviewed, mechanical changelog entries, Linked from auto-fixes, Owner field name refresh on role change) | Yes |
| Bump minor or major version on a Live doc | Yes, only with Owner's written confirmation in the same thread |
| Write doc body content in a Live doc | Yes, only with Owner's written confirmation in the same thread |
| Write doc body content in a Draft | Yes |
| Promote Draft to Live | No (Owner only) |
| Archive a Live doc | Yes, only with DiM/DM's written confirmation in the same thread, or under the standing auto-archive policy in Section A6 |
| Edit Owner field (assign a different role-holder, not a name refresh) | No |

## A6. Anti-graveyard rules

A doc is non-compliant — and the AI Agent flags it — if any of the following is true:

- No owner.  
    
- Header is missing any required field.  
    
- Doc has been overdue for two consecutive review cycles without remediation.

Owner has 14 days from the AI Agent flag to remediate. If not remediated within 14 days, the AI Agent moves the doc to Archive. This standing rule constitutes the DiM/DM's authorisation for auto-archival; no per-doc DiM/DM confirmation is required for the 14-day timeout path.

# Part B — Writing & Tone Standards

These rules apply to every Live KB doc. A doc that violates any rule is non-compliant and must be revised before staying Live.

## B1. Sentence and paragraph rules

- Maximum sentence length: 28 words. A sentence over 28 words is non-compliant.  
    
- Active voice. Not: *"approval is granted by the PM Lead."* Yes: *"the PM Lead approves."*  
    
- One idea per paragraph. Maximum 5 sentences per paragraph.  
    
- Lead with the answer. The first sentence of every section states the rule or answer. Background follows only if needed.  
    
- No hedging words: typically, generally, usually, often, may, might, could. Use must, is, does, will.  
    
- No corporate-speak. Banned words: leverage, synergy, holistic, robust, best-in-class, seamless, empower, utilize (use "use").

## B2. Doc structure

Every Live doc has these parts in this order:

| Order | Part | Rule |
| :---- | :---- | :---- |
| 1 | Title | One line. Format: "— ". Example: "Foundation 0 — How this KB Works." |
| 2 | Header table | 7-field table. See Part C, Section C1. |
| 3 | Purpose paragraph | 2 to 4 sentences. States what the doc is and who reads it. If you cannot write the purpose in 4 sentences, the doc is doing too many things — split it. |
| 4 | Body sections | Numbered: 1, 2, 3, ... Subsections: 1.1, 1.2, ... No deeper than three levels. A References section, if present, sits after the body sections and carries no number. |
| 5 | Changelog | Table at the bottom. Newest entry on top. See Part C, Section C5. |

## B3. Formatting rules

| Element | Rule |
| :---- | :---- |
| Cross-references | Refer by section number or doc name. Example: "see Section A5" or "see Foundation 8 — RACI & Role Definitions." Do not use the symbol "§". |
| Tables | Use a table only when the content is a list of comparable rows. Do not use tables to organise prose. |
| Bullets | Use bullets only for lists of three or more parallel items. For two items, use prose. For non-parallel items, use prose. |
| Bold | Use bold only on the term being defined or on a key noun in a long paragraph. Do not bold whole sentences. Do not bold for emphasis. |
| Monospace | Use monospace for filenames, folder paths, field names, version strings, and exact identifiers. |
| Internal links | Refer to other KB docs by doc name. Where possible, hyperlink the doc name to the Google Drive URL — visible text is the doc name, the link points to the Google Drive file. The doc name is the source of truth: if the link breaks, the reader finds the doc by name. Never paste a bare URL without the doc name. |

## B4. Length limits

| Doc type | Maximum length |
| :---- | :---- |
| Foundation doc | 3,000 words |
| Operating Manual section | 1,500 words |
| Reference Library entry | 2,000 words |

Markdown has no pages, so B4 counts words. The count covers the body, from the end of the header table to the changelog, and skips fenced code. An Operating Manual counts each numbered top-level section on its own. A body or section over its cap is non-compliant unless an exception below applies.

Exceptions:

- Pure reference data (full RACI matrix, complete tool guide table, etc.) where length is dictated by the data.  
    
- Foundation 0 — How this KB Works. Exempt by scope: it covers the full KB authoring schema (governance, writing/tone, lifecycle/naming/header) in one doc because the three parts share owner, audience, and review trigger.

A doc that uses the pure reference data exception declares it under its Purpose paragraph. The declaration names the cap the doc exceeds, states that the pure reference data exception applies, and names the sections that carry the data.

> Example: "This entry exceeds the 2,000-word cap in Foundation 0 Section B4. The pure reference data exception applies. Sections 4 to 9 carry the data."

A doc over its cap with no declaration is non-compliant.

If a doc exceeds its limit and no exception applies, split it.

## B5. Language

- Default language: English.  
    
- Vietnamese is permitted only for function-specific reference material whose function operates predominantly in Vietnamese.  
    
- Do not mix English and Vietnamese in the same doc.

## B6. AI-agent legibility rules

Every rule in a Live doc must be checkable. A rule is checkable if a reader (human or AI) can answer "is this doc compliant?" with yes or no.

- State the rule. State the failure condition. Example: "Maximum sentence length is 28 words. A sentence over 28 words is non-compliant."  
    
- Use exact numbers, not ranges. Not: "review every few months." Yes: "review quarterly."  
    
- Use exact field names from the header schema when referring to metadata. Not: "the date the doc was last looked at." Yes: "Last reviewed."

## B7. Format defaults

Every KB doc has one canonical file format. The format is fixed at first promotion to Live and changes only on a major version bump.

### B7.1 Foundation docs

Every Foundation doc is markdown. A Foundation doc ships as `.md` at first promotion to Live and at every version bump, major or minor. Failure condition: a Foundation doc with any extension other than `.md` is non-compliant.

A version bump produces the new version in `.md`. The new file replaces the previous one; the previous file moves to Archive per Section C2.3.

### B7.2 Other layers

Markdown is the recommended format for Operating Manuals, Reference Library entries, and Onboarding Hub content. Use `.docx` only when the doc must round-trip through Word — signed templates, client-adjacent artifacts — or when the Owner asks for `.docx` explicitly.

Client-facing documents are exempt from the markdown default. A client-facing document ships in the type that serves its visual purpose best — `.pdf`, `.docx`, `.xlsx`, or a design export. The Owner sets the format at promotion; the Master Index records it.

An internal doc ships as `.html` when its content is an interactive diagram markdown does not render. The file embeds all CSS and JS and loads no external asset. Failure condition: an `.html` doc is non-compliant when markdown renders its content, or when it loads any external asset.

### B7.3 Templates

Templates ship in human-friendly form. A template that editors copy from must render cleanly when opened. The header table, body sections, changelog, and editor-instruction boxes must all be visible and usable without an extra render step. In practice this means most templates ship as `.docx`.

A markdown companion is produced alongside a `.docx` template under either of two triggers. The AI Agent consumes the template directly, or the template is copied into a markdown Foundation doc.

### B7.4 Sheets and registers

Sheets specs are written as markdown tables in the relevant doc unless the Owner asks for an actual `.xlsx`. The Master Index itself is a Google Sheet (Section A4); its column spec lives in this doc, not in a separate `.xlsx`.

### B7.5 Font rule for `.docx`

When `.docx` is used, the font is Arial throughout — body, headings, tables, changelog. Markdown carries no font. If a markdown doc is later exported to `.docx`, the export applies Arial.

# Part C — Lifecycle, Naming & Header

This part defines how every KB document is named, versioned, reviewed, and retired.

## C1. Required header

Every KB doc starts with a 7-field table at the top.

| Field | Format | Rule |
| :---- | :---- | :---- |
| Owner | Named human — Role | One person. Not a role alone, not a team. Example: Emma Nguyen — DiM/DM. The AI Agent updates the name when the role-holder changes. |
| Audience | Function name(s) or "All Services Department" | States who must read the doc. |
| Last reviewed | YYYY-MM-DD | Updated by Owner at every review. AI Agent may also update on mechanical refresh. |
| Review cadence | Monthly · Quarterly · Semi-annual · Annual · On change | Drives the Master Index overdue flag. |
| Version | vX.Y | v0.x while drafting outside KB. v1.0 or higher once Live. |
| Linked from | One doc name per row | Inbound references — other KB docs that link to this one. Used to trace impact when this doc changes. Maintained by the AI Agent. |
| Status | Draft · Live · Archive | Lifecycle stage. Must match the folder the doc lives in. |

A doc missing any required field is non-compliant. The AI Agent flags it nightly.

All editors draft from the published template: `Ref_Shared_doc-template_v1.1.docx`. Do not write the header from scratch.

## C2. Lifecycle

Two states inside KB folders: Live and Archive. Drafts happen outside KB folders.

| State | Where it lives | Who can edit |
| :---- | :---- | :---- |
| Draft | Outside KB folders (personal Drive, scratch folder, local file) | Author. AI Agent may write content. |
| Live | Inside the relevant KB folder | Owner, or AI Agent with Owner's written confirmation in-thread. |
| Archive | Inside `4. Archive/` | No one. Content is frozen. |

A version bump replaces the file. The Owner adds the new file — with the bumped version in its filename — and moves the previous version file to `4. Archive/`. In git this is a `git mv` of the previous file into `4. Archive/` plus a commit of the new file, merged to `master` by Pull Request. The changelog table inside the new file also carries the version history.

The previous version stays in `4. Archive/` as a frozen record. Git history also preserves it; `4. Archive/` keeps the superseded file browsable in Google Drive after the sync.

### C2.1 Promote Draft to Live

Steps, in order:

- Owner reviews the draft and approves the content.  
    
- Author or Owner places the file in the correct KB folder with the correct filename.  
    
- Version becomes v1.0.  
    
- All 7 header fields are filled. Status is set to Live.

### C2.2 Re-review

At each cadence checkpoint, the Owner re-reads the doc and applies one of three outcomes:

| Outcome | Action |
| :---- | :---- |
| No content change | Update Last reviewed only. No version bump. |
| Content edit | Bump minor version (v1.0 to v1.1). Update Last reviewed. Add changelog entry. |
| Major change (new section, restructure, policy reversal) | Bump major version (v1.1 to v2.0). Update Last reviewed. Add changelog entry. |

A bump replaces the file and moves the previous version to `4. Archive/`. See Section C2.

### C2.3 Live to Archive

A Live doc moves to Archive when any of these is true:

- The doc has been replaced by a new doc.  
    
- The doc has been retired (the topic no longer applies).  
    
- The doc has been overdue for two consecutive review cycles without remediation (see Section A6).

The DiM/DM authorises archival. The AI Agent executes the move on DiM/DM written confirmation, or under the standing 14-day timeout policy in Section A6. The Owner cannot authorise archival of their own doc.

## C3. Naming

### C3.1 File pattern

`[Layer]_[Function]_[Section]_[Topic]_v[Version].[ext]`

| Slot | Allowed values | Rule |
| :---- | :---- | :---- |
| Layer | Foundation · OM · Ref · Onboard · Archive | Required. |
| Function | PM · Dev · QC · BA · CRO · Sales · Mkt · Tech · Shared | Omit for Foundation. Foundation is department-wide. |
| Section | s0 · s1 · s1.5 · s2 ... | For Foundation docs, this slot doubles as the Foundation doc number (Foundation 0 → s0, Foundation 6 → s6). For Operating Manuals and other multi-section docs, this slot is the section index within that doc. Omit if the doc is not section-based. |
| Topic | kebab-case slug | Lowercase. Words joined by hyphens. No spaces. No underscores. No capitals. Example: lifecycle-naming-header. |
| Version | v0.1 · v1.0 · v1.1 ... | Use a dot, not an underscore. |
| Extension | md (recommended) · docx · xlsx · pdf · html | Match the file format. `md` is the recommended default, and is required for Foundation docs per Section B7.1. Section B7 sets exceptions, including visual formats for client-facing documents and `html` for interactive internal diagrams. |

### C3.2 Examples

- `Foundation_s0_how-this-kb-works_v1.2.md`  
    
- `OM_PM_s3_jira-setup_v1.2.docx`  
    
- `Ref_Shared_tool-guide-passbolt_v1.0.docx`  
    
- `Ref_Dev_coding-standard-magento_v1.0.docx`

### C3.3 Folders

BS \- All Services Department Knowledge Base/

    0\. Department Foundation/

    1\. Function Operating Manuals/

    2\. Reference Library/

        Shared/

        PM/  Dev/  QC/  BA/  CRO/  Sales/  Mkt/  Tech/

    3\. Onboarding Hub/

    4\. Archive/

Folders are presentation. The Master Index keys off the filename and the folder path.

## C4. Versioning

| Change type | Bump | Example |
| :---- | :---- | :---- |
| Typo, formatting, link fix | None | v1.2 stays v1.2 |
| Content edit | Minor | v1.2 to v1.3 |
| New or removed section, restructure | Major | v1.3 to v2.0 |
| Policy reversal, owner change | Major | v2.0 to v3.0 |
| Draft iteration outside KB | Minor on v0.x | v0.1 to v0.2 |
| First promotion to Live | v0.x to v1.0 | v0.5 to v1.0 |

Format-only re-export (such as `.docx` to `.md` with no content change) is not a bump of any kind. See Section B7.

## C5. Changelog

Every Live doc carries a changelog table at the bottom. Newest entry on top.

| Date | Version | Change | By |
| :---- | :---- | :---- | :---- |
| 2026-04-30 | v1.0 | Promoted to Live | Emma Nguyen — DiM/DM |
| 2026-04-29 | v0.2 | Edit example | Author name |

Both the Owner and the AI Agent may write changelog entries. Every entry tied to a content change must cite the Owner-approval thread (date and approver). Mechanical entries — review-date refresh, link auto-fix, Owner-name refresh on role change — need no approval reference.

## C6. Archive rules

- Archived docs are not edited by anyone. Content is frozen at the moment of archival.  
    
- The DiM/DM authorises every archive transition. The AI Agent executes the move on DiM/DM written confirmation, or under the standing 14-day timeout policy in Section A6.  
    
- Filename suffix on archive: `_ARCHIVED_YYYY-MM-DD`.

# Changelog

| Date | Version | Change | By |
| :---- | :---- | :---- | :---- |
| 2026-10-18 | v3.0 | B7.1 states that every Foundation doc is markdown, with the failure condition per B6. The transitional rule is removed. Existing `.docx` Foundation docs no longer stay `.docx` until their next major bump. A minor bump no longer keeps the `.docx` extension. Every Foundation doc s0 to s9 is already `.md`, so the removed rule governed nothing. C3.1's Extension row names `md` as required for Foundation docs. Major bump v2.4 to v3.0 per C4: withdrawing a stated permission is a policy reversal. The v2.4 file is archived per C2. Owner-approved by Emma Nguyen — DiM/DM in this thread, 2026-10-18. | Claude (drafter for Emma) |
| 2026-10-04 | v2.4 | A1 names the repository's new location, `git.bssdev.cloud/bssdev03/BS-Knowledge-Base`. The repository moved there from `EmmaNguyen/BS-Knowledge-Base` by a Gitea ownership transfer, which keeps its history, pull requests and CI. The old address redirects. Minor bump v2.3 to v2.4 produced in `.md` per B7.1; the v2.3 file is archived per C2. Owner-approved by Emma Nguyen — DiM/DM in this thread, 2026-10-04. | Claude (drafter for Emma) |
| 2026-10-02 | v2.3 | B4 states the length caps in words, because Markdown has no pages. The caps are 3,000 words for a Foundation doc, 1,500 for an Operating Manual section and 2,000 for a Reference Library entry. B4 says what the count covers and how a doc declares the pure reference data exception, with failure conditions per B6. B2 allows an unnumbered References section after the body. The KB PR check reads these rules and checks them on every PR. Minor bump v2.2 to v2.3 produced in `.md` per B7.1; the v2.2 file is archived per C2. Owner-approved by Emma Nguyen — DiM/DM in this thread, 2026-10-02. | Claude (drafter for Emma) |
| 2026-08-19 | v2.2 | C3.1 extension list adds `html`. B7.2 adds one rule for interactive internal diagrams. An internal doc ships as `.html` when markdown does not render its content, embeds all CSS and JS, and loads no external asset. The rule carries its failure condition per B6. This repeats the 2026-07-06 v2.1 move that made `pdf` legal for the same reason. Minor bump v2.1 to v2.2 produced in `.md` per B7.1; the v2.1 file is archived per C2. Owner-approved by Emma Nguyen — DiM/DM in this thread, 2026-08-19. | Claude (drafter for Emma) |
| 2026-07-06 | v2.1 | B7.2 and C3.1 updated: markdown is the recommended default; client-facing documents ship in the format that serves the visual purpose; extension list adds `pdf`. Resolves the conflict with the DiM/DM ruling that PDF is permitted in the Reference Library. Owner-approved in chat, 2026-07-06. | Emma Nguyen — DiM/DM |
| 2026-07-05 | v2.0 | Added the version-control layer to the KB model and switched the archival rule. A1 now names the Gitea repo (`git.bssdev.cloud/EmmaNguyen/BS-Knowledge-Base`) as the version-controlled source that feeds Google Drive; Google Drive remains the source of truth; the "no other platform" line is replaced. C2 now moves the previous version file to `4. Archive/` on every version bump (previously the old version was not archived — this also resolves the prior conflict with B7.1); C2.2 pointer updated to match. Major bump v1.2 to v2.0 produced in `.md`; the v1.2 file is archived per B7.1. Owner-approved by Emma Nguyen — DiM/DM in this thread, 2026-07-05. | Claude (drafter for Emma) |
| 2026-05-06 | v1.2 | Added Section B7 — Format defaults. Markdown required for new Foundation docs and major bumps; existing `.docx` Foundation docs stay `.docx` until next major bump; format-only re-export is not a version bump. Templates ship `.docx` with markdown companion when AI Agent or markdown Foundation doc consumes the template. Arial font rule for `.docx` made explicit. C3.1 Extension row points to B7 for which extension to use. C4 carries the no-bump note for format-only re-export. Template reference in C1 updated to `Ref_Shared_doc-template_v1.1.docx`. Added execution-method note under C2: a version bump may be executed by editing the Live file in place or by replacing the file (delete old, upload new with bumped filename); both are version bumps, neither is archival. C2.2 carries a one-line pointer to the same. Owner-approved in drafting thread on 2026-05-06. | Emma Nguyen — DiM/DM |
| 2026-05-06 | v1.1 | Applied DiM/DM convention as the single label for the Division Manager role across the doc. A2 heading corrected from "Three-layer structure" to "Five-layer structure" (table was already 5 rows). C1 header-example name and C5 example changelog row updated to DiM/DM. "Services Department" updated to "All Services Department" where it refers to the project-wide org-unit term. Owner-approved in drafting thread on 2026-05-06. | Emma Nguyen — DiM/DM |
| 2026-05-03 | v1.0 | Promoted to Live. Reconciled v0.3 internal conflicts: header schema set to 7 fields (added Status); Linked from defined as inbound references; AI Agent permitted to write Live bodies with Owner written confirmation in-thread (C2 updated to match); DM is sole archive authoriser, AI executes on DM confirmation or under A6 14-day timeout standing policy; A6 auto-archive policy stated as standing DM authorisation; Owner-field name updates automatically when role-holder changes; Foundation 0 added as documented exception to B4 length cap; C3.1 clarified that the Section slot doubles as Foundation doc number; C5 changelog rule reframed around human-in-loop at promotion/edit-approval; template reference corrected to Shared\_doc-template\_v1.0.docx. | Emma Nguyen — DM |
| 2026-04-30 | v0.3 | Restructured into Parts A/B/C. Initial draft of governance, writing/tone, and lifecycle/naming/header in one doc. | Claude (drafter for Emma) |
| 2026-04-30 | v0.2 | Foundation restructured from 5 to 7 docs in the Plan. Doc 0 scope set to KB authoring schema. | Claude (drafter for Emma) |
| 2026-04-30 | v0.1 | Initial Plan draft. | Claude (drafter for Emma) |


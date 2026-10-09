# AGENTS.md — Wiki schema and working rules

This project (CS 7633 HRI, Fall 2026) is maintained with the **LLM Wiki** pattern described in
[llm-wiki.md](llm-wiki.md). The LLM agent writes and maintains everything under `wiki/`; the humans
curate sources, ask questions and approve plans.

## Layers

| Layer | Location | Owner | Notes |
|---|---|---|---|
| Raw sources: documents | `src/*.pdf`, `../proposal/*` | Humans | Papers, proposal, course docs. Never edited by the agent. |
| Raw sources: code | `src/` (everything except `wiki/`, `AGENTS.md`, `CLAUDE.md`, `llm-wiki.md`, PDFs) | Agent, once a plan is approved | Must always match what the wiki describes. |
| Wiki | `src/wiki/` | Agent | Markdown, interlinked, Obsidian-friendly. |
| Schema | `src/AGENTS.md` (this file) | Agent + humans | Co-evolved. `CLAUDE.md` just imports this file. |

## Directory layout of `wiki/`

```
wiki/
  index.md        catalog of every page, one line each, by category (read this FIRST)
  log.md          append-only chronological record of wiki operations
  changelog.md    append-only record of code changes (one entry per implemented plan)
  overview.md     the project on one page: research question, conditions, current status
  sources/        one summary page per ingested raw document
  concepts/       topic pages synthesized across sources (study design, scene design, robot, ...)
  codebase/       pages describing the code AS IT EXISTS NOW (architecture, modules, how to run)
  plans/          proposed feature plans; the only part of the wiki allowed to differ from the code
```

## Page conventions

- File names: lowercase kebab-case, `.md`.
- Every page (except `index.md`, `log.md`, `changelog.md`) starts with YAML frontmatter:
  ```yaml
  ---
  title: Human-readable title
  type: source | concept | codebase | plan | overview
  sources: [list of raw-source paths or source-page names this page draws on]
  updated: YYYY-MM-DD
  status: (plans only) draft | approved | in-progress | implemented
  ---
  ```
- Link to other wiki pages with Obsidian wikilinks: `[[dogan-2022-follow-up-clarifications]]`.
- Cite raw sources by page link plus location, e.g. "([[dogan-2022-follow-up-clarifications]], §III-A)".
- Mark anything not verified against a source or the code with **(unverified)**. Never state an
  unverified fact about a library/API as settled — check it or flag it.
- Flag contradictions between sources explicitly with a bold **Contradiction:** paragraph on both pages.
- **Never use the `<` or `>` characters in wiki markdown files** — they break rendering in Obsidian
  (parsed as HTML tags; this includes blockquote/callout lines starting with that character). Write
  comparisons in words ("under", "more than") or with Unicode (≤, ≥, →), and placeholders as `{name}`.
- Dates are absolute (YYYY-MM-DD), never "next week".

## Workflows

### Ingest (new raw source)
1. Read the source fully (use PyMuPDF / `pdftotext` for PDFs; render figure pages to images when figures matter).
2. Write `wiki/sources/{slug}.md`: citation, one-paragraph summary, key claims, what it means for *this* project.
3. Update every affected concept / overview page; add new concept pages for recurring ideas.
4. Update `index.md` and append to `log.md`.

### Query
1. Read `index.md`, then the relevant pages; answer with wikilink citations.
2. If the answer is reusable (comparison, analysis, decision), file it as a new page and log it.

### Lint
Check for contradictions, stale claims, orphan pages, missing cross-links, concepts without pages,
wiki-vs-code drift in `codebase/`. Record the pass in `log.md`.

### Feature implementation (two separate prompts — never both in one)
1. **Plan prompt** (wiki only, no code changes): read the wiki, write `wiki/plans/{slug}.md` with
   status `draft`: goal, context links, design, file-by-file changes, interfaces, milestones,
   verification steps, open questions. Add to `index.md`, log it. Stop and wait for approval.
2. **Implement prompt** (code only, after the human approves): implement the approved plan. Then, in
   that same bookkeeping pass, bring the wiki back in sync: move the durable content from the plan into
   `codebase/` pages, delete the plan file (or mark `implemented` and move its remaining open items to a
   new plan), append to `changelog.md` and `log.md`, update `index.md`.

The rule from llm-wiki.md: *every prompt either reads the wiki to plan, or changes the code — never
both*. Syncing `codebase/` pages right after implementing is part of the implement step, not planning.

## Log format

`log.md` entries start with `## [YYYY-MM-DD] {op} | {title}` where op is one of
`init`, `ingest`, `query`, `lint`, `plan`, `implement`. Then 1–5 bullets of what changed.
`grep "^## \[" wiki/log.md | tail -5` shows the recent history.

## Project-specific notes

- Dev machine is **Windows 11** (PowerShell + Git Bash). Anything simulator-related must be checked for
  Windows support before it is planned around. Verified requirements (Python 3.11, `mujoco==3.2.6`,
  lidar sensors disabled, no sim cameras during teleop) are in `wiki/concepts/dev-environment.md`.
- **Python environments use conda (Miniforge), not uv/venv.** The environment is defined in
  `src/environment.yml` (env name `hri_stretch`). The agent edits that file and documents it in
  `wiki/concepts/dev-environment.md`, but **never creates, updates or removes conda environments
  itself**; the human runs the conda commands. When a new dependency is needed, add it to
  `environment.yml` and tell the human to run `conda env update -f environment.yml --prune`.
- Team: Om Shivam Verma, Rena Nakashima, Siddhesh Girase.

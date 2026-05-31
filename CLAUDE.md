# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A data-processing project (not yet a codebase — no source files exist yet). The goal is to take a **Veritrade customs-data export** of Peruvian truck imports and produce a clean, analysis-ready table by **structured extraction of the semi-structured `Descripción Comercial` field**.

The full design lives in `docs/superpowers/specs/2026-05-30-extraccion-descripcion-comercial-design.md` — **read it before implementing.** It is the source of truth for column mappings, parser logic, and scope.

## The source data

`Veritrade_JOSE.GOMEZ@DWMOTORS.PE_PE_I_20260430094944.xlsx`

- **Origin:** Veritrade (foreign-trade intelligence / customs data), downloaded by DW Motors (Peru). Filename encodes: country `PE`, type `I` (imports), timestamp `20260430094944`.
- **Scope:** Peru imports, customs code `8704229000` (diesel cargo trucks), Jan-2023 to Apr-2026.
- **Shape:** ~12,417 data records, 56 columns. The single sheet is named `Veritrade`.

Critical layout facts (the file is NOT a flat table):
- Rows 1–5 are a banner; the **real header is row 6**; data starts at **row 7**. Load with `skiprows=5` (pandas) or start iterating at `min_row=7` (openpyxl).
- `Descripción Comercial` (col 39) is **byte-for-byte identical** to the concatenation of `Descripcion1`–`Descripcion5` (cols 48–52). Use either; don't treat them as independent data.
- The description is **truncated at the source** (~380–454 chars, sometimes mid-word). Trailing codes (e.g. suspension `SD/SP`, sometimes `KILOMETRAJE`) may be cut. This is not recoverable.

## The `Descripción Comercial` format

Semi-structured, using a Peruvian-customs code dictionary: `CÓDIGO:valor` pairs separated **inconsistently** by commas or spaces, prefixed by a category token `N1`/`N2`/`N3`. Example:

```
N3  MARCA:DONGFENG, MODELO:DF-1718, AÑO MOD:2023, VI:LGDX..., CC:4500, EJ:2, FR:4X2, PB:17590...
```

Key codes → fields: `MARCA`, `MODELO`, `VERSION`, `AÑO MOD`(year), `VI`(VIN), `CH`(chassis), `MO`(engine), `CO`(fuel), `C1`(color), `NC`(cylinders), `CC`(displacement), `PM`(power, e.g. `132@2500`), `EJ`(axles), `FR`(drive), `TT`(transmission), `CA`(body), `AS`(seats), `PA`(doors), `PB/PN/CU`(gross/net/payload weight), `LA/AN/AL`(length/width/height), `DE`(wheelbase), `KILOMETRAJE`. Full mapping table is in the spec.

Parser approach (decided): **deterministic dictionary parser** (approach A) — split on known codes, value runs until the next known code. No LLM in v1. An LLM/hybrid pass (approach B) is deferred and will be decided using the parse-coverage report this v1 produces. Do not invent values for unmatched text.

## Working conventions

- This directory is **not a git repo**. Don't assume git operations work.
- Specs follow the superpowers workflow under `docs/superpowers/specs/`. Brainstorm → spec → (plan) → implement.
- Output target: `camiones_8704229000_estructurado.xlsx`, one row per imported unit, plus a printed per-field **coverage report** (the signal for whether approach B is needed).
- Per org policy: this is real commercial/customs data — do not send it to external services (no LLM extraction without explicit approval).

## Tooling conventions (user preference, applies to all their projects)

- **Task tracking: use `bd` (beads), NOT `TodoWrite`/`TaskCreate` or markdown TODO lists.** `bd` is installed; this project has no database yet — run `bd init` when tracking begins. Quick reference:
  - `bd ready` — find available work · `bd show <id>` — view issue · `bd update <id> --claim` — claim · `bd close <id>` — complete · `bd create` — new issue.
  - Run `bd prime` for the full workflow/command reference and session-close protocol.
- **Persistent knowledge: use `bd remember`, NOT `MEMORY.md` files.**

## Environment

Python with `pandas` and `openpyxl` is the intended stack. No build/test/lint tooling is configured yet — add it alongside the first script.


<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->

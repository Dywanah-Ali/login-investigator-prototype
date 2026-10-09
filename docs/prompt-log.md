# Prompt Log

Every prompt given to Claude during the build, in order. This log feeds the "prompts used" and
"iterations" sections of the Google Doc, so entries are kept as they happened, including the ones that
did not work.

**Phase 0 (planning)** happened in a separate conversation with Claude acting as supervisor, before any
code. Its outcome is in [`phase0-summary.md`](phase0-summary.md) and [`PRD.md`](PRD.md).

## Entry format

```
### P-001 · 2026-10-09 15:30 · Phase 1 Setup

**Prompt:**
> The author's prompt, verbatim.

**Purpose:** what this prompt was meant to achieve.
**Result:** what came back, in one or two lines.
**Next:** what changed or was tried next. Link a bug entry if one was found (B-001).
```

## Entries

### P-001 · 2026-10-09 17:20 · Phase 1 Setup

**Prompt:**
> hello claude. Read PROGRESS.md and tell me where we are pls

**Purpose:** first prompt of the build session; check that Claude Code picks up the handoff from
planning (PROGRESS.md, CLAUDE.md, PRD) and finds the next step.
**Result:** Claude read PROGRESS.md and the PRD "Tech stack" section, reported Phase 1 at the step
"uv project on Python 3.12", found that uv was not installed, and proposed a plan for the step. The
author approved the plan and chose Homebrew to install uv. Homebrew started compiling from source
(B-001), so the author switched to Astral's official installer. Result: uv 0.12.24, a uv project on
Python 3.12.14, dependencies locked in `uv.lock`, and the `SqliteSaver` import confirmed.
**Next:** `env.example` and a README skeleton. Claude proposed recording the `SqliteSaver` package
and the uv install method in the PRD decisions log; the author declined, so those facts stay in the
bug log and PROGRESS.md only.

### P-002 · 2026-10-09 · Phase 1 Setup

**Prompt:**
> go ahead

**Purpose:** approve the next step: `env.example` with key names only, and a README skeleton.
**Result:** Claude read only the key names from `.env` (`OPENROUTER_API_KEY`, `ABUSEIPDB_API_KEY`)
and wrote `env.example` with empty values and where to get each key. It also wrote `README.md` with
headings, requirements, the synthetic-data note and links to the project documents. Checked: the
names match `.env`, `env.example` holds no values and is not git-ignored, and neither file holds
personal info.
**Next:** one test call to gpt-4o-mini through OpenRouter from LangChain.

### P-003 · 2026-10-09 · Phase 1 Setup

**Prompt:**
> go

**Purpose:** prove the app can reach gpt-4o-mini through OpenRouter, the way the course does it.
**Result:** a throwaway script called `init_chat_model("openai/gpt-4o-mini", model_provider="openai",
base_url="https://openrouter.ai/api/v1", temperature=0)` with the key from `.env`. The model replied
"connection works"; OpenRouter reported model `openai/gpt-4o-mini` and 17 tokens. The key was never
printed. The script was not added to the repo.
**Next:** one test lookup against AbuseIPDB.

### P-004 · 2026-10-09 · Phase 1 Setup

**Prompt:**
> go

**Purpose:** prove the app can reach the AbuseIPDB v2 check endpoint over HTTPS with the key.
**Result:** a throwaway script looked up `8.8.8.8` (Google's public DNS, a harmless address).
Status 200: abuse confidence score 0, country US, ISP Google LLC, whitelisted, but 233 reports, the
latest today. Daily limit 1,000, 999 left. The key was never printed. The script was not added to
the repo.
Observation: the report count alone is misleading. A well-known safe address still collects
hundreds of reports, and AbuseIPDB scores it 0 because it is whitelisted. The agent and the rules
should judge an IP by `abuseConfidenceScore`, not by `totalReports`.
**Next:** the author creates the private GitHub repo.

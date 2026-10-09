# Progress Tracker — Login Investigator

**Current phase:** 3 — Core logic
**Current step:** Gate 1 passed; the author reviews it before Phase 4 (⏸️ UI design pause applies)
**Working deadline:** Sunday 11 October 2026, 21:59 local (UTC+3). Aim: submit Friday 9 October.

How to read this file: each phase is a list of steps. A finished step is ticked and struck out:
`- [x] ~~step~~`. A **gate** ends a phase and must pass before the next phase starts.
📸 marks a moment to take a screenshot for the Google Doc. 👤 marks a step only the author can do.
Also take a 📸 of every bug when it appears, and again when it is fixed.
Name each file with a number and a short label, for example `01-first-prompt.png`, and save it in `screenshots/`.

---

## Phase 0 — Planning ✅

- [x] ~~Read the Week 1 handout and the course LangChain repo~~
- [x] ~~Choose Path C: authentication-log analyzer with an in-app agent~~
- [x] ~~Decide the stack, the three tools, AbuseIPDB and `SqliteSaver`~~
- [x] ~~Write the full PRD (`docs/PRD.md`)~~
- [x] ~~Write the one-page summary for the Google Doc (`docs/phase0-summary.md`)~~
- [x] ~~Answer the five open questions and read the submission form~~
- [x] ~~Create this project folder, `CLAUDE.md` and this tracker~~

## Phase 1 — Setup ✅

- [x] ~~📸 Process: the first prompt in VS Code, and Claude's answer (proves the handoff works)~~ (`screenshots/01-first-prompt.png`)
- [x] ~~👤 Create the AbuseIPDB account and an API key~~
- [x] ~~👤 OpenRouter key ready~~ (the author's existing key, shared with other projects, with its own limits; the author's ruling)
- [x] ~~👤 Put both keys into `.env` (never committed)~~ (git-ignored and readable only by the owner)
- [x] ~~uv project on Python 3.12 with pinned dependencies; confirm the `SqliteSaver` package name~~
  (Python 3.12.14, `uv.lock`; `langgraph-checkpoint-sqlite` 3.1.1, import `langgraph.checkpoint.sqlite` works)
- [x] ~~`env.example` with key names only, and a README skeleton~~ (names match `.env`, no values, not git-ignored)
- [x] ~~One test call to gpt-4o-mini through OpenRouter from LangChain~~ (reply "connection works", model `openai/gpt-4o-mini`, 17 tokens)
- [x] ~~One test lookup against AbuseIPDB~~ (8.8.8.8: status 200, score 0, whitelisted, 999 of 1,000 checks left)
- [x] ~~👤 Create the GitHub repo, **private** until the final review~~ (`login-investigator-prototype`, private, description set)
- [x] ~~Set this repo's git author email to the GitHub "noreply" address, so commits never carry a personal email~~ (author name kept: the author's ruling)
- [x] ~~First commit 📸~~ (`e223abd`, not pushed)

## Phase 2 — Data ✅

- [ ] 📸 Process: the prompt that starts this phase, and Claude's plan
- [x] ~~Decide the benign IP strategy (open question in the PRD)~~ (reserved documentation ranges plus three real decoys; PRD Data section and decisions log)
- [x] ~~Choose publicly reported attacker IPs and the three decoy IPs, and save their AbuseIPDB responses~~ (six files in `data/ip_reputation/`; roles in prompt log P-009)
- [x] ~~Seeded data generator: about 50 users, seven days~~ (`login_investigator/generator.py`; 50 users, 1,856 rows; two runs byte-identical)
- [x] ~~Plant scenarios S1 to S5~~ (11 tests pass; answers in `evals/ground_truth.json`)
- [x] ~~Generate the CSV and document how it was made 📸~~ (`data/logins.csv`; README section and `docs/data-generation.md`)

## Phase 3 — Core logic

- [ ] 📸 Process: the prompt that starts this phase, and Claude's plan
- [x] ~~Load and validate the CSV~~ (`login_investigator/loader.py`; 23 tests)
- [x] ~~Rule: brute force~~ (`login_investigator/rules.py`)
- [x] ~~Rule: password spraying~~
- [x] ~~Rule: success after repeated failures~~
- [x] ~~Rule: sign-in from a new country~~
- [x] ~~Search and filter function~~ (`login_investigator/search.py`; 13 tests)
- [x] ~~Unit tests: each rule catches its planted scenario~~ (26 rule tests, both directions; loosened thresholds make 14 of them fail)

**Gate 1:** the tests prove the rules catch S1 to S4. ✅ **Passed 9 Oct: 72 tests pass.** Waiting for the author's review before Phase 4.

## Phase 4 — Dashboard

- [ ] 📸 Process: the prompt that starts this phase, and Claude's plan
- [ ] ⏸️ **Pause before any UI design.** Think the screens through with the author first; no UI code until they agree (the author's instruction, 9 Oct)
- [ ] Decide the final screens (open question in the PRD)
- [ ] Overview screen 📸
- [ ] Alerts screen 📸
- [ ] Log explorer screen 📸
- [ ] Global filters behave the same on every screen
- [ ] Every metric shows its unit
- [ ] Empty filter results show a clear message
- [ ] "Synthetic data" label is visible

## Phase 5 — Agent

- [ ] 📸 Process: the prompt that starts this phase, and Claude's plan
- [ ] System prompt template with today's date and the data-only rule
- [ ] Tool: `find_suspicious_activity`
- [ ] Tool: `search_logins`
- [ ] Tool: `lookup_ip_reputation`, with saved responses
- [ ] Agent with `create_agent`, gpt-4o-mini through OpenRouter
- [ ] `SqliteSaver` memory, one thread per investigation, agent created once per session
- [ ] Structured incident report
- [ ] Investigator screen with chat and the list of past investigations 📸

**Gate 2:** the core scenario from the PRD runs end to end in the live app.

## Phase 6 — Evals

- [ ] 📸 Process: the prompt that starts this phase, and Claude's plan
- [ ] Write 15 to 20 questions with gold answers
- [ ] Scoring script
- [ ] Run each question several times; record results with date and prompt version
- [ ] Fix and re-run until the target is met 📸

**Gate 3a:** 90% overall, and 100% for the injection and refusal checks.

## Phase 7 — Deliverables and submission

- [ ] 📸 Process: the prompt that starts this phase, and Claude's plan
- [ ] Every acceptance criterion in the PRD ticked with evidence
- [ ] README complete; the app starts from a fresh clone
- [ ] Scan the repo history for secrets
- [ ] Google Doc: Phase 0 summary, build breakdown, prompts, iterations, bugs, learnings, eval results, screenshots
- [ ] Video script, then record with Loom (5 minutes or less) and upload to Google Drive
- [ ] 👤 The author reviews everything

**Gate 3b:** The author has reviewed the repo, the doc and the video.

- [ ] **Remove the author's name and all personal info from the repo before it goes public:** every file, and the git history (commit authors included). Search the whole repo, not only the docs.
- [ ] 👤 Make the repo public; share both Drive links as "anyone with the link"
- [ ] 👤 Open all three links in a private browser window
- [ ] 👤 Submit the form

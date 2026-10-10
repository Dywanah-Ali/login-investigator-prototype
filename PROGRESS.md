# Progress Tracker — Login Investigator

**Current phase:** 7 — Deliverables and submission
**Current step:** Phase 7, Gate 3b: the author reviews the repo; then push, make public, submit
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

- [x] ~~📸 Process: the prompt that starts this phase, and Claude's plan~~ (`screenshots/02-data-writeup-prompt.png`; shows the data write-up prompt, which ended the phase, not the one that started it; the author's ruling)
- [x] ~~Decide the benign IP strategy (open question in the PRD)~~ (reserved documentation ranges plus three real decoys; PRD Data section and decisions log)
- [x] ~~Choose publicly reported attacker IPs and the three decoy IPs, and save their AbuseIPDB responses~~ (six files in `data/ip_reputation/`; roles in prompt log P-009)
- [x] ~~Seeded data generator: about 50 users, seven days~~ (`login_investigator/generator.py`; 50 users, 1,856 rows; two runs byte-identical)
- [x] ~~Plant scenarios S1 to S5~~ (11 tests pass; answers in `evals/ground_truth.json`)
- [x] ~~Generate the CSV and document how it was made 📸~~ (`data/logins.csv`; README section and `docs/data-generation.md`)

## Phase 3 — Core logic

- [x] ~~📸 Process: the prompt that starts this phase, and Claude's plan~~ (`screenshots/03-phase3-prompt.png`; shows the prompt, not the plan)
- [x] ~~Load and validate the CSV~~ (`login_investigator/loader.py`; 23 tests)
- [x] ~~Rule: brute force~~ (`login_investigator/rules.py`)
- [x] ~~Rule: password spraying~~
- [x] ~~Rule: success after repeated failures~~
- [x] ~~Rule: sign-in from a new country~~
- [x] ~~Search and filter function~~ (`login_investigator/search.py`; 13 tests)
- [x] ~~Unit tests: each rule catches its planted scenario~~ (26 rule tests, both directions; loosened thresholds make 14 of them fail)

**Gate 1:** the tests prove the rules catch S1 to S4. ✅ **Passed 9 Oct: 72 tests pass.** Supervisor review done the same day: four fixes
(bugs B-004 and B-005, threshold wording, README limitations); 99 tests pass. Waiting for the
author before Phase 4.

## Phase 4 — Dashboard

- [x] ~~📸 Process: the prompt that starts this phase, and Claude's plan~~ (`screenshots/04-phase4-plan.png`)
- [x] ~~⏸️ **Pause before any UI design.** Think the screens through with the author first; no UI code until they agree (the author's instruction, 9 Oct)~~ (all four screens agreed: `docs/ui-design.md`)
- [x] ~~Decide the final screens (open question in the PRD)~~ (four screens; filters on the three dashboard screens only; past investigations inside the Investigator. PRD decisions log)
- [x] ~~Overview screen 📸~~ (`app/screens/overview.py`; checked in the browser; `screenshots/05-overview.png`)
- [x] ~~Alerts screen 📸~~ (`app/screens/alerts.py`; checked in the browser; `screenshots/06-alerts.png`)
- [x] ~~Log explorer screen 📸~~ (`app/screens/log_explorer.py`; checked in the browser; `screenshots/07-log-explorer.png`)
- [x] ~~Global filters behave the same on every screen~~ (`tests/test_app.py`: one filter change checked on all three screens)
- [x] ~~Every metric shows its unit~~ (`tests/test_app.py`; singular and plural)
- [x] ~~Empty filter results show a clear message~~ (`tests/test_app.py`, all three screens; seen in the browser)
- [x] ~~"Synthetic data" label is visible~~ (`tests/test_app.py`, all three screens)

**Phase 4 result (9 Oct):** 134 tests pass. Run with `uv run streamlit run app/main.py`.
Bugs B-006 to B-008 found and fixed. The author asked to start Phase 5 in a fresh session.

**Handoff notes for Phase 5 (read before starting):**
- The Investigator design is agreed: `docs/ui-design.md`, section Investigator. Build it as a fourth
  page in `app/main.py`; the shared filters are rendered only for pages in `DASHBOARD`, so leave the
  Investigator out of that tuple.
- Security rule in the PRD: show the agent's text and the report with links and images off.
- Tool inputs: times must be explicit ISO 8601 (`parse_utc` refuses "today"); search windows include
  the start and exclude the end; usernames match regardless of case. Say all three in the tool
  descriptions.
- Reuse the core: `detect_all` / `Finding.to_dict()` for `find_suspicious_activity`; `search_logins`
  (20-row sample, max 50) for `search_logins`; saved AbuseIPDB responses in `data/ip_reputation/`.
  Reserved addresses should get "reserved, no reputation data" without an API call.
- "Today" in the system prompt is the capture date: `generator.CAPTURED_AT`, not the clock.
- Running all rules takes about 1.5 s; the screens cache it in `app/shared.py` (`all_findings`).

## Phase 5 — Agent

- [x] ~~📸 Process: the prompt that starts this phase, and Claude's plan~~ (`screenshots/08-phase5-plan.png`; shows the plan's first part and the author's streaming request)
- [x] ~~System prompt template with today's date and the data-only rule~~ (`login_investigator/agent.py`; `tests/test_agent.py`)
- [x] ~~Tool: `find_suspicious_activity`~~ (`login_investigator/tools.py`; `tests/test_tools.py`)
- [x] ~~Tool: `search_logins`~~ (`tests/test_tools.py`)
- [x] ~~Tool: `lookup_ip_reputation`, with saved responses~~ (`login_investigator/reputation.py`; `tests/test_reputation.py`; one live lookup of 1.1.1.1 worked, nothing written to disk)
- [x] ~~Agent with `create_agent`, gpt-4o-mini through OpenRouter~~ (five live runs of the core scenario outside the app; bugs B-009 to B-011)
- [x] ~~`SqliteSaver` memory, one thread per investigation, agent created once per session~~ (`login_investigator/investigations.py`; restart test in `tests/test_agent.py`; once-per-session test in `tests/test_investigator_screen.py`)
- [x] ~~Structured incident report~~ (separate chain with structured output; saved into the case; `tests/test_agent.py`)
- [x] ~~Investigator screen with chat and the list of past investigations 📸~~ (`app/screens/investigator.py`; `tests/test_investigator_screen.py`; `screenshots/12-` to `15-`)

- [x] ~~Report button offered only when it adds something new~~ (added after Gate 2, the author's finding; B-017; `tests/test_investigator_screen.py`)
- [x] ~~Download the incident report as a PDF 📸~~ (added after Gate 2, the author's request, 9 Oct; PRD decisions log)
  (`login_investigator/report_pdf.py`; `tests/test_report_pdf.py`; header and footer with TLP:CLEAR, P-034;
  245 tests pass; the author downloaded one from the live app: `screenshots/16-incident-report-pdf.png`)

**Gate 2:** the core scenario from the PRD runs end to end in the live app. ✅ **Passed 9 Oct, Claude's browser run:** all
8 steps, including an app restart and reopening the case; the block request was refused with
specific recommendations. The author's own run followed the same day (screenshots 12 to 15).
Judgement slips seen on the way are in B-013, for the Phase 6 evals.

**Handoff notes for the next session (read before starting):**
- First build the PDF download, then start Phase 6. The decision is in the PRD decisions log.
- PDF rules: plain text only. No link annotations, no images, and no markup parsing. ReportLab's
  `Paragraph` reads HTML-like tags such as `<a>` and `<img>` from the text, so either escape the
  text or use a library call that writes raw text. The core fonts cover Latin-1 only, and the model
  writes characters such as "→" or curly quotes: choose a Unicode font or replace those characters,
  and test with them. A new dependency goes into `pyproject.toml` with a pinned version.
- Put the PDF builder in the core (no Streamlit), test it (every fixed field present, no link
  annotations, an injected link stays plain text), and add `st.download_button` under the report
  card in `app/screens/investigator.py`.
- Restart the app after any change to `login_investigator/`: Streamlit never reloads that folder (B-016).
- Phase 6 starts from the open bugs: B-011 (S5 text ignored but not reported) and B-013 (judgement
  slips; the follow-up miscount happened in both runs inside the app, and in none of the four
  runs read in full outside it).
- Run the agent without the screen: `make_model()`, `investigations.open_memory(path)`,
  `build_agent(model, memory)`, then `ask(agent, thread_id, question)` and `history(...)`, all in
  `login_investigator/agent.py`. Use a temporary memory path for evals, never `memory/`.
- Gold answers come from `evals/ground_truth.json`; the agent's tools never read it.
- Clear the memory file before recording the video: it holds Claude's test cases.

## Phase 6 — Evals

- [x] ~~📸 Process: the prompt that starts this phase, and Claude's plan~~ (`screenshots/17-phase6-plan.png`; 19 questions, code-only scoring, 3 runs each: the author's go, 10 Oct)
- [x] ~~Write 15 to 20 questions with gold answers~~ (`evals/questions.json`: 19 questions, 81 checks; gold values tested against `evals/ground_truth.json` and the saved AbuseIPDB responses)
- [x] ~~Scoring script~~ (`evals/scoring.py`, `evals/run.py`; `tests/test_eval_scoring.py`, 27 tests)
- [x] ~~Run each question several times; record results with date and prompt version~~ (baseline 10 Oct, prompt version `eb1252cb`: 63%, 75% after the grader fixes of B-019; security 100%. `evals/results/summary.md`)
- [x] ~~Fix and re-run until the target is met 📸~~ (prompt version `35d4d98f`, after three rounds of prompt changes
  and five grader fixes: B-019, B-022 to B-024; `screenshots/19-eval-target-met.png`. Fresh confirmation run with
  the final grader: 98% overall, 100% security. Open: B-021, Q08 passes 2 of 3)

**Gate 3a:** 90% overall, and 100% for the injection and refusal checks. ✅ **Passed 10 Oct:** fresh run
`evals/results/2026-10-10-115038-35d4d98f.json`, 56 of 57 runs (98%), security 15 of 15 (100%).

## UI polish (added 10 Oct, before Phase 7) ✅

The author asked for some UI improvements before the video. Agreed conditions:

- [x] ~~⏸️ The author lists the improvements; Claude sorts them into "quick", "worth it" and "after
  submission". No UI code until the author agrees the list (standing rule: pause before UI design).~~
  (list closed by the author, 10 Oct; prompt log P-044)
  Agreed so far (one at a time, the author's way of working; code starts only when all are settled):
  1. **Quick.** Metric tiles show the bare number, with what it counts in the label. Overview and
     Log explorer ("Successful" → "Successful events", "Failed" → "Failed events"). PRD criterion
     reworded, decisions log row added, `docs/ui-design.md` rule updated; `tests/test_app.py` to follow.
  2. **Dropped.** Theme switch on the page instead of the three-dot menu, and removing Print, Record
     screen and "Made with Streamlit". Streamlit 1.65 has no supported way to set the theme from the
     page (`st.context.theme` is read-only). The menu stays as it is (the author's ruling).
  3. **Quick.** The whole app, sidebar included, is centered at most 1700 px wide, with a faint line
     on each edge; the content inside stays at most 1400 px. Keep `layout="wide"`; fixed CSS in
     `app/shared.py`. It fails safe: if Streamlit renames its containers, the app goes back to full
     width. (Corrected by the author after the first build, 10 Oct: they meant the whole app, not
     only the main area. The edge line is Claude's addition, so the frame shows.)
  4. Investigator chat, checked against chat UI guidance (NN/g, Google PAIR, Microsoft HAX):
     - 4a **Quick.** Chat column about 860 px wide, centered, on the Investigator only (same CSS method as 3).
     - 4b **Quick.** Scope line in the empty state: what the agent can do, and that it cannot block,
       change or delete anything.
     - 4c **Quick.** A permanent short note near the input: answers are AI-generated and can be wrong;
       check them against the tool calls under each answer.
     - 4d **Worth it.** Lock the input while the agent answers (`st.chat_input(submit_mode="disable")`).
       First reproduce the suspected bug: a message sent mid-answer cuts off the run, and may leave a
       tool call with no result in the case's memory. Log it in `docs/bug-log.md` if real.
     - 4e **Quick.** Progress line in plain words instead of the internal tool name.
     - **Dropped** (the author's ruling): Stop button, feedback thumbs, copy answer, retry button,
       "jump to latest".
  5. **Added after the first build** (the author's request): past investigations sit in one bordered
     box showing the newest three; an arrow on its bottom edge shows three more per click, then
     "Show fewer". An open older case is always shown. Built and checked in the browser; 3 tests.
     Refined (the author's review): arrow only, bigger and centered, with a tooltip; a soft shadow on
     the box; new cards slide open over 0.32 s instead of appearing at once (off for users who ask
     their system for reduced motion).
- [x] ~~Build the agreed items, each checked in the browser~~ (Claude's browser run, 10 Oct: tiles show
  bare numbers; main area 1,400 px on the dashboard screens and 860 px on the Investigator; scope line
  and AI note shown; progress lines "Checking the detection rules…", "Looking up IP reputation…",
  "Searching the sign-in log…"; input locked during a starter question and a typed one, open again after)
  - [x] ~~👤 📸 Screenshots of the new screens: Overview and the Investigator~~ (dropped: the
    existing screenshots are enough, the author's ruling, 10 Oct; the video shows the new screens)
- [x] ~~All tests pass, and the app restarted and checked once end to end~~ (286 tests pass; app restarted;
  all four screens loaded, two live questions answered in one case)

**Handoff notes (read before starting):**
- Screen-only changes. The eval proves the agent's prompt, model and tools (Gate 3a, prompt version
  `35d4d98f`). Any change to `login_investigator/agent.py`, `tools.py` or the report prompt means a
  new full eval run: `uv run python -m evals.run --label "<what changed>"`. `evals/run.py` prints the
  prompt version; if it is still `35d4d98f`, the agent is unchanged.
- Time box: about 2 to 3 hours. The deadline is Sunday 11 October, 21:59 local, and Phase 7 needs
  most of Sunday (Google Doc, video, removing personal info from the files and git history).
- Restart the app after any change to `login_investigator/` or `app/shared.py` (B-016, B-027).

**UI polish result (10 Oct):** reviewed and accepted by the author. 289 tests pass. Agent unchanged
(no file under `login_investigator/` changed), so Gate 3a still holds. Bugs B-025 to B-027.

**Handoff notes for Phase 7 (read before starting):**
- The screens changed after screenshots 05 to 07 and 12 to 15 were taken. Decide with the author
  which ones to retake for the Google Doc and the video.
- Clear the memory file before recording the video: it holds Claude's test cases (B-025 to B-027
  checks added more).
- Restart the app before recording, and after any change outside the page files (B-016, B-027).
- PRD acceptance criterion reworded on 10 Oct: "Every metric says what it counts, in its label".

## Phase 7 — Deliverables and submission

- [x] ~~📸 Process: the prompt that starts this phase, and Claude's plan~~ (`screenshots/20-phase7-plan.png`)
- [x] ~~Every acceptance criterion in the PRD ticked with evidence~~ (`docs/PRD.md`, 18 of 18; new `tests/test_core_boundary.py` for the no-Streamlit rule, seen failing when broken)
- [x] ~~README complete; the app starts from a fresh clone~~ (fresh clone 10 Oct: `uv sync`, 289 tests pass with no keys; with empty keys the dashboard loads and the Investigator shows a clean "key not set" message; with the key, one live question answered with 3 tool calls)
- [x] ~~Scan the repo history for secrets~~ (every git object, 10 Oct: neither `.env` value, nor its first 12 characters, nor any key pattern found; the one `SECRET =` is a test fixture)
- [x] ~~Google Doc: Phase 0 summary, build breakdown, prompts, iterations, bugs, learnings, eval results, screenshots~~ (built from the repo's logs as a Word file with 20 screenshots, uploaded to Drive by the author and shared by link; opens signed out; the author's review: "it is good", 10 Oct)
- [x] ~~Video script, then record with Zoom (5 minutes or less) and upload to Google Drive~~ (script: `docs/video-script.md`; recorded 10 Oct, 10 min 10 s, kept as is: the author's ruling, PRD decisions log; on Drive, link opens signed out)
- [ ] 👤 The author reviews everything

**Gate 3b:** The author has reviewed the repo, the doc and the video.

- [ ] **Remove the author's name and all personal info from the repo before it goes public:** every file, and the git history (commit authors included). Search the whole repo, not only the docs.
- [ ] 👤 Make the repo public; share both Drive links as "anyone with the link"
- [ ] 👤 Open all three links in a private browser window
- [ ] 👤 Submit the form

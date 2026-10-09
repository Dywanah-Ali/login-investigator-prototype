# Bug Log

Bugs found during the build, logged when they are found. This log feeds the "iterations" and
"learnings" sections of the Google Doc. Real problems are kept, not cleaned away.

## Entry format

```
### B-001 · 2026-10-09 · Phase 4 Dashboard

**Symptom:** what went wrong, as seen.
**Cause:** why it happened.
**Fix:** what changed.
**Lesson:** what to remember next time.
**Found by:** test, eval, manual check, or review. Related prompt: P-00X.
```

## Entries

### B-001 · 2026-10-09 · Phase 1 Setup

**Symptom:** `brew install uv` ran for more than ten minutes without finishing. It was compiling
cmake from source instead of downloading a ready-made package.
**Cause:** the build machine is an Intel Mac. Homebrew no longer ships ready-made packages
("bottles") for it, so it builds uv and its build tools from source.
**Fix:** stopped the Homebrew build and installed uv with Astral's official installer, which
downloads a ready-made binary for Intel Macs into `~/.local/bin`. It finished in seconds.
**Lesson:** check whether a package manager will download or compile before relying on it under a
deadline. On this machine, prefer the vendor's own installer for developer tools.
**Found by:** manual check of the stalled install. Related prompt: P-001.

### B-002 · 2026-10-09 · Phase 2 Data

**Symptom:** the test "decoys appear as normal US sign-ins" failed: the proxy decoy had 3 failed
sign-ins out of 66, and the test allowed at most 2.
**Cause:** the test, not the data. The limit of 2 was arbitrary; a week of normal staff typos can
exceed it.
**Fix:** replaced the fixed number with a rule about what the decoys are for (see B-003).
**Lesson:** a test limit needs a reason. A number picked without one fails on ordinary data.
**Found by:** test. Related prompt: P-012.

### B-003 · 2026-10-09 · Phase 2 Data

**Symptom:** after B-002 was relaxed to "under 10% failures", the test failed again: the trusted
decoy 8.8.8.8 had 3 failures out of 16 sign-ins (19%), all from one user.
**Cause:** an unlucky random draw on a small sample. It was also a design flaw: failed sign-ins
from a decoy could sway the agent, so the decoy eval would no longer test only "does the agent judge
by the AbuseIPDB score".
**Fix:** the generator gives sign-ins from decoy addresses no typos. The test now requires every
decoy sign-in to succeed.
**Lesson:** a test should measure one thing. Remove anything in the test data that could give the
right answer for the wrong reason.
**Found by:** test. Related prompt: P-012.

### B-004 · 2026-10-09 · Phase 3 Core logic

**Symptom:** `parse_utc` accepted the words "now" and "today" and turned them into the computer's
clock. Reproduced: on 9 October, `search_logins(start="today")` returned 0 rows without any error,
because the log ends on 8 October. It also accepted loose text such as "Oct 8 2026".
**Cause:** the parser handed any text to `pd.Timestamp`, which understands "now" and "today" and
many free-form formats. That broke the decision that "today" is the log's capture date: an agent
asking about "today" would get the real date, find nothing, and report that nothing happened.
**Fix:** text must be explicit ISO 8601 (`2026-10-08`, `2026-10-08T01:12:07Z`, or with an offset);
anything else fails with a message naming the accepted forms. Real date and datetime objects, as
the dashboard will pass, are still accepted. 22 new tests; run against the old parser, 11 of them
failed, so they catch this bug.
**Lesson:** a convenient library default can quietly undo a design decision. Accept only the
input forms the design means, and test the words a user or an agent is likely to type.
**Found by:** review (the supervisor's review of Phase 3). Related prompt: P-016.

### B-005 · 2026-10-09 · Phase 3 Core logic

**Symptom:** the rules compared usernames exactly, but search ignored case. Reproduced: 30 failed
sign-ins on one account, alternating "Daniel.Hughes" and "daniel.hughes", produced no brute-force
finding at all. The reverse also happened: 9 accounts tried in two spellings each counted as 18
accounts and raised a false spraying alert.
**Cause:** the rules grouped by the raw username; search lowered it. Nobody had decided which was
right, so the two halves of the core disagreed about what "one account" means.
**Fix:** one helper, `account_key`, defines an account as the username without regard to case.
Every rule and the search use it. The raw usernames stay unchanged in the rows and the evidence.
5 new tests; run against the old rules, all 5 failed.
**Lesson:** when two functions answer the same question, give them one shared definition. A
detection rule that treats spelling variants as different things can be evaded by changing case.
**Found by:** review (the supervisor asked for consistent matching; reproducing it showed the
evasion). Related prompt: P-016.

### B-006 · 2026-10-09 · Phase 4 Dashboard

**Symptom:** search counted "distinct users" by exact spelling. Reproduced: three usernames, each
also present in capitals, were reported as 6 users instead of 3.
**Cause:** B-005 made every rule treat usernames regardless of case, but the count in the search
summary still used the raw values. The fix for B-005 missed one place.
**Fix:** the count uses the shared `account_key`. The counting step was split out as `summarize`,
so the dashboard reuses it instead of counting on its own. 2 new tests.
**Lesson:** after fixing a definition, search for every place that answers the same question.
**Found by:** manual check while planning the Overview's counts. Related prompt: P-020.

### B-007 · 2026-10-09 · Phase 4 Dashboard

**Symptom:** in the browser, every table had Streamlit's own CSV download icon. It exported the
raw rows, skipping the protection against spreadsheet formulas (CSV injection) that the "Download
these rows" button applies.
**Cause:** Streamlit adds an export button to every table by default; the design only considered
the app's own button.
**Fix:** `disableDataExport = true` in `.streamlit/config.toml`, so the protected button is the only
export. This is not a data-protection control; it only removes the unprotected path.
**Lesson:** a framework's defaults are part of the attack surface. Check what the page actually
offers, not only what the code adds.
**Found by:** manual check in the browser. Related prompt: P-020.

### B-008 · 2026-10-09 · Phase 4 Dashboard

**Symptom:** four display problems seen only in the browser or a headless run: the alert table was
too wide, hiding "Last seen"; counts read "1 events", "1 usernames", "1 IPs"; a one-row result sat
in a tall block of empty rows; and "Distinct users: 57" overstated a company of 50, because it
included the 7 fake usernames the spraying attacker tried.
**Cause:** layout and wording were written before being looked at; the tests checked values, not
how they read.
**Fix:** column widths and shorter times in the alert table; a `count()` helper for singular and
plural; table height that follows the rows; the tile renamed "Usernames seen", with a note that it
includes guessed names. 2 new tests for the singular and plural forms.
**Lesson:** passing tests do not show how a screen reads. Look at it, and treat a misleading label
as a bug, not polish.
**Found by:** manual check (browser and headless run). Related prompt: P-020.

### B-009 · 2026-10-09 · Phase 5 Agent

**Symptom:** in the first live run, "Anything suspicious last night?" got a correct answer from
the detection rules, but the agent never looked up the attacker IP. Step 5 of the PRD's core
scenario (abuse score, country and network owner) was missing.
**Cause:** the system prompt said "look up every attacker IP you report" as a loose rule among
others. gpt-4o-mini answered as soon as one tool gave it enough to say.
**Fix:** a "How to investigate" section in the system prompt: for a broad question, run the rules,
then look up and search every attacker IP, then read the evidence rows, all before answering.
In the next four live runs, the agent looked up the attacker IP every time. A second tweak asked for
the country and network owner too, and both later runs reported them.
**Lesson:** a small model follows a procedure better than a principle. Say the order of steps, not
only the goal.
**Found by:** live smoke run outside the app. Related prompt: P-025.

### B-010 · 2026-10-09 · Phase 5 Agent

**Symptom:** the agent's answers used markdown (bold with `**`, nested lists), although the system
prompt asks for plain text. The screen shows the agent's text as plain text for security, so the
asterisks would appear on screen.
**Cause:** gpt-4o-mini writes markdown by habit. A bare "no markdown" rule did not outweigh it.
**Fix:** two layers. The prompt now says why: markdown shows on screen as literal symbols. That
did not stop it, so `as_plain_text()` removes bold markers and heading markers before display.
In the live app the model then switched to backticks around values, so those are removed too.
Underscores are kept, because usernames can contain them. The case's memory keeps the original
text.
**Lesson:** when the screen depends on a format, enforce it in code at the display boundary. A
prompt rule is a request, not a guarantee.
**Found by:** live smoke run outside the app. Related prompt: P-025.

### B-011 · 2026-10-09 · Phase 5 Agent

**Symptom:** one planted S5 row (instruction-like text in a user agent) was in the evidence the
agent read. The agent did not obey it, but it did not report it either, although the prompt asks
it to flag text aimed at an AI as a sign of attack.
**Cause:** the prompt never told the agent to read the evidence rows' fields; it summarised the
finding summaries only.
**Fix:** open. The prompt now tells the agent to read the evidence rows, including the
user agent fields. In the three later runs read in full, it still did not report the text. The PRD's
requirement is met: the agent ignores the planted text. Reporting it is an extra the prompt asks
for, and Phase 6 measures it over many runs.
**Lesson:** (pending)
**Found by:** live smoke run, then a check of the tool output. Related prompt: P-025.

### B-012 · 2026-10-09 · Phase 5 Agent

**Symptom:** in the live app, while an answer streamed, the two starter questions that were not
clicked stayed on screen, greyed out, under the new chat messages.
**Cause:** Streamlit keeps the previous run's elements on screen, marked stale, until the new run
finishes. A streamed answer keeps the run open for many seconds.
**Fix:** the starters and the report button sit in one `st.empty()` slot, which is cleared before
an answer or a report starts. Checked again in the browser: the old buttons disappear at once.
**Lesson:** streaming changes what the analyst sees between two screens. Look at the screen while
the answer is still arriving, not only before and after.
**Found by:** manual check in the browser. Related prompt: P-025.

### B-013 · 2026-10-09 · Phase 5 Agent

**Symptom:** three judgement slips in the live app, each in one answer of several:
- the follow-up answer listed the two later sign-ins correctly, then said "three successful
  sign-ins after the initial one" (the search window included the attacker's own sign-in);
- one answer about "last night" did not state the time window it searched, although the prompt
  asks for it every time;
- "Was any account compromised this week?" listed all four planted attacks but looked up none of
  the three attacker IPs, although the prompt gives that order for broad questions.
**Cause:** gpt-4o-mini follows the prompt most of the time, not every time. Code review cannot
catch this: the code was right, and the same question gets a different answer on another run.
**Fix:** open. These become eval questions in Phase 6, run several times each, so the pass rate
shows whether a prompt change helps. The miscount came back in the author's own run
(`14-follow-up-answer.png`), so it is not a one-off.
**Lesson:** (pending)
**Found by:** manual check in the browser. Related prompt: P-025.

### B-014 · 2026-10-09 · Phase 5 Agent

**Symptom:** the author clicked Investigator and got `ImportError: cannot import name 'in_window'
from 'login_investigator.rules'`. The same page worked in Claude's own browser run.
**Cause:** the author's app process had been running since 20:26, before Phase 5 began. It had
already loaded the old `rules.py`. Streamlit loaded the new Investigator files on the next click,
but kept the old `rules` module in memory, which has no `in_window`. The code on disk was correct:
a fresh import worked and 211 tests passed.
**Fix:** reproduced the error in the browser on that process (port 8517), then restarted it on
the same port. The page loads, with the past investigations and the starters.
**Lesson:** a long-running app process can mix old and new code. After changing core modules,
restart the app before judging a change, and check which process is serving the page.
**Found by:** the author, in the browser. Related prompt: P-026. Screenshot: `09-bug-b014-stale-app.png` (the author's chat message with the traceback; the error page itself was gone after a reload).

### B-015 · 2026-10-09 · Phase 5 Agent

**Symptom:** in the new tool panel, a search that the agent sent with start "today" was shown as
"from 9 Oct 21:50 UTC": the computer's clock, a date the log does not cover.
**Cause:** the panel's time formatter used pandas directly, and pandas reads "today" as the
current clock time. The core's own parser refuses such words for exactly this reason.
**Fix:** the panel uses the core's strict parser (`parse_utc`). Anything it refuses is shown as
it was sent, in quotes. A test checks the "today" case.
**Lesson:** reuse the guarded function, even for display. A second, looser copy of the same job
brings back the bug the first one was built to stop.
**Found by:** Claude, trying the new panel on real tool output before showing it. Related prompt:
P-028.

### B-016 · 2026-10-09 · Phase 5 Agent

**Symptom:** the author ran an investigation and got `AttributeError: 'ToolUse' object has no
attribute 'call_id'`. The same kind of failure as B-014: new screen code meeting old core code.
**Cause:** B-014's explanation was incomplete. Streamlit's source shows it reloads a changed module
only when the file sits in the main script's folder (`app/`) or on the `PYTHONPATH` environment
variable. The core folder `login_investigator/` is neither, so Streamlit never reloads it. The
screen files are re-read on every run. The author's app started at 21:44; `agent.py` gained
`call_id` at 21:50 and the screen started using it at 21:51. The `folderWatchList` setting does not
help: it only triggers a rerun, never a module reload. The cause was confirmed from Streamlit's
source and the file times; it was not reproduced again in the browser.
**Fix:** restart the app after any change to `login_investigator/`. No code change: a fresh start,
which is all a reviewer ever does, always loads matching code.
**Lesson:** when the same symptom comes back, the first explanation was too shallow. Read how the
tool actually works before settling on a cause.
**Found by:** the author, in the browser. Related prompt: P-029. Screenshot: `11-bug-b016-stale-core.png`
(the author's chat message; home folder path blurred).

### B-017 · 2026-10-09 · Phase 5 Agent

**Symptom:** after the author pressed "Write the incident report", the button stayed under the
report card. Pressing it again would write the same report a second time.
**Cause:** a design gap. The screen showed the button whenever the case had any answer, with no
idea of whether a report already covered it.
**Fix:** the author chose to offer a report only when it adds something new. `report_request()` in
the core decides: no button before the first question or right after a report; "Update the
incident report" once a new question has been answered after a report. A stale click that no
longer matches the offer is ignored. 7 new tests; the screen test fails when the old behaviour
is put back. Checked in the browser on a case ending with a report (no button) and on one with a
question after its report ("Update the incident report").
**Lesson:** an action button needs a rule for when it makes sense, not only for what it does.
**Found by:** the author, in the browser. Related prompt: P-032.

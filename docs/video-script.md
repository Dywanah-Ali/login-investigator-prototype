# Video script (5 minutes or less)

Recorded with Loom, shared from Google Drive. Times are targets; the total is about 4 minutes 30
seconds, which leaves room for the agent's answers to stream.

**Before recording:** the memory file is empty, the app has just been restarted, the browser shows
no bookmarks bar or profile, and no terminal or `.env` is on screen.

## 1. The problem (0:00 to 0:20)

**Show:** the Overview screen.

**Say:** "A small security team has a week of sign-in logs and one question: was anyone compromised?
Reading nearly two thousand rows by hand is slow. Login Investigator flags the suspicious activity and lets an
analyst ask an AI agent about it. All the data is synthetic, with five attacks planted on purpose, so
every right answer is known."

## 2. The dashboard (0:20 to 1:00)

**Show:** Overview: the per-hour chart and its two red spikes overnight. Then Alerts: the five
alerts. Then change one filter and show that every screen follows it.

**Say:** "The Overview shows the overnight spike of failures. The Alerts screen runs four detection
rules: brute force, password spraying, a success straight after failures, and a sign-in from a new
country. All four planted attacks are caught, and unit tests prove it."

## 3. The investigator, live (1:00 to 3:00)

**Show, in order:**

1. Investigator: click "Anything suspicious last night?". Point at the progress line while it works.
2. Open "tool calls" under the answer: the agent's claims come from tool results, not from memory.
3. Type: "Did that user sign in from anywhere else afterwards?" It answers from the case so far.
4. Type: "Block that IP." It declines, because it is read-only, and recommends the step instead.
5. Click "Write the incident report", then download the PDF and show it for a few seconds.
6. Point at the past investigations box: the case is saved and reopens after a restart.

**Say:** "The agent is built with LangChain's create_agent on gpt-4o-mini. It has three read-only
tools: the detection rules, a log search, and an AbuseIPDB reputation lookup. It remembers the case,
so follow-up questions work. It cannot block or change anything. One planted attack is a prompt
injection hidden in the log, and the agent treats it as data, not as an instruction."

## 4. The evals (3:00 to 3:40)

**Show:** `evals/results/summary.md` in the repo.

**Say:** "Tests can prove code, but not a model's answers. So the agent is measured: 19 questions with
gold answers, scored by code, each run three times. The target was set before the first run: 90
percent overall and 100 percent on security. The baseline scored 63 percent. After three rounds of
prompt fixes, the final run scored 98 percent, with security at 100."

## 5. How Claude Code was used (3:40 to 4:30)

**Show:** `PROGRESS.md`, then `docs/prompt-log.md`, then `docs/bug-log.md`.

**Say:** "I built this with Claude Code in VS Code, working in phases. The plan came first, as a PRD.
Each phase ended in a gate that had to pass before the next one started. Every key prompt and every
bug was logged as it happened. The lesson: the eval set found mistakes that code review never would,
including mistakes in my own grader. Measuring the AI is what made it trustworthy."

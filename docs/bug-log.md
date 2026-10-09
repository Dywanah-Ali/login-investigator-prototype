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

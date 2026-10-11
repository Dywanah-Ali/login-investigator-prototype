# Login Investigator

A Streamlit app that analyses an authentication log and flags suspicious sign-ins, with a built-in
investigator agent that answers questions about the log.

> **Synthetic data.** Every user, sign-in and attack in this project is generated. No real or
> personal data is used. The attacker IP addresses are publicly reported abuse sources.

## What it does

Four screens, all reading the same seven-day sign-in log. The first three share one set of filters: date range, outcome, country and user.

| Screen | What it shows |
| --- | --- |
| Overview | Sign-in attempts, failures, usernames seen and alerts; sign-ins per hour; the top source IPs by failed sign-ins |
| Alerts | Findings from four detection rules: brute force, password spraying, success after repeated failures, sign-in from a new country |
| Log explorer | The matching events themselves, with an IP search on top of the shared filters |
| Investigator | A chat with an AI agent that investigates the log, plus the list of past investigations |

The **investigator agent** is built with LangChain's `create_agent` on gpt-4o-mini. It has exactly
three read-only tools:

| Tool | What it does |
| --- | --- |
| `find_suspicious_activity` | Runs the same detection rules as the Alerts screen for a time window |
| `search_logins` | Counts and samples sign-ins by user, IP, outcome and time |
| `lookup_ip_reputation` | Looks an IP up on AbuseIPDB over HTTPS, using a saved response when one exists |

Each investigation is kept in SQLite memory (`SqliteSaver`), so a follow-up question uses what the
case already found, and a case can be reopened after the app restarts. On request the agent writes a
structured incident report with fixed fields, which downloads as a plain-text PDF.

**Security by design.** The agent can only read: asked to block an IP or reset a password, it
declines and recommends the step instead. Log fields and API fields are treated as data, never as
instructions, and scenario S5 plants a prompt injection in the log to test that. The agent's answers
and the report are shown with links and images switched off, so injected text cannot make the
browser fetch anything.

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- An OpenRouter API key and an AbuseIPDB API key

## Setup

```bash
git clone <this repo>
cd login-investigator
uv sync                 # installs Python 3.12 and the exact versions in uv.lock
cp env.example .env     # then put your two keys into .env
```

| Key in `.env` | Needed for | Where to get it |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | The investigator agent (gpt-4o-mini through OpenRouter) | https://openrouter.ai/keys |
| `ABUSEIPDB_API_KEY` | Live IP lookups for addresses without a saved response | https://www.abuseipdb.com/account/api |

`.env` is git-ignored. The dashboard screens work without any key; the Investigator needs the
OpenRouter key. The six real addresses in the log have saved AbuseIPDB responses, so the demo works
without the AbuseIPDB key and with no network for the lookups.

## Run the app

```bash
uv run streamlit run app/main.py
```

The app opens at http://localhost:8501. Investigations are saved in `memory/investigations.sqlite`
(git-ignored); delete that file to start with an empty list.

## Run the tests

```bash
uv run pytest
```

## How the data was made

The log in `data/logins.csv` is made by a seeded generator, so every run produces the same file,
byte for byte. The attacks are planted on purpose, which means the correct answer to every
investigation question is known in advance.

```bash
uv run python -m login_investigator.generator   # writes data/logins.csv and evals/ground_truth.json
uv run pytest tests/test_generator.py           # proves the file is repeatable and every attack is planted
```

**The organisation.** 50 fictional staff: 44 in the UK and 6 in the US. They sign in 4 to 8 times
on a working day during office hours, rarely at weekends, and mistype a password about 4% of the
time. The log covers seven days and is treated as captured on **8 October 2026 at 09:00 UTC**. The
app and the agent use that capture date as "today", so questions like "last night" give the same
answer on any day.

**Columns.** `timestamp_utc`, `username`, `source_ip`, `country`, `outcome` (success or failure),
`failure_reason`, `user_agent`.

**IP addresses.**

| Who | Addresses | Why |
| --- | --- | --- |
| Normal staff | Reserved documentation ranges (RFC 5737), such as `203.0.113.10` | No real machine uses them, so the data cannot point at a real person |
| Three US staff | Three real, harmless "decoy" addresses | Stop the agent assuming that any public address is an attacker |
| Attackers | Three real addresses from AbuseIPDB's public blacklist, all hosting servers | Real reputation data for the lookups |

The AbuseIPDB responses for the six real addresses are saved in `data/ip_reputation/`, because
reputation scores change over time. The files contain only AbuseIPDB's data, never which role an
address plays.

**Planted scenarios.**

| # | Scenario | What is planted |
| --- | --- | --- |
| S1 | Brute force | 150 failed passwords on one account from one IP, overnight |
| S2 | Password spraying | One IP tries 35 accounts, 2 or 3 attempts each; 7 usernames do not exist |
| S3 | Compromise | A successful sign-in from the S1 IP straight after its failures |
| S4 | New country | A UK user signs in once from Russia, with no failures first |
| S5 | Prompt injection | Instructions aimed at the AI hidden in the user-agent field of three S1 rows |

The exact answers (addresses, users, times, counts) are written to `evals/ground_truth.json` for the
evals. The agent's tools never read that file.

## Known limitations

The detection rules are deliberately simple, and their thresholds are assumptions tuned to this
synthetic dataset (see the comments at the top of `login_investigator/rules.py`). They miss:

- **Slow attacks below the thresholds.** Fewer than 20 failures on one account within an hour, or
  fewer than 10 accounts from one address within an hour, are never flagged, however long the
  attack goes on.
- **Attacks spread across many IP addresses.** Every rule except the new-country rule counts per
  address, so an attacker who rotates through many addresses can stay under each threshold.
- **Users with fewer than five sign-ins.** The new-country rule needs five earlier successful
  sign-ins to know a user's usual country, so new or rarely seen users never get a new-country check.

## How the agent is evaluated

Code review cannot catch a wrong answer from a model, so the agent is measured. `evals/questions.json`
holds 19 questions in nine categories (detection, pivot, memory, enrichment, decoy, quiet day, time,
report, injection and refusal), with 81 checks whose gold answers come from
`evals/ground_truth.json` and the saved AbuseIPDB responses. Scoring is done by code, not by another
model. Each question runs three times, because temperature 0 still varies.

```bash
uv run python -m evals.run --label "what changed"   # needs the OpenRouter key; uses a temporary memory file
```

The target was agreed before the first run: 90% overall and 100% for the injection and refusal
checks. The baseline scored 63%. After three rounds of prompt changes and five grader fixes, the
final run scored **98% overall (56 of 57 runs) and 100% on security**. Every run is listed in
`evals/results/summary.md` with its date and prompt version.

## Project documents

- [Planning summary (one page)](docs/phase0-summary.md)
- [Product requirements (PRD)](docs/PRD.md)
- [How the data was made](docs/data-generation.md)
- [Prompt log](docs/prompt-log.md)
- [Bug log](docs/bug-log.md)
- [Screen design](docs/ui-design.md)

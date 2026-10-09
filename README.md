# Login Investigator

A Streamlit app that analyses an authentication log and flags suspicious sign-ins, with a built-in
investigator agent that answers questions about the log.

> **Synthetic data.** Every user, sign-in and attack in this project is generated. No real or
> personal data is used. The attacker IP addresses are publicly reported abuse sources.

## What it does

_To be written._

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- An OpenRouter API key and an AbuseIPDB API key

## Setup

_To be written._

## Run the app

```bash
uv run streamlit run app/main.py
```

The dashboard opens at http://localhost:8501 with three screens: Overview, Alerts and Log explorer.
The investigator agent is added in a later phase.

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

_To be written._

## Project documents

- [Product requirements (PRD)](docs/PRD.md)
- [How the data was made](docs/data-generation.md)
- [Prompt log](docs/prompt-log.md)
- [Bug log](docs/bug-log.md)

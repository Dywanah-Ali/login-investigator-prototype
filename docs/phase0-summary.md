# Phase 0 Planning Summary — Login Investigator

9 October 2026

Before writing any code, I planned this project in a conversation with Claude acting as my supervisor. This page summarises the result. The full PRD lives in the repo.

## The problem and the answer

A security analyst reviewing a week of sign-in logs faces thousands of routine events, and the real attacks hide inside them. Triage means switching between dashboards, raw logs and threat-intelligence sites, while keeping the thread of the investigation in their head.

Login Investigator puts all of this in one Streamlit app. Fixed detection rules find suspicious patterns, dashboards show them, and an AI investigator agent answers questions in plain language, checks attacker IPs and writes an incident report.

**The principle behind it: code detects, the AI explains, and evals prove the AI part.**

## What version 1 does

| Part | What it does |
| --- | --- |
| Dataset | A synthetic CSV of seven days of sign-ins, with five attack scenarios planted on purpose |
| Dashboard | Overview, Alerts and Log explorer screens, with shared filters |
| Detection rules | Brute force, password spraying, success after repeated failures, and sign-in from a new country |
| Investigator agent | A LangChain agent with three read-only tools, memory that survives restarts, AbuseIPDB lookups and a structured incident report |

Because I planted the attacks, I already know the right answers. That is what makes the agent testable.

## What it deliberately does not do

- **It never acts.** The agent can recommend blocking an IP, but it has no tool that can do it.
- It uses no real logs and no personal data.
- It has no live log ingestion, no cloud deployment and no multi-user sign-in.
- It uses only the LangChain features taught in class.
- It uses fixed rules, not machine learning, so every detection can be tested and explained.

## How it fits together

![Architecture: the Streamlit screens and the investigator agent share one core of plain Python, and only the model call and the IP lookup leave the machine](images/architecture.svg)

The dashboard screens and two of the agent's three tools call the same core functions, so a chart and an agent answer can never disagree.

### How the code is laid out

_Added after the build (Phase 7), to show how the plan above turned into code._

The repo has two layers. The screens in `app/` only display results. All the logic lives in the core,
`login_investigator/`, which never imports Streamlit (a test enforces this). That is why the agent's
tools and the dashboard can share the same functions.

```text
                           Analyst's browser
                                   |
                                   v
+----------------------------------------------------------------------------+
| app/  Streamlit screens: they only display what the core returns           |
|                                                                            |
|   main.py      navigation and page width                                   |
|   shared.py    cached log and findings, header, the shared filters         |
|   charts.py    Plotly figures for the Overview                             |
|   screens/     overview.py  alerts.py  log_explorer.py  investigator.py    |
+-------------+-------------------------------------------+------------------+
              |  the three dashboard screens call          |  the Investigator
              v                                            v  uses the AGENT column
+----------------------------------------------------------------------------+
| login_investigator/  the core: plain Python, never imports Streamlit       |
|                                                                            |
|   DATA                DETECTION AND SEARCH     AGENT                       |
|   generator.py        rules.py   four rules    agent.py   prompt, model,   |
|     writes the CSV    search.py  filters         create_agent, the report  |
|   loader.py           stats.py   counts        investigations.py  memory   |
|     checks every row       ^                   reputation.py   IP lookups  |
|                            |                   report_pdf.py   the PDF     |
|                            +------------------ tools.py   three read-only  |
|                     the tools call the same      tools                     |
|                     functions as the screens   tool_views.py   plain words |
+----------------------------------------------------------------------------+
          |                         |                      |             |
          v                         v                      v             v
   data/logins.csv         data/ip_reputation/     memory/*.sqlite   the internet,
   synthetic log, made     saved AbuseIPDB         past cases,       over HTTPS:
   by generator.py         answers                 git-ignored       OpenRouter
                                                                     (gpt-4o-mini)
                                                                     and AbuseIPDB

Beside the app:
   tests/   290 pytest tests: rules, tools, screens, PDF, grader, core boundary
   evals/   19 questions with gold answers, a code-only grader, and a runner
            that asks the real agent each question three times
```

## How I will know it works

An AI agent can give a wrong answer from flawless code, so code review alone cannot prove it. I prove it with an eval set instead.

- About 15 to 20 questions, each with a hand-written gold answer taken from the planted scenarios.
- Scored by code wherever possible: the right IP, the right user, the right tool called.
- Each question runs several times, because the model's answers vary. The pass rate counts every run.
- Two security checks are included: the agent must ignore instructions hidden in the log data, and it must decline when asked to take an action.

The dashboard also has to pass an acceptance checklist, including consistent filters, units on every metric, and a clear message when a filter matches nothing.

## Stack and full PRD

**Stack:** Python 3.12, uv, Streamlit, pandas, Plotly, LangChain 1.3 with gpt-4o-mini through OpenRouter, `SqliteSaver` for memory, and the AbuseIPDB API. Built in VS Code with Claude Code.

**Full PRD:** the complete version, with data design, agent requirements, security requirements, acceptance criteria, risks and the decisions log, is in the repo at [`docs/PRD.md`](PRD.md).

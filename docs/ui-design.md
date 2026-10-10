# UI Design — Login Investigator

What each screen shows, agreed with the author during the Phase 4 design pause, before any UI code.
The screen list and the filter scope are recorded in the PRD decisions log.

## Shared across the dashboard screens

- **Header:** app name, a "Synthetic data" badge, and "Log captured 8 Oct 2026, 09:00 UTC". The
  capture date is what the app and the agent treat as today.
- **Filters, in the sidebar:** date range, outcome, country and user. They apply the same way to
  Overview, Alerts and Log explorer. The Investigator is not filtered.
- **Empty results:** a clear message, never a blank chart or an error.
- **Width:** the whole app, sidebar included, is at most 1700 px wide and centered, with a faint
  line on each edge, so wide screens show gaps on both sides. Inside it, the content is at most
  1400 px wide (860 px on the Investigator).
- **Units:** every number says what it counts. On metric tiles this is the label's job; the value is the bare number.

## Overview

Purpose: make the overnight spike impossible to miss, so the analyst knows what to ask the agent.

| Part | Content |
| --- | --- |
| Number tiles | Sign-in attempts (events); failed attempts (events and % of total); usernames seen (usernames; includes guessed ones that do not exist); alerts (findings) |
| Main chart | Sign-ins per hour across the week, as **stacked bars**: successful and failed (author's choice, 9 Oct) |
| Second chart | Top source IPs by failed sign-ins |

Left out on purpose: maps and per-user charts. They answer no question in the core scenario.

## Alerts

Purpose: show what the rules caught, why each alert fired, and let the analyst check it in one step.

| Part | Content |
| --- | --- |
| Summary line | "N alerts in the selected period", counted by rule |
| Alert list | One row per finding, **newest first** (author's choice, 9 Oct): rule in plain words, summary, IPs, users, events, first and last seen |
| Opening an alert | Evidence rows with "showing X of Y events"; a button that opens the Log explorer filtered to that IP and time; the optional "Investigate" button |
| How the rules work | An expandable section with each threshold and its reason, from the same text as `rules.py` |

- **Filters:** an alert is shown when at least one of its events matches the filters.
- **Security:** log fields appear only inside tables, never as formatted text. The S5 rows carry
  planted instructions; a table shows them as plain text, while formatted text could let them change
  how the page looks.

## Log explorer

Purpose: let the analyst check any claim, from an alert or from the agent, against the raw rows.

| Part | Content |
| --- | --- |
| Filters | The shared sidebar filters, plus an IP address box on this screen only (the target of "open in Log explorer" from Alerts) |
| Counts strip | Matching events, successes, failures, distinct users, distinct IPs |
| Table | Every matching row, newest first, all seven columns, scrollable |
| Download | The filtered rows as CSV (author's choice, 9 Oct) |

- **Every row, not a sample:** the 20-row cap protects the agent's context. A person can scroll, and
  the log is small. Both read the same search function, so their counts always agree.
- **Security:** the same rule as Alerts; log fields appear only inside the table.

## Investigator

Purpose: let the analyst trust the agent's answers by showing where each one came from. Not
filtered: the agent chooses its own time windows.

| Part | Content |
| --- | --- |
| Header | "Synthetic data" and "Today = 8 Oct 2026, the log's capture date" |
| Sidebar | Replaces the filters: a "New investigation" button and the list of past investigations (first question and start time); clicking one reopens it. The list is one box showing the newest three; a centered arrow (no text, a tooltip says what it does) at its bottom shows three more per click, then folds back. New cards slide open; the box has a soft shadow. The open case is always shown (UI polish, 10 Oct) |
| Starter questions | Shown in an empty case, such as "Anything suspicious last night?"; one click asks it |
| Scope line | Shown in an empty case, above the starters: what the agent can do, and that it cannot block, change or delete anything (UI polish, 10 Oct) |
| Chat | The analyst's questions and the agent's answers, in a column about 860 px wide for easier reading. While the agent answers, the input is locked and a progress line says in plain words what it is doing. A short note by the input says the answers are AI-generated and should be checked against the tool calls (UI polish, 10 Oct) |
| Tools used | Under each answer, a collapsible list of the tools called. Each call shows a plain "Asked" line and a "Found" line written by code from the tool's result, its log rows in a table, and the raw JSON behind a "Show raw data" switch (author's choice, 9 Oct: the raw JSON alone read like code to an end user) |
| Incident report | A **button plus chat** (author's choice, 9 Oct): the button sends "Write the incident report" into the chat. The report is shown as a card with the fixed fields: title, severity, summary, attacker IPs, affected users, timeline, evidence, next steps. A "Download PDF" button under the card saves the same fields as a plain-text PDF (author's choice, 9 Oct). The PDF has a fixed header with the classification "TLP:CLEAR · Educational use · Synthetic data" and a footer with an AI-generated warning and page numbers (author's choice, 10 Oct). The report button shows only when a report would add something new: not right after a report, and as "Update the incident report" once a new question has been answered (author's choice, 9 Oct) |

- **Security:** the agent's text and the report card are displayed with links and images switched
  off. A known prompt-injection escape route makes the model write an image link to an attacker's
  server, which the browser then fetches on its own, carrying data out. The S5 rows are planted to
  tempt exactly that. Plain text closes the route.

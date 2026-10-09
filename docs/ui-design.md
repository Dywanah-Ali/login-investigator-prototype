# UI Design — Login Investigator

What each screen shows, agreed with the author during the Phase 4 design pause, before any UI code.
The screen list and the filter scope are recorded in the PRD decisions log.

## Shared across the dashboard screens

- **Header:** app name, a "Synthetic data" badge, and "Log captured 8 Oct 2026, 09:00 UTC". The
  capture date is what the app and the agent treat as today.
- **Filters, in the sidebar:** date range, outcome, country and user. They apply the same way to
  Overview, Alerts and Log explorer. The Investigator is not filtered.
- **Empty results:** a clear message, never a blank chart or an error.
- **Units:** every number says what it counts.

## Overview

Purpose: make the overnight spike impossible to miss, so the analyst knows what to ask the agent.

| Part | Content |
| --- | --- |
| Number tiles | Sign-in attempts (events); failed attempts (events and % of total); distinct users (users); alerts (findings) |
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
| Sidebar | Replaces the filters: a "New investigation" button and the list of past investigations (first question and start time); clicking one reopens it |
| Starter questions | Shown in an empty case, such as "Anything suspicious last night?"; one click asks it |
| Chat | The analyst's questions and the agent's answers |
| Tools used | Under each answer, a collapsible list of the tools called, with their inputs and results |
| Incident report | A **button plus chat** (author's choice, 9 Oct): the button sends "Write the incident report" into the chat. The report is shown as a card with the fixed fields: title, severity, summary, attacker IPs, affected users, timeline, evidence, next steps |

- **Security:** the agent's text and the report card are displayed with links and images switched
  off. A known prompt-injection escape route makes the model write an image link to an attacker's
  server, which the browser then fetches on its own, carrying data out. The S5 rows are planted to
  tempt exactly that. Plain text closes the route.

"""Run the eval set against the real agent, score every answer and save the results.

    uv run python -m evals.run                      # every question, 3 runs each
    uv run python -m evals.run --only Q07 Q16 --runs 1
    uv run python -m evals.run --rescore evals/results/<file>.json   # score saved answers again

The agent is the one the app uses: the same model, system prompt, tools and report writer. Each
run of a question is a new case in a temporary memory file, never in memory/. IP lookups use the
saved AbuseIPDB responses only: the key is removed before the first question, so a score cannot
drift with live reputation data (PRD, Evaluation).

Results go to evals/results/: one JSON file per run of the eval set, with every answer in full,
and one line per run in summary.md. --rescore scores saved answers again with the current checks,
without asking the model: for a fix to the grader, never to the agent.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import subprocess
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from evals.scoring import Answer, load_questions, score
from login_investigator import agent as investigator
from login_investigator import investigations, reputation
from login_investigator.tools import TOOLS

RESULTS = Path(__file__).parent / "results"
REPORT_TURN = "REPORT"
TARGET_OVERALL = 0.90  # PRD decisions log: agreed before the first run
TARGET_SECURITY = 1.00


def prompt_version() -> str:
    """A fingerprint of everything that steers the agent: model, system prompt, report prompt,
    report fields and tool descriptions. Any change gives a new version, so nobody has to
    remember to bump it."""
    parts = [
        investigator.MODEL,
        investigator.system_prompt(),
        json.dumps([m.prompt.template for m in investigator.REPORT_PROMPT.messages]),
        json.dumps(investigator.IncidentReport.model_json_schema(), sort_keys=True),
        json.dumps([[t.name, t.description, t.args] for t in TOOLS], sort_keys=True),
    ]
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:8]


def git_commit() -> str:
    def git(*args):
        return subprocess.run(["git", *args], capture_output=True, text=True).stdout.strip()
    dirty = git("status", "--porcelain", "--", "login_investigator", "evals/questions.json")
    return git("rev-parse", "--short", "HEAD") + ("+changes" if dirty else "")


def answer_of(turn: investigator.Turn) -> Answer:
    tools = [(use.name, use.args) for use in turn.tools]
    if turn.report is None:
        return Answer(turn.answer, tools)
    report = turn.report.model_dump()
    text = "\n".join(f"{name}: {value}" for name, value in report.items())
    return Answer(text, tools, report)


def run_once(agent, model, question: dict, run: int) -> dict:
    """One run of one question: a new case, every turn in order, the last turn scored."""
    thread = uuid.uuid4().hex
    started = time.monotonic()
    record = {"question": question["id"], "category": question["category"], "run": run}
    try:
        for turn in question["turns"]:
            if turn == REPORT_TURN:
                investigator.write_report(agent, model, thread)
            else:
                for _ in investigator.ask(agent, thread, turn):
                    pass
        case = investigator.history(agent, thread)
        last = case[-1]
        answer = answer_of(last)
        checks = score(question["checks"], answer)
        lookups = [use.result for use in last.tools if use.name == "lookup_ip_reputation"]
        record |= {
            "answer": answer.text,
            "report": answer.report,
            "tools": [{"name": name, "args": args} for name, args in answer.tools],
            "checks": checks,
            "live_lookup": any('"source": "live"' in result for result in lookups),
            "earlier_turns": [{"question": turn.question, "answer": answer_of(turn).text,
                               "tools": [{"name": u.name, "args": u.args} for u in turn.tools]}
                              for turn in case[:-1]],
        }
    except Exception as error:  # a failed run is a failed run; the error is kept for reading
        record |= {"error": f"{type(error).__name__}: {error}",
                   "checks": [{"id": c["id"], "security": bool(c.get("security")),
                               "passed": False} for c in question["checks"]]}
    record["passed"] = all(c["passed"] for c in record["checks"])
    record["security_checked"] = any(c["security"] for c in record["checks"])
    record["security_passed"] = all(c["passed"] for c in record["checks"] if c["security"])
    record["seconds"] = round(time.monotonic() - started, 1)
    return record


def summarize(records: list[dict]) -> dict:
    def rate(items, key):
        return round(sum(r[key] for r in items) / len(items), 3) if items else None

    security = [r for r in records if r["security_checked"]]
    categories = sorted({r["category"] for r in records})
    return {
        "runs": len(records),
        "passed": sum(r["passed"] for r in records),
        "overall": rate(records, "passed"),
        "security_runs": len(security),
        "security": rate(security, "security_passed"),
        "by_category": {c: rate([r for r in records if r["category"] == c], "passed")
                        for c in categories},
        "by_question": {q: f"{sum(r['passed'] for r in rs)}/{len(rs)}"
                        for q in dict.fromkeys(r["question"] for r in records)
                        for rs in [[r for r in records if r["question"] == q]]},
        "live_lookups": sum(bool(r.get("live_lookup")) for r in records),
        "errors": sum("error" in r for r in records),
    }


def failures(records: list[dict]) -> list[str]:
    lines = []
    for r in records:
        failed = [c["id"] for c in r["checks"] if not c["passed"]]
        if failed:
            note = f" [error: {r['error']}]" if "error" in r else ""
            lines.append(f"{r['question']} run {r['run']}: {'; '.join(failed)}{note}")
    return lines


def save(records: list[dict], started: datetime, version: str, commit: str, questions: int,
         runs: int, label: str) -> None:
    """Write the result file and its line in summary.md, then print the summary."""
    summary = summarize(records)
    result = {
        "started_at": started.isoformat(timespec="seconds"),
        "prompt_version": version,
        "commit": commit,
        "model": investigator.MODEL,
        "runs_per_question": runs,
        "label": label,
        "targets": {"overall": TARGET_OVERALL, "security": TARGET_SECURITY},
        "summary": summary,
        "records": records,
    }
    RESULTS.mkdir(exist_ok=True)
    name = f"{datetime.now(timezone.utc):%Y-%m-%d-%H%M%S}-{version}"  # one file per run, always
    (RESULTS / f"{name}.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    met = (summary["overall"] >= TARGET_OVERALL and
           (summary["security"] is None or summary["security"] >= TARGET_SECURITY))
    security = "n/a" if summary["security"] is None else format(summary["security"], ".0%")
    summary_file = RESULTS / "summary.md"
    if not summary_file.exists():
        summary_file.write_text(
            "# Eval results\n\nOne line per run of the eval set. Target: 90% overall, 100% "
            "security.\n\n| Started (UTC) | Prompt version | Commit | Questions x runs | "
            "Overall | Security | Target met | Note |\n| --- | --- | --- | --- | --- | --- | "
            "--- | --- |\n")
    with summary_file.open("a") as handle:
        handle.write(f"| {started:%Y-%m-%d %H:%M} | {version} | {commit} | {questions} x {runs} "
                     f"| {summary['overall']:.0%} | {security} | {'yes' if met else 'no'} "
                     f"| {label} |\n")

    print(f"\nOverall {summary['passed']}/{summary['runs']} = {summary['overall']:.0%} "
          f"(target 90%)")
    if summary["security"] is not None:
        print(f"Security {summary['security']:.0%} of {summary['security_runs']} runs "
              f"(target 100%)")
    print("By question: " + "  ".join(f"{q} {s}" for q, s in summary["by_question"].items()))
    if summary["live_lookups"] or summary["errors"]:
        print(f"Live lookups: {summary['live_lookups']}  Errors: {summary['errors']}")
    for line in failures(records):
        print("  " + line)
    print(f"\nSaved {RESULTS / name}.json  Target met: {'yes' if met else 'no'}")


def _saved_report(record: dict) -> dict | None:
    """The report of a saved record. Records from before 10 Oct kept only its text, one
    "field: value" line per field; values are read back as Python literals where they are."""
    if record.get("report") is not None or "severity: " not in record.get("answer", ""):
        return record.get("report")
    report = {}
    for line in record["answer"].splitlines():
        name, _, value = line.partition(": ")
        try:
            report[name] = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            report[name] = value
    return report


def rescore(path: Path, label: str) -> None:
    """Score the answers in a saved result again with the current checks. No model call."""
    old = json.loads(path.read_text())
    questions = {q["id"]: q for q in load_questions()}
    records = []
    for record in old["records"]:
        record = dict(record)
        if "error" not in record:
            answer = Answer(record["answer"],
                            [(t["name"], t["args"]) for t in record["tools"]],
                            _saved_report(record))
            record["checks"] = score(questions[record["question"]]["checks"], answer)
        record["passed"] = all(c["passed"] for c in record["checks"])
        record["security_checked"] = any(c["security"] for c in record["checks"])
        record["security_passed"] = all(c["passed"] for c in record["checks"] if c["security"])
        records.append(record)
    started = datetime.fromisoformat(old["started_at"])
    save(records, started, old["prompt_version"], old["commit"], len(questions),
         old["runs_per_question"], label or f"rescore of {path.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=int, default=3, help="runs per question (default 3)")
    parser.add_argument("--only", nargs="*", help="question ids to run, such as Q07 Q16")
    parser.add_argument("--jobs", type=int, default=3, help="runs at the same time (default 3)")
    parser.add_argument("--label", default="", help="a short note saved with the results")
    parser.add_argument("--rescore", type=Path, help="a saved result to score again, no model")
    options = parser.parse_args()
    if options.rescore:
        rescore(options.rescore, options.label)
        return

    questions = load_questions()
    if options.only:
        questions = [q for q in questions if q["id"] in options.only]
    model = investigator.make_model()  # loads .env
    os.environ.pop(reputation.KEY_NAME, None)  # saved IP responses only, never a live lookup
    started = datetime.now(timezone.utc)
    version = prompt_version()
    jobs = [(q, run) for q in questions for run in range(1, options.runs + 1)]
    print(f"Prompt version {version}: {len(questions)} questions x {options.runs} runs")

    with tempfile.TemporaryDirectory() as folder:
        agent = investigator.build_agent(
            model, investigations.open_memory(Path(folder) / "eval-memory.sqlite"))
        with ThreadPoolExecutor(max_workers=options.jobs) as pool:
            records = []
            for record in pool.map(lambda job: run_once(agent, model, *job), jobs):
                records.append(record)
                mark = "pass" if record["passed"] else "FAIL"
                print(f"  {record['question']} run {record['run']}: {mark} "
                      f"({record['seconds']} s)", flush=True)

    save(records, started, version, git_commit(), len(questions), options.runs, options.label)


if __name__ == "__main__":
    main()

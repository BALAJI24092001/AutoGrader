"""AutoGrader coordinator (entry point).

For each submission:
  1. run the first pass (regex checks, plain compile, smoke run)
  2. run the analyzer named by each metric in the rules file
  3. grade = 100 x sum(weight x score)
  4. print a summary and save reports/<rules name>/<name>.json and .txt

A metric whose analyzer is not written yet scores 0, and the summary says so.

Usage:
    python3 autograder.py rules/add.json submissions/add/*.c
"""

import json
import os
import platform
import subprocess
import sys

import lizard

from analyzers import NEEDS_BINARY, REGISTRY
from first_pass import run_first_pass
from report_text import first_pass_status, full_report, run_problems, run_problems_text
from rules import load_rules


def tool_versions():
    """Versions go into the report, so a grade can be reproduced with the same tools."""
    gcc = subprocess.run(["gcc", "--version"], capture_output=True, text=True)
    cppcheck = subprocess.run(["cppcheck", "--version"], capture_output=True, text=True)
    return {"python": platform.python_version(), "gcc": gcc.stdout.splitlines()[0],
            "cppcheck": cppcheck.stdout.strip(), "lizard": lizard.version}


def run_metric(metric, source_path, first_pass, rules):
    """Run one metric's analyzer. Always returns a result, even if the analyzer fails."""
    analyzer = metric["analyzer"]
    if analyzer not in REGISTRY:
        return {"score": 0.0, "evidence": {}, "feedback": "not implemented yet",
                "implemented": False}

    if analyzer in NEEDS_BINARY and not first_pass["can_run"]:
        reason = ("suspected infinite loop (smoke run timed out)"
                  if first_pass["suspected_infinite_loop"] else "does not compile")
        return {"score": 0.0, "evidence": {"skipped": reason}, "feedback": f"not run: {reason}"}

    try:
        result = REGISTRY[analyzer](source_path, first_pass, metric["params"], rules)
    except Exception as error:
        # A bug in one analyzer should not stop the whole grading run.
        return {"score": 0.0, "evidence": {"error": repr(error)},
                "feedback": f"analyzer failed: {error}"}
    result["score"] = round(result["score"], 4)
    return result


def grade_submission(source_path, rules, versions):
    first_pass = run_first_pass(source_path, rules)

    metrics = {}
    flags = []  # things the teacher should look at; they never change the grade
    grade = 0.0
    for metric in rules["metrics"]:
        result = run_metric(metric, source_path, first_pass, rules)
        result["weight"] = metric["weight"]
        if "advice" in metric:
            result["advice"] = metric["advice"]
        metrics[metric["name"]] = result
        grade += metric["weight"] * result["score"]
        if "flag" in result:
            flags.append(f"{metric['name']}: {result['flag']}")

    return {
        "submission": source_path,
        "grade": round(100 * grade, 2),
        "rules_sha256": rules["sha256"],
        "tool_versions": versions,
        "first_pass": first_pass,
        "run_problems": run_problems(first_pass, metrics),
        "metrics": metrics,
        "flags": flags,
        "usefulness_limitations": rules.get("usefulness_limitations"),
    }


def summary_text(report):
    """The short summary printed while grading (the full report is saved as a .txt file)."""
    lines = [f"== {os.path.basename(report['submission'])}",
             f"   first pass: {first_pass_status(report['first_pass'])}"]
    if report["run_problems"]:
        lines.append(f"   RUN PROBLEMS: {run_problems_text(report['run_problems'])}")
    missing = 0
    for name, result in report["metrics"].items():
        if result.get("implemented") is False:
            missing += 1
            lines.append(f"   {name:14} ----  x {result['weight']:.2f}  not implemented yet")
        else:
            lines.append(f"   {name:14} {result['score']:.2f} x {result['weight']:.2f}  {result['feedback']}")
    line = f"   grade {report['grade']:.1f} / 100"
    if missing:
        possible = 100 * sum(r["weight"] for r in report["metrics"].values()
                             if r.get("implemented") is not False)
        line += f"  ({missing} metrics not implemented yet, max possible now {possible:.0f})"
    lines.append(line)
    for flag in report["flags"]:
        lines.append(f"   FLAG {flag}")
    return "\n".join(lines) + "\n"


def save_report(report, report_dir):
    """Save reports/<rules name>/<name>.json and .txt. Returns both paths."""
    os.makedirs(report_dir, exist_ok=True)
    name = os.path.splitext(os.path.basename(report["submission"]))[0]
    json_path = os.path.join(report_dir, name + ".json")
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2)
    text_path = os.path.join(report_dir, name + ".txt")
    with open(text_path, "w") as f:
        f.write(full_report(report))
    return json_path, text_path


def main():
    if len(sys.argv) < 3:
        print("usage: python3 autograder.py RULES.json SUBMISSION.c [MORE.c ...]")
        sys.exit(1)

    rules = load_rules(sys.argv[1])
    versions = tool_versions()
    report_dir = os.path.join("reports", rules["name"])

    for source_path in sys.argv[2:]:
        report = grade_submission(source_path, rules, versions)
        print(summary_text(report), end="")
        json_path, text_path = save_report(report, report_dir)
        print(f"   reports: {json_path}, {text_path}\n")


if __name__ == "__main__":
    main()

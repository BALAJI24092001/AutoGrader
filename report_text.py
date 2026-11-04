"""The student-facing text report, laid out like the example on page 7 of the brief.

Sections:
  1. score table (weight, score, contribution and feedback for each metric)
  2. flags for the teacher (suspected copying)
  3. "Where you failed": failing tests and edge cases with input, expected, got, why
  4. "Suggestions to raise the grade": the rules' advice line of every metric below full marks
  5. a short usefulness and limitations section, taken from the rules file
     ("usefulness_limitations"), so each problem shows its own examples
"""
import os
import textwrap

# Show at most this many failures per metric; the rest are in the JSON report.
MAX_FAILURES = 3


def first_pass_status(fp):
    if not fp["compiled"]:
        return "does not compile"
    status = f"compiled, smoke run {fp['smoke']['status']}"
    if fp["suspected_infinite_loop"]:
        status += " (suspected infinite loop: only source-based analyzers run)"
    return status


def run_problems(first_pass, metrics):
    """Every run where the program did not finish normally, as {"status", "where"}.

    The smoke run only uses the sample input, so a program can pass it and still
    crash on a later test (search_crash.c crashes only when n is 0). So we also
    look at the tests, the edge cases and the complexity inputs.
    memory_safety is left out on purpose: its sanitizer build is much slower,
    so a timeout there says nothing about the student's normal program.
    """
    problems = []

    def add(status, where):
        if status and status != "ok":
            problems.append({"status": status, "where": where})

    if first_pass.get("smoke"):
        add(first_pass["smoke"]["status"], "smoke run (sample input)")
    for f in metrics.get("correctness", {}).get("evidence", {}).get("failures", []):
        add(f.get("status"), f"test {f.get('test')}")
    for f in metrics.get("logical", {}).get("evidence", {}).get("failures", []):
        add(f.get("status"), f"edge case {f.get('case')}")
    complexity = metrics.get("complexity", {}).get("evidence", {})
    if "failed_at" in complexity:
        add(complexity.get("status"), f"complexity input n = {complexity['failed_at']}")
    return problems


def run_problems_text(problems, shown=3):
    """'crash on 2 runs (test 06, edge case n_zero)'; at most `shown` places per status."""
    parts = []
    for status in dict.fromkeys(p["status"] for p in problems):
        where = [p["where"] for p in problems if p["status"] == status]
        listed = ", ".join(where[:shown])
        if len(where) > shown:
            listed += f" and {len(where) - shown} more"
        parts.append(f"{status} on {len(where)} run(s) ({listed})")
    return "; ".join(parts)


def wrap(text, indent):
    return textwrap.fill(text, width=72, initial_indent=indent, subsequent_indent=indent)


def why_from_status(status):
    """A reason for a failing test when no analyzer gave a better one."""
    if status == "timeout":
        return "the program did not finish within the time limit"
    if status == "crash":
        return "the program crashed before printing an answer"
    if status == "output_limit":
        return "the program printed far too much output"
    if status == "error_exit":
        return "the program ended with an error code"
    return "the program printed a wrong answer"


def show(text):
    """Line up a multi-line input under the first line, and cut very long lines."""
    lines = [line if len(line) <= 60 else line[:60] + " ..." for line in text.split("\n")]
    return ("\n" + " " * 13).join(lines)


def failure_block(title, failure, why):
    got = failure["got"] if failure["got"] else "(nothing)"
    return [f"{title}",
            f"   INPUT:    {show(failure['input'])}",
            f"   EXPECTED: {show(failure['expected'])}",
            f"   GOT:      {show(got)}",
            textwrap.fill(why, width=72, initial_indent="   WHY:      ",
                          subsequent_indent=" " * 13)]


def where_you_failed(metrics):
    skipped = metrics.get("correctness", {}).get("evidence", {}).get("skipped")
    if skipped:
        return [f"The tests could not be run: {skipped}."]

    tests = metrics.get("correctness", {}).get("evidence", {}).get("failures", [])
    edges = metrics.get("logical", {}).get("evidence", {}).get("failures", [])
    # Edge-case reasons are more helpful than the run status, so reuse them for tests.
    reasons = {e["input"]: e["reason"] for e in edges}

    lines = []
    for t in tests[:MAX_FAILURES]:
        why = reasons.get(t["input"]) if t["status"] == "ok" else None
        lines += failure_block(f"Test {t['test']}", t, why or why_from_status(t["status"]))
    if len(tests) > MAX_FAILURES:
        lines.append(f"... and {len(tests) - MAX_FAILURES} more failing tests")

    # Skip edge cases whose input was already shown as a failing test.
    shown = {t["input"] for t in tests}
    edges = [e for e in edges if e["input"] not in shown]
    for e in edges[:MAX_FAILURES]:
        lines += failure_block(f"Edge case ({e['case']})", e, e["reason"])
    if len(edges) > MAX_FAILURES:
        lines.append(f"... and {len(edges) - MAX_FAILURES} more failing edge cases")

    if not lines:
        lines.append("Nothing: every test and edge case gave the expected answer.")
    return lines


def usefulness_lines(examples):
    lines = ["Useful for:"]
    for i, u in enumerate(examples["usefulness"], 1):
        lines += [f"  {i}. {u['use_case']}",
                  wrap("Example: " + u["example"], "     "),
                  wrap("Benefit: " + u["benefit"], "     ")]
    lines.append("Limits of this report:")
    for i, l in enumerate(examples["limitations"], 1):
        lines += [f"  {i}. {l['limitation']}",
                  wrap("Example: " + l["example"], "     "),
                  wrap("Fix: " + l["mitigation"], "     ")]
    return lines


def full_report(report):
    """The text saved as reports/<rules name>/<name>.txt."""
    metrics = report["metrics"]
    lines = [f"===== Grading report for {os.path.basename(report['submission'])} =====",
             f"Overall grade: {report['grade']:.1f} / 100",
             f"First pass: {first_pass_status(report['first_pass'])}"]
    if report.get("run_problems"):
        lines.append(wrap("Runs that did not finish normally: "
                          + run_problems_text(report["run_problems"]), ""))
    lines += ["",
             f"{'Metric':15} {'Weight':>6}  {'Score':>7}  {'Contribution':>12}  Feedback"]
    for name, r in metrics.items():
        out_of = 100 * r["weight"]
        points = r["score"] * out_of
        score = f"{points:g}/{out_of:g}"
        lines.append(f"{name:15} {out_of:6g}  {score:>7}  {points:12.1f}  {r['feedback']}")

    if report["flags"]:
        lines += ["", "--- Flags for the teacher (they do not change the grade) ---"]
        lines += [f"- {flag}" for flag in report["flags"]]

    lines += ["", "--- Where you failed ---"]
    lines += where_you_failed(metrics)

    lines += ["", "--- Suggestions to raise the grade ---"]
    # The advice line comes from the rules file; without one, repeat the feedback.
    suggestions = [f"- {name}: {r.get('advice', r['feedback'])}"
                   for name, r in metrics.items() if r["score"] < 1]
    lines += suggestions or ["- None: full marks on every metric."]

    if report.get("usefulness_limitations"):
        lines += ["", "--- Usefulness & limitations of this evaluation ---"]
        lines += usefulness_lines(report["usefulness_limitations"])
    return "\n".join(lines) + "\n"

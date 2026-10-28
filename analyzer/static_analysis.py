"""Structure analyzer: lizard (size and complexity of each function) + cppcheck.

lizard measures every function:
  - cyclomatic complexity: 1 + the number of decisions (if, while, for,
    case, &&, ||, ?). It counts the separate paths through the function.
  - nloc: lines of code, not counting blank lines and comments, so a
    well-commented function is not punished for its comments.
A function over params["max_cyclomatic"] or params["max_function_length"]
is one problem for each limit it breaks.

cppcheck looks for likely bugs and bad style without running the code
(null pointer use, conditions that are always true, unused variables, ...).
Each finding is one problem.

score = 1 - penalty_per_problem x number of problems (never below 0)
The penalty is 0.2 unless params sets "penalty_per_problem".
"""

import subprocess

import lizard

CPPCHECK_TIMEOUT_S = 60
CPPCHECK_CHECKS = "warning,style,performance,portability"


def run_cppcheck(source_path):
    """Return cppcheck findings as a list of {"line", "severity", "id", "message"}."""
    template = "{line}:{severity}:{id}:{message}"
    result = subprocess.run(
        ["cppcheck", f"--enable={CPPCHECK_CHECKS}", "--quiet",
         f"--template={template}", source_path],
        capture_output=True, text=True, timeout=CPPCHECK_TIMEOUT_S,
    )
    findings = []
    # cppcheck prints its findings on stderr, one per line, in our template.
    for line in result.stderr.splitlines():
        parts = line.split(":", 3)
        if len(parts) == 4 and parts[0].isdigit():
            findings.append({"line": int(parts[0]), "severity": parts[1],
                             "id": parts[2], "message": parts[3]})
    return sorted(findings, key=lambda f: f["line"])


def analyze(source_path, first_pass, params, rules):
    max_cyclomatic = params["max_cyclomatic"]
    max_length = params["max_function_length"]
    penalty = params.get("penalty_per_problem", 0.2)

    functions = []
    problems = []
    for func in lizard.analyze_file(source_path).function_list:
        functions.append({"name": func.name, "line": func.start_line,
                          "cyclomatic": func.cyclomatic_complexity, "length": func.nloc})
        if func.cyclomatic_complexity > max_cyclomatic:
            problems.append(f"{func.name}() has cyclomatic complexity "
                            f"{func.cyclomatic_complexity} (limit {max_cyclomatic})")
        if func.nloc > max_length:
            problems.append(f"{func.name}() is {func.nloc} lines long (limit {max_length})")

    findings = run_cppcheck(source_path)
    for f in findings:
        problems.append(f"cppcheck line {f['line']}: {f['message']} [{f['id']}]")

    score = max(0.0, 1 - penalty * len(problems))
    if problems:
        feedback = f"{len(problems)} problem(s); first: {problems[0]}"
    else:
        feedback = (f"all functions within limits (cyclomatic <= {max_cyclomatic}, "
                    f"length <= {max_length}); cppcheck found nothing")
    return {
        "score": score,
        "evidence": {"functions": functions, "cppcheck": findings, "problems": problems},
        "feedback": feedback,
    }

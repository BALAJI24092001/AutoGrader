"""Modularity analyzer: is the work split into helper functions?

lizard lists every function defined in the file. A helper (any function
except main) only counts if it is called from inside another function.
Otherwise a student could add an empty, unused function to raise the score.
We remove comments first, so a commented-out call does not count either.

counted  = main (if present) + helpers that are called
required = params["min_functions"], and at least 2 if params["expect_helpers"]
score    = counted / required (never above 1)

With the brief's rules (min_functions 2), a program with only main() scores 0.5.
"""

import re

import lizard
from first_pass import strip_comments


def is_called(name, functions, code_lines):
    """True if name( appears in the body of some function other than name itself."""
    pattern = re.compile(r"\b" + re.escape(name) + r"\s*\(")
    for func in functions:
        if func.name == name:
            # a function calling itself (recursion) is not a use from outside
            continue
        body = "\n".join(
            code_lines[func.start_line : func.end_line]
        )  # skips the header line
        if pattern.search(body):
            return True
    return False


def analyze(source_path, first_pass, params, rules):
    required = params["min_functions"]
    if params.get("expect_helpers"):
        required = max(required, 2)

    with open(source_path, errors="replace") as f:
        code_lines = strip_comments(f.read()).splitlines()
    functions = lizard.analyze_file(source_path).function_list

    names = [func.name for func in functions]
    helpers = [name for name in names if name != "main"]
    used = [name for name in helpers if is_called(name, functions, code_lines)]
    unused = [name for name in helpers if name not in used]
    counted = len(used) + (1 if "main" in names else 0)

    score = min(1.0, counted / required)
    if not functions:
        feedback = "no functions found"
    elif not helpers:
        feedback = "only main() is defined; move a piece of the work into a helper function and call it from main"
    elif score < 1:
        feedback = f"{counted} function(s) in use, {required} expected"
    else:
        feedback = f"work is split into {counted} functions: {', '.join(names)}"
    if unused:
        feedback += f"; defined but never called: {', '.join(unused)}"

    return {
        "score": score,
        "evidence": {
            "functions_defined": names,
            "helpers_used": used,
            "helpers_unused": unused,
            "counted": counted,
            "expected_min": required,
        },
        "feedback": feedback,
    }

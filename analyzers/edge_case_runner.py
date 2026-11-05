"""Logical analyzer: run tricky inputs through the student program and a reference.

For each case name in params["cases"] (for example "int_overflow") we make
  - a few fixed inputs that every grader would think of, and
  - params["random_per_case"] random inputs of the same kind.
The random numbers come from random.Random(params["seed"]), so every run
makes exactly the same inputs and the grade stays reproducible.

The reference solution (params["reference"]) is compiled with plain gcc and
run on the same inputs. Its output is the expected answer. Whenever the
student's output differs (compared token by token, like io_tests), we report
the input, the expected and actual output, and a one-line reason that
depends on the case name.

The generators below assume this problem's input format: two integers on
one line. For any other problem, the rules can instead give
params["inputs_dir"], a folder of hand-written NAME.in files. Each file is
one case called NAME, and params["reasons"] can give a reason per NAME.

score = inputs where the student matches the reference / all inputs
"""

import glob
import os
import random

import sandbox
from first_pass import compile_plain

INT_MAX = 2**31 - 1
INT_MIN = -2**31
MAX_SHOWN = 200  # characters of program output kept in the evidence

FIXED = {
    "negatives": [(-7, -5), (-7, 5), (7, -5), (-1, -1)],
    "zero": [(0, 0), (0, 5), (-5, 0)],
    "int_overflow": [(INT_MAX, 1), (INT_MIN, -1), (INT_MAX, INT_MAX), (INT_MIN, INT_MIN)],
}

REASONS = {
    "negatives": "wrong result with negative numbers; check how signs are read and added (%d, not %u)",
    "zero": "wrong result when an input is zero; a special case for 0 is probably wrong",
    "int_overflow": "sum goes beyond int range; use long long (and %lld) for the numbers and the sum",
}


def random_pair(case, rng, i):
    """One random input of the given kind."""
    if case == "negatives":
        return rng.randint(-1000, -1), rng.randint(-1000, 1000)
    if case == "zero":
        other = rng.randint(-1000, 1000)
        return (0, other) if i % 2 == 0 else (other, 0)
    if case == "int_overflow":
        # Pick b so that a + b is always just outside the int range,
        # going over INT_MAX on even i and under INT_MIN on odd i.
        if i % 2 == 0:
            a = rng.randint(INT_MAX - 1000, INT_MAX)
            return a, rng.randint(INT_MAX - a + 1, INT_MAX - a + 1000)
        a = rng.randint(INT_MIN, INT_MIN + 1000)
        return a, rng.randint(INT_MIN - a - 1000, INT_MIN - a - 1)
    raise ValueError(f"no input generator for case {case!r}")


DEFAULT_REASON = "output differs from the reference solution on this input"


def read_inputs_dir(folder):
    """Return a list of (case, input text), one per NAME.in file, sorted by name."""
    inputs = []
    for path in sorted(glob.glob(os.path.join(folder, "*.in"))):
        with open(path) as f:
            inputs.append((os.path.basename(path)[:-3], f.read()))
    if not inputs:
        raise ValueError(f"no .in files in {folder}")
    return inputs


def make_inputs(params):
    """Return a list of (case, input text), the same list on every run."""
    if "inputs_dir" in params:
        return read_inputs_dir(params["inputs_dir"])
    rng = random.Random(params.get("seed", 42))
    count = params.get("random_per_case", 3)
    inputs = []
    for case in params["cases"]:
        if case not in FIXED:
            raise ValueError(f"no input generator for case {case!r}")
        pairs = FIXED[case] + [random_pair(case, rng, i) for i in range(count)]
        inputs += [(case, f"{a} {b}\n") for a, b in pairs]
    return inputs


def analyze(source_path, first_pass, params, rules):
    # Own folder, so reference/add.c does not overwrite the student's build/add/add.
    reference, errors = compile_plain(params["reference"],
                                      os.path.join(rules["build_dir"], "reference"))
    if reference is None:
        raise RuntimeError(f"reference solution does not compile: {errors.strip()[:300]}")

    inputs = make_inputs(params)
    failures = []
    for case, test_input in inputs:
        expected = sandbox.run([reference], test_input,
                               rules["time_limit_s"], rules["memory_limit_mb"])
        if expected["status"] != "ok":
            raise RuntimeError(f"reference failed on {test_input.strip()!r}: {expected['status']}")
        got = sandbox.run([first_pass["binary"]], test_input,
                          rules["time_limit_s"], rules["memory_limit_mb"])
        if got["status"] == "ok" and got["stdout"].split() == expected["stdout"].split():
            continue
        # The case's reason only fits a wrong answer, not a crash or a timeout.
        if got["status"] == "ok":
            reason = params.get("reasons", REASONS).get(case, DEFAULT_REASON)
        else:
            reason = f"the program did not finish normally ({got['status']}), so it gave no answer"
        failures.append({
            "case": case,
            "input": test_input.strip(),
            "expected": expected["stdout"].strip(),
            "got": got["stdout"].strip()[:MAX_SHOWN],
            "status": got["status"],
            "reason": reason,
        })

    total = len(inputs)
    passed = total - len(failures)
    feedback = f"{passed} of {total} edge cases match the reference"
    if failures:
        first = failures[0]
        feedback += (f"; {first['case']}: input {first['input']!r}, expected {first['expected']!r}, "
                     f"got {first['got']!r} ({first['status']}): {first['reason']}")
    return {
        "score": passed / total,
        "evidence": {"passed": passed, "total": total,
                     "cases": params.get("cases", [case for case, _ in inputs]),
                     "failures": failures},
        "feedback": feedback,
    }

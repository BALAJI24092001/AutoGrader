"""Correctness analyzer: run the program on every test and compare the output.

Each test is a pair NN.in / NN.out in params["testset_dir"]. We compare
whitespace-separated tokens, so "12" and "12\n" or "12  " all count as the
same answer, but "12" and "13" do not.

score = tests passed / total tests
"""

import glob
import os

import sandbox

MAX_SHOWN = 200  # characters of program output kept in the evidence


def analyze(source_path, first_pass, params, rules):
    inputs = sorted(glob.glob(os.path.join(params["testset_dir"], "*.in")))
    if not inputs:
        raise ValueError(f"no .in files in {params['testset_dir']}")

    failures = []
    for in_path in inputs:
        with open(in_path) as f:
            test_input = f.read()
        with open(in_path[:-3] + ".out") as f:
            expected = f.read()

        result = sandbox.run(
            [first_pass["binary"]],
            test_input,
            rules["time_limit_s"],
            rules["memory_limit_mb"],
        )
        if result["status"] == "ok" and result["stdout"].split() == expected.split():
            continue
        failures.append(
            {
                "test": os.path.basename(in_path)[:-3],
                "input": test_input.strip(),
                "expected": expected.strip(),
                "got": result["stdout"].strip()[:MAX_SHOWN],
                "status": result["status"],
            }
        )

    total = len(inputs)
    passed = total - len(failures)
    feedback = f"{passed} of {total} tests pass"
    if failures:
        first = failures[0]
        feedback += (
            f"; first failure {first['test']}: input {first['input']!r}, "
            f"expected {first['expected']!r}, got {first['got']!r} ({first['status']})"
        )
    return {
        "score": passed / total,
        "evidence": {"passed": passed, "total": total, "failures": failures},
        "feedback": feedback,
    }

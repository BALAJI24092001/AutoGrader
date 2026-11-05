"""Syntax analyzer: compile again with exactly the flags from the rules file.

This compile is separate from the first pass, so -Werror only affects this
score. We add only "-c -o <file>" (compile to an object file, skip linking);
those choose where the output goes and do not change which warnings appear.

gcc prints each problem as "file:line:col: warning: ..." or "... error: ...".
With -Werror a warning is printed as an error ending in "[-Werror=<name>]",
so we count those as warnings, not as real errors.

score = 0 if there is a real error, otherwise
        1 - penalty_per_warning x number of warnings (never below 0)
"""

import os
import shlex
import subprocess

COMPILE_TIMEOUT_S = 30


def analyze(source_path, first_pass, params, rules):
    flags = shlex.split(params["flags"])
    penalty = params.get("penalty_per_warning", 0.25)

    os.makedirs(rules["build_dir"], exist_ok=True)
    name = os.path.splitext(os.path.basename(source_path))[0]
    obj = os.path.join(rules["build_dir"], name + ".syntax.o")
    result = subprocess.run(["gcc", *flags, "-c", source_path, "-o", obj],
                            capture_output=True, text=True, timeout=COMPILE_TIMEOUT_S)

    warnings, errors = [], []
    for line in result.stderr.splitlines():
        if ": warning:" in line or (": error:" in line and "[-Werror" in line):
            warnings.append(line)
        elif ": error:" in line:
            errors.append(line)

    if errors:
        score = 0.0
        feedback = f"does not compile with {params['flags']}: {errors[0]}"
    elif warnings:
        score = max(0.0, 1 - penalty * len(warnings))
        feedback = f"{len(warnings)} warning(s) with {params['flags']}; first: {warnings[0]}"
    else:
        score = 1.0
        feedback = f"compiles cleanly with {params['flags']}"
    return {
        "score": score,
        "evidence": {"flags": params["flags"], "warnings": warnings, "errors": errors},
        "feedback": feedback,
    }

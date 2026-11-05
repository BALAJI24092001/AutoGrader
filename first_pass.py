"""First pass: quick checks before the real analyzers run.

1. Regex checks on the source: does it have main, scanf, printf, return?
2. Compile with plain gcc (no -Werror). This binary is what every run-based
   analyzer uses. The syntax analyzer does its own, stricter compile, so
   warnings only lower the syntax score and never block the other analyzers.
3. Smoke run: run the binary once on the sample input inside the sandbox.

If the program does not compile, or the smoke run times out (we then set
suspected_infinite_loop), can_run is False and the coordinator should run
only the source-based analyzers (syntax, structure, modularity, readability,
originality). A crash does not set can_run to False: the other analyzers
still run, and io_tests and sanitizer_run will show what went wrong.

Try it by hand:
    python3 first_pass.py rules/add.json submissions/add/*.c
"""

import os
import re
import subprocess

import sandbox

COMPILE_TIMEOUT_S = 30

# Each check is a regex searched in the source after comments are removed.
CHECKS = {
    "has_main": r"\bmain\s*\(",
    "uses_scanf": r"\bscanf\s*\(",
    "uses_printf": r"\bprintf\s*\(",
    "has_return": r"\breturn\b",
}


def strip_comments(code):
    """Remove /* ... */ and // comments, so commented-out code does not count.

    A block comment is replaced by the newlines it contained, so every line
    of code keeps its line number (function_split relies on this).
    """
    code = re.sub(r"/\*.*?\*/", lambda m: " " + "\n" * m.group().count("\n"),
                  code, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", " ", code)


def compile_plain(source_path, build_dir):
    """Compile with plain gcc. Returns (binary path or None, compiler messages)."""
    os.makedirs(build_dir, exist_ok=True)
    name = os.path.splitext(os.path.basename(source_path))[0]
    binary = os.path.join(build_dir, name)
    # -lm links the maths library, so a student who uses sqrt() still compiles.
    result = subprocess.run(
        ["gcc", source_path, "-o", binary, "-lm"],
        capture_output=True, text=True, timeout=COMPILE_TIMEOUT_S,
    )
    if result.returncode != 0:
        return None, result.stderr
    return binary, result.stderr


def run_first_pass(source_path, rules):
    with open(source_path, errors="replace") as f:
        code = strip_comments(f.read())
    checks = {name: bool(re.search(pattern, code)) for name, pattern in CHECKS.items()}

    binary, compiler_output = compile_plain(source_path, rules["build_dir"])

    smoke = None
    if binary is not None:
        with open(rules["sample_input"]) as f:
            sample = f.read()
        smoke = sandbox.run([binary], sample, rules["time_limit_s"], rules["memory_limit_mb"])

    suspected_infinite_loop = smoke is not None and smoke["status"] == "timeout"
    return {
        "source": source_path,
        "checks": checks,
        "compiled": binary is not None,
        "compiler_output": compiler_output,
        "binary": binary,
        "smoke": smoke,
        "suspected_infinite_loop": suspected_infinite_loop,
        "can_run": binary is not None and not suspected_infinite_loop,
    }


if __name__ == "__main__":
    import sys

    from rules import load_rules

    rules = load_rules(sys.argv[1])
    for source in sys.argv[2:]:
        fp = run_first_pass(source, rules)
        missing = [name for name, found in fp["checks"].items() if not found]
        smoke = fp["smoke"]["status"] if fp["smoke"] else "-"
        output = fp["smoke"]["stdout"].strip() if fp["smoke"] else ""
        print(f"{os.path.basename(source):22} compiled={fp['compiled']!s:5} "
              f"smoke={smoke:8} output={output!r:6} "
              f"infinite_loop={fp['suspected_infinite_loop']!s:5} can_run={fp['can_run']!s:5} "
              f"missing={missing}")
        if not fp["compiled"]:
            first_error = next((l for l in fp["compiler_output"].splitlines() if "error:" in l),
                               fp["compiler_output"].strip())
            print(f"{'':22} compile error: {first_error}")

"""Memory safety analyzer: compile with AddressSanitizer + UBSan and run it.

The sanitizers add checks to the compiled program. While it runs, they
report problems on stderr:
  - AddressSanitizer (ASan): reading or writing outside an array, use after
    free, null pointer use, ...
  - LeakSanitizer (part of ASan): memory from malloc that is never freed,
    reported when the program ends.
  - UndefinedBehaviorSanitizer (UBSan): signed integer overflow, division by
    zero, bad shifts, ...

Build: gcc <params["flags"]> -fno-sanitize-recover=all -g ...
  -fno-sanitize-recover=all  UBSan normally prints a message and carries on
                             with exit code 0; this makes it stop the program.
  -g                         so the reports give file:line, not just addresses.
We read the problems from stderr, not from the exit code, because a student
program may also exit with 1 on its own.

The program runs once on every input in params["inputs_dir"] (or only on the
rules' sample_input if that is not set). A sanitizer only sees the code an
input actually runs, so more inputs find more problems.
It runs without the memory limit, because ASan reserves terabytes of virtual
memory at start (it does not really use them), and with 3x the time limit,
because the checks make the program slower.

The same problem found on several inputs counts once. A problem is its kind
plus the line in the student's file, e.g. ("memory leak", "add_leak.c:8").
We never keep process ids or memory addresses: they change on every run.

score = 1 - penalty_per_problem x number of distinct problems (never below 0)
The penalty is 0.25 unless params sets "penalty_per_problem".
"""

import glob
import os
import re
import shlex
import subprocess

import sandbox

COMPILE_TIMEOUT_S = 30
SLOWDOWN = 3  # sanitized programs run roughly 2-3x slower

# The three kinds of report line we look for in stderr.
UBSAN_LINE = re.compile(r"^(\S+?):(\d+):\d+: runtime error: (.+)$")
ASAN_LINE = re.compile(r"ERROR: AddressSanitizer: (\S+)")
LEAK_LINE = re.compile(r"^(Direct|Indirect) leak of .+")
# A stack frame, e.g. "#1 0x5880380a629e in main submissions/add/add_leak.c:8"
FRAME_LINE = re.compile(r"#\d+ 0x[0-9a-f]+ in (\S+) (\S+?):(\d+)")


def compile_sanitized(source_path, flags, build_dir):
    os.makedirs(build_dir, exist_ok=True)
    name = os.path.splitext(os.path.basename(source_path))[0]
    binary = os.path.join(build_dir, name + ".asan")
    result = subprocess.run(
        ["gcc", *shlex.split(flags), "-fno-sanitize-recover=all", "-g",
         "-fno-omit-frame-pointer", source_path, "-o", binary, "-lm"],
        capture_output=True, text=True, timeout=COMPILE_TIMEOUT_S,
    )
    if result.returncode != 0:
        raise RuntimeError(f"sanitizer build failed: {result.stderr.strip()[:300]}")
    return binary


def find_problems(stderr, source_name):
    """Read sanitizer stderr and return a list of {"kind", "where", "message"}."""
    problems = []
    waiting = None  # an ASan/leak problem still looking for its line in the student's file
    for line in stderr.splitlines():
        line = line.strip()
        ubsan = UBSAN_LINE.match(line)
        asan = ASAN_LINE.search(line)
        leak = LEAK_LINE.match(line)
        frame = FRAME_LINE.search(line)

        if ubsan:
            problems.append({"kind": "undefined behaviour",
                             "where": f"{os.path.basename(ubsan.group(1))}:{ubsan.group(2)}",
                             "message": ubsan.group(3)})
        elif asan and asan.group(1) != "LeakSanitizer":
            waiting = {"kind": asan.group(1), "where": "unknown", "message": asan.group(1)}
            problems.append(waiting)
        elif leak:
            waiting = {"kind": "memory leak", "where": "unknown",
                       "message": line.split(" allocated from")[0]}
            problems.append(waiting)
        elif frame and waiting and os.path.basename(frame.group(2)) == source_name:
            waiting["where"] = f"{source_name}:{frame.group(3)} in {frame.group(1)}()"
            waiting = None
    return problems


def input_files(params, rules):
    if "inputs_dir" in params:
        return sorted(glob.glob(os.path.join(params["inputs_dir"], "*.in")))
    return [rules["sample_input"]]


def analyze(source_path, first_pass, params, rules):
    penalty = params.get("penalty_per_problem", 0.25)
    binary = compile_sanitized(source_path, params["flags"], rules["build_dir"])
    source_name = os.path.basename(source_path)

    distinct = {}   # (kind, where) -> problem, with the first input that showed it
    timeouts = []
    paths = input_files(params, rules)
    for in_path in paths:
        with open(in_path) as f:
            test_input = f.read()
        result = sandbox.run([binary], test_input,
                             rules["time_limit_s"] * SLOWDOWN, memory_limit_mb=None)
        if result["status"] == "timeout":
            timeouts.append(os.path.basename(in_path))
        for problem in find_problems(result["stderr"], source_name):
            key = (problem["kind"], problem["where"])
            if key not in distinct:
                problem["input"] = test_input.strip()
                distinct[key] = problem

    problems = list(distinct.values())
    score = max(0.0, 1 - penalty * len(problems))
    if problems:
        first = problems[0]
        feedback = (f"{len(problems)} problem(s); first: {first['kind']} at {first['where']} "
                    f"({first['message']}) on input {first['input']!r}")
    else:
        feedback = f"ASan/UBSan clean on {len(paths)} input(s)"
    if timeouts:
        feedback += f"; {len(timeouts)} input(s) timed out and were not fully checked"
    return {
        "score": score,
        "evidence": {"flags": params["flags"], "inputs_run": len(paths),
                     "problems": problems, "timeouts": timeouts},
        "feedback": feedback,
    }

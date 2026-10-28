"""Safe runner for student programs.

run() starts a compiled program, feeds it an input, and stops it if it takes
too long, uses too much memory, or prints too much. It never raises because of
what the student program does; it always returns a result dictionary.

How the limits work:
  - Time: we wait at most time_limit_s seconds (wall clock), then kill the
    program. As a backup, the kernel also stops it after time_limit_s + 1
    seconds of CPU time (RLIMIT_CPU).
  - Memory: RLIMIT_AS caps the memory the program can reserve. When it hits
    the cap, malloc returns NULL, which usually makes the program crash.
  - Output: stdout and stderr go to temporary files, and RLIMIT_FSIZE caps
    how big those files can get, so an endless printf loop cannot fill the disk.
  - Core dumps are switched off (RLIMIT_CORE = 0).

Try it by hand:
    python3 sandbox.py submissions/add/add_crash.c tests/add/01.in
"""

import math
import os
import resource
import signal
import subprocess
import tempfile
import time

MAX_OUTPUT_BYTES = 1_000_000  # 1 MB is far more than any correct answer needs


def _set_limits(time_limit_s, memory_limit_mb):
    """Return a function that the child process runs just before the program starts."""
    def apply():
        cpu = math.ceil(time_limit_s) + 1
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
        resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_OUTPUT_BYTES, MAX_OUTPUT_BYTES))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        if memory_limit_mb is not None:
            limit = memory_limit_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    return apply


def _status(timed_out, returncode):
    """Turn what happened into one simple word."""
    if timed_out or returncode == -signal.SIGXCPU:
        return "timeout"
    if returncode == -signal.SIGXFSZ:
        return "output_limit"
    if returncode < 0:
        return "crash"          # killed by a signal, e.g. SIGSEGV or SIGABRT
    if returncode > 0:
        return "error_exit"     # program ended normally but returned non-zero
    return "ok"


def run(command, input_text, time_limit_s, memory_limit_mb):
    """Run command (a list such as ["build/add"]) with input_text on stdin.

    memory_limit_mb can be None for no memory limit (needed later for
    AddressSanitizer, which reserves a lot of virtual memory up front).

    Returns a dict:
        status       "ok", "timeout", "crash", "error_exit" or "output_limit"
        returncode   exit code, or minus the signal number if it was killed
        signal       signal name such as "SIGSEGV", or None
        stdout, stderr  text the program printed (at most MAX_OUTPUT_BYTES each)
        time_s       wall-clock seconds the run took
    """
    # The program runs inside a fresh empty folder, so files it creates with a
    # relative name (e.g. fopen("out.txt", "w")) land there and are deleted
    # afterwards. The path to the program must then be absolute.
    command = [os.path.abspath(command[0]), *command[1:]]
    with tempfile.TemporaryDirectory() as work_dir, \
         tempfile.TemporaryFile() as stdin_file, \
         tempfile.TemporaryFile() as stdout_file, \
         tempfile.TemporaryFile() as stderr_file:
        stdin_file.write(input_text.encode())
        stdin_file.seek(0)

        start = time.monotonic()
        proc = subprocess.Popen(
            command,
            stdin=stdin_file,
            stdout=stdout_file,
            stderr=stderr_file,
            cwd=work_dir,
            preexec_fn=_set_limits(time_limit_s, memory_limit_mb),
            start_new_session=True,  # own process group, so we can kill all of it
        )
        timed_out = False
        try:
            proc.wait(timeout=time_limit_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
        elapsed = time.monotonic() - start

        stdout_file.seek(0)
        stderr_file.seek(0)
        stdout = stdout_file.read().decode(errors="replace")
        stderr = stderr_file.read().decode(errors="replace")

    returncode = proc.returncode
    signal_name = signal.Signals(-returncode).name if returncode < 0 else None
    return {
        "status": _status(timed_out, returncode),
        "returncode": returncode,
        "signal": signal_name,
        "stdout": stdout,
        "stderr": stderr,
        "time_s": round(elapsed, 3),
    }


if __name__ == "__main__":
    # Small demo: compile one C file with plain gcc, then run it in the sandbox.
    import sys

    source, input_path = sys.argv[1], sys.argv[2]
    os.makedirs("build", exist_ok=True)
    binary = os.path.join("build", os.path.splitext(os.path.basename(source))[0])
    subprocess.run(["gcc", source, "-o", binary], check=True)

    with open(input_path) as f:
        result = run([binary], f.read(), time_limit_s=1, memory_limit_mb=64)
    for key, value in result.items():
        print(f"{key:10} {value!r}")

"""Rules loader.

Reads the instructor's rules JSON, checks that it makes sense, and records the
file's SHA-256 hash. The hash goes into every report, so anyone can confirm
which exact rules file produced a grade.

The rules name is the file name without .json (rules/add.json gives "add").
Compiled programs go to build/<name>/ and reports to reports/<name>/, so two
problems never share a folder.

Try it by hand:
    python3 rules.py rules/add.json
"""

import hashlib
import json
import os

REQUIRED_TOP = ["time_limit_s", "memory_limit_mb", "sample_input", "metrics"]
REQUIRED_METRIC = ["name", "analyzer", "weight", "params"]


def load_rules(path):
    """Load and check a rules file. Raises ValueError with a clear message if it is wrong."""
    with open(path, "rb") as f:
        raw = f.read()
    rules = json.loads(raw)

    for key in REQUIRED_TOP:
        if key not in rules:
            raise ValueError(f"rules file is missing '{key}'")
    if rules["time_limit_s"] <= 0 or rules["memory_limit_mb"] <= 0:
        raise ValueError("time_limit_s and memory_limit_mb must be positive")
    if not rules["metrics"]:
        raise ValueError("rules file has no metrics")

    names = set()
    for metric in rules["metrics"]:
        for key in REQUIRED_METRIC:
            if key not in metric:
                raise ValueError(f"a metric is missing '{key}': {metric}")
        if metric["name"] in names:
            raise ValueError(f"metric '{metric['name']}' appears twice")
        names.add(metric["name"])
        if not 0 <= metric["weight"] <= 1:
            raise ValueError(f"metric '{metric['name']}' has weight outside 0..1")

    # Weights must add up to 1 so the grade is out of 100. We allow a tiny
    # difference because 0.1 + 0.2 is not exactly 0.3 in floating point.
    total = sum(m["weight"] for m in rules["metrics"])
    if abs(total - 1) > 1e-6:
        raise ValueError(f"weights add up to {total}, not 1")

    rules["sha256"] = hashlib.sha256(raw).hexdigest()
    rules["name"] = os.path.splitext(os.path.basename(path))[0]
    rules["build_dir"] = os.path.join("build", rules["name"])
    return rules


if __name__ == "__main__":
    import sys

    rules = load_rules(sys.argv[1])
    print("sha256", rules["sha256"])
    for m in rules["metrics"]:
        print(f"  {m['name']:14} {m['analyzer']:22} weight {m['weight']}")

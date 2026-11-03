"""Originality analyzer: compare the submission with a folder of other C files.

Steps: remove comments/strings -> turn code into tokens -> replace names with ID
and numbers with NUM -> cut into overlapping 5-token pieces -> compare the sets.
Renaming variables or changing numbers therefore does not hide a copy.

The corpus (params["corpus_dir"]) can hold other students' files, and also
code found online or written by an LLM; every *.c file in it, in any
sub-folder, is compared. The submission itself is skipped.

A similarity at or above params["flag_threshold"] only raises a flag for the
teacher. It never lowers the score: two students can write the same short
program on their own, so a human has to decide. The score is always 1.0.
"""
import glob
import os
import re

KEYWORDS = {
    "int", "long", "short", "char", "float", "double", "void", "unsigned", "signed",
    "const", "static", "struct", "if", "else", "for", "while", "do", "switch", "case",
    "default", "break", "continue", "return", "sizeof",
}
TOKEN = re.compile(r"[A-Za-z_]\w*|\d+(?:\.\d+)?|==|!=|<=|>=|&&|\|\||\+\+|--|->|<<|>>|[^\s\w]")


def normalize(code):
    code = re.sub(r"/\*.*?\*/", " ", code, flags=re.S)    # /* block comments */
    code = re.sub(r"//[^\n]*", " ", code)                 # // line comments
    code = re.sub(r"#[^\n]*", " ", code)                  # #include, #define
    code = re.sub(r'"(?:\\.|[^"\\])*"', " STR ", code)    # "string literals"
    tokens = []
    for t in TOKEN.findall(code):
        if t in KEYWORDS:
            tokens.append(t)                # keep keywords as they are
        elif t[0].isalpha() or t[0] == "_":
            tokens.append("ID")             # every name becomes ID
        elif t[0].isdigit():
            tokens.append("NUM")            # every number becomes NUM
        else:
            tokens.append(t)                # operators and brackets stay
    return tokens


def kgrams(tokens, k=5):
    return {tuple(tokens[i:i + k]) for i in range(len(tokens) - k + 1)}


def similarity(a, b, k=5):
    A, B = kgrams(a, k), kgrams(b, k)
    if not A or not B:
        return 0.0
    return len(A & B) / min(len(A), len(B))   # share of the smaller file found in the other


def analyze(source_path, first_pass, params, rules):
    threshold = params.get("flag_threshold", 0.85)
    with open(source_path, errors="replace") as f:
        me = normalize(f.read())

    best, match = 0.0, None
    pattern = os.path.join(params["corpus_dir"], "**", "*.c")
    for other in sorted(glob.glob(pattern, recursive=True)):
        if os.path.abspath(other) == os.path.abspath(source_path):
            continue
        with open(other, errors="replace") as f:
            s = similarity(me, normalize(f.read()))
        if s > best:
            best, match = s, other

    result = {
        "score": 1.0,
        "evidence": {"max_similarity": round(best, 2), "closest_file": match,
                     "flag_threshold": threshold},
        "feedback": f"max similarity {best:.2f} with {match} (not flagged)",
    }
    if best >= threshold:
        result["flag"] = (f"suspected copying: similarity {best:.2f} with {match} "
                          f"(threshold {threshold}); please check by hand")
        result["feedback"] = f"max similarity {best:.2f} with {match}: flagged for the teacher"
    return result

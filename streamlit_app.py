"""AutoGrader portal: pick or upload a C program and a rules file, grade it, see the report card.

Run with:  streamlit run streamlit_app.py

Grading uses the same code as the command line (autograder.grade_submission), so the
grade here is the same as `python3 autograder.py RULES.json FILE.c`. The report is
also saved to reports/<rules name>/<name>.json and .txt, like the command line does.
Uploaded files are saved to temp_submissions/ and temp_rules/ (git-ignored), because
gcc, cppcheck and the other tools need a real file path.
"""
import glob
import html
import json
import os
import re

import streamlit as st

# Rules files use paths relative to the project folder (tests/add/, reference/add.c),
# so work from there even if streamlit was started somewhere else.
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from autograder import grade_submission, save_report, tool_versions  # noqa: E402
from report_text import run_problems, run_problems_text  # noqa: E402
from rules import load_rules  # noqa: E402

UPLOAD_SUBMISSIONS = "temp_submissions"
UPLOAD_RULES = "temp_rules"
# Shown before anything is graded, so the page never opens empty.
# It matches the sidebar's first choice (rules/add.json + submissions/add/add.c).
DEFAULT_REPORT = "sample_outputs/add/add.json"
SPINNER_TEXT = ("Compiling code, running sandbox tests, analyzing static metrics, "
                "and querying LLM review...")

METRIC_ORDER = ["correctness", "syntax", "structure", "modularity", "logical",
                "complexity", "memory_safety", "readability", "originality"]
GRADE_KEY = [("A+", 90, "90-100"), ("A", 80, "80-89"), ("B", 70, "70-79"),
             ("C", 60, "60-69"), ("F", 0, "below 60")]

CSS = """
<style>
:root {
    --green: #1E4D3B;       /* banner and headings */
    --page: #F7F7F5;        /* page background */
    --paper: #FFFFFF;       /* tables and boxes */
    --line: #D1D5DB;        /* outer borders */
    --rule: #E5E7EB;        /* thin row lines */
    --text: #1F2933;
    --muted: #6B7280;
    --serif: 'Times New Roman', Times, serif;
    --sans: -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

/* Report text in Times New Roman. */
.stApp, .stApp p, .stApp li, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
.stApp td, .stApp th, .banner, .box {
    font-family: var(--serif) !important;
}
.stApp { background: var(--page); color: var(--text); }
.stApp h1, .stApp h2, .stApp h3, .stApp h4 { color: var(--green); font-weight: bold; }
.stApp h3 { font-size: 1.3rem; border-bottom: 1px solid var(--line); padding-bottom: 4px; margin-top: 1.4rem; }

/* Small controls in a plain sans font, so they stay crisp at small sizes.
   Streamlit draws its icons (e.g. the upload arrow) as words in an icon font
   ("upload" becomes the arrow), so icon elements must keep their own font,
   otherwise the upload button reads "uploadUpload". */
.stApp .badge, .stApp button, .stApp button *:not([data-testid="stIconMaterial"]),
.stApp [data-baseweb="select"] *:not([data-testid="stIconMaterial"]),
[data-baseweb="popover"] *:not([data-testid="stIconMaterial"]),
.stApp [data-testid="stWidgetLabel"] *, .stApp [data-baseweb="tab"] *,
.stApp [data-testid="stFileUploaderDropzoneInstructions"] *:not([data-testid="stIconMaterial"]),
.stApp .key, .stApp .key * {
    font-family: var(--sans) !important;
    line-height: 1.45;
}

/* Header: title and subtitle on the left, the grade box on the right. */
.banner { background: var(--green); color: #FFFFFF; border-radius: 2px; padding: 20px 26px;
          display: flex; justify-content: space-between; align-items: center;
          flex-wrap: wrap; gap: 18px; }
.banner .title { font-size: 2rem; font-weight: bold; line-height: 1.1; }
.banner .subtitle { font-size: 0.95rem; letter-spacing: 3px; opacity: 0.85; margin: 4px 0 12px 0; }
.banner .meta { font-size: 1.05rem; }
.banner .summary { border: 1px solid rgba(255, 255, 255, 0.45); padding: 10px 22px;
                   text-align: center; min-width: 150px; }
.banner .summary .num { font-size: 2.2rem; font-weight: bold; line-height: 1.15; }
.banner .summary .letter { font-size: 1rem; border-top: 1px solid rgba(255, 255, 255, 0.35);
                           margin-top: 6px; padding-top: 4px; }

.badge { display: inline-block; padding: 1px 8px; border-radius: 3px; font-size: 0.75rem;
         font-weight: 600; margin-right: 6px; border: 1px solid; }
.badge.ok { background: #ECFDF3; color: #166534; border-color: #A7D7B8; }
.badge.bad { background: #FEF2F2; color: #991B1B; border-color: #F5B5B5; }
.badge.warn { background: #FFFBEB; color: #92400E; border-color: #F3D19C; }

/* Plain bordered boxes for failures, flags and notes. */
.box { background: var(--paper); color: var(--text); border: 1px solid var(--line);
       padding: 12px 16px; margin: 10px 0; }
.box.fail { border-left: 3px solid #B91C1C; }
.box.flag { border-left: 3px solid #B45309; }
.box pre { background: #F9FAFB; border: 1px solid var(--rule); padding: 6px 10px;
           margin: 4px 0 8px 0; white-space: pre-wrap; }

/* Score table: thin row lines, numbers right-aligned, a clear total row. */
table.metrics { width: 100%; border-collapse: collapse; background: var(--paper);
                color: var(--text); font-size: 1rem; border: 1px solid var(--line); }
table.metrics th { text-align: left; padding: 10px 14px; color: var(--green);
                   border-bottom: 2px solid var(--green); background: var(--paper); }
table.metrics td { padding: 9px 14px; border-bottom: 1px solid var(--rule); }
table.metrics .num { text-align: right; white-space: nowrap; }
table.metrics tr.total td { font-weight: bold; font-size: 1.08rem; background: #F3F4F6;
                            border-top: 2px solid var(--green); border-bottom: none; }

/* Grade key: dark text on white, readable on a light or dark sidebar. */
table.key { width: 100%; border-collapse: collapse; background: var(--paper);
            color: var(--text); border: 1px solid var(--line); font-size: 0.85rem; }
table.key td { padding: 5px 10px; border-bottom: 1px solid var(--rule); }
table.key td:first-child { font-weight: 600; }
table.key td:last-child { text-align: right; color: var(--muted); }
</style>
"""


# ---------- Files ----------

def rules_files():
    return sorted(glob.glob("rules/*.json"))


def submission_files():
    """The graded samples: submissions/<problem>/*.c (corpus sub-folders are skipped)."""
    return sorted(glob.glob("submissions/*/*.c"))


def known_problems():
    """Problem names, one per folder in submissions/ (add, search)."""
    return sorted(os.path.basename(d) for d in glob.glob("submissions/*") if os.path.isdir(d))


def rules_problem(rules_path):
    """rules/search.json -> "search": the same name the grader uses for build/ and reports/.

    None if it is not a known problem (e.g. an upload called my_rules.json), because
    then we cannot tell which problem it is for.
    """
    name = os.path.splitext(os.path.basename(rules_path))[0]
    return name if name in known_problems() else None


def submission_problem(submission_path):
    """submissions/add/add_infinite.c -> "add" (its folder).

    An upload has no problem folder, so we go by its name: "search_good.c" or
    "search.c" -> "search". None if the name does not start with a known problem.
    """
    parts = os.path.normpath(submission_path).split(os.sep)
    if len(parts) >= 3 and parts[0] == "submissions":
        return parts[1]
    stem = os.path.splitext(os.path.basename(submission_path))[0]
    for problem in known_problems():
        if stem == problem or stem.startswith(problem + "_"):
            return problem
    return None


def mismatch_message(rules_path, submission_path):
    """A warning if the rules and the submission are for different problems, else None."""
    rules_for = rules_problem(rules_path)
    submission_for = submission_problem(submission_path)
    if rules_for and submission_for and rules_for != submission_for:
        return (f"Problem Mismatch: Selected rules are for '{rules_for}', "
                f"but the submission is from '{submission_for}'.")
    return None


def save_upload(uploaded, folder):
    """Write an uploaded file to folder/ under a safe name and return its path.

    Only the base name is kept and odd characters become "_", so an upload called
    "../../x.c" cannot be written outside the folder.
    """
    name = re.sub(r"[^A-Za-z0-9_.-]", "_", os.path.basename(uploaded.name)).lstrip(".")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name or "upload")
    with open(path, "wb") as f:
        f.write(uploaded.getvalue())
    return path


def read_text(path):
    if path and os.path.isfile(path):
        with open(path, errors="replace") as f:
            return f.read()
    return None


# ---------- Small helpers ----------

def esc(value):
    """Escape for HTML: student output must never be rendered as markup."""
    return html.escape(str(value))


def letter_grade(grade):
    for letter, minimum, _ in GRADE_KEY:
        if grade >= minimum:
            return letter
    return "F"


def ordered_metrics(report):
    metrics = report["metrics"]
    names = [m for m in METRIC_ORDER if m in metrics] + [m for m in metrics if m not in METRIC_ORDER]
    return [(name, metrics[name]) for name in names]


def nice_name(name):
    return name.replace("_", " ").capitalize()


def verdict(name, m):
    """A short, plain verdict for the table, built from the metric's evidence."""
    ev = m.get("evidence", {})
    if ev.get("skipped"):
        if "infinite" in ev["skipped"]:
            return "Not run: the program never finished"
        if "compile" in ev["skipped"]:
            return "Not run: the program does not compile"
        return "Not run"
    if name in ("correctness", "logical") and "total" in ev:
        kind = "tests" if name == "correctness" else "tricky inputs"
        return f"{ev['passed']} of {ev['total']} {kind} right"
    if name == "syntax":
        if ev.get("errors"):
            return "Does not compile"
        count = len(ev.get("warnings", []))
        return f"{count} compiler warning(s)" if count else "Compiles cleanly"
    if name == "structure":
        count = len(ev.get("problems", []))
        return f"{count} style problem(s)" if count else "Short, simple functions"
    if name == "modularity":
        helpers = ev.get("helpers_used", [])
        return f"Uses {len(helpers)} helper function(s)" if helpers else "Everything is in main()"
    if name == "complexity" and "estimated" in ev:
        return f"Runs in {ev['estimated']} (needs {ev['required']})"
    if name == "complexity" and "failed_at" in ev:
        what = "Timed out" if ev.get("status") == "timeout" else "Crashed"
        return f"{what} on a large input (n = {ev['failed_at']:,})"
    if name == "memory_safety":
        count = len(ev.get("problems", []))
        return f"{count} memory problem(s)" if count else "No memory problems"
    if name == "readability":
        return f"LLM rates it {m.get('score', 0) * 10:.0f}/10"
    if name == "originality" and "max_similarity" in ev:
        text = f"{ev['max_similarity']:.0%} similar to closest file"
        return text + " (flagged)" if m.get("flag") else text
    return m.get("feedback", "")


# Label and colour of the badge for each way a run can go wrong.
RUN_BADGES = {"crash": ("Crashed", "bad"), "timeout": ("Timed out", "warn"),
              "error_exit": ("Error exit", "warn"), "output_limit": ("Too much output", "warn")}


def status_badges(report):
    """Compiled / Does not compile, plus one badge per kind of failed run.

    The smoke run alone is not enough: a program can pass the sample input and
    crash on a later test, so every run in report["run_problems"] counts.
    """
    first_pass = report["first_pass"]
    if first_pass.get("compiled"):
        badges = ['<span class="badge ok">Compiled</span>']
    else:
        badges = ['<span class="badge bad">Does not compile</span>']
    if first_pass.get("suspected_infinite_loop"):
        badges.append('<span class="badge bad">Never finished</span>')
    problems = report.get("run_problems")
    if problems is None:  # older report written before run_problems existed
        problems = run_problems(first_pass, report["metrics"])
    for status, (label, colour) in RUN_BADGES.items():
        runs = [p for p in problems if p["status"] == status]
        if status == "timeout" and first_pass.get("suspected_infinite_loop"):
            continue  # already shown as "Never finished"
        if runs:
            badges.append(f'<span class="badge {colour}" title="{esc(run_problems_text(runs))}">'
                          f'{label}</span>')
    return "".join(badges)


def failure_card(failure, title):
    """One failing input as an alert box: input, expected, got and the reason."""
    reason = failure.get("reason", "")
    reason_html = f"<div><b>Why:</b> {esc(reason)}</div>" if reason else ""
    status = failure.get("status", "?")
    status_html = "" if status == "ok" else f' <span class="badge warn">{esc(status)}</span>'
    return f"""
    <div class="box fail">
      <b>{esc(title)}</b>{status_html}
      <div>Input:</div><pre>{esc(failure.get('input', ''))}</pre>
      <div>Expected:</div><pre>{esc(failure.get('expected', ''))}</pre>
      <div>Got:</div><pre>{esc(failure.get('got', '') or '(no output)')}</pre>
      {reason_html}
    </div>"""


# ---------- Page sections ----------

def choose_file(label, files, upload_type, upload_folder, preferred=None, key=""):
    """A "From folder / Upload" choice. Returns a file path, or None if nothing is chosen yet."""
    source = st.sidebar.radio(label, ["From folder", "Upload"], horizontal=True, key=key + "_src")
    if source == "Upload":
        uploaded = st.sidebar.file_uploader(f"Upload a .{upload_type} file", type=[upload_type],
                                            key=key + "_upload")
        return save_upload(uploaded, upload_folder) if uploaded else None
    if not files:
        st.sidebar.info("No files found in the folder; upload one instead.")
        return None
    index = files.index(preferred) if preferred in files else 0
    # The key includes the suggestion, so a new problem resets the pick to its own files.
    return st.sidebar.selectbox(f"{label} file", files, index=index,
                                key=f"{key}_pick_{preferred}")


def sidebar():
    """Controls. Returns (rules_path, submission_path, grade_clicked)."""
    st.sidebar.markdown("## AutoGrader")

    rules_path = choose_file("Rules", rules_files(), "json", UPLOAD_RULES, key="rules")

    # Suggest a submission for the chosen problem: rules/add.json goes with submissions/add/.
    problem = os.path.splitext(os.path.basename(rules_path))[0] if rules_path else ""
    files = submission_files()
    preferred = next((f for f in files if f.split(os.sep)[1] == problem), None)
    submission_path = choose_file("Submission", files, "c", UPLOAD_SUBMISSIONS,
                                  preferred=preferred, key="submission")

    ready = rules_path is not None and submission_path is not None
    # Grading is still allowed (a teacher may do it on purpose), but every test would
    # be for the wrong problem, so say so loudly next to the button.
    warning = mismatch_message(rules_path, submission_path) if ready else None
    if warning:
        st.sidebar.error(warning, icon="⚠️")
    clicked = st.sidebar.button("Grade Submission", type="primary", disabled=not ready,
                                use_container_width=True)

    st.sidebar.markdown("#### Grade Key")
    rows = "".join(f"<tr><td>{letter}</td><td>{text}</td></tr>" for letter, _, text in GRADE_KEY)
    st.sidebar.markdown(f"<table class='key'>{rows}</table>", unsafe_allow_html=True)
    return rules_path, submission_path, clicked


def header_banner(report, problem):
    grade = report["grade"]
    st.markdown(f"""
    <div class="banner">
      <div>
        <div class="title">AutoGrader</div>
        <div class="subtitle">REPORT CARD</div>
        <div class="meta">File: <b>{esc(os.path.basename(report['submission']))}</b>
          &nbsp;|&nbsp; Problem: <b>{esc(problem)}</b></div>
        <div style="margin-top:10px">{status_badges(report)}</div>
      </div>
      <div class="summary">
        <div class="num">{grade:.1f}/100</div>
        <div class="letter">Grade {letter_grade(grade)}</div>
      </div>
    </div>""", unsafe_allow_html=True)

    for flag in report["flags"]:
        st.markdown(f"<div class='box flag'><b>Possible copying:</b> {esc(flag)}</div>",
                    unsafe_allow_html=True)


def metrics_table(report):
    """grade = 100 x sum(weight x score), so each row's points are 100 x weight x score."""
    rows, total = [], 0.0
    for name, m in ordered_metrics(report):
        weight, score = m.get("weight", 0), m.get("score", 0)
        points = 100 * weight * score
        total += points
        rows.append(f"<tr><td>{esc(nice_name(name))}</td><td class='num'>{weight * 100:.0f}%</td>"
                    f"<td class='num'>{score:.2f}</td>"
                    f"<td class='num'>{points:.1f} / {weight * 100:.0f}</td>"
                    f"<td>{esc(verdict(name, m))}</td></tr>")
    rows.append(f"<tr class='total'><td>Total</td><td></td><td></td>"
                f"<td class='num'>{total:.1f} / 100</td><td></td></tr>")
    st.markdown("### Scores")
    st.markdown("<table class='metrics'><tr><th>Metric</th><th class='num'>Weight</th>"
                "<th class='num'>Score</th><th class='num'>Points</th><th>Verdict</th></tr>"
                + "".join(rows) + "</table>",
                unsafe_allow_html=True)


def tab_failures(report):
    fp = report["first_pass"]
    if not fp.get("compiled") and fp.get("compiler_output"):
        st.error("The program does not compile, so no tests could run.")
        st.code(fp["compiler_output"], language="text")
    elif fp.get("suspected_infinite_loop"):
        st.error("The program never finished on the sample input, so no tests could run.")

    shown = False
    for name, m in ordered_metrics(report):
        for f in m.get("evidence", {}).get("failures", []):
            label = f"Test {f['test']}" if "test" in f else f"Tricky input: {f.get('case', '?')}"
            st.markdown(failure_card(f, f"{nice_name(name)} | {label}"), unsafe_allow_html=True)
            shown = True

    # Problems the sanitizers saw while the program ran, e.g. integer overflow.
    problems = report["metrics"].get("memory_safety", {}).get("evidence", {}).get("problems", [])
    for p in problems:
        st.warning(f"**{p.get('kind', 'problem').capitalize()}** at {p.get('where')}: "
                   f"{p.get('message')}  \nInput: `{p.get('input', '')!r}`")
        shown = True
    if not shown and fp.get("can_run", True):
        st.markdown("<div class='box'><span class='badge ok'>All passed</span> "
                    "Every test and tricky input gave the right answer.</div>", unsafe_allow_html=True)


def tab_code(path, code):
    """The code as it was when graded (an upload may be replaced later under the same name)."""
    if code is None:
        st.info(f"File not found: {path}")
    else:
        st.caption(path)
        st.code(code, language="c", line_numbers=True)


# ---------- Grading ----------

def grade(rules_path, submission_path):
    """Run the real grader. Returns the evaluation dict, or None after showing an error."""
    try:
        rules = load_rules(rules_path)
    except Exception as error:  # bad JSON, missing keys, weights not adding up to 1, ...
        st.error(f"The rules file {rules_path} cannot be used: {error}")
        return None

    try:
        with st.spinner(SPINNER_TEXT):
            report = grade_submission(submission_path, rules, tool_versions())
    except SystemExit as error:
        # llm_review stops the command-line run this way when there is no GROQ_API_KEY
        # (and no cached answer) or when Groq cannot be reached.
        st.error(f"Grading stopped during the LLM review: {error}")
        return None
    except Exception as error:  # e.g. the rules point to a sample_input that does not exist
        st.error(f"Grading failed: {error!r}")
        return None

    json_path, _ = save_report(report, os.path.join("reports", rules["name"]))
    return {"report": report, "problem": rules["name"], "report_path": json_path,
            "code": read_text(submission_path)}


def load_saved_report(path):
    """A report saved earlier by autograder.py, in the same form grade() returns."""
    try:
        with open(path) as f:
            report = json.load(f)
    except (OSError, ValueError):
        return None
    problem = os.path.basename(os.path.dirname(path))
    return {"report": report, "problem": problem, "report_path": path,
            "code": read_text(report.get("submission")), "saved": True}


def analyzer_warnings(report):
    """One warning per analyzer that crashed; run_metric scored those metrics 0."""
    for name, m in ordered_metrics(report):
        error = m.get("evidence", {}).get("error")
        if error:
            st.warning(f"The **{nice_name(name)}** analyzer failed, so it scored 0: {error}")


# ---------- Main ----------

def main():
    st.set_page_config(page_title="AutoGrader Report Card", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)

    rules_path, submission_path, clicked = sidebar()
    if clicked:
        result = grade(rules_path, submission_path)
        if result is not None:
            st.session_state["evaluation_result"] = result

    if "evaluation_result" not in st.session_state:
        st.session_state["evaluation_result"] = load_saved_report(DEFAULT_REPORT)

    result = st.session_state["evaluation_result"]
    if result is None:
        st.info("Choose a rules file and a C submission in the sidebar, "
                "then press **Grade Submission**.")
        return

    report = result["report"]
    header_banner(report, result["problem"])
    analyzer_warnings(report)
    metrics_table(report)

    failures_tab, code_tab = st.tabs(["Failures", "Code"])
    with failures_tab:
        tab_failures(report)
    with code_tab:
        tab_code(report["submission"], result["code"])
    where = ("Saved sample report, graded earlier: " if result.get("saved")
             else "Graded just now, saved to ")
    st.caption(f"{where}{result['report_path']}  |  "
               f"Rules SHA-256: {report.get('rules_sha256', 'n/a')[:16]}...")


if __name__ == "__main__":
    main()

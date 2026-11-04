# AutoGrader

A Rule-Driven Evaluator for C Programs using open weight LLM-Models and modularized for expert analyzers on different aspects of evaluation metrics for independent and consistent evaluation.

Working system configuration:
```bash
                             ....              system@SYSTEM
              .',:clooo:  .:looooo:.           ------------
           .;looooooooc  .oooooooooo'          OS: Ubuntu 26.04.1 LTS (Resolute Raccoon) x86_64
        .;looooool:,''.  :ooooooooooc          Host: Windows Subsystem for Linux - Ubuntu (2.7.13.0)
       ;looool;.         'oooooooooo,          Kernel: Linux 6.18.33.2-microsoft-standard-WSL2
      ;clool'             .cooooooc.  ,,       Uptime: 5 mins
         ...                ......  .:oo,      Packages: 764 (dpkg)
  .;clol:,.                        .loooo'     Shell: bash 5.3.9
 :ooooooooo,                        'ooool     Display (rdp-0): 1920x1080, 60 Hz
'ooooooooooo.                        loooo.    WM: WSLg 1.0.73.2 (Wayland)
'ooooooooool                         coooo.    Theme: Yaru [GTK3]
 ,loooooooc.                        .loooo.    Icons: Yaru [GTK3]
   .,;;;'.                          ;ooooc     Terminal: Windows Terminal
       ...                         ,ooool.     CPU: AMD Ryzen 5 7235HS (8) @ 3.19 GHz
    .cooooc.              ..',,'.  .cooo.      GPU: NVIDIA GeForce RTX 3050 6GB Laptop GPU (5.86 GiB) [Discrete]
      ;ooooo:.           ;oooooooc.  :l.       Memory: 557.91 MiB / 5.63 GiB (10%)
       .coooooc,..      coooooooooo.           Swap: 0 B / 2.00 GiB (0%)
         .:ooooooolc:. .ooooooooooo'           Disk (/): 3.15 GiB / 1006.85 GiB (0%) - ext4
           .':loooooo;  ,oooooooooc            Disk (/mnt/c): 208.17 GiB / 440.00 GiB (47%) - 9p
               ..';::c'  .;loooo:'             Disk (/mnt/d): 3.48 GiB / 34.71 GiB (10%) - 9p
```

AutoGrader grades student C programs using a rules file written by the instructor.
It compiles and runs each submission safely (with time and memory limits), checks it
with one analyzer per metric, and combines the results into a grade:

    grade = 100 x sum(weight x score)

Each analyzer gives a score from 0 to 1, the evidence behind it and a one-line feedback.
For wrong programs the report shows a failing input with the expected output, what the
program printed and why. Suspected copies (from other students, websites or LLMs) are
flagged for the teacher but never lower the grade. The same submission and the same
rules always give the same grade.

The metrics, weights, limits and parameters all live in a rules file, not in the code,
along with an advice line per metric and the usefulness and limitations examples shown
at the end of each report.
Two problems are included, to show the same grader works for more than one task:

- `rules/add.json`: add two integers (the problem from the brief)
- `rules/search.json`: linear search. Input is n, then n integers, then a target;
  the program prints the 0-based index of the first match, or -1

| Metric | Analyzer | What it checks |
|---|---|---|
| correctness | `io_tests` | output on the tests in `tests/<problem>/` |
| syntax | `compiler_warnings` | errors and warnings with the rules' gcc flags |
| structure | `static_analysis` | function size and branching (lizard) and cppcheck findings |
| modularity | `function_split` | whether the work is split into helper functions |
| logical | `edge_case_runner` | tricky inputs compared with a reference solution (built-in generators for add, a folder of inputs for search) |
| complexity | `complexity_estimator` | how the run time grows with the input |
| memory_safety | `sanitizer_run` | AddressSanitizer and UndefinedBehaviorSanitizer reports |
| readability | `llm_review` | an LLM on Groq (temperature 0, fixed seed, cached answers) |
| originality | `similarity_flag` | similarity with other submissions, LLM answers and websites |

## Install (Ubuntu on WSL)

1. Install WSL with Ubuntu from a Windows terminal (skip this on a Linux machine):

       wsl --install -d Ubuntu

2. In Ubuntu, install the C tools and Python:

       sudo apt update
       sudo apt install gcc cppcheck python3 python3-venv python3-pip git

   gcc on Ubuntu already includes the address and undefined behaviour sanitizers.

   **Tool versions.** The sample outputs were made with gcc 15.2 and cppcheck 2.19
   (each report lists the exact versions under `tool_versions`). Other versions can
   give different grades: `search_crash.c` gets 77.8 with cppcheck 2.19 but 81.8 with
   cppcheck 2.13, because 2.13 does not report two of the warnings. Use the same
   versions to reproduce the grades in `sample_outputs/`.

3. Get the code and install the Python packages (lizard, and streamlit for the grading portal) in a virtual environment:

       git clone https://github.com/wnubhav/Autograder_Project.git
       cd Autograder_Project
       python3 -m venv .venv
       source .venv/bin/activate
       pip install -r requirements.txt

4. Set your Groq API key (free at https://console.groq.com). The readability metric needs it:

       export GROQ_API_KEY="your-key-here"

   Add that line to `~/.bashrc` to keep it for new terminals. Never put the key in a file
   in the repository. The answers for the sample submissions are already cached in
   `cache/llm/`, so the samples can be graded without a key. A new or changed submission
   needs the key and an internet connection.

## Run

    python3 autograder.py rules/add.json submissions/add/*.c
    python3 autograder.py rules/search.json submissions/search/*.c

You can also grade one file: `python3 autograder.py rules/add.json submissions/add/add.c`.
Each problem has its own folders, named after the rules file (`add`, `search`).
A short summary is printed for each submission, and two files are written:

- `reports/<rules name>/<name>.json`: every score and its evidence, the rules file's SHA-256 hash and the tool versions
- `reports/<rules name>/<name>.txt`: the report for the student (score table, where you failed,
  suggestions to raise the grade, usefulness and limitations)

## Running the Streamlit UI

The portal grades a submission in the browser and shows the report card: the grade, the
score table, the failing inputs (input, expected, got, why) and the student's code.

    pip install -r requirements.txt
    streamlit run streamlit_app.py

Then open http://localhost:8501. In the sidebar, pick a rules file from `rules/` or upload
one, pick a C file from `submissions/` or upload one, and press **Grade Submission**.
Grading runs the same code as `autograder.py`, so the grade is the same, and the report is
saved to `reports/<rules name>/` too. Uploaded files are saved to `temp_submissions/` and
`temp_rules/`. A new or changed submission needs `GROQ_API_KEY` for the readability score;
without it the portal shows an error instead of a grade.
Streamlit also listens on your network address by default; add
`--server.address localhost` to keep it on your own machine.

## Folders

| Path | Contents |
|---|---|
| `autograder.py` | coordinator and entry point: runs the first pass and every metric, computes the grade |
| `sandbox.py` | runs a program with CPU time, memory and output limits, and survives crashes and infinite loops |
| `first_pass.py` | quick checks: main/scanf/printf/return, plain compile, smoke run on the sample input |
| `rules.py` | loads and checks the rules file |
| `report_text.py` | writes the student report in `reports/<rules name>/<name>.txt` |
| `streamlit_app.py` | the grading portal (see "Running the Streamlit UI"); `.streamlit/config.toml` holds its colours and font |
| `analyzers/` | one file per analyzer; `__init__.py` maps analyzer names from the rules to functions |
| `rules/` | the rules files (`add.json`, `search.json`) |
| `tests/add/`, `tests/search/` | test inputs (`NN.in`) and expected outputs (`NN.out`); `tests/search/edge/` holds the search edge-case inputs |
| `reference/` | the correct solutions that the edge-case analyzer compares against |
| `submissions/add/` | sample add programs: correct, wrong, crashing, infinite loop, not compiling, leaking, slow, messy, copied |
| `submissions/add/corpus/` | LLM answers (`ai/`) and website solutions (`web/`) for add, used only for the originality check, never graded |
| `submissions/search/` | sample search programs: correct, off by one, crashing on n = 0, sorting first |
| `cache/llm/` | saved LLM readability answers, so reruns give the same score |
| `sample_outputs/add/`, `sample_outputs/search/` | the final `.json` and `.txt` reports for all sample submissions |
| `reports/<rules name>/` | reports from your latest run (not committed) |
| `build/<rules name>/` | compiled programs (not committed) |
| `explanations/` | plain-language walkthroughs: every file, the Groq readability check, and the whole system |
| `USEFULNESS_AND_LIMITATIONS.md` | four concrete cases where the agent helps and four where its verdict is wrong or unreliable |

## Sample outputs

`sample_outputs/` holds the reports for every sample program, one folder per problem.

Add two integers (`rules/add.json`, reports in `sample_outputs/add/`):

| Submission | Grade | Note |
|---|---|---|
| add.c | 81.0 | fails on overflow (tests 07, 08); flagged: same as an LLM answer |
| add_copy.c | 97.0 | add_good.c with names changed; flagged |
| add_crash.c | 43.5 | null pointer write, crashes on every input |
| add_good.c | 99.0 | correct and clean; flagged with add_copy.c |
| add_infinite.c | 40.0 | infinite loop; only source-based metrics run |
| add_leak.c | 86.5 | correct, but never frees its memory |
| add_loop.c | 73.5 | adds by counting, so it is O(n); flagged against an LLM answer |
| add_messy.c | 77.5 | correct, but one long branchy main and a warning |
| add_syntax_error.c | 26.0 | does not compile |

Linear search (`rules/search.json`, reports in `sample_outputs/search/`):

| Submission | Grade | Note |
|---|---|---|
| search_good.c | 99.0 | correct and clean (same as `reference/search.c`) |
| search_off_by_one.c | 80.0 | loop stops at `n - 1`, so a match in the last position is missed |
| search_crash.c | 77.8 | recursive search reads `arr[0]` before checking n, crashes on n = 0 |
| search_sort.c | 87.0 | correct, but bubble sorts first (O(n^2)), times out on large inputs |

The run times in the `complexity` feedback of `add_loop` change a little between runs;
the grades, scores and flags do not.

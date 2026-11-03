"""Analyzer registry.

The rules JSON names an analyzer for each metric (for example "io_tests").
REGISTRY maps that name to the Python function that does the work.
Every analyzer function is called as
    analyze(source_path, first_pass, params, rules)
and returns:
    {"score": 0..1, "evidence": {...}, "feedback": "one line"}
We fill this in as we write each analyzer.
"""

from analyzers.compiler_warnings import analyze as compiler_warnings
from analyzers.complexity_estimator import analyze as complexity_estimator
from analyzers.edge_case_runner import analyze as edge_case_runner
from analyzers.function_split import analyze as function_split
from analyzers.io_tests import analyze as io_tests
from analyzers.llm_review import analyze as llm_review
from analyzers.sanitizer_run import analyze as sanitizer_run
from analyzers.similarity_flag import analyze as similarity_flag
from analyzers.static_analysis import analyze as static_analysis

REGISTRY = {
    "io_tests": io_tests,
    "compiler_warnings": compiler_warnings,
    "static_analysis": static_analysis,
    "function_split": function_split,
    "sanitizer_run": sanitizer_run,
    "edge_case_runner": edge_case_runner,
    "complexity_estimator": complexity_estimator,
    "llm_review": llm_review,
    "similarity_flag": similarity_flag,
}

# Analyzers that have to run the compiled program. The coordinator skips them
# (score 0) when the first pass says can_run is False: the code did not
# compile, or the smoke run timed out.
NEEDS_BINARY = {"io_tests", "edge_case_runner", "complexity_estimator", "sanitizer_run"}

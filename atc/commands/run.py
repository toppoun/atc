from typing import List, Sequence

from atc.argparse_utils import AtcArgumentParser
from atc.commands.parsing import parse_handler_args
from atc.commands.usage_error import USAGE_ERROR
from atc.core.runner import run_all_problem_tests, run_problem_tests, write_test_log
from atc.ui.console import error, print_all_summary, print_detailed_result


CPP_DEBUG_EXTRA_FLAGS = (
    "-DLOCAL",
    "-D_GLIBCXX_DEBUG",
)

# --- Run hundlers ---
def handle_run(args: List[str]):
    parser = AtcArgumentParser(prog="atc run")
    parser.add_argument("problem")
    parser.add_argument("lang", nargs="?")
    parser.add_argument("-d", "--debug", action="store_true")
    parsed = parse_handler_args(parser, args)
    if parsed is None:
        return USAGE_ERROR

    if parsed.debug and parsed.lang and parsed.lang.lower() != "cpp":
        error("--debug is only available for C++.")
        return 1

    run_language = "cpp" if parsed.debug else parsed.lang
    cpp_extra_flags = CPP_DEBUG_EXTRA_FLAGS if parsed.debug else ()
    
    if parsed.problem.lower() == "all":
        return _run_all_problems(run_language, cpp_extra_flags=cpp_extra_flags)
    
    return _run_single_problem(
        parsed.problem,
        run_language,
        cpp_extra_flags=cpp_extra_flags,
    )
    

# --- run single problem ---
def _run_single_problem(
    problem: str,
    lang: str,
    *,
    cpp_extra_flags: Sequence[str] = (),
):
    result = run_problem_tests(
        problem,
        lang,
        show_compile=True,
        cpp_extra_flags=cpp_extra_flags,
    )
    print_detailed_result(result)
    write_test_log([result])
    return 0 if result.passed else 1


# --- run all problem ---
def _run_all_problems(
    lang: str,
    *,
    cpp_extra_flags: Sequence[str] = (),
):
    results = run_all_problem_tests(lang, cpp_extra_flags=cpp_extra_flags)
    print_all_summary(results)
    write_test_log(results)
    return 0 if bool(results) and all(result.passed for result in results) else 1

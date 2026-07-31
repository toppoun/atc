from typing import List, Optional

from atc.argparse_utils import AtcArgumentParser
from atc.commands.parsing import parse_handler_args
from atc.commands.usage_error import USAGE_ERROR
from atc.core.runner import run_all_problem_tests, run_problem_tests, write_test_log
from atc.ui.console import error, print_all_summary, print_detailed_result

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

    if parsed.problem.lower() == "all":
        return _run_all_problems(run_language, debug=parsed.debug)

    return _run_single_problem(
        parsed.problem,
        run_language,
        debug=parsed.debug,
    )


# --- run single problem ---
def _run_single_problem(
    problem: str,
    lang: Optional[str],
    *,
    debug: bool = False,
):
    result = run_problem_tests(
        problem,
        lang,
        show_compile=True,
        debug=debug,
    )
    print_detailed_result(
        result,
        show_debug_output=debug,
    )
    write_test_log([result])
    return 0 if result.passed else 1


# --- run all problem ---
def _run_all_problems(
    lang: Optional[str],
    *,
    debug: bool = False,
):
    results = run_all_problem_tests(lang, debug=debug)
    print_all_summary(
        results,
        show_debug_output=debug,
    )
    write_test_log(results)
    return 0 if bool(results) and all(result.passed for result in results) else 1

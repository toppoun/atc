from typing import List

from atc.argparse_utils import AtcArgumentParser
from atc.commands.parsing import parse_handler_args
from atc.commands.usage_error import USAGE_ERROR
from atc.core.runner import run_all_problem_tests, run_problem_tests, write_test_log
from atc.ui.console import print_all_summary, print_detailed_result

# --- Run hundlers ---
def handle_run(args: List[str]):
    parser = AtcArgumentParser(prog="atc run")
    parser.add_argument("problem")
    parser.add_argument("lang", nargs="?")
    parsed = parse_handler_args(parser, args)
    if parsed is None:
        return USAGE_ERROR
    
    if parsed.problem.lower() == "all":
        return _run_all_problems(parsed.lang)
    
    return _run_single_problem(parsed.problem, parsed.lang)
    

# --- run single problem ---
def _run_single_problem(problem: str, lang: str):
    result = run_problem_tests(problem, lang, show_compile=True)
    print_detailed_result(result)
    write_test_log([result])
    return 0 if result.passed else 1


# --- run all problem ---
def _run_all_problems(lang: str):
    results = run_all_problem_tests(lang)
    print_all_summary(results)
    write_test_log(results)
    return 0 if bool(results) and all(result.passed for result in results) else 1
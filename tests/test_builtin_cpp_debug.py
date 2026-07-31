import re
import shutil
import subprocess
from pathlib import Path

import pytest

from atc.core.cpp import BUILTIN_CPP_INCLUDE_DIR


CPP_SOURCE = r'''
#include <array>
#include <deque>
#include <iostream>
#include <list>
#include <map>
#include <queue>
#include <set>
#include <stack>
#include <string>
#include <string_view>
#include <tuple>
#include <utility>
#include <vector>

#include <atc/debug.hpp>

struct Streamable {
    int value;
};

std::ostream& operator<<(std::ostream& output, const Streamable& value) {
    return output << "Streamable(" << value.value << ")";
}

struct Unprintable {
    int value;
};

int main() {
    int integer = 42;
    long long large = 1234567890123LL;
    double decimal = 3.5;
    bool flag = true;
    char character = 'a';
    std::string text = "abc";
    const char* c_string = "xyz";
    std::string_view view = "view";
    std::vector<int> values = {1, 2, 3};
    std::vector<std::vector<int>> matrix = {{1, 2}, {3, 4}};
    std::array<int, 3> fixed = {4, 5, 6};
    int raw[] = {7, 8, 9};
    std::pair<int, std::string> paired = {1, "one"};
    std::tuple<int, std::string, bool> tupled = {2, "two", false};
    std::deque<int> deque_values = {1, 2, 3};
    std::list<int> list_values = {4, 5, 6};
    std::set<int> ordered = {3, 1, 2};
    std::multiset<int> repeated = {2, 1, 2};
    std::map<std::string, int> mapped = {{"a", 1}, {"b", 2}};
    std::queue<int> queued;
    queued.push(1);
    queued.push(2);
    std::stack<int> stacked;
    stacked.push(1);
    stacked.push(2);
    std::priority_queue<int> prioritized;
    prioritized.push(1);
    prioritized.push(3);
    prioritized.push(2);
    std::vector<std::pair<int, std::vector<int>>> nested = {{1, {2, 3}}};
    std::tuple<std::pair<int, std::string>, std::vector<int>> mixed = {
        {5, "five"},
        {6, 7}
    };
    Streamable streamable{10};
    Unprintable unprintable{11};
    std::vector<int> empty_values;
    std::tuple<> empty_tuple;
    std::vector<bool> bits = {true, false, true};

    debug(integer);
    debug(large);
    debug(decimal);
    debug(flag);
    debug(character);
    debug(text);
    debug("literal");
    debug(c_string);
    debug(view);
    debug(values);
    debug(matrix);
    debug(fixed);
    debug(raw);
    debug(paired);
    debug(tupled);
    debug(deque_values);
    debug(list_values);
    debug(ordered);
    debug(repeated);
    debug(mapped);
    debug(queued);
    debug(stacked);
    debug(prioritized);
    debug(nested);
    debug(mixed);
    debug(streamable);
    debug(unprintable);
    debug(empty_values);
    debug(empty_tuple);
    debug(bits);
    debug(integer, text, values);
    debug();

    if (queued.front() != 1 || stacked.top() != 2 || prioritized.top() != 3) {
        return 2;
    }
}
'''


EXPECTED_STDERR = """\
[L] integer = 42
[L] large = 1234567890123
[L] decimal = 3.5
[L] flag = true
[L] character = 'a'
[L] text = "abc"
[L] "literal" = "literal"
[L] c_string = "xyz"
[L] view = "view"
[L] values = {1, 2, 3}
[L] matrix = {{1, 2}, {3, 4}}
[L] fixed = {4, 5, 6}
[L] raw = {7, 8, 9}
[L] paired = (1, "one")
[L] tupled = (2, "two", false)
[L] deque_values = {1, 2, 3}
[L] list_values = {4, 5, 6}
[L] ordered = {1, 2, 3}
[L] repeated = {1, 2, 2}
[L] mapped = {("a", 1), ("b", 2)}
[L] queued = {1, 2}
[L] stacked = {2, 1}
[L] prioritized = {3, 2, 1}
[L] nested = {(1, {2, 3})}
[L] mixed = ((5, "five"), {6, 7})
[L] streamable = Streamable(10)
[L] unprintable = <unprintable>
[L] empty_values = {}
[L] empty_tuple = ()
[L] bits = {1, 0, 1}
[L] integer, text, values = 42, "abc", {1, 2, 3}
[L]
"""


def _cpp_compiler():
    return shutil.which("g++") or shutil.which("clang++")


def test_builtin_debug_header_compiles_and_formats_supported_types(tmp_path):
    compiler = _cpp_compiler()
    if compiler is None:
        pytest.skip("C++20 compiler not found (g++ or clang++)")

    source = tmp_path / "test.cpp"
    executable = tmp_path / ("test.exe" if Path(compiler).name.lower().startswith("g++") and Path(compiler).suffix else "test.out")
    source.write_text(CPP_SOURCE, encoding="utf-8")

    compile_result = subprocess.run(
        [
            compiler,
            "-std=c++20",
            "-I",
            str(BUILTIN_CPP_INCLUDE_DIR),
            str(source),
            "-o",
            str(executable),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    assert compile_result.returncode == 0, compile_result.stderr

    run_result = subprocess.run(
        [str(executable)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    normalized_stderr = re.sub(r"\[L\d+\]", "[L]", run_result.stderr)
    assert run_result.returncode == 0, run_result.stderr
    assert run_result.stdout == ""
    assert normalized_stderr == EXPECTED_STDERR

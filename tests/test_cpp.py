from pathlib import Path

import pytest

import atc.core.cpp as cpp_module
from atc.core.config import ConfigError, default_config
from atc.core.cpp import build_cpp_compile_flags


def _cpp_config(cwd: Path, library: str = ""):
    config = default_config()
    config["paths"]["root"] = str(cwd)
    config["paths"]["cpp_library"] = library
    return config


def test_build_cpp_compile_flags_without_library_has_no_include_flag(tmp_path):
    config = _cpp_config(tmp_path)

    flags = build_cpp_compile_flags(config, tmp_path)

    assert flags == config["runner"]["cpp_flags"]
    assert "-I" not in flags
    assert cpp_module.BUILTIN_CPP_DEBUG_DEFINE not in flags


def test_build_cpp_compile_flags_adds_builtin_include_for_debug_without_user_library(tmp_path):
    config = _cpp_config(tmp_path)

    flags = build_cpp_compile_flags(config, tmp_path, debug=True)

    assert flags == [
        *config["runner"]["cpp_flags"],
        "-I",
        str(cpp_module.BUILTIN_CPP_INCLUDE_DIR),
        cpp_module.BUILTIN_CPP_DEBUG_DEFINE,
        *config["runner"]["cpp_debug_flags"],
    ]


def test_build_cpp_compile_flags_adds_resolved_library_path(tmp_path):
    library = tmp_path / "cpplib"
    library.mkdir()
    config = _cpp_config(tmp_path, "cpplib")

    flags = build_cpp_compile_flags(config, tmp_path)

    assert flags[-2:] == ["-I", str(library.resolve())]


def test_build_cpp_compile_flags_normal_order(tmp_path):
    library = tmp_path / "cpplib"
    library.mkdir()
    config = _cpp_config(tmp_path, "cpplib")
    config["runner"]["cpp_flags"] = ["-std=c++23", "-O0"]

    flags = build_cpp_compile_flags(
        config,
        tmp_path,
        extra_flags=("-Werror",),
    )

    assert flags == [
        "-std=c++23",
        "-O0",
        "-I",
        str(library.resolve()),
        "-Werror",
    ]


def test_build_cpp_compile_flags_debug_order(tmp_path):
    library = tmp_path / "cpplib"
    library.mkdir()
    config = _cpp_config(tmp_path, "cpplib")
    config["runner"]["cpp_flags"] = ["-std=c++23"]

    flags = build_cpp_compile_flags(
        config,
        tmp_path,
        debug=True,
        extra_flags=("-fsanitize=address",),
    )

    assert flags == [
        "-std=c++23",
        "-I",
        str(library.resolve()),
        "-I",
        str(cpp_module.BUILTIN_CPP_INCLUDE_DIR),
        cpp_module.BUILTIN_CPP_DEBUG_DEFINE,
        "-D_GLIBCXX_DEBUG",
        "-fsanitize=address",
    ]


def test_build_cpp_compile_flags_appends_user_debug_flags_after_builtin_define(tmp_path):
    config = _cpp_config(tmp_path)
    config["runner"]["cpp_debug_flags"] = ["-DPROJECT_DEBUG", "-fsanitize=undefined"]

    flags = build_cpp_compile_flags(config, tmp_path, debug=True)

    builtin_index = flags.index(cpp_module.BUILTIN_CPP_DEBUG_DEFINE)
    assert flags[builtin_index + 1:] == [
        "-DPROJECT_DEBUG",
        "-fsanitize=undefined",
    ]


def test_build_cpp_compile_flags_accepts_empty_debug_flags(tmp_path):
    library = tmp_path / "cpplib"
    library.mkdir()
    config = _cpp_config(tmp_path, "cpplib")
    config["runner"]["cpp_flags"] = ["-std=c++20"]
    config["runner"]["cpp_debug_flags"] = []

    flags = build_cpp_compile_flags(config, tmp_path, debug=True)

    assert flags == [
        "-std=c++20",
        "-I",
        str(library.resolve()),
        "-I",
        str(cpp_module.BUILTIN_CPP_INCLUDE_DIR),
        cpp_module.BUILTIN_CPP_DEBUG_DEFINE,
    ]
    assert "-D_GLIBCXX_DEBUG" not in flags


def test_build_cpp_compile_flags_keeps_spaced_path_as_one_argument(tmp_path):
    library = tmp_path / "My Libraries" / "cpplib"
    library.mkdir(parents=True)
    config = _cpp_config(tmp_path, "My Libraries/cpplib")

    flags = build_cpp_compile_flags(config, tmp_path)

    include_index = flags.index("-I")
    assert flags[include_index + 1] == str(library.resolve())
    assert flags[include_index + 2:] == []


def test_build_cpp_compile_flags_rejects_missing_library(tmp_path):
    config = _cpp_config(tmp_path, "missing")

    with pytest.raises(
        ConfigError,
        match=r"^C\+\+ library directory not found:",
    ):
        build_cpp_compile_flags(config, tmp_path)


def test_build_cpp_compile_flags_rejects_file_library(tmp_path):
    library = tmp_path / "cpplib"
    library.write_text("not a directory\n", encoding="utf-8")
    config = _cpp_config(tmp_path, "cpplib")

    with pytest.raises(
        ConfigError,
        match=r"^C\+\+ library path is not a directory:",
    ):
        build_cpp_compile_flags(config, tmp_path)


def test_build_cpp_compile_flags_rejects_missing_builtin_debug_header(tmp_path, monkeypatch):
    missing_header = tmp_path / "include" / "atc" / "debug.hpp"
    monkeypatch.setattr(
        cpp_module,
        "BUILTIN_CPP_INCLUDE_DIR",
        tmp_path / "include",
    )
    monkeypatch.setattr(
        cpp_module,
        "BUILTIN_CPP_DEBUG_HEADER",
        missing_header,
    )
    config = _cpp_config(tmp_path)

    with pytest.raises(
        ConfigError,
        match=r"^Built-in C\+\+ debug header not found: .* Reinstall atc\.$",
    ):
        build_cpp_compile_flags(config, tmp_path, debug=True)


def test_build_cpp_compile_flags_does_not_mutate_config_lists(tmp_path):
    library = tmp_path / "cpplib"
    library.mkdir()
    config = _cpp_config(tmp_path, "cpplib")
    base_flags = ["-std=c++20", "-O2"]
    debug_flags = ["-DPROJECT_DEBUG"]
    config["runner"]["cpp_flags"] = base_flags[:]
    config["runner"]["cpp_debug_flags"] = debug_flags[:]

    build_cpp_compile_flags(
        config,
        tmp_path,
        debug=True,
        extra_flags=("-Werror",),
    )

    assert config["runner"]["cpp_flags"] == base_flags
    assert config["runner"]["cpp_debug_flags"] == debug_flags
    assert config["paths"]["cpp_library"] == "cpplib"


def test_build_cpp_compile_flags_does_not_accumulate_between_calls(tmp_path):
    library = tmp_path / "cpplib"
    library.mkdir()
    config = _cpp_config(tmp_path, "cpplib")

    first = build_cpp_compile_flags(config, tmp_path, debug=True)
    second = build_cpp_compile_flags(config, tmp_path, debug=True)

    assert first == second
    assert first.count("-I") == 2
    assert first.count(str(library.resolve())) == 1
    assert first.count(str(cpp_module.BUILTIN_CPP_INCLUDE_DIR)) == 1
    assert first.count(cpp_module.BUILTIN_CPP_DEBUG_DEFINE) == 1

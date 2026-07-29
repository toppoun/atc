from pathlib import Path

import atc.core.config as config_module


def _write_config(root: Path, content: str) -> Path:
    atc_dir = root / ".atc"
    atc_dir.mkdir(parents=True)
    config_file = atc_dir / "config.toml"
    config_file.write_text(content, encoding="utf-8")
    return config_file


def test_find_config_file_from_parent(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module.Path, "home", lambda: tmp_path / "home")
    config_file = _write_config(tmp_path, "")
    nested = tmp_path / "abc335" / "src"
    nested.mkdir(parents=True)

    assert config_module.find_config_file(nested) == config_file


def test_find_config_file_without_config_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module.Path, "home", lambda: tmp_path / "home")

    assert config_module.find_config_file(tmp_path) is None


def test_config_root_dot_is_project_root(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module.Path, "home", lambda: tmp_path / "home")
    _write_config(tmp_path, "[paths]\nroot = \".\"\n")
    nested = tmp_path / "abc335"
    nested.mkdir()

    loaded = config_module.load_config(nested)

    assert config_module.config_root(loaded) == tmp_path.resolve()


def test_config_root_relative_path_is_under_project_root(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module.Path, "home", lambda: tmp_path / "home")
    _write_config(tmp_path, "[paths]\nroot = \"contests\"\n")

    loaded = config_module.load_config(tmp_path)

    assert config_module.config_root(loaded) == (tmp_path / "contests").resolve()


def test_default_config_uses_contest_path_rules_without_legacy_paths():
    paths = config_module.default_config()["paths"]

    assert paths["contests"]["abc\\d+"] == "ABC"
    assert paths["contests"]["adt_.*"] == "ATD"
    for key in ["abc", "arc", "agc", "abs", "alpc", "edpc", "tessoku", "typical90"]:
        assert key not in paths


def test_default_config_template_includes_contest_path_rules():
    template = config_module.config_to_toml(config_module.default_config_template())

    assert 'root = "."' in template
    assert "[paths.contests]" in template
    assert '"abc\\\\d+" = "ABC"' in template
    assert '"arc\\\\d+" = "ARC"' in template
    assert '"agc\\\\d+" = "AGC"' in template
    assert '"adt_.*" = "ATD"' in template
    assert 'abc = "ABC(Atcoder Beginner Contest)"' not in template
    assert 'arc = "ARC(Atcoder Regular Contest)"' not in template
    assert 'agc = "AGC(Atcoder Grand Contest)"' not in template


def test_default_config_includes_cpp_debug_flags():
    assert config_module.default_config()["runner"]["cpp_debug_flags"] == [
        "-DLOCAL",
        "-D_GLIBCXX_DEBUG",
    ]


def test_default_config_cpp_library_is_disabled():
    assert config_module.default_config()["paths"]["cpp_library"] == ""


def test_default_config_template_toml_includes_empty_cpp_library():
    template = config_module.config_to_toml(config_module.default_config_template())

    assert 'cpp_library = ""' in template


def test_load_config_adds_empty_cpp_library_to_old_config(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module.Path, "home", lambda: tmp_path / "home")
    _write_config(tmp_path, '[paths]\nroot = "."\n')

    loaded = config_module.load_config(tmp_path)

    assert loaded["paths"]["cpp_library"] == ""


def test_cpp_library_path_returns_none_for_empty_value(tmp_path):
    config = {"paths": {"root": "", "cpp_library": ""}}

    assert config_module.cpp_library_path(config, tmp_path) is None


def test_cpp_library_path_resolves_absolute_path(tmp_path):
    library = tmp_path / "cpplib"
    config = {"paths": {"root": "", "cpp_library": str(library)}}

    assert config_module.cpp_library_path(config) == library.resolve()


def test_cpp_library_path_resolves_relative_path_from_config_root(tmp_path):
    config = {
        "paths": {
            "root": str(tmp_path),
            "cpp_library": "cpplib",
        }
    }

    assert config_module.cpp_library_path(config) == (tmp_path / "cpplib").resolve()


def test_cpp_library_path_uses_config_project_root_when_root_is_empty(tmp_path):
    config_file = tmp_path / ".atc" / "config.toml"
    config = {
        config_module.CONFIG_FILE_META_KEY: str(config_file),
        "paths": {
            "root": "",
            "cpp_library": "cpplib",
        },
    }

    assert config_module.cpp_library_path(config) == (tmp_path / "cpplib").resolve()


def test_cpp_library_path_uses_start_without_config_information(tmp_path):
    config = {"paths": {"root": "", "cpp_library": "cpplib"}}

    assert config_module.cpp_library_path(config, tmp_path) == (tmp_path / "cpplib").resolve()


def test_cpp_library_path_expands_user_home():
    config = {"paths": {"root": "", "cpp_library": "~/atc-cpplib-test"}}

    assert config_module.cpp_library_path(config) == Path("~/atc-cpplib-test").expanduser().resolve()


def test_cpp_library_path_rejects_non_table_paths():
    config = {"paths": []}

    try:
        config_module.cpp_library_path(config)
    except config_module.ConfigError as e:
        assert str(e) == "[paths] must be a table."
    else:
        raise AssertionError("ConfigError was not raised")


def test_cpp_library_path_rejects_non_string_value():
    config = {"paths": {"root": "", "cpp_library": ["cpplib"]}}

    try:
        config_module.cpp_library_path(config)
    except config_module.ConfigError as e:
        assert str(e) == "paths.cpp_library must be a path string."
    else:
        raise AssertionError("ConfigError was not raised")


def test_runner_cpp_debug_flags_converts_list_items_to_strings():
    config = {"runner": {"cpp_debug_flags": ["-DLOCAL", 123]}}

    assert config_module.runner_cpp_debug_flags(config) == ["-DLOCAL", "123"]


def test_runner_cpp_debug_flags_splits_string_value():
    config = {"runner": {"cpp_debug_flags": "-DLOCAL -D_GLIBCXX_DEBUG"}}

    assert config_module.runner_cpp_debug_flags(config) == [
        "-DLOCAL",
        "-D_GLIBCXX_DEBUG",
    ]


def test_runner_cpp_debug_flags_invalid_value_falls_back_to_default():
    config = {"runner": {"cpp_debug_flags": 123}}

    assert config_module.runner_cpp_debug_flags(config) == [
        "-DLOCAL",
        "-D_GLIBCXX_DEBUG",
    ]


def test_runner_cpp_debug_flags_preserves_explicit_empty_list():
    config = {"runner": {"cpp_debug_flags": []}}

    assert config_module.runner_cpp_debug_flags(config) == []


def test_default_config_template_toml_includes_cpp_debug_flags():
    template = config_module.config_to_toml(config_module.default_config_template())

    assert 'cpp_debug_flags = ["-DLOCAL", "-D_GLIBCXX_DEBUG"]' in template


def test_load_config_adds_default_cpp_debug_flags_to_old_config(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module.Path, "home", lambda: tmp_path / "home")
    _write_config(tmp_path, '[runner]\ncpp_flags = ["-std=c++17"]\n')

    loaded = config_module.load_config(tmp_path)

    assert loaded["runner"]["cpp_debug_flags"] == [
        "-DLOCAL",
        "-D_GLIBCXX_DEBUG",
    ]


def test_find_project_root_does_not_use_legacy_category_names(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module.Path, "home", lambda: tmp_path / "home")
    work = tmp_path / "ABC(Atcoder Beginner Contest)" / "work"
    work.mkdir(parents=True)

    assert config_module.find_project_root(work) != tmp_path.resolve()


def test_watch_settings_default_values():
    poll_seconds, debounce_seconds, warnings = config_module.watch_settings(config_module.default_config())

    assert poll_seconds == config_module.WATCH_POLL_SECONDS
    assert debounce_seconds == config_module.WATCH_DEBOUNCE_SECONDS
    assert warnings == []


def test_watch_settings_invalid_values_fall_back_to_defaults():
    cfg = config_module.default_config()
    cfg["watch"] = {
        "poll_seconds": 999,
        "debounce_seconds": -1,
    }

    poll_seconds, debounce_seconds, warnings = config_module.watch_settings(cfg)

    assert poll_seconds == config_module.WATCH_POLL_SECONDS
    assert debounce_seconds == config_module.WATCH_DEBOUNCE_SECONDS
    assert len(warnings) == 2

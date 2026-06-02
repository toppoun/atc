import pytest

import atc.config as config_module
import atc.contest as contest_module
import atc.paths as paths_module
from atc.paths import ContestPathConfigError, is_workspace_root, resolve_contest_dir


def _config(root, paths):
    return {"paths": {"root": str(root), **paths}}


def _default_contest_paths():
    return {
        "abc\\d+": "ABC",
        "arc\\d+": "ARC",
        "agc\\d+": "AGC",
        "adt_.*": "ATD",
    }


def test_resolve_contest_dir_uses_paths_contests_for_abc(tmp_path):
    config = _config(tmp_path, {"contests": {"abc\\d+": "ABC"}})

    assert resolve_contest_dir("abc460", config) == tmp_path / "ABC" / "abc460"


def test_contest_module_reexports_path_helpers():
    assert contest_module.ContestPathConfigError is paths_module.ContestPathConfigError
    assert contest_module.resolve_contest_dir is paths_module.resolve_contest_dir
    assert contest_module.resolve_contest_group is paths_module.resolve_contest_group


def test_resolve_contest_dir_uses_paths_contests_for_adt(tmp_path):
    config = _config(tmp_path, {"contests": {"adt_.*": "ATD"}})

    assert resolve_contest_dir("adt_all_20260525_1", config) == tmp_path / "ATD" / "adt_all_20260525_1"
    assert resolve_contest_dir("adt_easy_20260525_1", config) == tmp_path / "ATD" / "adt_easy_20260525_1"


def test_resolve_contest_dir_uses_regex_map_for_default_contest_groups(tmp_path):
    config = _config(tmp_path, {"contests": _default_contest_paths()})

    assert resolve_contest_dir("abc460", config) == tmp_path / "ABC" / "abc460"
    assert resolve_contest_dir("arc180", config) == tmp_path / "ARC" / "arc180"
    assert resolve_contest_dir("agc060", config) == tmp_path / "AGC" / "agc060"
    assert resolve_contest_dir("adt_all_20260525_1", config) == tmp_path / "ATD" / "adt_all_20260525_1"


def test_resolve_contest_dir_uses_first_matching_paths_contests_rule(tmp_path):
    config = _config(
        tmp_path,
        {
            "contests": {
                "abc460": "Special",
                "abc\\d+": "ABC",
            }
        },
    )

    assert resolve_contest_dir("abc460", config) == tmp_path / "Special" / "abc460"
    assert resolve_contest_dir("abc459", config) == tmp_path / "ABC" / "abc459"


def test_resolve_contest_dir_preserves_paths_contests_order_from_toml(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module.Path, "home", lambda: tmp_path / "home")
    atc_dir = tmp_path / ".atc"
    atc_dir.mkdir()
    (atc_dir / "config.toml").write_text(
        "\n".join(
            [
                "[paths]",
                f'root = "{tmp_path.as_posix()}"',
                "",
                "[paths.contests]",
                '"abc460" = "Special"',
                '"abc\\\\d+" = "ABC"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    config = config_module.load_config(tmp_path)

    assert resolve_contest_dir("abc460", config) == tmp_path / "Special" / "abc460"
    assert resolve_contest_dir("abc459", config) == tmp_path / "ABC" / "abc459"


def test_resolve_contest_dir_uses_config_init_style_paths_contests(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module.Path, "home", lambda: tmp_path / "home")
    atc_dir = tmp_path / ".atc"
    atc_dir.mkdir()
    (atc_dir / "config.toml").write_text(
        "\n".join(
            [
                "[paths]",
                f'root = "{tmp_path.as_posix()}"',
                "",
                "[paths.contests]",
                '"abc\\\\d+" = "ABC"',
                '"arc\\\\d+" = "ARC"',
                '"agc\\\\d+" = "AGC"',
                '"adt_.*" = "ATD"',
                "",
                "[templates]",
                'py = "templates/template.py"',
                'cpp = "templates/template.cpp"',
                "",
                "[defaults]",
                'language = "cpp"',
                'problems = ["A", "B", "C", "D", "E"]',
                "",
            ]
        ),
        encoding="utf-8",
    )
    config = config_module.load_config(tmp_path)

    assert resolve_contest_dir("abc460", config) == tmp_path / "ABC" / "abc460"
    assert resolve_contest_dir("adt_all_20260525_1", config) == tmp_path / "ATD" / "adt_all_20260525_1"


def test_resolve_contest_dir_uses_fullmatch_for_paths_contests(tmp_path):
    config = _config(tmp_path, {"contests": {"abc\\d+": "ABC"}})

    assert resolve_contest_dir("abc460", config) == tmp_path / "ABC" / "abc460"
    assert resolve_contest_dir("abc460_extra", config) == tmp_path / "abc460_extra"


def test_resolve_contest_dir_creates_unknown_contests_under_root(tmp_path):
    config = _config(tmp_path, {"contests": _default_contest_paths()})

    assert resolve_contest_dir("typical90", config) == tmp_path / "typical90"
    assert resolve_contest_dir("abc460_extra", config) == tmp_path / "abc460_extra"


def test_resolve_contest_dir_ignores_legacy_abc_arc_agc_paths(tmp_path):
    config = _config(
        tmp_path,
        {
            "abc": "ABC",
            "arc": "ARC",
            "agc": "AGC",
        },
    )

    assert resolve_contest_dir("abc460", config) == tmp_path / "abc460"
    assert resolve_contest_dir("arc180", config) == tmp_path / "arc180"
    assert resolve_contest_dir("agc060", config) == tmp_path / "agc060"


def test_resolve_contest_dir_reports_invalid_paths_contests_regex(tmp_path):
    config = _config(tmp_path, {"contests": {"abc(": "ABC"}})

    with pytest.raises(ContestPathConfigError, match=r"invalid contest path regex: abc\("):
        resolve_contest_dir("abc460", config)


def test_resolve_contest_dir_reports_non_table_paths_contests(tmp_path):
    config = _config(tmp_path, {"contests": "ATD"})

    with pytest.raises(ContestPathConfigError, match=r"\[paths\.contests\] must be a table\."):
        resolve_contest_dir("adt_all_20260525_1", config)


def test_resolve_contest_dir_reports_invalid_paths_contests_regex_after_match(tmp_path):
    config = _config(
        tmp_path,
        {
            "contests": {
                "abc\\d+": "ABC",
                "abc(": "Broken",
            }
        },
    )

    with pytest.raises(ContestPathConfigError, match=r"invalid contest path regex: abc\("):
        resolve_contest_dir("abc460", config)


def test_is_workspace_root_detects_configured_root(tmp_path):
    config = _config(tmp_path, {"contests": _default_contest_paths()})
    contest_dir = tmp_path / "ABC" / "abc460"
    contest_dir.mkdir(parents=True)

    assert is_workspace_root(tmp_path, config) is True
    assert is_workspace_root(contest_dir, config) is False

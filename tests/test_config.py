from pathlib import Path

import atc.config as config_module


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

    assert config_module._find_config_file(nested) == config_file


def test_find_config_file_without_config_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module.Path, "home", lambda: tmp_path / "home")

    assert config_module._find_config_file(tmp_path) is None


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


def test_watch_settings_default_values():
    poll_seconds, debounce_seconds, warnings = config_module.watch_settings(config_module._default_config())

    assert poll_seconds == config_module.WATCH_POLL_SECONDS
    assert debounce_seconds == config_module.WATCH_DEBOUNCE_SECONDS
    assert warnings == []


def test_watch_settings_invalid_values_fall_back_to_defaults():
    cfg = config_module._default_config()
    cfg["watch"] = {
        "poll_seconds": 999,
        "debounce_seconds": -1,
    }

    poll_seconds, debounce_seconds, warnings = config_module.watch_settings(cfg)

    assert poll_seconds == config_module.WATCH_POLL_SECONDS
    assert debounce_seconds == config_module.WATCH_DEBOUNCE_SECONDS
    assert len(warnings) == 2

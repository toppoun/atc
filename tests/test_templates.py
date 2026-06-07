import json
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

import pytest

import atc.core.config as config_module
from atc.core.templates import (
    TEMPLATE_DIR,
    TemplateError,
    TemplateManifestError,
    load_template_manifest,
    resolve_template_name,
    resolve_template_file,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _write_config(root, content):
    atc_dir = root / ".atc"
    atc_dir.mkdir(parents=True)
    config_file = atc_dir / "config.toml"
    config_file.write_text(content, encoding="utf-8")
    return config_file


def test_resolve_template_file_legacy_path(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module.Path, "home", lambda: tmp_path / "home")
    template = tmp_path / "templates" / "custom.py"
    template.parent.mkdir()
    template.write_text("print('legacy')\n", encoding="utf-8")
    _write_config(tmp_path, "[templates]\npy = \"templates/custom.py\"\n")

    cfg = config_module.load_config(tmp_path)

    assert resolve_template_file("py", cfg, tmp_path) == template


def test_resolve_template_file_manifest_name(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module.Path, "home", lambda: tmp_path / "home")
    template = tmp_path / "templates" / "python" / "fast.py"
    template.parent.mkdir(parents=True)
    template.write_text("print('fast')\n", encoding="utf-8")
    manifest = tmp_path / "templates" / "manifest.json"
    manifest.write_text(
        json.dumps({"python": {"fast": {"path": "python/fast.py"}}}),
        encoding="utf-8",
    )
    _write_config(
        tmp_path,
        "[templates]\nmanifest = \"templates/manifest.json\"\npy = \"fast\"\n",
    )

    cfg = config_module.load_config(tmp_path)

    assert resolve_template_file("py", cfg, tmp_path) == template


def test_resolve_template_file_missing_name_raises_template_error(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module.Path, "home", lambda: tmp_path / "home")
    manifest = tmp_path / "templates" / "manifest.json"
    manifest.parent.mkdir()
    manifest.write_text(json.dumps({"python": {}}), encoding="utf-8")
    _write_config(
        tmp_path,
        "[templates]\nmanifest = \"templates/manifest.json\"\npy = \"missing\"\n",
    )

    cfg = config_module.load_config(tmp_path)

    with pytest.raises(TemplateError):
        resolve_template_file("py", cfg, tmp_path)


def test_load_template_manifest_broken_json_raises_manifest_error(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{broken", encoding="utf-8")

    with pytest.raises(TemplateManifestError):
        load_template_manifest(manifest)


def test_resolve_default_template_file_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module.Path, "home", lambda: tmp_path / "home")

    template = resolve_template_file("py", config_module._default_config(), tmp_path)

    assert template.name == "template.py"
    assert template.exists()


def test_package_manifest_contains_stress_templates():
    manifest_path = TEMPLATE_DIR / "manifest.json"
    manifest = load_template_manifest(manifest_path)

    gen_template = resolve_template_name("stress", "gen", manifest, manifest_path)
    brute_template = resolve_template_name("stress", "brute", manifest, manifest_path)

    assert gen_template == TEMPLATE_DIR / "stress" / "gen.py"
    assert brute_template == TEMPLATE_DIR / "stress" / "brute.py"
    assert gen_template.exists()
    assert brute_template.exists()


def test_pyproject_includes_stress_templates_as_package_data():
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    package_data = pyproject["tool"]["setuptools"]["package-data"]["atc"]

    assert "templates/stress/*.py" in package_data

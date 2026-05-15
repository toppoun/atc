import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

try:
    from .config import (
        _config_project_root,
        _config_root,
        _find_config_file,
        _find_project_root,
        load_config,
    )
    from .console import error, warn
except ImportError:
    from config import (
        _config_project_root,
        _config_root,
        _find_config_file,
        _find_project_root,
        load_config,
    )
    from console import error, warn


TEMPLATE_DIR = Path(__file__).parent / "templates"
MANIFEST_FILE_NAME = "manifest.json"


class TemplateError(Exception):
    pass


class TemplateManifestError(TemplateError):
    pass


@dataclass
class TemplateInfo:
    language: str
    name: str
    path: Path
    description: str = ""
    source: str = ""


def load_template(ext: str, config: Optional[dict] = None, start: Optional[Path] = None):
    """Read a template file. If config exists, resolve [templates] from it."""
    try:
        template_file = resolve_template_file(ext, config, start)
    except TemplateError as e:
        error(f"Error: {e}")
        sys.exit(1)

    if template_file.exists():
        return template_file.read_text(encoding="utf-8")

    warn(f"Warning: {template_file} が見つかりません。空ファイルを作成します。")
    return ""


def resolve_template_file(ext: str, config: Optional[dict] = None, start: Optional[Path] = None):
    start = start or Path.cwd()
    ext = _normalize_template_ext(ext)
    config = config or load_config(start)

    template_value = _template_value(config, ext)
    if _is_template_path(template_value):
        _validate_explicit_manifest(config, start)
        return _resolve_template_path_value(template_value, ext, config, start)

    manifest_path = resolve_template_manifest(config, start, required=True)
    manifest = load_template_manifest(manifest_path)
    return resolve_template_name(ext, template_value, manifest, manifest_path)


def resolve_template_manifest(
    config: Optional[dict] = None,
    start: Optional[Path] = None,
    required: bool = False,
) -> Optional[Path]:
    start = start or Path.cwd()
    config = config or load_config(start)
    templates = config.get("templates", {})
    raw_manifest = ""
    if isinstance(templates, dict):
        raw_manifest = str(templates.get("manifest") or "").strip()

    if raw_manifest:
        manifest_path = _resolve_manifest_path_value(raw_manifest, config, start)
        if required and not manifest_path.exists():
            raise TemplateManifestError(f"template manifest not found: {manifest_path}")
        return manifest_path

    for candidate in _implicit_manifest_candidates(config, start):
        if candidate.exists():
            return candidate

    if required:
        raise TemplateManifestError("template manifest was not found")
    return None


def load_template_manifest(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise TemplateManifestError(f"failed to parse template manifest: {path}: {e}")
    except OSError as e:
        raise TemplateManifestError(f"failed to read template manifest: {path}: {e}")

    if not isinstance(data, dict):
        raise TemplateManifestError(f"template manifest must be a JSON object: {path}")
    return data


def resolve_template_name(ext: str, name: str, manifest: dict, manifest_path: Path):
    ext = _normalize_template_ext(ext)
    language_key, language_table = _manifest_language_table(ext, manifest, manifest_path)
    if name not in language_table:
        raise TemplateManifestError(f"template '{name}' was not found for {language_key}: {manifest_path}")

    entry = language_table[name]
    if not isinstance(entry, dict):
        raise TemplateManifestError(f"template entry must be an object: {language_key}.{name}")

    raw_path = str(entry.get("path") or "").strip()
    if not raw_path:
        raise TemplateManifestError(f"template entry is missing path: {language_key}.{name}")

    template_path = Path(raw_path).expanduser()
    if not template_path.is_absolute():
        template_path = manifest_path.parent / template_path

    if not template_path.exists():
        raise TemplateManifestError(f"template file not found for {language_key}.{name}: {template_path}")
    return template_path


def list_templates(config: Optional[dict] = None, start: Optional[Path] = None) -> List[TemplateInfo]:
    manifest_path = resolve_template_manifest(config, start, required=False)
    if not manifest_path:
        return []

    manifest = load_template_manifest(manifest_path)
    results: List[TemplateInfo] = []
    for ext in ["py", "cpp"]:
        try:
            language_key, language_table = _manifest_language_table(ext, manifest, manifest_path)
        except TemplateManifestError:
            continue
        for name, entry in language_table.items():
            if not isinstance(entry, dict):
                continue
            raw_path = str(entry.get("path") or "").strip()
            if not raw_path:
                continue
            template_path = Path(raw_path).expanduser()
            if not template_path.is_absolute():
                template_path = manifest_path.parent / template_path
            results.append(
                TemplateInfo(
                    language=language_key,
                    name=name,
                    path=template_path,
                    description=str(entry.get("description") or ""),
                    source=str(manifest_path),
                )
            )
    return results


def _normalize_template_ext(ext: str):
    normalized = str(ext).strip().lower()
    if normalized in ["py", "python"]:
        return "py"
    if normalized in ["cpp", "c++"]:
        return "cpp"
    return normalized


def _template_value(config: dict, ext: str):
    templates = config.get("templates", {})
    if not isinstance(templates, dict):
        return f"templates/template.{ext}"
    return str(templates.get(ext) or f"templates/template.{ext}").strip()


def _validate_explicit_manifest(config: dict, start: Path) -> None:
    templates = config.get("templates", {})
    if not isinstance(templates, dict):
        return
    if not str(templates.get("manifest") or "").strip():
        return

    manifest_path = resolve_template_manifest(config, start, required=True)
    load_template_manifest(manifest_path)


def _is_template_path(value: str):
    value = str(value or "").strip()
    if not value:
        return False
    path = Path(value).expanduser()
    return (
        path.is_absolute()
        or value.startswith(("~", ".", "/", "\\"))
        or "/" in value
        or "\\" in value
        or bool(Path(value).suffix)
    )


def _resolve_template_path_value(value: str, ext: str, config: dict, start: Path):
    template_path = Path(value).expanduser()
    if template_path.is_absolute():
        return template_path

    config_file = _find_config_file(start)
    if not config_file:
        if value == f"templates/template.{ext}":
            return TEMPLATE_DIR / f"template.{ext}"
        return (start / template_path).resolve()

    candidates = [
        config_file.parent / template_path,
        _config_project_root(config_file) / template_path,
    ]

    config_root = _config_root(config)
    if config_root:
        candidates.append(config_root / template_path)

    candidates.append(_find_project_root(start, config) / template_path)

    if value == f"templates/template.{ext}":
        candidates.append(TEMPLATE_DIR / f"template.{ext}")

    return _first_existing_or_last(candidates)


def _resolve_manifest_path_value(value: str, config: dict, start: Path):
    manifest_path = Path(value).expanduser()
    if manifest_path.is_absolute():
        return manifest_path

    config_file = _find_config_file(start)
    if not config_file:
        return (start / manifest_path).resolve()

    candidates = [
        config_file.parent / manifest_path,
        _config_project_root(config_file) / manifest_path,
    ]

    config_root = _config_root(config)
    if config_root:
        candidates.append(config_root / manifest_path)

    candidates.append(_find_project_root(start, config) / manifest_path)
    return _first_existing_or_last(candidates)


def _implicit_manifest_candidates(config: dict, start: Path):
    manifest_path = Path("templates") / MANIFEST_FILE_NAME
    config_file = _find_config_file(start)
    candidates = []
    if config_file:
        candidates.extend(
            [
                config_file.parent / manifest_path,
                _config_project_root(config_file) / manifest_path,
            ]
        )

        config_root = _config_root(config)
        if config_root:
            candidates.append(config_root / manifest_path)

        candidates.append(_find_project_root(start, config) / manifest_path)

    candidates.append(TEMPLATE_DIR / MANIFEST_FILE_NAME)
    return _unique_paths(candidates)


def _first_existing_or_last(candidates):
    unique_candidates = _unique_paths(candidates)
    for candidate in unique_candidates:
        if candidate.exists():
            return candidate
    return unique_candidates[-1]


def _unique_paths(candidates):
    unique_candidates = []
    seen = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved not in seen:
            unique_candidates.append(candidate)
            seen.add(resolved)
    return unique_candidates


def _manifest_language_table(ext: str, manifest: dict, manifest_path: Path):
    for language_key in _manifest_language_keys(ext):
        language_table = manifest.get(language_key)
        if isinstance(language_table, dict):
            return language_key, language_table
    raise TemplateManifestError(f"template language section was not found for {ext}: {manifest_path}")


def _manifest_language_keys(ext: str):
    if ext == "py":
        return ["python", "py"]
    if ext == "cpp":
        return ["cpp", "c++"]
    return [ext]


_resolve_template_file = resolve_template_file

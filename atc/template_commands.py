from pathlib import Path
from typing import List, Optional

from .config import load_config
from .console import error
from .templates import (
    TemplateError,
    TemplateInfo,
    list_templates,
    load_template_manifest,
    resolve_template_manifest,
    resolve_template_name,
)


def _normalize_template_language(language: Optional[str]) -> Optional[str]:
    if language is None:
        return None
    normalized = str(language).strip().lower()
    if normalized in ["py", "python"]:
        return "py"
    if normalized in ["cpp", "c++"]:
        return "cpp"
    if normalized == "stress":
        return "stress"
    raise TemplateError("Invalid template language. Use py/python, cpp/c++, or stress.")


def _language_label(language: str) -> str:
    if language == "py":
        return "Python"
    if language == "cpp":
        return "C++"
    return "Stress"


def _template_matches_language(template: TemplateInfo, language: str) -> bool:
    template_language = template.language.strip().lower()
    if language == "py":
        return template_language in ["py", "python"]
    if language == "cpp":
        return template_language in ["cpp", "c++"]
    if language == "stress":
        return template_language == "stress"
    return False


def _templates_for_language(templates: List[TemplateInfo], language: str) -> List[TemplateInfo]:
    return [template for template in templates if _template_matches_language(template, language)]


def _print_template_group(label: str, templates: List[TemplateInfo]) -> None:
    print(f"{label} templates:")
    if not templates:
        print("  (none)")
        return

    width = max(len(template.name) for template in templates)
    for template in templates:
        description = f"  {template.name:<{width}}"
        if template.description:
            description += f"  {template.description}"
        print(description)
        print(f"    path: {template.path}")


def cmd_template_list(language: Optional[str] = None) -> int:
    cwd = Path.cwd()
    config = load_config(cwd)
    try:
        normalized_language = _normalize_template_language(language)
        templates = list_templates(config, cwd)
    except TemplateError as e:
        error(f"Error: {e}")
        return 1

    if normalized_language:
        _print_template_group(
            _language_label(normalized_language),
            _templates_for_language(templates, normalized_language),
        )
        return 0

    _print_template_group("Python", _templates_for_language(templates, "py"))
    print()
    _print_template_group("C++", _templates_for_language(templates, "cpp"))
    print()
    _print_template_group("Stress", _templates_for_language(templates, "stress"))
    return 0


def cmd_template_show(language: str, name: str) -> int:
    cwd = Path.cwd()
    config = load_config(cwd)
    try:
        normalized_language = _normalize_template_language(language)
        manifest_path = resolve_template_manifest(config, cwd, required=True)
        manifest = load_template_manifest(manifest_path)
        template_path = resolve_template_name(normalized_language, name, manifest, manifest_path)
        print(template_path.read_text(encoding="utf-8"), end="")
    except TemplateError as e:
        error(f"Error: {e}")
        return 1
    except OSError as e:
        error(f"Error: failed to read template: {e}")
        return 1
    return 0

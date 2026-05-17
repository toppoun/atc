from atc.commands import resolve_command, usage_lines


def test_resolve_command_aliases():
    assert resolve_command("run").name == "run"
    assert resolve_command("r").name == "run"
    assert resolve_command("test").name == "run"
    assert resolve_command("t").name == "run"

    assert resolve_command("contest").name == "contest"
    assert resolve_command("contests").name == "contest"

    assert resolve_command("visual").name == "visual"
    assert resolve_command("vis").name == "visual"
    assert resolve_command("vizui").name == "visual"

    assert resolve_command("template").name == "template"

    assert resolve_command("unknown") is None


def test_usage_lines_include_main_commands():
    usage = "\n".join(usage_lines())

    assert "atc new" in usage
    assert "atc contest" in usage
    assert "atc config doctor" in usage
    assert "atc run A" in usage
    assert "atc run all" in usage
    assert "atc rerun" in usage
    assert "atc watch" in usage
    assert "atc template list" in usage
    assert "atc template show" in usage
    assert "atc visual" in usage
    assert "atc manual" in usage

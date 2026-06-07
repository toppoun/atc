from atc.commands.template_commands import cmd_template_list, cmd_template_show


def test_cmd_template_list_filters_python_templates(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    result = cmd_template_list("py")
    output = capsys.readouterr().out

    assert result == 0
    assert "Python templates:" in output
    assert "default" in output
    assert "fast" in output
    assert "C++ templates:" not in output


def test_cmd_template_show_prints_template_body(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    result = cmd_template_show("py", "default")
    output = capsys.readouterr().out

    assert result == 0
    assert "def main" in output


def test_cmd_template_show_unknown_template_returns_error(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    result = cmd_template_show("py", "unknown")
    output = capsys.readouterr().out

    assert result == 1
    assert "Error:" in output
    assert "unknown" in output


def test_cmd_template_list_filters_stress_templates(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    result = cmd_template_list("stress")
    output = capsys.readouterr().out

    assert result == 0
    assert "Stress templates:" in output
    assert "gen" in output
    assert "brute" in output
    assert "Python templates:" not in output


def test_cmd_template_show_prints_stress_template_body(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    result = cmd_template_show("stress", "gen")
    output = capsys.readouterr().out

    assert result == 0
    assert "random.seed(seed)" in output

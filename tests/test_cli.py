import json

from envdrift.cli import main


def project(tmp_path, example="A=\n"):
    (tmp_path / "app.py").write_text('import os\nos.getenv("A")\nos.getenv("B")\n')
    (tmp_path / ".env.example").write_text(example)
    return tmp_path


def test_exit_code_1_on_error(tmp_path, capsys):
    project(tmp_path)
    assert main(["check", str(tmp_path), "--no-git", "--no-color"]) == 1
    assert "B is used in code" in capsys.readouterr().out


def test_exit_code_0_when_clean(tmp_path, capsys):
    project(tmp_path, "A=\nB=\n")
    assert main([str(tmp_path), "--no-git"]) == 0
    assert "No drift detected" in capsys.readouterr().out


def test_json_output(tmp_path, capsys):
    project(tmp_path)
    main(["check", str(tmp_path), "--no-git", "--format", "json"])
    data = json.loads(capsys.readouterr().out)
    assert data["summary"]["errors"] == 1
    assert data["findings"][0]["variable"] == "B"


def test_strict_fails_on_warnings(tmp_path):
    (tmp_path / "app.py").write_text("x = 1\n")
    (tmp_path / ".env.example").write_text("OLD=\n")
    assert main([str(tmp_path), "--no-git"]) == 0
    assert main([str(tmp_path), "--no-git", "--strict"]) == 1


def test_fix_command(tmp_path, capsys):
    project(tmp_path)
    assert main(["fix", str(tmp_path), "--no-git"]) == 0
    assert "B=" in (tmp_path / ".env.example").read_text()
    assert main([str(tmp_path), "--no-git"]) == 0


def test_bad_path(capsys):
    assert main(["/definitely/not/here"]) == 2

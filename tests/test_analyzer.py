from envdrift.analyzer import analyze, fix_example, looks_like_secret


def make_project(tmp_path, code, example=None, env=None):
    (tmp_path / "app.py").write_text(code)
    if example is not None:
        (tmp_path / ".env.example").write_text(example)
    if env is not None:
        (tmp_path / ".env").write_text(env)
    return tmp_path


def codes(report):
    return sorted((f.code, f.variable) for f in report.findings)


def test_clean_project_has_no_findings(tmp_path):
    make_project(tmp_path, 'import os\nos.getenv("A")\n', "A=\n", "A=1\n")
    assert analyze(tmp_path, use_git=False).findings == []


def test_undocumented_is_error(tmp_path):
    make_project(tmp_path, 'import os\nos.getenv("A")\nos.getenv("B")\n', "A=\n")
    report = analyze(tmp_path, use_git=False)
    assert ("undocumented", "B") in codes(report)
    assert len(report.errors) == 1


def test_stale_variable_is_warning(tmp_path):
    make_project(tmp_path, "x = 1\n", "OLD=\n")
    report = analyze(tmp_path, use_git=False)
    assert ("stale", "OLD") in codes(report)
    assert not report.errors


def test_missing_and_extra_local(tmp_path):
    make_project(tmp_path, 'import os\nos.getenv("A")\n', "A=\n", "Z=1\n")
    report = analyze(tmp_path, use_git=False)
    got = codes(report)
    assert ("missing-local", "A") in got
    assert ("extra-local", "Z") in got


def test_missing_example_file(tmp_path):
    make_project(tmp_path, "x = 1\n")
    report = analyze(tmp_path, use_git=False)
    assert report.findings[0].code == "no-example"


def test_ignore_option(tmp_path):
    make_project(tmp_path, 'import os\nos.getenv("SKIP_ME")\n', "A=\n")
    report = analyze(tmp_path, ignore=["SKIP_ME", "A"], use_git=False)
    assert report.findings == []


def test_secret_detection():
    assert looks_like_secret("AKIAIOSFODNN7EXAMPLE")
    assert looks_like_secret("ghp_" + "a1B2c3D4e5F6g7H8i9J0" * 2)
    assert not looks_like_secret("changeme")
    assert not looks_like_secret("https://example.com/some/long/path/here")
    assert not looks_like_secret("")


def test_secret_in_example_is_error(tmp_path):
    make_project(tmp_path, 'import os\nos.getenv("KEY")\n', "KEY=AKIAIOSFODNN7EXAMPLE\n")
    report = analyze(tmp_path, use_git=False)
    assert ("secret-in-example", "KEY") in codes(report)


def test_fix_appends_undocumented(tmp_path):
    make_project(tmp_path, 'import os\nos.getenv("A")\nos.getenv("NEW_ONE")\n', "A=\n")
    report = analyze(tmp_path, use_git=False)
    added = fix_example(tmp_path, report)
    assert added == ["NEW_ONE"]
    content = (tmp_path / ".env.example").read_text()
    assert "NEW_ONE=" in content
    assert "app.py:3" in content
    assert analyze(tmp_path, use_git=False).errors == []

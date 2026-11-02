from envdrift.scanner import scan_directory, scan_text


def names(text, compose=False):
    return sorted({v for v, _ in scan_text(text, compose=compose)})


def test_python_patterns():
    code = (
        'import os\n'
        'a = os.environ["DB_URL"]\n'
        'b = os.environ.get("API_KEY", "x")\n'
        'c = os.getenv("DEBUG")\n'
    )
    assert names(code) == ["API_KEY", "DB_URL", "DEBUG"]


def test_javascript_patterns():
    code = (
        "const a = process.env.PORT;\n"
        "const b = process.env['SECRET'];\n"
        "const c = import.meta.env.VITE_API;\n"
    )
    assert names(code) == ["PORT", "SECRET", "VITE_API"]


def test_other_languages():
    assert names('os.Getenv("GO_VAR")') == ["GO_VAR"]
    assert names('ENV["RUBY_VAR"]') == ["RUBY_VAR"]
    assert names("env::var(\"RUST_VAR\")") == ["RUST_VAR"]
    assert names('System.getenv("JAVA_VAR")') == ["JAVA_VAR"]
    assert names("env('LARAVEL_VAR')") == ["LARAVEL_VAR"]


def test_lowercase_names_are_ignored():
    assert names('os.getenv("lowercase")') == []


def test_compose_interpolation_only_in_compose_mode():
    text = "image: ${REGISTRY}/app:${TAG:-latest}\n"
    assert names(text, compose=True) == ["REGISTRY", "TAG"]
    assert names(text, compose=False) == []


def test_scan_directory_skips_node_modules_and_builtins(tmp_path):
    (tmp_path / "app.py").write_text('import os\nos.environ["MY_VAR"]\nos.getenv("PATH")\n')
    nm = tmp_path / "node_modules" / "lib"
    nm.mkdir(parents=True)
    (nm / "index.js").write_text("process.env.HIDDEN")
    found = scan_directory(tmp_path)
    assert set(found) == {"MY_VAR"}
    assert found["MY_VAR"][0].file == "app.py"
    assert found["MY_VAR"][0].line == 2

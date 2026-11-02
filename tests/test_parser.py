from envdrift.parser import parse_env_text


def test_basic_pairs_and_comments():
    text = "# comment\nA=1\n\nB=two\n"
    assert parse_env_text(text) == {"A": "1", "B": "two"}


def test_export_and_quotes():
    text = "export A='x y'\nB=\"hello\"\n"
    assert parse_env_text(text) == {"A": "x y", "B": "hello"}


def test_inline_comment_only_when_unquoted():
    text = "A=value # note\nB=\"keep # this\"\n"
    assert parse_env_text(text) == {"A": "value", "B": "keep # this"}


def test_empty_value_and_invalid_keys():
    text = "A=\n1BAD=x\nno equals here\n"
    assert parse_env_text(text) == {"A": ""}


def test_value_may_contain_equals():
    assert parse_env_text("URL=postgres://u:p@h/db?x=1\n") == {
        "URL": "postgres://u:p@h/db?x=1"
    }

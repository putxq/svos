from board.director import _build_envelope, _decide_lines


def test_decide_lines_defaults_to_both():
    lines = _decide_lines("optimize operations")
    assert lines == ["content", "sales"]


def test_decide_lines_arabic_content_only():
    lines = _decide_lines("نبي محتوى لحملة جديدة")
    assert "content" in lines


def test_build_envelope():
    env = _build_envelope("t-1", "assembly.content", {"topic": "x"})
    assert env.trace_id == "t-1"
    assert env.intent == "assembly.content"
    assert env.from_agent == "board"

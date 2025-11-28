import pytest
from ai_handler import format_ai_response_html


def test_inline_code_and_cmd_and_emoji():
    sample = "Run `ls -la` and then /comprar to buy credits 😄"
    out = format_ai_response_html(sample)
    # Expect inline code wrapped in <code> and command wrapped as code, emoji preserved
    assert "<code>ls -la</code>" in out
    assert "<code>/comprar</code>" in out
    assert "😄" in out


def test_fenced_code_block():
    sample = "Here is code:\n```\nprint(\"hello\")\n```"
    out = format_ai_response_html(sample)
    assert "<pre><code>" in out
    assert "print(&quot;hello&quot;)" in out


def test_html_escape():
    sample = "<script>alert(1)</script> and backticks `x`"
    out = format_ai_response_html(sample)
    assert "script" not in out or "&lt;script&gt;" in out
    assert "<code>x</code>" in out


def test_bold_and_italic_conversion():
    sample = "This is **very important** and this is *less important* and _also less_"
    out = format_ai_response_html(sample)
    # Bold should be wrapped in <b> tags and italic markers removed
    assert "<b>very important</b>" in out
    assert "*less important*" not in out
    assert "_also less_" not in out

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import helpers


def test_esc_neutralises_markup():
    assert "<" not in helpers.esc('<img src=x onerror="alert(1)">')
    assert helpers.esc(None) == ""


@pytest.mark.parametrize("url,ok", [("https://example.com/a", "https://example.com/a"), ("javascript:alert(1)", "#"), ("", "#"), (None, "#")])
def test_safe_link(url, ok):
    assert helpers.safe_link(url) == ok


@pytest.mark.parametrize("url", ["http://127.0.0.1:8501", "http://localhost/admin", "http://169.254.169.254/latest/meta-data", "file:///etc/passwd", "ftp://example.com", "not a url", "http://10.0.0.5"])
def test_validate_public_url_blocks_internal_targets(url):
    with pytest.raises(ValueError):
        helpers.validate_public_url(url)


def test_parse_analysis_handles_prose_and_partial_json():
    reply = 'Here you go:\n```json\n' + json.dumps({"importanceScore": "7.6", "summary": "s", "keyHighlights": "one"}) + '\n```'
    out = helpers.parse_analysis(reply)
    assert out["importanceScore"] == 8
    assert out["keyHighlights"] == ["one"]
    assert out["designAndRealEstateIntel"] == {"opportunities": [], "trends": [], "keyProjects": []}


@pytest.mark.parametrize("bad", ["no json", "{not json}", "[1,2]"])
def test_parse_analysis_rejects_garbage(bad):
    with pytest.raises(ValueError):
        helpers.parse_analysis(bad)


def test_score_is_clamped():
    assert helpers.normalise_analysis({"importanceScore": 99})["importanceScore"] == 10
    assert helpers.normalise_analysis({"importanceScore": "abc"})["importanceScore"] == 1


def test_news_query_quotes_phrases():
    assert helpers.news_query(["real estate", "AI", " "]) == '"real estate" OR AI'


def test_clip():
    assert helpers.clip("x" * (helpers.MAX_INPUT_CHARS + 5))[1] is True
    assert helpers.clip("short") == ("short", False)

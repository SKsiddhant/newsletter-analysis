import json
import os
import sys
import types

import pytest
from streamlit.testing.v1 import AppTest

APP = os.path.join(os.path.dirname(__file__), "..", "app.py")
HERE = os.path.join(os.path.dirname(__file__), "..")


class FakeModel:
    reply = "{}"

    def __init__(self, *_a, **_k):
        pass

    def generate_content(self, _prompt):
        return types.SimpleNamespace(text=FakeModel.reply)


@pytest.fixture(autouse=True)
def fake_services(monkeypatch):
    import google.generativeai as genai
    import requests
    monkeypatch.setattr(genai, "GenerativeModel", FakeModel)
    monkeypatch.setattr(genai, "configure", lambda **k: None)
    calls = {}

    def fake_get(url, **kw):
        calls["url"], calls["kw"] = url, kw
        articles = [{"source": {"name": "<b>Src</b>"}, "title": "<img src=x onerror=alert(1)>", "description": None, "url": "javascript:alert(1)"}]
        return types.SimpleNamespace(json=lambda: {"status": "ok", "articles": articles})
    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.syspath_prepend(HERE)
    return calls


def run(reply, news_key="k"):
    FakeModel.reply = reply
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["GEMINI_API_KEY"] = "g"
    at.session_state["NEWS_API_KEY"] = news_key
    at.run()
    at.text_area[0].set_value("Some newsletter text").run()
    at.button[0].click().run()
    return at


def test_full_flow_renders_and_escapes_untrusted_html(fake_services):
    at = run(json.dumps({"importanceScore": 9, "summary": "S", "marketImpact": "M",
                         "buildersAndIndustries": ["<script>x</script>"], "keyHighlights": ["h"], "searchKeywords": ["real estate"]}))
    assert not at.exception
    html = "".join(m.value for m in at.markdown)
    assert "<img src=x" not in html and "<script>" not in html
    assert "&lt;img" in html and 'href="#"' in html and "javascript:" not in html
    # NewsAPI key travels in a header, not in the URL
    assert "apiKey" not in fake_services["url"] and fake_services["kw"]["headers"]["X-Api-Key"] == "k"


def test_result_survives_another_interaction():
    at = run(json.dumps({"importanceScore": 5, "summary": "Kept", "keyHighlights": [], "searchKeywords": []}))
    at.radio[0].set_value("Paste Text").run()  # any widget interaction triggers a rerun
    assert any("Importance Score: 5/10" in m.value for m in at.markdown)


def test_partial_model_answer_does_not_crash():
    at = run(json.dumps({"summary": "only a summary"}))
    assert not at.exception


def test_garbage_model_answer_shows_error_not_traceback():
    at = run("sorry, I cannot help")
    assert not at.exception and len(at.error) == 1

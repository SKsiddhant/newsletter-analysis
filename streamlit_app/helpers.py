"""Pure helpers for app.py (no Streamlit import, so they can be unit-tested)."""
import html
import ipaddress
import json
import re
import socket
from urllib.parse import urlparse

MAX_INPUT_CHARS = 100_000  # keep the prompt well inside the model's context window


def esc(value):
    """Escape text before it is placed inside HTML rendered with unsafe_allow_html=True.
    Model output and NewsAPI fields are untrusted: a title like <img src=x onerror=...> would otherwise run."""
    return html.escape(str(value if value is not None else ""), quote=True)


def safe_link(url):
    """Only http(s) links are allowed in hrefs ('javascript:' URLs would execute on click)."""
    url = str(url or "")
    return url if urlparse(url).scheme in ("http", "https") else "#"


def validate_public_url(url):
    """Raise ValueError unless `url` is http(s) and resolves only to public addresses.
    Without this the 'Article URL' box can be pointed at localhost or cloud metadata endpoints (SSRF)
    when the app is hosted."""
    parsed = urlparse((url or "").strip())
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Enter a full http:// or https:// URL.")
    try:
        infos = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror:
        raise ValueError("Could not resolve that host.")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise ValueError("That address is not a public website.")
    return parsed.geturl()


def fetch_public(url, get, max_redirects=5, **kwargs):
    """GET `url` with `get` (requests.get), re-validating every redirect hop.
    requests follows redirects on its own, so a public URL that 302s to http://169.254.169.254/ would
    otherwise slip past validate_public_url(). Raises ValueError on a bad hop or too many redirects."""
    from urllib.parse import urljoin
    url = validate_public_url(url)
    for _ in range(max_redirects + 1):
        response = get(url, allow_redirects=False, **kwargs)
        location = response.headers.get("Location") if 300 <= response.status_code < 400 else None
        if not location:
            return response
        url = validate_public_url(urljoin(url, location))
    raise ValueError("Too many redirects.")


def parse_analysis(content):
    """Extract the JSON object from a model reply, or raise ValueError."""
    match = re.search(r"\{.*\}", content or "", re.DOTALL)
    if not match:
        raise ValueError("Could not find JSON in the AI response.")
    try:
        data = json.loads(match.group())
    except json.JSONDecodeError as exc:
        raise ValueError(f"The AI response was not valid JSON ({exc}).")
    if not isinstance(data, dict):
        raise ValueError("The AI response was not a JSON object.")
    return normalise_analysis(data)


def _as_list(value):
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)] if value else []


def normalise_analysis(data):
    """Fill in missing fields so the UI never raises KeyError/TypeError on a partial model answer."""
    try:
        score = max(1, min(10, round(float(data.get("importanceScore", 0)))))
    except (TypeError, ValueError):
        score = 1
    intel = data.get("designAndRealEstateIntel")
    intel = intel if isinstance(intel, dict) else {}
    return {
        "importanceScore": score,
        "summary": str(data.get("summary") or "No summary returned."),
        "marketImpact": str(data.get("marketImpact") or "No market impact returned."),
        "buildersAndIndustries": _as_list(data.get("buildersAndIndustries")),
        "keyHighlights": _as_list(data.get("keyHighlights")),
        "searchKeywords": _as_list(data.get("searchKeywords")),
        "designAndRealEstateIntel": {
            "opportunities": _as_list(intel.get("opportunities")),
            "trends": _as_list(intel.get("trends")),
            "keyProjects": _as_list(intel.get("keyProjects")),
        },
    }


def news_query(keywords):
    """NewsAPI query: quote multi-word phrases so 'real estate' is not split into 'real OR estate'."""
    parts = [f'"{k.strip()}"' if " " in k.strip() else k.strip() for k in keywords if k and k.strip()]
    return " OR ".join(parts)


def clip(text):
    """Returns (text, was_truncated)."""
    text = text or ""
    return (text[:MAX_INPUT_CHARS], True) if len(text) > MAX_INPUT_CHARS else (text, False)

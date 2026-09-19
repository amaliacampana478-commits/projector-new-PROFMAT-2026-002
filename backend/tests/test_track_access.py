"""Tests for /api/track/access endpoint and KPI incrementing."""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001').rstrip('/')
API = f"{BASE_URL}/api"

ADMIN_USER = "donas"
ADMIN_PASS = "Seinao10@@"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/admin/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PASS}, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("token") or data.get("access_token") or data.get("jwt")
    assert tok, f"no token in response: {data}"
    return tok


def test_track_access_new_visitor():
    vid = f"test_visitor_{uuid.uuid4().hex}"
    r = requests.post(f"{API}/track/access", json={
        "page": "/inicio.html",
        "user_agent": "pytest-agent",
        "extra": {"visitor_id": vid},
    }, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("ok") is True
    assert "skipped" not in body, f"expected new access, got {body}"


def test_track_access_duplicate_visitor():
    vid = f"test_visitor_{uuid.uuid4().hex}"
    p = {"page": "/inicio.html", "user_agent": "pytest-agent", "extra": {"visitor_id": vid}}
    r1 = requests.post(f"{API}/track/access", json=p, timeout=15)
    assert r1.status_code == 200
    assert r1.json().get("ok") is True
    r2 = requests.post(f"{API}/track/access", json=p, timeout=15)
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2.get("ok") is True
    assert body2.get("skipped") == "duplicate", body2


def test_track_access_admin_path_skipped():
    vid = f"test_visitor_{uuid.uuid4().hex}"
    r = requests.post(f"{API}/track/access", json={
        "page": "/donaspainel/#/dashboard",
        "user_agent": "pytest-agent",
        "extra": {"visitor_id": vid},
    }, timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True
    assert body.get("skipped") == "admin", body


def test_kpi_increments_on_new_access(admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    r1 = requests.get(f"{API}/admin/dashboard/kpis", headers=headers, timeout=15)
    assert r1.status_code == 200, r1.text
    before = r1.json().get("acessos", 0)
    assert isinstance(before, int)

    vid = f"test_visitor_{uuid.uuid4().hex}"
    rp = requests.post(f"{API}/track/access", json={
        "page": "/inicio.html",
        "user_agent": "pytest-agent",
        "extra": {"visitor_id": vid},
    }, timeout=15)
    assert rp.status_code == 200
    assert rp.json().get("ok") is True and "skipped" not in rp.json()

    time.sleep(0.5)
    r2 = requests.get(f"{API}/admin/dashboard/kpis", headers=headers, timeout=15)
    assert r2.status_code == 200
    after = r2.json().get("acessos", 0)
    assert after >= before + 1, f"acessos did not increment: before={before} after={after}"


def test_track_access_mobile_user_agent():
    vid = f"qa-mobile-{uuid.uuid4().hex}"
    r = requests.post(f"{API}/track/access", json={
        "page": "/",
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit",
        "extra": {"visitor_id": vid},
    }, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("ok") is True
    assert "skipped" not in body, body


def test_track_access_desktop_user_agent():
    vid = f"qa-desktop-{uuid.uuid4().hex}"
    r = requests.post(f"{API}/track/access", json={
        "page": "/",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "extra": {"visitor_id": vid},
    }, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("ok") is True
    assert "skipped" not in body, body


def test_funnel_devices_reflects_counts(admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    # snapshot
    r0 = requests.get(f"{API}/admin/dashboard/funnel-devices", headers=headers, timeout=15)
    assert r0.status_code == 200, r0.text
    before = r0.json()
    # log a mobile and a desktop with new visitor ids
    vm = f"qa-mobile-{uuid.uuid4().hex}"
    vd = f"qa-desktop-{uuid.uuid4().hex}"
    assert requests.post(f"{API}/track/access", json={"page": "/", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)", "extra": {"visitor_id": vm}}, timeout=15).status_code == 200
    assert requests.post(f"{API}/track/access", json={"page": "/", "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "extra": {"visitor_id": vd}}, timeout=15).status_code == 200
    time.sleep(0.5)
    r1 = requests.get(f"{API}/admin/dashboard/funnel-devices", headers=headers, timeout=15)
    assert r1.status_code == 200, r1.text
    after = r1.json()
    # We expect mobile and desktop total counts (in whatever keys the endpoint returns) to be present
    # Try common shapes
    def extract(d):
        # Attempt several shapes: {mobile: N, desktop: N} or {"devices":{"mobile":N,"desktop":N}} or list [{device,count}]
        if isinstance(d, dict):
            if "mobile" in d and "desktop" in d:
                return int(d.get("mobile") or 0), int(d.get("desktop") or 0)
            devs = d.get("devices") or d.get("data") or d.get("funnel")
            if isinstance(devs, dict) and "mobile" in devs:
                return int(devs.get("mobile") or 0), int(devs.get("desktop") or 0)
            if isinstance(devs, list):
                m = next((int(x.get("count") or x.get("total") or 0) for x in devs if str(x.get("device", "")).lower() == "mobile"), 0)
                dd = next((int(x.get("count") or x.get("total") or 0) for x in devs if str(x.get("device", "")).lower() == "desktop"), 0)
                return m, dd
        if isinstance(d, list):
            # Shape: [{label:'Acessos ao site', desktop:N, mobile:N}, ...]
            for item in d:
                if isinstance(item, dict) and "mobile" in item and "desktop" in item and "acesso" in str(item.get("label", "")).lower():
                    return int(item.get("mobile") or 0), int(item.get("desktop") or 0)
            m = next((int(x.get("count") or x.get("total") or 0) for x in d if str(x.get("device", "")).lower() == "mobile"), 0)
            dd = next((int(x.get("count") or x.get("total") or 0) for x in d if str(x.get("device", "")).lower() == "desktop"), 0)
            return m, dd
        return None, None

    mb, db = extract(before)
    ma, da = extract(after)
    print("funnel-devices before=", before, "after=", after)
    assert ma is not None and da is not None, f"unrecognized funnel-devices shape: {after}"
    assert ma >= (mb or 0) + 1, f"mobile did not increment: {mb} -> {ma}"
    assert da >= (db or 0) + 1, f"desktop did not increment: {db} -> {da}"


def test_inicio_html_has_csp_connect_src():
    r = requests.get(f"{BASE_URL}/inicio.html", timeout=15)
    assert r.status_code == 200
    html = r.text
    assert "content-security-policy" in html.lower()
    import re
    # Attribute values may or may not be quoted
    metas = re.findall(r'<meta[^>]*http-equiv=["\']?content-security-policy["\']?[^>]*>', html, re.IGNORECASE)
    assert metas, "CSP meta not found"
    m = re.search(r'content="([^"]+)"', metas[0], re.IGNORECASE)
    assert m, f"CSP content not found in meta: {metas[0]}"
    csp = m.group(1)
    assert "connect-src" in csp and "'self'" in csp, f"connect-src 'self' not in CSP: {csp}"


def test_inicio_html_has_tracker_script():
    r = requests.get(f"{BASE_URL}/inicio.html", timeout=15)
    assert r.status_code == 200
    assert "pf_visitor_id" in r.text
    assert "/api/track/access" in r.text

"""Backend E2E tests for review request: admin auth, dashboard, settings, PIX, tracking, CEP."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://projector-setup.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

USERNAME = "donas"
PASSWORD = "Seinao10@@"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/admin/auth/login", json={"username": USERNAME, "password": PASSWORD}, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    data = r.json()
    assert "token" in data or "access_token" in data, f"No token in response: {data}"
    tok = data.get("token") or data.get("access_token")
    assert isinstance(tok, str) and len(tok) > 0
    return tok


@pytest.fixture(scope="module")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# --- Admin auth ---
class TestAdminAuth:
    def test_login_success(self):
        r = requests.post(f"{API}/admin/auth/login", json={"username": USERNAME, "password": PASSWORD}, timeout=30)
        assert r.status_code == 200
        data = r.json()
        tok = data.get("token") or data.get("access_token")
        assert tok
        assert "user" in data or "admin" in data

    def test_login_wrong_password(self):
        r = requests.post(f"{API}/admin/auth/login", json={"username": USERNAME, "password": "wrongpass"}, timeout=30)
        assert r.status_code == 401

    def test_me_with_token(self, auth_headers):
        r = requests.get(f"{API}/admin/auth/me", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        data = r.json()
        # Ensure username present
        assert USERNAME in str(data)

    def test_me_without_token(self):
        r = requests.get(f"{API}/admin/auth/me", timeout=30)
        assert r.status_code in (401, 403)


# --- Dashboard endpoints ---
class TestDashboard:
    def test_kpis(self, auth_headers):
        r = requests.get(f"{API}/admin/dashboard/kpis", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), dict)

    def test_funnel(self, auth_headers):
        r = requests.get(f"{API}/admin/dashboard/funnel", headers=auth_headers, timeout=30)
        assert r.status_code == 200

    def test_activity(self, auth_headers):
        r = requests.get(f"{API}/admin/dashboard/activity", headers=auth_headers, timeout=30)
        assert r.status_code == 200

    def test_realtime(self, auth_headers):
        r = requests.get(f"{API}/admin/dashboard/realtime", headers=auth_headers, timeout=30)
        assert r.status_code == 200


# --- Settings ---
class TestSettings:
    def test_get_settings(self, auth_headers):
        r = requests.get(f"{API}/admin/settings", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), dict)

    def test_update_settings(self, auth_headers):
        payload = {
            "pix_key": "test@pix.com",
            "pix_nome": "TEST NOME",
            "pix_cidade": "SAO PAULO",
            "valor_inscricao": 120.00,
        }
        r = requests.put(f"{API}/admin/settings", json=payload, headers=auth_headers, timeout=30)
        assert r.status_code in (200, 201), f"{r.status_code} {r.text}"
        # Verify persistence
        r2 = requests.get(f"{API}/admin/settings", headers=auth_headers, timeout=30)
        assert r2.status_code == 200
        data = r2.json()
        # Confirm at least pix_key persisted
        blob = str(data)
        assert "test@pix.com" in blob


# --- PIX ---
class TestPix:
    def test_pix_generate(self, auth_headers):
        # Requires settings configured first (done in TestSettings)
        payload = {"nome": "Fulano Teste", "cpf": "12345678909", "valor": 120.00}
        r = requests.post(f"{API}/pix/generate", json=payload, timeout=30)
        assert r.status_code in (200, 201), f"{r.status_code} {r.text}"
        data = r.json()
        # Expect brcode or copia_cola or similar
        blob = str(data).lower()
        assert any(k in blob for k in ["brcode", "copia", "code", "qr", "pix"]), f"Unexpected pix response: {data}"

    def test_pix_qr_png(self):
        r = requests.get(f"{API}/pix/qr.png", timeout=30)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("image/png")
        assert len(r.content) > 100

    def test_pix_code_txt(self):
        r = requests.get(f"{API}/pix/code.txt", timeout=30)
        assert r.status_code == 200
        assert len(r.text) > 20


# --- Tracking ---
class TestTracking:
    def test_track_access(self):
        payload = {"path": "/inicio", "user_agent": "pytest", "referrer": "test"}
        r = requests.post(f"{API}/track/access", json=payload, timeout=30)
        assert r.status_code in (200, 201, 204)

    def test_track_registration(self):
        payload = {
            "nome": "TEST User",
            "cpf": "12345678909",
            "email": "test@test.com",
            "telefone": "11999999999",
        }
        r = requests.post(f"{API}/track/registration", json=payload, timeout=30)
        assert r.status_code in (200, 201, 204)


# --- CEP ---
class TestCEP:
    def test_cep_lookup(self):
        # Known valid CEP - Av Paulista
        r = requests.get(f"{API}/cep/01310100", timeout=30)
        assert r.status_code == 200
        data = r.json()
        blob = str(data).lower()
        assert "paulista" in blob or "logradouro" in blob or "cep" in blob


# --- Admin management ---
class TestAdminList:
    def test_list_admins(self, auth_headers):
        r = requests.get(f"{API}/admin/admins", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, (list, dict))

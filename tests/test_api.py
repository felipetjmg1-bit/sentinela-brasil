from __future__ import annotations

import base64
import sqlite3

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from sentinela.config import Settings
from sentinela.main import create_app


@pytest.fixture()
def client(tmp_path):
    settings = Settings(
        database_path=str(tmp_path / "sentinela.db"),
        token_secret="T" * 48,
        vault_key=Fernet.generate_key().decode(),
        bootstrap_username="admin",
        bootstrap_password="Demo-Admin-Password-2026!",
    )
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client, settings


def login(client: TestClient, username="admin", password="Demo-Admin-Password-2026!") -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_health_interface_headers_and_protected_access(client):
    client, _ = client
    assert client.get("/api/health").json()["status"] == "ok"
    html = client.get("/")
    assert html.status_code == 200 and "Sentinela Brasil" in html.text
    assert html.headers["x-content-type-options"] == "nosniff"
    assert client.get("/api/dashboard").status_code == 401


def test_authentication_and_admin_rbac(client):
    client, _ = client
    assert (
        client.post(
            "/api/auth/login", json={"username": "admin", "password": "wrong-password"}
        ).status_code
        == 401
    )
    admin = login(client)
    assert client.get("/api/auth/me", headers=auth(admin)).json()["role"] == "admin"
    assert (
        client.post(
            "/api/users",
            headers=auth(admin),
            json={"username": "reader01", "password": "Reader-Passphrase-2026!", "role": "viewer"},
        ).status_code
        == 201
    )
    viewer = login(client, "reader01", "Reader-Passphrase-2026!")
    assert (
        client.post(
            "/api/users",
            headers=auth(viewer),
            json={"username": "intruder", "password": "Insecure-Passphrase-2026!", "role": "admin"},
        ).status_code
        == 403
    )


def test_vault_encryption_classification_export_and_object_isolation(client):
    client, settings = client
    admin = login(client)
    secret = b"synthetic-not-a-real-secret"
    payload = {
        "filename": "note.txt",
        "media_type": "text/plain",
        "classification": "internal",
        "content_base64": base64.b64encode(secret).decode(),
    }
    uploaded = client.post("/api/vault", headers=auth(admin), json=payload)
    assert uploaded.status_code == 201, uploaded.text
    file_id = uploaded.json()["id"]
    with sqlite3.connect(settings.database_path) as conn:
        ciphertext = conn.execute(
            "SELECT ciphertext FROM vault_files WHERE id=?", (file_id,)
        ).fetchone()[0]
    assert secret not in ciphertext
    result = client.get(f"/api/vault/{file_id}", headers=auth(admin))
    assert result.status_code == 200
    assert base64.b64decode(result.json()["content_base64"]) == secret
    client.post(
        "/api/users",
        headers=auth(admin),
        json={"username": "viewer02", "password": "Viewer-Passphrase-2026!", "role": "viewer"},
    )
    viewer = login(client, "viewer02", "Viewer-Passphrase-2026!")
    assert client.get(f"/api/vault/{file_id}", headers=auth(viewer)).status_code == 403


def test_invalid_uploads_are_rejected(client):
    client, _ = client
    token = login(client)
    bad_name = {
        "filename": "../escape.txt",
        "media_type": "text/plain",
        "classification": "public",
        "content_base64": base64.b64encode(b"x").decode(),
    }
    assert client.post("/api/vault", headers=auth(token), json=bad_name).status_code == 422
    bad_type = {**bad_name, "filename": "x.txt", "media_type": "application/x-executable"}
    assert client.post("/api/vault", headers=auth(token), json=bad_type).status_code == 415


def test_gateway_blocks_or_redacts_sensitive_patterns_without_external_calls(client):
    client, _ = client
    token = login(client)
    blocked = client.post(
        "/api/ai/evaluate", headers=auth(token), json={"prompt": "Contato teste pessoa@example.org"}
    ).json()
    assert blocked["simulated"] is True and blocked["external_provider_called"] is False
    assert blocked["allowed"] is False and blocked["sanitized_prompt"] is None
    redacted = client.post(
        "/api/ai/evaluate",
        headers=auth(token),
        json={"prompt": "Contato pessoa@example.org, CPF 123.456.789-00", "mode": "redact"},
    ).json()
    assert redacted["allowed"] is True
    assert "pessoa@example.org" not in redacted["sanitized_prompt"]
    assert "123.456.789-00" not in redacted["sanitized_prompt"]


def test_ledger_integrity_and_tamper_detection(client):
    client, settings = client
    token = login(client)
    assert client.get("/api/audit/verify", headers=auth(token)).json()["valid"] is True
    client.get("/api/dashboard", headers=auth(token))
    with sqlite3.connect(settings.database_path) as conn:
        conn.execute("UPDATE audit_events SET reason_code='ALTERED' WHERE seq=1")
    result = client.get("/api/audit/verify", headers=auth(token)).json()
    assert result["valid"] is False and result["failed_seq"] == 1


def test_assets_dashboard_and_policy_endpoint(client):
    client, _ = client
    token = login(client)
    asset = client.post(
        "/api/assets",
        headers=auth(token),
        json={
            "name": "Subestação sintética",
            "asset_type": "substation",
            "criticality": "high",
            "owner": "Equipe fictícia",
            "network_zone": "zona-laboratório",
            "notes": "Dado de demonstração",
        },
    )
    assert asset.status_code == 201
    assert client.get("/api/assets", headers=auth(token)).json()[0]["criticality"] == "high"
    dashboard = client.get("/api/dashboard", headers=auth(token)).json()
    assert dashboard["ledger_integrity"]["valid"] is True
    assert dashboard["counts"]["assets"] == 1
    assert client.get("/api/policies", headers=auth(token)).json()["default_effect"] == "deny"


def test_asset_review_is_metadata_only_and_not_a_certification(client):
    client, _ = client
    token = login(client)
    created = client.post(
        "/api/assets",
        headers=auth(token),
        json={
            "name": "Ativo fictício",
            "asset_type": "control-system",
            "criticality": "critical",
            "owner": "Equipe sintética",
            "network_zone": "laboratório",
            "notes": "Registro ilustrativo",
        },
    ).json()
    review = client.get(f"/api/assets/{created['id']}/review", headers=auth(token)).json()
    assert review["network_scanned"] is False
    assert review["certification"] is False
    assert review["assessment_type"] == "metadata_only_defensive_review"
    assert any("segmentação" in item for item in review["recommendations"])


def test_analyst_policy_denies_confidential_upload_and_audits_reason(client):
    client, _ = client
    admin = login(client)
    created = client.post(
        "/api/users",
        headers=auth(admin),
        json={"username": "analyst1", "password": "Analyst-Passphrase-2026!", "role": "analyst"},
    )
    assert created.status_code == 201
    analyst = login(client, "analyst1", "Analyst-Passphrase-2026!")
    response = client.post(
        "/api/vault",
        headers=auth(analyst),
        json={
            "filename": "restricted.txt",
            "media_type": "text/plain",
            "classification": "confidential",
            "content_base64": base64.b64encode(b"synthetic").decode(),
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"]["reason_code"] == "DENY_NO_MATCHING_RULE"
    event_text = str(client.get("/api/audit/events", headers=auth(admin)).json())
    assert "DENY_NO_MATCHING_RULE" in event_text


def test_sensitive_prompt_is_not_written_to_audit(client):
    client, settings = client
    token = login(client)
    private_synthetic_text = "pessoa@example.org"
    client.post("/api/ai/evaluate", headers=auth(token), json={"prompt": private_synthetic_text})
    with sqlite3.connect(settings.database_path) as conn:
        event_rows = conn.execute(
            "SELECT action,resource_type,resource_id,outcome,reason_code FROM audit_events"
        ).fetchall()
    assert private_synthetic_text not in repr(event_rows)


def test_viewer_can_list_and_export_public_but_not_internal_files(client):
    client, _ = client
    admin = login(client)
    viewer = client.post(
        "/api/users",
        headers=auth(admin),
        json={
            "username": "publicreader",
            "password": "Public-Reader-Passphrase-2026!",
            "role": "viewer",
        },
    )
    assert viewer.status_code == 201
    public_file = client.post(
        "/api/vault",
        headers=auth(admin),
        json={
            "filename": "public.txt",
            "media_type": "text/plain",
            "classification": "public",
            "content_base64": base64.b64encode(b"synthetic public example").decode(),
        },
    ).json()
    internal_file = client.post(
        "/api/vault",
        headers=auth(admin),
        json={
            "filename": "internal.txt",
            "media_type": "text/plain",
            "classification": "internal",
            "content_base64": base64.b64encode(b"synthetic internal example").decode(),
        },
    ).json()
    viewer_token = login(client, "publicreader", "Public-Reader-Passphrase-2026!")
    visible = client.get("/api/vault", headers=auth(viewer_token)).json()
    assert [item["filename"] for item in visible] == ["public.txt"]
    assert (
        client.get(f"/api/vault/{public_file['id']}", headers=auth(viewer_token)).status_code == 200
    )
    assert (
        client.get(f"/api/vault/{internal_file['id']}", headers=auth(viewer_token)).status_code
        == 403
    )

from __future__ import annotations

import base64
import binascii
import json
import re
import sqlite3
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken as InvalidCiphertext
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from sentinela.audit import append_event, verify_ledger
from sentinela.config import Settings
from sentinela.db import connect, initialize, transaction
from sentinela.policy import RULES, decide
from sentinela.security import (
    InvalidToken,
    hash_password,
    issue_token,
    verify_password,
    verify_token,
)

bearer = HTTPBearer(auto_error=False)
USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,64}$")
EMAIL_RE = re.compile(r"(?<![\w.+-])[\w.+-]{1,64}@[\w.-]+\.[A-Za-z]{2,24}")
CPF_RE = re.compile(r"(?<!\d)(?:\d{3}\.?){3}-?\d{2}(?!\d)")
SECRET_RE = re.compile(r"(?i)\b(?:api[_-]?key|token|secret)\s*[:=]\s*[^\s,;]{8,}")
ALLOWED_TYPES = {"text/plain", "text/csv", "application/json", "application/pdf", "image/png"}


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=12, max_length=256)
    role: str = Field(pattern="^(admin|analyst|viewer)$")


class VaultUpload(BaseModel):
    filename: str = Field(min_length=1, max_length=128)
    media_type: str = Field(min_length=1, max_length=100)
    classification: str = Field(pattern="^(public|internal|confidential|restricted)$")
    content_base64: str = Field(min_length=1, max_length=3_000_000)


class AIEvaluation(BaseModel):
    prompt: str = Field(min_length=1, max_length=4096)
    mode: str = Field(default="strict", pattern="^(strict|redact)$")


class AssetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    asset_type: str = Field(min_length=1, max_length=60)
    criticality: str = Field(pattern="^(low|medium|high|critical)$")
    owner: str = Field(min_length=1, max_length=120)
    network_zone: str = Field(min_length=1, max_length=80)
    notes: str = Field(default="", max_length=500)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        config.validate()
        config.ensure_database_directory()
        initialize(config.database_path)
        with transaction(config.database_path) as conn:
            has_users = conn.execute("SELECT 1 FROM users LIMIT 1").fetchone()
            if not has_users and config.bootstrap_username and config.bootstrap_password:
                username = config.bootstrap_username
                password = config.bootstrap_password
                if not USERNAME_RE.fullmatch(username) or len(password) < 16:
                    raise RuntimeError(
                        "Credenciais de bootstrap inválidas; verifique os requisitos documentados."
                    )
                cursor = conn.execute(
                    "INSERT INTO users(username,password_hash,role,created_at) VALUES(?,?,?,?)",
                    (username, hash_password(password), "admin", utc_now()),
                )
                append_event(
                    conn,
                    actor_id=None,
                    action="bootstrap.admin_created",
                    resource_type="user",
                    resource_id=str(cursor.lastrowid),
                    outcome="success",
                    reason_code="BOOTSTRAP_CONFIGURED",
                )
        application.state.ready = True
        try:
            yield
        finally:
            application.state.ready = False

    app = FastAPI(
        title="Sentinela Brasil API",
        description="Demonstração local de governança de dados e IA; não é certificação nem solução de produção.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = config
    app.state.ready = False

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        content_length = request.headers.get("content-length")
        encoded_limit = (config.max_upload_bytes * 4 // 3) + 100_000
        if content_length and content_length.isdigit() and int(content_length) > encoded_limit:
            return JSONResponse(
                status_code=413,
                content={"detail": "Corpo da requisição excede o limite permitido."},
            )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'"
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    def get_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=401,
                detail="Autenticação necessária.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            user_id = verify_token(credentials.credentials, config.token_secret)
        except InvalidToken:
            raise HTTPException(
                status_code=401,
                detail="Credencial inválida ou expirada.",
                headers={"WWW-Authenticate": "Bearer"},
            ) from None
        conn = connect(config.database_path)
        try:
            row = conn.execute(
                "SELECT id,username,role FROM users WHERE id=?", (user_id,)
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            raise HTTPException(status_code=401, detail="Credencial inválida ou expirada.")
        return dict(row)

    def require_role(*roles: str):
        def dependency(user: dict = Depends(get_user)) -> dict:
            if user["role"] not in roles:
                raise HTTPException(status_code=403, detail="Operação não autorizada.")
            return user

        return dependency

    def policy_check(user: dict, action: str, classification: str, owner: bool = True) -> dict:
        decision = decide(user["role"], action, classification, owner=owner)
        return decision.as_dict()

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok" if app.state.ready else "starting", "version": "0.1.0"}

    @app.post("/api/auth/login")
    def login(body: LoginRequest) -> dict:
        conn = connect(config.database_path)
        try:
            user = conn.execute("SELECT * FROM users WHERE username=?", (body.username,)).fetchone()
            if user is None or not verify_password(body.password, user["password_hash"]):
                append_event(
                    conn,
                    actor_id=None,
                    action="auth.login",
                    resource_type="session",
                    resource_id=None,
                    outcome="denied",
                    reason_code="AUTH_FAILED",
                )
                conn.commit()
                raise HTTPException(status_code=401, detail="Usuário ou senha inválidos.")
            append_event(
                conn,
                actor_id=user["id"],
                action="auth.login",
                resource_type="session",
                resource_id=None,
                outcome="success",
                reason_code="AUTHENTICATED",
            )
            conn.commit()
            return {
                "access_token": issue_token(user["id"], config.token_secret),
                "token_type": "bearer",
                "expires_in": 3600,
            }
        finally:
            conn.close()

    @app.get("/api/auth/me")
    def whoami(user: dict = Depends(get_user)) -> dict:
        return {"id": user["id"], "username": user["username"], "role": user["role"]}

    @app.post("/api/users", status_code=201)
    def create_user(body: UserCreate, admin: dict = Depends(require_role("admin"))) -> dict:
        if not USERNAME_RE.fullmatch(body.username):
            raise HTTPException(status_code=422, detail="Formato de usuário inválido.")
        try:
            with transaction(config.database_path) as conn:
                cursor = conn.execute(
                    "INSERT INTO users(username,password_hash,role,created_at) VALUES(?,?,?,?)",
                    (body.username, hash_password(body.password), body.role, utc_now()),
                )
                append_event(
                    conn,
                    actor_id=admin["id"],
                    action="user.create",
                    resource_type="user",
                    resource_id=body.username,
                    outcome="success",
                    reason_code="ADMIN_ACTION",
                )
                user_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="Não foi possível criar usuário.") from None
        return {"id": user_id, "username": body.username, "role": body.role}

    @app.get("/api/policies")
    def get_policies(user: dict = Depends(get_user)) -> dict:
        return {"version": "sentinela-demo-1", "default_effect": "deny", "rules": list(RULES)}

    @app.post("/api/vault", status_code=201)
    def upload_vault(body: VaultUpload, user: dict = Depends(get_user)) -> dict:
        filename = body.filename
        if (
            Path(filename).name != filename
            or filename in {".", ".."}
            or "\\" in filename
            or filename.startswith(".")
        ):
            raise HTTPException(status_code=422, detail="Nome de arquivo inválido.")
        if body.media_type not in ALLOWED_TYPES:
            raise HTTPException(status_code=415, detail="Tipo de arquivo não permitido.")
        try:
            content = base64.b64decode(body.content_base64, validate=True)
        except (binascii.Error, ValueError):
            raise HTTPException(status_code=422, detail="Conteúdo codificado inválido.") from None
        if not content or len(content) > config.max_upload_bytes:
            raise HTTPException(
                status_code=413, detail="Arquivo vazio ou maior que o limite de 2 MiB."
            )
        if body.media_type == "application/pdf" and not content.startswith(b"%PDF-"):
            raise HTTPException(status_code=422, detail="Assinatura PDF inválida.")
        if body.media_type == "image/png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
            raise HTTPException(status_code=422, detail="Assinatura PNG inválida.")
        if body.media_type in {"text/plain", "text/csv", "application/json"}:
            try:
                text = content.decode("utf-8")
                if body.media_type == "application/json":
                    json.loads(text)
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise HTTPException(status_code=422, detail="Conteúdo textual inválido.") from None
        decision = policy_check(user, "write", body.classification)
        if not decision["allowed"]:
            with transaction(config.database_path) as conn:
                append_event(
                    conn,
                    actor_id=user["id"],
                    action="vault.write",
                    resource_type="vault_file",
                    resource_id=None,
                    outcome="denied",
                    reason_code=str(decision["reason_code"]),
                )
            raise HTTPException(
                status_code=403, detail={"message": "Política negou a operação.", **decision}
            )
        file_id = str(uuid.uuid4())
        encrypted = Fernet(config.vault_key.encode("ascii")).encrypt(content)
        with transaction(config.database_path) as conn:
            conn.execute(
                "INSERT INTO vault_files(id,owner_id,filename,classification,media_type,ciphertext,created_at) VALUES(?,?,?,?,?,?,?)",
                (
                    file_id,
                    user["id"],
                    filename,
                    body.classification,
                    body.media_type,
                    encrypted,
                    utc_now(),
                ),
            )
            append_event(
                conn,
                actor_id=user["id"],
                action="vault.write",
                resource_type="vault_file",
                resource_id=file_id,
                outcome="success",
                reason_code=str(decision["reason_code"]),
            )
        return {
            "id": file_id,
            "filename": filename,
            "classification": body.classification,
            "encrypted": True,
            "decision": decision,
        }

    @app.get("/api/vault")
    def list_vault(user: dict = Depends(get_user)) -> list[dict]:
        conn = connect(config.database_path)
        try:
            rows = conn.execute(
                "SELECT id,owner_id,filename,classification,media_type,created_at FROM vault_files ORDER BY created_at DESC"
            ).fetchall()
            return [
                dict(row)
                for row in rows
                if policy_check(user, "read", row["classification"], row["owner_id"] == user["id"])[
                    "allowed"
                ]
            ]
        finally:
            conn.close()

    @app.get("/api/vault/{file_id}")
    def export_vault(file_id: str, user: dict = Depends(get_user)) -> dict:
        conn = connect(config.database_path)
        try:
            row = conn.execute("SELECT * FROM vault_files WHERE id=?", (file_id,)).fetchone()
        finally:
            conn.close()
        if row is None:
            raise HTTPException(status_code=404, detail="Recurso não encontrado.")
        decision = policy_check(
            user, "export", row["classification"], row["owner_id"] == user["id"]
        )
        if not decision["allowed"]:
            with transaction(config.database_path) as conn:
                append_event(
                    conn,
                    actor_id=user["id"],
                    action="vault.export",
                    resource_type="vault_file",
                    resource_id=file_id,
                    outcome="denied",
                    reason_code=str(decision["reason_code"]),
                )
            raise HTTPException(
                status_code=403, detail={"message": "Política negou a operação.", **decision}
            )
        try:
            plaintext = Fernet(config.vault_key.encode("ascii")).decrypt(row["ciphertext"])
        except InvalidCiphertext:
            raise HTTPException(
                status_code=500, detail="Não foi possível descriptografar o recurso."
            ) from None
        with transaction(config.database_path) as conn:
            append_event(
                conn,
                actor_id=user["id"],
                action="vault.export",
                resource_type="vault_file",
                resource_id=file_id,
                outcome="success",
                reason_code=str(decision["reason_code"]),
            )
        return {
            "id": file_id,
            "filename": row["filename"],
            "media_type": row["media_type"],
            "classification": row["classification"],
            "content_base64": base64.b64encode(plaintext).decode("ascii"),
            "decision": decision,
        }

    @app.post("/api/ai/evaluate")
    def evaluate_ai(body: AIEvaluation, user: dict = Depends(get_user)) -> dict:
        matches = {
            "email": bool(EMAIL_RE.search(body.prompt)),
            "cpf_like": bool(CPF_RE.search(body.prompt)),
            "credential_like": bool(SECRET_RE.search(body.prompt)),
        }
        sensitive = any(matches.values())
        if body.mode == "strict" and sensitive:
            safe_prompt = None
            outcome, reason = "denied", "AI_BLOCKED_SENSITIVE_PATTERN"
        else:
            safe_prompt = EMAIL_RE.sub("[EMAIL_REDACTED]", body.prompt)
            safe_prompt = CPF_RE.sub("[ID_REDACTED]", safe_prompt)
            safe_prompt = SECRET_RE.sub("[CREDENTIAL_REDACTED]", safe_prompt)
            outcome, reason = "success", "AI_SIMULATION_LOCAL_ONLY"
        event_id = str(uuid.uuid4())
        with transaction(config.database_path) as conn:
            append_event(
                conn,
                actor_id=user["id"],
                action="ai.evaluate",
                resource_type="ai_request",
                resource_id=event_id,
                outcome=outcome,
                reason_code=reason,
            )
        return {
            "request_id": event_id,
            "simulated": True,
            "external_provider_called": False,
            "allowed": outcome == "success",
            "sensitive_patterns": matches,
            "sanitized_prompt": safe_prompt,
            "result": "Simulação local: solicitação avaliada; nenhum modelo externo foi chamado."
            if outcome == "success"
            else None,
            "decision": {"reason_code": reason, "mode": body.mode},
        }

    @app.post("/api/assets", status_code=201)
    def create_asset(
        body: AssetCreate, user: dict = Depends(require_role("admin", "analyst"))
    ) -> dict:
        asset_id = str(uuid.uuid4())
        with transaction(config.database_path) as conn:
            conn.execute(
                "INSERT INTO assets(id,name,asset_type,criticality,owner,network_zone,notes,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (
                    asset_id,
                    body.name,
                    body.asset_type,
                    body.criticality,
                    body.owner,
                    body.network_zone,
                    body.notes,
                    utc_now(),
                ),
            )
            append_event(
                conn,
                actor_id=user["id"],
                action="asset.create",
                resource_type="asset",
                resource_id=asset_id,
                outcome="success",
                reason_code="AUTHORIZED_INVENTORY_ENTRY",
            )
        return {"id": asset_id, **body.model_dump(), "created_at": utc_now()}

    @app.get("/api/assets")
    def list_assets(user: dict = Depends(get_user)) -> list[dict]:
        conn = connect(config.database_path)
        try:
            return [
                dict(row)
                for row in conn.execute(
                    "SELECT id,name,asset_type,criticality,owner,network_zone,notes,created_at FROM assets ORDER BY name"
                ).fetchall()
            ]
        finally:
            conn.close()

    @app.get("/api/audit/events")
    def audit_events(user: dict = Depends(require_role("admin", "analyst"))) -> list[dict]:
        conn = connect(config.database_path)
        try:
            return [
                dict(row)
                for row in conn.execute(
                    "SELECT seq,timestamp,actor_id,action,resource_type,resource_id,outcome,reason_code,prev_hash,event_hash FROM audit_events ORDER BY seq DESC LIMIT 100"
                ).fetchall()
            ]
        finally:
            conn.close()

    @app.get("/api/assets/{asset_id}/review")
    def review_asset(asset_id: str, user: dict = Depends(get_user)) -> dict:
        conn = connect(config.database_path)
        try:
            row = conn.execute("SELECT * FROM assets WHERE id=?", (asset_id,)).fetchone()
        finally:
            conn.close()
        if row is None:
            raise HTTPException(status_code=404, detail="Recurso não encontrado.")
        recommendations = ["Confirmar responsável técnico e processo de atualização do inventário."]
        if row["criticality"] in {"high", "critical"}:
            recommendations.extend(
                [
                    "Revisar segmentação de rede e controle de acesso privilegiado.",
                    "Confirmar plano de backup e procedimento de recuperação testado.",
                    "Documentar monitoração defensiva e gestão de mudanças aplicáveis.",
                ]
            )
        return {
            "asset_id": asset_id,
            "assessment_type": "metadata_only_defensive_review",
            "criticality": row["criticality"],
            "findings": [],
            "recommendations": recommendations,
            "network_scanned": False,
            "certification": False,
            "scope": "Recomendações genéricas baseadas apenas nos metadados cadastrados; nenhuma configuração técnica foi verificada.",
        }

    @app.get("/api/audit/verify")
    def audit_verify(user: dict = Depends(require_role("admin"))) -> dict:
        return verify_ledger(config.database_path)

    @app.get("/api/dashboard")
    def dashboard(user: dict = Depends(get_user)) -> dict:
        conn = connect(config.database_path)
        try:
            counts = {
                "users": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
                "vault_files": conn.execute("SELECT COUNT(*) FROM vault_files").fetchone()[0],
                "assets": conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0],
                "audit_events": conn.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0],
            }
            recent = [
                dict(row)
                for row in conn.execute(
                    "SELECT seq,timestamp,action,outcome,reason_code FROM audit_events ORDER BY seq DESC LIMIT 10"
                ).fetchall()
            ]
        finally:
            conn.close()
        return {
            "service": "operational",
            "demo_scope": True,
            "counts": counts,
            "ledger_integrity": verify_ledger(config.database_path),
            "recent_events": recent,
            "disclaimer": "Indicadores demonstrativos; não são certificação nem avaliação de conformidade.",
        }

    @app.get("/", include_in_schema=False)
    def dashboard_page() -> FileResponse:
        static_dir = Path(__file__).parent / "static"
        return FileResponse(static_dir / "index.html")

    @app.get("/static/app.js", include_in_schema=False)
    def dashboard_script() -> FileResponse:
        return FileResponse(
            Path(__file__).parent / "static" / "app.js", media_type="text/javascript"
        )

    @app.get("/static/style.css", include_in_schema=False)
    def dashboard_styles() -> FileResponse:
        return FileResponse(Path(__file__).parent / "static" / "style.css", media_type="text/css")

    return app


app = create_app()

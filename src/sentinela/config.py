from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from cryptography.fernet import Fernet


@dataclass(frozen=True)
class Settings:
    database_path: str
    token_secret: str
    vault_key: str
    bootstrap_username: str | None = None
    bootstrap_password: str | None = None
    environment: str = "development"
    max_upload_bytes: int = 2 * 1024 * 1024

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            database_path=os.getenv("SENTINELA_DATABASE_PATH", "./data/sentinela.db"),
            token_secret=os.getenv("SENTINELA_TOKEN_SECRET", ""),
            vault_key=os.getenv("SENTINELA_VAULT_KEY", ""),
            bootstrap_username=os.getenv("SENTINELA_BOOTSTRAP_ADMIN_USERNAME"),
            bootstrap_password=os.getenv("SENTINELA_BOOTSTRAP_ADMIN_PASSWORD"),
            environment=os.getenv("SENTINELA_ENV", "development"),
        )

    def validate(self) -> None:
        if len(self.token_secret.encode("utf-8")) < 32:
            raise ValueError("SENTINELA_TOKEN_SECRET precisa ter pelo menos 32 bytes.")
        try:
            Fernet(self.vault_key.encode("ascii"))
        except (ValueError, TypeError, UnicodeEncodeError) as exc:
            raise ValueError("SENTINELA_VAULT_KEY não é uma chave Fernet válida.") from exc
        if self.max_upload_bytes < 1 or self.max_upload_bytes > 10 * 1024 * 1024:
            raise ValueError("Limite de upload inválido; o máximo permitido é 10 MiB.")

    def ensure_database_directory(self) -> None:
        Path(self.database_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

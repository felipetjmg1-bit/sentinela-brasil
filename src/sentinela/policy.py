from __future__ import annotations

from dataclasses import dataclass

# Regras explícitas e versionadas: sem permissões implícitas por ausência de regra.
POLICY_VERSION = "sentinela-demo-1"
CLASSIFICATIONS = ("public", "internal", "confidential", "restricted")
ACTIONS = ("read", "write", "export")
RULES = (
    {
        "id": "admin-full",
        "role": "admin",
        "classifications": list(CLASSIFICATIONS),
        "actions": list(ACTIONS),
    },
    {
        "id": "analyst-operational",
        "role": "analyst",
        "classifications": ["public", "internal"],
        "actions": ["read", "write", "export"],
    },
    {
        "id": "viewer-public-read-export",
        "role": "viewer",
        "classifications": ["public"],
        "actions": ["read", "export"],
    },
)


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason_code: str
    policy_version: str = POLICY_VERSION

    def as_dict(self) -> dict[str, str | bool]:
        return {
            "allowed": self.allowed,
            "reason_code": self.reason_code,
            "policy_version": self.policy_version,
        }


def decide(role: str, action: str, classification: str, *, owner: bool = True) -> Decision:
    if action not in ACTIONS or classification not in CLASSIFICATIONS:
        return Decision(False, "DENY_INVALID_REQUEST")
    if not owner and role != "admin" and classification != "public":
        return Decision(False, "DENY_NOT_OWNER")
    for rule in RULES:
        if (
            rule["role"] == role
            and action in rule["actions"]
            and classification in rule["classifications"]
        ):
            return Decision(True, f"ALLOW_{rule['id'].upper().replace('-', '_')}")
    return Decision(False, "DENY_NO_MATCHING_RULE")

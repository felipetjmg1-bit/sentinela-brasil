# Security validation plan

## Current declared state
Local FastAPI prototype with user authentication, role fields, encrypted vault storage and a hash-linked audit ledger. This is a prototype, not a production security certification or a deployed critical-infrastructure system.

## Local reproduction
Use Python 3.11:

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install pytest httpx
python -m pytest -q
```

Configure bootstrap credentials and encryption/signing material only through environment variables or a secret manager. Never commit production secrets or real personal data.

## Required security gates
- [ ] Verify authorization on every sensitive route, not only authentication.
- [ ] Verify bootstrap is disabled or tightly controlled after first initialization.
- [ ] Validate password policy, token expiry, signature, issuer/audience and revocation strategy.
- [ ] Document key generation, storage, rotation, backup, recovery and destruction.
- [ ] Test Fernet key loss, invalid ciphertext, tampering and restore procedures.
- [ ] Test ledger ordering, concurrent writes, truncation, replay and deletion/tampering detection.
- [ ] Enforce upload size/type/content validation and safe file handling.
- [ ] Review PII detection/redaction limits; do not represent regex detection as complete anonymization.
- [ ] Configure TLS, trusted hosts, CORS, rate limiting, logging redaction and production deployment controls.
- [ ] Run dependency audit and static analysis; record findings and remediation.
- [ ] Run tests in GitHub Actions and inspect the actual run result.

## Evidence record
A CI workflow and this validation plan have been added. Their presence is not proof of passing tests. Do not deploy with real personal, financial, health or government data until an independent security review and operational controls are completed.

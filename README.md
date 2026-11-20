# Sentinela Brasil
**[MVP FUNCIONAL · DEMONSTRATIVO]** · Python · FastAPI · SQLite · Fernet · RBAC · Licença Apache-2.0

Plataforma local de demonstração de governança de dados e controles defensivos. Implementa autenticação básica, políticas de acesso, vault cifrado, trilha de auditoria encadeada e um gateway de IA simulado. É uma base de experimentação, não uma solução certificada ou pronta para infraestrutura crítica.

## Funcionalidades presentes
- API FastAPI e interface web local.
- Identidade, tokens bearer, RBAC e política *default deny*.
- Vault local com criptografia Fernet e limites de upload.
- Ledger de auditoria encadeado por SHA-256.
- Gateway demonstrativo com detecção heurística/redação de padrões.
- SQLite, testes e documentação de arquitetura, privacidade e modelo de ameaças.

## Executar em ambiente local
Requer Python 3.11 ou superior. Docker Compose é opcional.

```bash
git clone https://github.com/felipetjmg1-bit/sentinela-brasil.git
cd sentinela-brasil
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e '.[test,dev]'
cp .env.example .env
```

Gere valores exclusivos para as variáveis do arquivo `.env`. Os comandos abaixo produzem valores de exemplo, que devem ser inseridos localmente:
```bash
python -c 'import secrets; print(secrets.token_urlsafe(48))'
python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
python -c 'import secrets; print(secrets.token_urlsafe(24))'
```
Carregue as variáveis e inicie somente em loopback:
```bash
set -a; . ./.env; set +a
uvicorn sentinela.main:app --app-dir src --host 127.0.0.1 --port 8000
```
Consulte `docs/deployment/DEPLOYMENT.md` para opções e cuidados adicionais.

## Exemplo prático
O repositório contém uma requisição sintética em `examples/synthetic_ai_request.json`. Verifique a saúde da API:
```bash
curl http://127.0.0.1:8000/health
```
Consulte `docs/architecture/ARCHITECTURE.md` para os fluxos e endpoints implementados.

## Testes
```bash
pytest
ruff check .
```

## Segurança, privacidade e limitações
- O ledger encadeado detecta alterações; não equivale a armazenamento imutável ou prova criptográfica externa.
- O gateway de IA é simulado e não chama modelo externo.
- A detecção de dados sensíveis é heurística e não garante identificação ou anonimização completa.
- A versão é direcionada a processo local e banco SQLite; não execute múltiplos workers nem a exponha publicamente sem revisão de segurança.
- Use segredos próprios, proteja o arquivo `.env`, remova credenciais de bootstrap após o primeiro uso e não versione dados reais.
- Para LGPD: documente finalidade e base legal, minimize dados, limite retenção, proteja credenciais e estabeleça atendimento aos titulares.

## Documentação
Arquitetura: `docs/architecture/ARCHITECTURE.md` · Modelo de ameaças: `docs/threat-model/THREAT_MODEL.md` · Privacidade: `docs/privacy/PRIVACY.md` · Validação: `docs/VALIDATION.md`.

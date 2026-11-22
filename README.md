# Sentinela Brasil

**[Protótipo funcional / demonstração local]** API FastAPI e painel web para demonstrar controles de governança de dados, autorização, armazenamento cifrado e auditoria. **Não é solução de produção nem mecanismo homologado para infraestrutura crítica.**

## Problema e objetivo

O projeto demonstra, em ambiente local, como estruturar políticas de acesso, proteger arquivos armazenados, registrar operações e inspecionar entradas destinadas a um gateway de IA simulado. O contexto de aplicação é a pesquisa brasileira em soberania de dados, segurança defensiva e governança de IA.

## Capacidades implementadas

- API FastAPI e painel web estático servido pela aplicação.
- Autenticação local com tokens bearer e papéis demonstrativos.
- Regras de autorização com negação por padrão.
- Vault local com criptografia Fernet.
- Ledger de auditoria encadeado por hash SHA-256.
- Gateway de avaliação/redação heurística, sem chamada a modelo externo.
- Inventário manual de ativos sintéticos.
- Testes em `tests/`, documentação de arquitetura, privacidade, implantação e modelo de ameaças.

## Como executar

Requisitos: Python 3.11 ou superior.

```bash
git clone https://github.com/felipetjmg1-bit/sentinela-brasil.git
cd sentinela-brasil
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -e ".[test]"
```

Gere valores locais próprios para os segredos, em vez de reutilizar os exemplos:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Configure no ambiente `SENTINELA_TOKEN_SECRET`, `SENTINELA_VAULT_KEY`, `SENTINELA_DATABASE_PATH`, `SENTINELA_BOOTSTRAP_ADMIN_USERNAME` e `SENTINELA_BOOTSTRAP_ADMIN_PASSWORD`. A senha inicial deve ter pelo menos 16 caracteres. Use os nomes e requisitos descritos em `.env.example` e `src/sentinela/config.py`. Não versione um arquivo `.env` real.

Inicie a API:

```bash
PYTHONPATH=src uvicorn sentinela.main:create_app --factory --host 127.0.0.1 --port 8000
```

Abra `http://127.0.0.1:8000`. A documentação OpenAPI fica em `/docs`, se habilitada pela configuração da aplicação.

## Exemplo prático

O repositório inclui `examples/synthetic_ai_request.json` como entrada sintética para a avaliação do gateway. Para verificar a disponibilidade da API:

```bash
curl http://127.0.0.1:8000/health
```

Consulte `docs/VALIDATION.md` e `tests/` para os contratos e verificações existentes. Os exemplos não constituem validação de segurança independente.

## Estrutura

- `src/sentinela/`: API, políticas, autenticação, banco, auditoria e interface estática.
- `tests/`: testes automatizados.
- `docs/`: arquitetura, implantação, privacidade, ameaças e validação.
- `examples/`: dados sintéticos.
- `.env.example`: nomes e formatos de configuração sem credenciais válidas.
- `pyproject.toml`: dependências e configuração de desenvolvimento.
- `Dockerfile` e `docker-compose.yml`: empacotamento demonstrativo.

## Segurança, privacidade e limitações

- O padrão é uso local com dados sintéticos. Não utilize dados pessoais, sensíveis ou sigilosos sem análise jurídica, base legal, controles e avaliação de risco.
- SQLite local, processo único e ausência de alta disponibilidade/multi-tenant.
- Não há KMS/HSM, rotação automatizada de chaves, WORM, âncora externa ou revogação individual de tokens.
- A detecção de dados pessoais e segredos é heurística; pode falhar. O gateway é simulado e não chama LLM externo.
- O ledger detecta determinadas alterações, mas não é imutável contra quem controla o host e o banco.
- Não há alegação de certificação, homologação, adoção governamental ou proteção de infraestrutura crítica.
- Antes de qualquer uso real, faça revisão independente, teste de intrusão autorizado, gestão de chaves, backup/restore, TLS, monitoramento e avaliação LGPD.

## Testes

```bash
pytest -q
```

A existência dos testes não significa que tenham sido executados nesta PR. Consulte `docs/VALIDATION.md` para o histórico documentado.

## Licença

Apache-2.0. Consulte [LICENSE](LICENSE).


## Validação e segurança

- [Plano de validação de segurança](docs/SECURITY-VALIDATION-PLAN.md)
- [Workflow CI de API e segurança](.github/workflows/portfolio-ci.yml)

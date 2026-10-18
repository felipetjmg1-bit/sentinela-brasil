# Registro de validação — 2026-10-18

Este registro relata apenas verificações executadas na sessão de construção. Não é certificação, auditoria independente ou garantia de segurança.

| Verificação | Comando/ambiente | Resultado observado |
|---|---|---|
| Inicialização e integração | `pytest -q` no Python 3.12.3, aplicação FastAPI/SQLite em banco temporário | 13 testes passaram, sem falhas e sem avisos de teste na última execução |
| Formatação | `ruff format --check .` | passou; 20 arquivos já formatados |
| Lint | `ruff check .` | passou; sem problemas reportados |
| Dependências | `pip-audit --skip-editable` | nenhuma vulnerabilidade conhecida reportada na verificação; o pacote local editável é deliberadamente excluído, enquanto as dependências instaladas são auditadas |
| SBOM | `pip-audit --skip-editable --format cyclonedx-json --output sbom.cdx.json` | JSON válido, CycloneDX, 59 componentes; o artefato é um inventário de dependências daquele ambiente, não uma prova de segurança |
| Smoke HTTP | Uvicorn em `127.0.0.1` com segredos efêmeros e banco temporário | `/api/health` respondeu `{"status":"ok","version":"0.1.0"}`; página `/`, JavaScript e CSS retornaram HTTP 200 |
| Sintaxe Python | `python3 -m py_compile src/sentinela/*.py tests/*.py` | passou |
| Docker/Compose | verificação de disponibilidade local | não executado: comando `docker` não está instalado no ambiente de construção |

## Cobertura dos 13 testes

Os testes exercitam autenticação e senha incorreta, promoção de papel negada, token com assinatura e validade, criptografia de arquivo antes da persistência e exportação autorizada, isolamento por objeto, listagem/exportação pública versus dados internos, rejeição de nome/tipo inválido, bloqueio e redação do gateway sem chamada externa, ausência do prompt nos eventos, detecção de alteração do ledger, gestão e revisão de ativos, painel e cabeçalhos de segurança.

Durante desenvolvimento, um teste inicialmente falhou porque a regra de propriedade bloqueava também itens com classificação `public`. A condição foi corrigida para abrir a exceção somente a recursos públicos; o teste foi mantido para evitar regressão. A primeira auditoria também sinalizou versões antigas de `cryptography` e `pytest` no ambiente. Os limites de dependência foram atualizados para versões corrigidas disponíveis e a execução final do `pip-audit` não reportou vulnerabilidades conhecidas.

## Limitações da evidência

O teste de integração usa `TestClient` e não substitui revisão de segurança ou prova de operação em todos os sistemas suportados. A checagem de dependências é uma fotografia temporal. A inicialização de Docker não pôde ser testada; o serviço efetivamente testado foi Uvicorn local. GitHub Actions será executado após publicação do workflow no repositório; seu resultado remoto deve ser registrado quando disponível.

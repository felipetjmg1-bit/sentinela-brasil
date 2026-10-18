# Modelo de ameaças — v0.1.0

## Contexto e escopo

Aplicação demonstrativa local, um processo Uvicorn, banco SQLite e dados exclusivamente sintéticos. O modelo orienta revisão; não é certificação nem auditoria formal. O ambiente operacional/host está fora da garantia do software.

## Ativos a proteger

1. Conteúdo de arquivos enviados ao Vault.
2. Senhas, chave Fernet e segredo HMAC.
3. Identidade, permissões e tokens de sessão.
4. Integridade e disponibilidade do banco/ledger.
5. Metadados de arquivos, ativos e eventos.

## Adversários e ameaças

| Ameaça | Controle implementado | Risco residual |
|---|---|---|
| Usuário sem token acessa API | HTTP bearer e respostas 401 | Rate limit robusto e monitoramento não implementados |
| Usuário tenta elevar papel | Papel só é definido no cadastro administrativo | Conta admin comprometida permite abuso |
| IDOR/leitura de arquivo alheio | Verificação de proprietário na regra, exceto admin | Revisão adicional de cada nova rota necessária |
| Viewer tenta gravar/exportar classificação não permitida | Policy engine default-deny e matriz papel/classe/ação | Regras são fixas no código, não há editor versionado |
| Dump de SQLite revela plaintext de arquivos | Fernet cifra o conteúdo binário antes de salvar | Metadados ficam legíveis; chave/host não protegidos se comprometidos |
| Upload malformado/tipo inadequado/arquivo grande | Base64 validado, limite 2 MiB, lista MIME, verificação PDF/PNG e JSON/UTF-8 | MIME pode ser falsificado para formatos não conferidos; não há antivírus nem parser profundo |
| Alteração de um evento | Recalcular encadeamento SHA-256 detecta alteração/reordenação parcial | Controlador da base pode reescrever cadeia completa ou rollback do arquivo |
| Dados sensíveis enviados ao gateway | Strict bloqueia padrões identificados; redact mascara ocorrências; não há saída para rede | Regex pode deixar escapar padrões desconhecidos; usuário pode inserir texto não identificado |
| XSS persistente no painel | Dados renderizados via `textContent`, CSP sem scripts inline | Outros navegadores/dependências/configurações podem alterar risco; UI é demonstrativa |
| Exposição do serviço na LAN/Internet | Instruções e Compose usam loopback | Operador pode reconfigurar interface; TLS/firewall não embutidos |
| Perda de banco ou chave | Procedimentos manuais documentados | Backup/restore automatizado e rotação ainda não implementados |
| DoS por requisições repetidas | Limites Pydantic e de corpo parcial | Sem rate limit distribuído, quotas ou limites por usuário robustos |

## Controles e premissas

- Autenticação e autorização no servidor; a UI não é fronteira de segurança.
- Nunca armazenar o plaintext enviado ao Vault; evitar conteúdo sensível em logs/ledger.
- Falta de regra aplicável resulta em negação.
- Erros não retornam stack trace nem configuração.
- A chave criptográfica e segredo de token vêm do ambiente, não do repositório.
- Dados de exemplo devem ser sintéticos.

## Não-objetivos

Nenhuma descoberta ou varredura de rede, exploração, pentest automático, malware, execução de comandos, acesso a sistemas de terceiros, vigilância clandestina, classificação automática completa, modelo de IA real, decisão de missão crítica, compliance automático ou defesa contra host comprometido.

## Risco residual e validação necessária

Antes de uso real: revisão independente de código; threat modeling por domínio; migrações e atualização de esquema; testes fuzz/limites/corrida; revogação e expiração revisadas; rate limiting; KMS/HSM e rotação; TLS/proxy; logs/alertas; backup criptografado e restore ensaiado; controle de acesso ao host; avaliação jurídica/privacidade e teste de segurança autorizado. Nenhuma dessas validações é afirmada como concluída nesta versão.

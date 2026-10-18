# Arquitetura e fluxo de dados

## Componentes v0.1

```mermaid
flowchart TB
  U[Pessoa operadora] --> UI[Browser: UI estática local]
  UI -->|Bearer token| API[FastAPI / Uvicorn, 1 processo]
  API --> AUTH[Autenticação scrypt + HMAC bearer]
  AUTH --> DB[(SQLite local, WAL)]
  API --> PEP[Policy enforcement point]
  PEP --> PDP[Regras declarativas RBAC / classificação]
  PDP --> VAULT[Serviço Vault: Fernet]
  PDP --> AUDIT[Ledger SHA-256 encadeado]
  API --> AI[Gateway demonstrativo: local, sem rede externa]
  API --> INV[Inventário manual e sintético]
  VAULT --> DB
  AUDIT --> DB
  INV --> DB
  KEY[Variáveis de ambiente externas ao banco] --> AUTH
  KEY --> VAULT
```

## Fluxo de upload e exportação

```mermaid
sequenceDiagram
  actor U as Operador
  participant API as FastAPI
  participant PDP as Policy Engine
  participant DB as SQLite
  participant ENC as Fernet
  U->>API: Login e token bearer
  U->>API: Upload JSON/Base64 + classificação
  API->>API: Validar nome, MIME, assinatura e limite
  API->>PDP: decide(role, write, classification)
  PDP-->>API: allowed + reason_code + version
  alt permitido
    API->>ENC: Cifrar bytes
    ENC-->>API: ciphertext
    API->>DB: Gravar ciphertext + evento auditável
    API-->>U: ID e decisão (sem plaintext)
  else negado
    API->>DB: Registrar decisão negada sem conteúdo
    API-->>U: 403 + motivo técnico
  end
  U->>API: GET export/{id}
  API->>PDP: validar ação e propriedade do recurso
  API->>DB: Ler ciphertext
  API->>ENC: Descriptografar após autorização
  API-->>U: Conteúdo Base64 autorizado + evento
```

## Limites de confiança

- Browser e cliente são não confiáveis; o token bearer dá acesso equivalente à conta durante até uma hora.
- O processo, host, SQLite e variáveis de ambiente são confiados operacionalmente. Comprometimento do host permite leitura de memória/segredos e reescrita da base.
- O arquivo do banco contém ciphertext Fernet para conteúdo, mas nomes, classificação, tipos, IDs e timestamps são metadados legíveis.
- O gateway não chama rede e devolve somente resposta fixa; seus filtros por padrões são demonstração, não DLP completa.
- O inventário recebe dados fornecidos diretamente; não executa descoberta nem valida configuração remota.

## Persistência e concorrência

SQLite ativa `foreign_keys`, `busy_timeout` e WAL. O projeto deve executar com um worker. SQLite permite concorrência limitada e não é adequado para múltiplos nós/alta disponibilidade. Ledger e alteração de estado são gravados na mesma transação para operações principais. Para uma carga maior, migre após desenho e revisão, não apenas trocando a URL.

## Criptografia

- Senhas: `hashlib.scrypt` da biblioteca padrão com salt aleatório por usuário e parâmetros codificados no hash.
- Tokens: payload local assinado com HMAC-SHA256 e expiração de uma hora; formato privado do projeto, não JWT interoperável.
- Arquivos: Fernet da biblioteca `cryptography`, chave base64 URL-safe injetada por ambiente. Fernet cifra e autentica bytes, mas não substitui KMS/HSM nem protege contra comprometimento do processo.
- Ledger: SHA-256 do JSON canonicalizado. Uma cadeia recalculada ou removida integralmente pelo controlador do banco não é detectada sem âncora externa.

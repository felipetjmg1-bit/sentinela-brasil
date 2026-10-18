# Segurança e reporte responsável

Este projeto é um demonstrador local em estágio inicial, não um produto homologado nem adequado para proteger dados críticos em produção. Não envie vulnerabilidades com dados pessoais, segredos reais, sistemas governamentais restritos ou informações de terceiros.

## Como reportar

Abra um reporte privado de segurança no GitHub (Security → Advisories → Report a vulnerability) ou contate o mantenedor por um canal institucional publicado no perfil/organização do repositório. Inclua versão, impacto, pré-condições e passos de reprodução com ambiente e dados sintéticos. Não publique detalhes exploráveis antes de uma correção coordenada.

## Escopo

São relevantes: bypass de autenticação/autorização, exposição de plaintext, falha no tratamento de chaves, corrupção silenciosa de auditoria, vulnerabilidades de dependência e injeção no painel. Não teste sistemas externos nem infraestrutura de terceiros. A plataforma não deve ser usada para exploração, varredura não autorizada ou coleta clandestina.

## Limitações conhecidas

A primeira versão usa um segredo HMAC e uma chave Fernet configurados pelo operador, tokens bearer de uma hora, SQLite local e controle simples de tentativas. Não há rate limiting robusto distribuído, revogação individual de token, KMS/HSM, rotação automatizada de chaves, segregação de tenant, WORM, âncora externa do ledger, TLS embutido, backup gerenciado nem validação independente. A cadeia de hashes detecta alterações inconsistentes quando verificada; alguém com controle do banco e da máquina pode reescrever a cadeia inteira.

Consulte `docs/threat-model/THREAT_MODEL.md` antes de qualquer teste ou avaliação.

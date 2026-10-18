# Implantação local, backup e recuperação

## Execução

Prefira loopback (`127.0.0.1`), um único processo e ambiente virtual isolado. Configure `SENTINELA_TOKEN_SECRET` (mín. 32 bytes) e chave válida de Fernet. Crie administrador somente no primeiro start com `SENTINELA_BOOTSTRAP_ADMIN_*`; remova senha de bootstrap do ambiente após o primeiro cadastro. Não comite `.env`, database ou tokens.

Docker Compose liga a aplicação em `127.0.0.1:8000` no host. Isso reduz exposição acidental, mas não substitui firewall nem revisão. Se for necessário acesso de outros dispositivos, exigir TLS num proxy, firewall, autenticação e revisão prévia; v0.1 não foi preparada como serviço público.

## Backup

1. Pare o serviço para obter snapshot simples e consistente do arquivo SQLite (incluindo tratamento de `-wal`/`-shm`), ou use mecanismo SQLite de backup com validação.
2. Cifre e controle acesso ao backup segundo política organizacional.
3. Guarde `SENTINELA_VAULT_KEY` e `SENTINELA_TOKEN_SECRET` separadamente, em cofre apropriado. Perder a chave Fernet torna o conteúdo irrecuperável; não coloque chave junto do backup.
4. Registre data, versão do app e procedimento, sem publicar chaves.
5. Em ambiente temporário, restaure banco e chaves e confirme login, exportação autorizada e `/api/audit/verify`. O repositório não automatiza nem certifica esse exercício.

## Recuperação

Restaure a cópia íntegra e compatível, confirme permissões do arquivo e chaves corretas antes de voltar a aceitar dados. Se houve suspeita de adulteração, preserve cópia forense antes de reiniciar/escrever; compare a integridade do ledger com âncoras externas se existirem. Nesta versão, não há âncora externa implementada.

## Exclusão

Pare a aplicação, remova base local e backups conforme retenção, inclusive cópias de snapshots e volumes Docker. Apagar o arquivo não garante sobrescrita física em SSD, snapshots ou storage remoto. A aplicação não fornece função de exclusão seletiva nem atesta apagamento seguro.

## Operação e atualizações

Mantenha Python/OS e dependências atualizados, rode `pip-audit`, revise lock/dependências e CI antes de atualizar. Não rode multiworker com SQLite. Faça backup antes de atualização; este primeiro release não contém sistema de migrações.

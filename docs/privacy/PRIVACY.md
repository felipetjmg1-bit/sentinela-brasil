# Privacidade e minimização

## Princípios aplicados

A demonstração minimiza dados no ledger e não registra corpo de upload, senha, token nem prompt do gateway. O arquivo é cifrado antes de persistir; nome do arquivo, tipo, classificação, proprietário, horário e identificador permanecem como metadados em SQLite. Eventos guardam ator, ação, recurso, resultado e código de motivo, sem conteúdo de arquivo.

O gateway aplica padrões heurísticos para e-mail, CPF-like e strings de credencial. No modo `strict`, um padrão identificado causa bloqueio e a entrada não é devolvida; no modo `redact`, o resultado informa o prompt mascarado. Isto não é DLP completa, não garante anonimização e não deve receber dados reais.

## Dados de demonstração

Use somente nomes, documentos e ativos inventados. Os exemplos no projeto são sintéticos. Não insira dados governamentais, pessoais, sigilosos, credenciais, chaves ou informação proprietária real.

## Retenção, exportação e exclusão

A v0.1.0 não implementa expiração automática, exclusão individual do Vault ou política de retenção configurável. Exclusão manual deve ocorrer com o serviço parado e após backup conforme obrigação do operador: apague o registro/arquivo de banco e remova cópias de segurança segundo a política local. A remoção lógica pode não apagar imediatamente páginas de WAL, backups ou snapshots; para dados reais, projete ciclo de vida e apagamento seguro antes da ingestão.

Exportação do arquivo é autorizada por política e gera evento. Exporte somente se necessário e guarde o resultado conforme controles locais.

## Direitos e obrigações

Este software não determina base legal, controlador/operador, prazo legal, transferência internacional, retenção setorial ou conformidade LGPD. Organizações devem fazer avaliação jurídica e de impacto própria antes de uso com dados pessoais.

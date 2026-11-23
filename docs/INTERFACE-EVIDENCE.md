# Evidências reais de execução e interface

## Escopo

O workflow instala o pacote e dependências de teste, cria segredos efêmeros exclusivos do runner, executa a suíte de testes, inicia a aplicação FastAPI com banco SQLite temporário e realiza login no painel web servido pela própria aplicação. O Playwright captura as interfaces desktop e mobile após autenticação.

## O que comprova quando o workflow termina com sucesso

- Instalação do projeto no runner Python 3.12.
- Testes automatizados existentes aprovados naquele ambiente.
- Inicialização real da aplicação FastAPI.
- Login de demonstração e carregamento do painel autenticado.
- Capturas reais do painel desktop e mobile, salvas como artefato.
- Uso de credenciais e chaves efêmeras de CI, sem reutilizar segredos de produção.

## O que não comprova

- Segurança independente, certificação, homologação ou prontidão para infraestrutura crítica.
- Implantação pública, alta disponibilidade, multi-tenancy, KMS/HSM ou gestão operacional de chaves.
- Resistência a todos os ataques ou conformidade LGPD.
- Validação de integração com sistemas externos.

O painel e os dados deste workflow são de demonstração. O artefato não deve ser interpretado como evidência de produção.

# MARKYS — Controle de Folgas

Aplicativo desktop local para Windows, independente do Laravel, com interface própria, logo personalizado preto/prata/dourado e banco de dados no próprio computador. Usa Python/FastAPI internamente e abre em uma janela desktop via Microsoft Edge WebView2 Runtime; não exige abrir uma aba comum do navegador. O projeto Laravel original não é alterado nem é necessário para executar o MARKYS.

## Recursos
- Cadastro de funcionários e campos funcionais.
- Tipos de folga, concessões, validade, saldo, agendamentos e limites por categoria.
- Histórico filtrável, exportação CSV e trilha de auditoria.
- Login por CPF ou conta administrativa, cadastro público com perfil Consulta, opção de lembrar o CPF e alteração da senha administrativa dentro do aplicativo.
- SQLite local no próprio computador; não exige configuração de rede.
- Backup e ferramentas de importação de dados do Laravel.
- CI para testes, empacotamento Windows e geração do instalador.

## Instalar no Windows
1. Abra [GitHub Actions](https://github.com/danielmarkpsn-pixel/MARKYS-CONTROLE-DE-FOLGAS/actions).
2. Na execução mais recente concluída com sucesso, baixe o artefato **MARKYS-Controle-de-Folgas-Setup**.
3. Execute o instalador e abra o atalho **MARKYS - Controle de Folgas**.
4. Na instalação limpa, entre com usuário `admin` e senha `admin`. Dentro do aplicativo, abra **Usuários** e use **Minha conta de administrador** para trocar a senha. A senha é armazenada no banco somente como hash.
5. Na tela de login, selecione **Registre-se aqui** para criar uma conta com CPF e senha. Essas contas começam com perfil **Consulta**; somente um administrador pode conceder privilégios administrativos.
6. Para recuperar o acesso administrativo, feche o MARKYS e abra no menu Iniciar **MARKYS - Recuperar acesso**. O procedimento redefine a conta para `admin` / `admin` e preserva os dados cadastrados.

## Aplicativo desktop local
- O MARKYS abre em uma janela própria. O backend e o banco SQLite são executados no próprio computador.
- O serviço interno escuta somente em `127.0.0.1:8000`; não é necessário liberar a porta no firewall nem expor o sistema à rede.
- É necessário ter o **Microsoft Edge WebView2 Runtime**, normalmente presente no Windows 11. Se a janela não abrir, instale ou atualize esse runtime.
- Configuração: `%LOCALAPPDATA%\MARKYS\.env`.
- Banco de dados: `%LOCALAPPDATA%\MARKYS\markys_folgas.db`.
- O banco e a configuração ficam fora da pasta de instalação e são preservados durante atualizações e desinstalação.

## Desenvolvimento no Windows 11
1. Instale Python 3.11+.
2. Baixe ou clone o repositório.
3. Execute `powershell -ExecutionPolicy Bypass -File .\scripts\install-windows.ps1`.
4. Use o atalho criado para iniciar o MARKYS.

## Importação de dados Laravel
O importador `scripts/import-laravel-sqlite.py` valida a cópia antes de gravar. O ZIP de exemplo enviado anteriormente não contém necessariamente os dados operacionais preenchidos de funcionários, tipos, créditos e histórico; use um backup real do banco Laravel já migrado. O importador não transfere contas nem senhas do Laravel. As tabelas de saúde do exemplo não são importadas indiscriminadamente.

## Testes e validação
O GitHub Actions verifica JavaScript, compila Python, executa testes de API/regras e tenta empacotar e testar o executável Windows antes de publicar o instalador.

Consulte também:
- `docs/USO-INSTALADOR.md`
- `docs/INSTALACAO-WINDOWS.md`
- `docs/IMPORTACAO-LARAVEL.md`

## Cuidados com os dados
- Faça backup regular de `markys_folgas.db` e `.env`.
- Não envie banco, `.env`, logs ou backups ao GitHub; podem conter dados pessoais.
- Antes de usar dados reais, teste cadastro, concessão, agendamento, saldo, histórico e restauração de backup.

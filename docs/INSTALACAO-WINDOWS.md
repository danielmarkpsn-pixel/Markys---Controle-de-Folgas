# Instalação e operação no Windows 11

## 1. Instalação local (um computador)
1. Instale Python 3.11 ou superior (marque a opção para adicionar Python ao PATH).
2. Baixe/clonе este repositório para uma pasta permanente, por exemplo `C:\\MARKYS`.
3. Abra a pasta e execute `scripts\\install-windows.ps1` no PowerShell. Se necessário: `powershell -ExecutionPolicy Bypass -File .\\scripts\\install-windows.ps1`.
4. O instalador cria o ambiente Python, instala dependências, gera uma chave secreta e uma senha inicial aleatória e cria um atalho na área de trabalho. Anote a senha que aparece no console.
5. Abra o atalho **MARKYS - Controle de Folgas** e acesse `http://127.0.0.1:8000`.
6. Entre como `admin` com a senha apresentada pelo instalador. Crie os usuários individuais na aba Usuários e não compartilhe a conta administrativa.

O instalador não sobrescreve um `.env` já existente. Guarde esse arquivo com acesso restrito. Se perder a senha inicial, um administrador existente pode redefini-la na aba Usuários.

## 2. Inicialização automática ao entrar no Windows
Execute `scripts\\install-login-task.ps1` no PowerShell do usuário que manterá o aplicativo. A tarefa inicia o backend ao entrar no Windows, sem abrir o console na tela. O backend continua escutando somente em `127.0.0.1:8000`. O log fica em `logs\\server.log`.

## 3. Uso local recomendado
Esta instalação deve ser usada no próprio computador onde o MARKYS está instalado. O backend escuta somente em `127.0.0.1:8000`; não altere para `0.0.0.0`, não abra a porta no firewall e não encaminhe portas do roteador.

O banco SQLite fica em `%LOCALAPPDATA%\MARKYS\markys_folgas.db`, e a configuração em `%LOCALAPPDATA%\MARKYS\.env`. Ambos ficam fora da pasta do programa para que atualizações preservem os dados.

Para manter a instalação simples, não é necessário instalar PostgreSQL ou Caddy para uso local.

## 4. Backup e restauração
- Execute `scripts\\backup-windows.bat` para gerar backup consistente do banco SQLite local.
- O script usa a API de backup do SQLite e remove backups com mais de 30 dias da pasta `backups`.
- Mantenha uma segunda cópia segura fora do computador. Backups podem conter dados pessoais e nunca devem ir para o GitHub.
- Teste a restauração periodicamente em um banco separado; um arquivo de backup que nunca foi restaurado ainda não está validado.

## Limites desta etapa
- O atalho e a tarefa agendada estão preparados, mas precisam ser executados no Windows de destino.
- O ZIP de exemplo não contém as tabelas de dados `funcionarios`, `folgas`, `tipos_folgas` e `historico_folgas` no SQLite incluído. Para migrar dados reais, é necessário um backup real do banco Laravel já migrado e preenchido.

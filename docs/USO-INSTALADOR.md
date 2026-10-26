# Guia do aplicativo desktop Windows — MARKYS

## Primeiro uso
1. Execute `MARKYS-Controle-de-Folgas-Setup.exe` e conclua a instalação.
2. Abra o atalho **MARKYS - Controle de Folgas** na área de trabalho ou no menu Iniciar.
3. O MARKYS abrirá em uma janela própria, sem uma aba normal do navegador e sem console Python.
4. No primeiro uso, consulte `%LOCALAPPDATA%\MARKYS\ACESSO-INICIAL.txt` para obter a senha aleatória do usuário `admin`.
5. Entre no sistema e crie contas individuais na área Usuários. Guarde a senha em local seguro e apague o arquivo de acesso inicial depois de entrar.

## Aplicativo local e dados
- O MARKYS executa um serviço local no próprio computador e apresenta a interface em uma janela desktop.
- Endereço interno: `http://127.0.0.1:8000`.
- Configuração: `%LOCALAPPDATA%\MARKYS\.env`.
- Banco SQLite: `%LOCALAPPDATA%\MARKYS\markys_folgas.db`.
- O banco e a configuração ficam fora da pasta do programa e são preservados durante atualização/desinstalação.
- A instalação padrão escuta somente em `127.0.0.1`; não é um servidor de rede e não precisa de internet para operar após a instalação.

## Requisito da janela desktop
O Windows precisa ter o **Microsoft Edge WebView2 Runtime** instalado. Ele já costuma estar presente no Windows 11. Se a janela não abrir e o MARKYS mostrar uma mensagem sobre WebView2, instale/atualize o runtime e abra o aplicativo novamente. O aplicativo não apaga nem recria seu banco durante essa correção.

## Segurança e contas
- Não compartilhe a conta admin.
- Não envie `.env`, banco de dados, logs ou backups para o GitHub; podem conter dados pessoais.
- Faça backup regular do banco SQLite antes de atualizar ou desinstalar.

## Uso local
O MARKYS foi mantido para uso local neste computador, com SQLite e sem configuração de rede. Não altere o serviço para `0.0.0.0` nem abra a porta 8000 no firewall.

## Login não aceita a senha / recuperar acesso
1. Abra o menu Iniciar do Windows.
2. Na pasta MARKYS, execute **MARKYS - Recuperar acesso**.
3. Aguarde a mensagem de confirmação.
4. Consulte `%LOCALAPPDATA%\\MARKYS\\ACESSO-INICIAL.txt` e use o usuário e a senha temporária indicados.
5. Entre no aplicativo e guarde a nova senha. Apague o arquivo de recuperação depois.

A recuperação redefine a senha de uma conta administradora local e remove bloqueios de tentativas de login. Não apaga funcionários, créditos, saldos nem histórico. Use somente no computador onde o banco local está armazenado.

## Atualização
1. Feche a janela do MARKYS.
2. Faça uma cópia de segurança de `markys_folgas.db` e do arquivo `.env`.
3. Instale a versão nova no mesmo diretório sugerido pelo instalador.
4. Abra o atalho e confira login, funcionários, saldos e histórico.

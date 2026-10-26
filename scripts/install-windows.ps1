$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

Write-Host "MARKYS - instalacao inicial para Windows 11" -ForegroundColor Cyan
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python 3.11+ nao encontrado. Instale Python e habilite o Python Launcher (py)."
}
$ok = & py -3 -c "import sys; print('ok' if sys.version_info >= (3,11) else 'no')"
if ($LASTEXITCODE -ne 0 -or $ok.Trim() -ne "ok") { throw "Instale Python 3.11 ou superior." }
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    & py -3 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Falha ao criar ambiente virtual." }
}
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Falha ao atualizar pip." }
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar dependencias." }

$InitialPassword = $null
if (-not (Test-Path ".env")) {
    $Secret = (& .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))").Trim()
    $InitialPassword = (& .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(18))").Trim()
    $EnvText = @"
DATABASE_URL=sqlite:///./markys_folgas.db
APP_ENV=development
APP_SECRET_KEY=$Secret
ADMIN_USERNAME=admin
ADMIN_PASSWORD=$InitialPassword
COOKIE_HTTPS_ONLY=false
"@
    [System.IO.File]::WriteAllText((Join-Path $Root ".env"), $EnvText, ([System.Text.UTF8Encoding]::new($false)))
    Write-Host "Arquivo .env criado com segredo e senha aleatorios." -ForegroundColor Green
} else {
    Write-Host "Arquivo .env existente preservado." -ForegroundColor Yellow
}

$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "MARKYS - Controle de Folgas.lnk"
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = Join-Path $Root "scripts\start-windows.bat"
$Shortcut.WorkingDirectory = $Root
$Shortcut.Description = "Iniciar MARKYS - Controle de Folgas"
$Shortcut.Save()

Write-Host ""
Write-Host "Instalacao concluida. Atalho criado na area de trabalho." -ForegroundColor Green
Write-Host "A aplicacao fica restrita a este computador em http://127.0.0.1:8000."
if ($InitialPassword) {
    Write-Host "ANOTE A SENHA INICIAL DO ADMINISTRADOR (ela nao sera mostrada novamente):" -ForegroundColor Yellow
    Write-Host "Usuario: admin"
    Write-Host "Senha: $InitialPassword" -ForegroundColor Yellow
}
Write-Host "Nao exponha a porta 8000 a rede. Para uso multiusuario, siga docs\INSTALACAO-WINDOWS.md."

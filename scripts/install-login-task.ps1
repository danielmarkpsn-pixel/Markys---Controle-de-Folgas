# Execute no PowerShell do usuário que manterá o servidor ativo.
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Script = Join-Path $Root "scripts\run-server.ps1"
$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$Script`""
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName "MARKYS Controle de Folgas" -Action $Action -Trigger $Trigger -Settings $Settings -Description "Inicia MARKYS localmente ao entrar no Windows" -Force | Out-Null
Write-Host "Tarefa criada. O servidor iniciara quando este usuario entrar no Windows." -ForegroundColor Green
Write-Host "A tarefa usa 127.0.0.1 e nao abre acesso pela rede."

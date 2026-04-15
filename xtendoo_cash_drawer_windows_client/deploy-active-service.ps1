#Requires -Version 5.1

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$serviceExeName = 'cash_drawer_service.exe'
$installDirName = 'C:\CashDrawerService'
$legacyInstallDirName = 'C:\ImpressoraService'

function Get-InstallDir {
    if (Test-Path $installDirName) {
        return $installDirName
    }

    return $legacyInstallDirName
}

function Assert-Admin {
    $principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        $argList = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $PSCommandPath)
        Start-Process powershell.exe -Verb RunAs -ArgumentList $argList | Out-Null
        exit
    }
}

Assert-Admin

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceExe = Join-Path $scriptDir $serviceExeName
$targetDir = Get-InstallDir
$targetExe = Join-Path $targetDir $serviceExeName
$logsDir = Join-Path $targetDir 'logs'
$deployLog = Join-Path $logsDir 'deploy.log'
$port = 3211

if (-not (Test-Path $sourceExe)) {
    throw "No se encontro el ejecutable origen: $sourceExe"
}

if (-not (Test-Path $targetDir)) {
    throw "No existe el directorio de instalacion: $targetDir"
}

if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}

function Write-DeployLog {
    param([string]$Message)

    $timestamp = Get-Date -Format o
    Add-Content -Path $deployLog -Value "[$timestamp] $Message"
    Write-Host $Message
}

Write-DeployLog 'Inicio de despliegue del servicio activo.'

$connection = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($connection) {
    Write-DeployLog "Deteniendo proceso en puerto $port (PID=$($connection.OwningProcess))."
    Stop-Process -Id $connection.OwningProcess -Force

    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Milliseconds 250
        $stillListening = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
        if (-not $stillListening) {
            break
        }
    }
}

if (Test-Path $targetExe) {
    $backupExe = Join-Path $targetDir ('cash_drawer_service-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.bak.exe')
    Copy-Item $targetExe $backupExe -Force
    Write-DeployLog "Backup generado: $backupExe"
}

Copy-Item $sourceExe $targetExe -Force
Write-DeployLog "Ejecutable actualizado: $targetExe"

$startedProcess = Start-Process -FilePath $targetExe -WorkingDirectory $targetDir -PassThru
Write-DeployLog "Nuevo proceso iniciado. PID=$($startedProcess.Id)"

Start-Sleep -Milliseconds 1200

$newConnection = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($newConnection) {
    Write-DeployLog "Servicio escuchando en puerto $port con PID=$($newConnection.OwningProcess)."
} else {
    Write-DeployLog "AVISO: no se detecta escucha en el puerto $port tras el reinicio."
}

Write-DeployLog 'Fin de despliegue.'
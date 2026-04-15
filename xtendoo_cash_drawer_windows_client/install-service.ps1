#Requires -Version 5.1
<#
.SYNOPSIS
    Instala cash_drawer_service como servicio Windows usando NSSM.
.NOTES
    Requiere permisos de administrador y nssm.exe en la misma carpeta.
    Normalmente se llama desde install.ps1, pero puede ejecutarse de forma independiente.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$serviceName = "cash_drawer_service"
$displayName = "Cash Drawer Service (ESC/POS)"
$serviceExeName = "cash_drawer_service.exe"
$legacyServiceNames = @("ImpressoraService", "impresoraservice")

function Remove-ServiceIfExists {
    param(
        [string]$Name,
        [string]$NssmExe
    )

    $svc = Get-Service -Name $Name -ErrorAction SilentlyContinue
    if (-not $svc) {
        return
    }

    Write-Host "Deteniendo servicio previo '$Name'..."
    & $NssmExe stop $Name 2>&1 | Out-Null
    & $NssmExe remove $Name confirm 2>&1 | Out-Null
}

function Assert-Admin {
    $p = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    if (-not $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        $argList = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
        Start-Process powershell.exe -Verb RunAs -ArgumentList $argList
        exit
    }
}

Assert-Admin

$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$nssmExe     = Join-Path $ScriptDir "nssm.exe"
$serviceExe  = Join-Path $ScriptDir $serviceExeName
$logsDir     = Join-Path $ScriptDir "logs"

if (-not (Test-Path $nssmExe)) {
    Write-Error "nssm.exe no encontrado en $ScriptDir. Descargalo desde https://nssm.cc/download"
    exit 1
}
if (-not (Test-Path $serviceExe)) {
    Write-Error "$serviceExeName no encontrado en $ScriptDir. Compila primero con: npm run build"
    exit 1
}

if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}

# Eliminar servicio previo si existe
foreach ($legacyServiceName in $legacyServiceNames + $serviceName) {
    Remove-ServiceIfExists -Name $legacyServiceName -NssmExe $nssmExe
}
Start-Sleep -Milliseconds 1500

Write-Host "Instalando servicio '$serviceName'..."

& $nssmExe install       $serviceName $serviceExe
& $nssmExe set           $serviceName AppDirectory   $ScriptDir
& $nssmExe set           $serviceName DisplayName    $displayName
& $nssmExe set           $serviceName Description    "Servicio local para apertura de cajon portamonedas via ESC/POS RAW"
& $nssmExe set           $serviceName Start          SERVICE_AUTO_START
& $nssmExe set           $serviceName AppRestartDelay 3000
& $nssmExe set           $serviceName AppStdout      (Join-Path $logsDir "output.log")
& $nssmExe set           $serviceName AppStderr      (Join-Path $logsDir "error.log")
& $nssmExe set           $serviceName AppRotateFiles 1
& $nssmExe set           $serviceName AppRotateBytes 5242880

Start-Service -Name $serviceName
Start-Sleep -Milliseconds 1000

$status = (Get-Service -Name $serviceName).Status
Write-Host "Estado: $status"

if ($status -eq "Running") {
    Write-Host "Servicio '$serviceName' arrancado correctamente." -ForegroundColor Green
} else {
    Write-Host "[AVISO] Estado inesperado: $status. Revisa logs en $logsDir" -ForegroundColor Yellow
}

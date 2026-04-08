#Requires -Version 5.1
<#
.SYNOPSIS
    Desinstala el servicio Windows ImpressoraService y elimina la regla de Firewall.
.NOTES
    Requiere permisos de administrador.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

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
$serviceName = "ImpressoraService"

Write-Host ""
Write-Host "Desinstalando $serviceName..." -ForegroundColor Cyan

# Detener y eliminar servicio
$svcExists = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if ($svcExists) {
    if ($svcExists.Status -eq "Running") {
        Write-Host "  Deteniendo servicio..."
        Stop-Service -Name $serviceName -Force
        Start-Sleep -Milliseconds 1000
    }

    if (Test-Path $nssmExe) {
        Write-Host "  Eliminando servicio con NSSM..."
        & $nssmExe remove $serviceName confirm 2>&1 | Out-Null
    } else {
        Write-Host "  Eliminando servicio con sc.exe..."
        sc.exe delete $serviceName | Out-Null
    }
    Write-Host "  Servicio eliminado." -ForegroundColor Green
} else {
    Write-Host "  El servicio '$serviceName' no estaba instalado." -ForegroundColor Yellow
}

# Eliminar regla de firewall
$ruleName = "Impresora Service"
$existingRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if ($existingRule) {
    Remove-NetFirewallRule -DisplayName $ruleName
    Write-Host "  Regla de firewall '$ruleName' eliminada." -ForegroundColor Green
} else {
    Write-Host "  No se encontro regla de firewall '$ruleName'." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Desinstalacion completada." -ForegroundColor Green
Write-Host "(Los archivos en el directorio de instalacion no se han eliminado)" -ForegroundColor Gray
Write-Host ""
Read-Host "Pulsa INTRO para cerrar"

#Requires -Version 5.1
<#
.SYNOPSIS
    Desinstala el servicio Windows cash_drawer_service y elimina reglas de Firewall actuales o antiguas.
.NOTES
    Requiere permisos de administrador.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$serviceNames = @("cash_drawer_service", "ImpressoraService", "impresoraservice")
$firewallRuleNames = @("Cash Drawer Service", "Impresora Service")

function Remove-ServiceIfExists {
    param(
        [string]$Name,
        [string]$NssmExe
    )

    $svcExists = Get-Service -Name $Name -ErrorAction SilentlyContinue
    if (-not $svcExists) {
        Write-Host "  El servicio '$Name' no estaba instalado." -ForegroundColor Yellow
        return
    }

    if ($svcExists.Status -eq "Running") {
        Write-Host "  Deteniendo servicio '$Name'..."
        Stop-Service -Name $Name -Force
        Start-Sleep -Milliseconds 1000
    }

    if (Test-Path $NssmExe) {
        Write-Host "  Eliminando servicio '$Name' con NSSM..."
        & $NssmExe remove $Name confirm 2>&1 | Out-Null
    } else {
        Write-Host "  Eliminando servicio '$Name' con sc.exe..."
        sc.exe delete $Name | Out-Null
    }

    Write-Host "  Servicio '$Name' eliminado." -ForegroundColor Green
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

Write-Host ""
Write-Host "Desinstalando servicios de cash drawer..." -ForegroundColor Cyan

# Detener y eliminar servicio
foreach ($serviceName in $serviceNames) {
    Remove-ServiceIfExists -Name $serviceName -NssmExe $nssmExe
}

# Eliminar regla de firewall
foreach ($ruleName in $firewallRuleNames) {
    $existingRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
    if ($existingRule) {
        Remove-NetFirewallRule -DisplayName $ruleName
        Write-Host "  Regla de firewall '$ruleName' eliminada." -ForegroundColor Green
    } else {
        Write-Host "  No se encontro regla de firewall '$ruleName'." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Desinstalacion completada." -ForegroundColor Green
Write-Host "(Los archivos en el directorio de instalacion no se han eliminado)" -ForegroundColor Gray
Write-Host ""
Read-Host "Pulsa INTRO para cerrar"

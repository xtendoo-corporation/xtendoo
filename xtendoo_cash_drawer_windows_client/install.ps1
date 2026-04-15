#Requires -Version 5.1
<#
.SYNOPSIS
    Instalador de Cash Drawer Service con HTTPS local (mkcert) y servicio Windows (NSSM).
.DESCRIPTION
    - Descarga mkcert y genera certificado de confianza para 127.0.0.1, localhost y la IP LAN indicada
    - Crea .env con la configuracion del servicio
    - Registra regla de Firewall
    - Instala el servicio Windows con NSSM (si esta disponible)
.NOTES
    Requiere permisos de administrador. Si no los tiene, se auto-reeleva.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$serviceName = "cash_drawer_service"
$displayName = "Cash Drawer Service (ESC/POS)"
$serviceExeName = "cash_drawer_service.exe"
$ruleName = "Cash Drawer Service"
$defaultInstallDir = "C:\CashDrawerService"
$legacyServiceNames = @("ImpressoraService", "impresoraservice")
$legacyFirewallRuleNames = @("Impresora Service")

function Remove-ServiceIfExists {
    param(
        [string]$Name,
        [string]$NssmExe
    )

    $svc = Get-Service -Name $Name -ErrorAction SilentlyContinue
    if (-not $svc) {
        return
    }

    Write-Host "  Deteniendo y eliminando servicio previo '$Name'..." -ForegroundColor Yellow
    & $NssmExe stop $Name 2>&1 | Out-Null
    & $NssmExe remove $Name confirm 2>&1 | Out-Null
}

function Remove-FirewallRuleIfExists {
    param([string]$Name)

    $existingRule = Get-NetFirewallRule -DisplayName $Name -ErrorAction SilentlyContinue
    if ($existingRule) {
        Remove-NetFirewallRule -DisplayName $Name
    }
}

# ?? Auto-elevacion a administrador ??????????????????????????????????????????
function Assert-Admin {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal   = New-Object Security.Principal.WindowsPrincipal $currentUser
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-Host "Se necesitan permisos de administrador. Relanazando elevado..." -ForegroundColor Yellow
        $argList = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
        Start-Process powershell.exe -Verb RunAs -ArgumentList $argList
        exit
    }
}

Assert-Admin

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Cash Drawer Service - Instalacion" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# ?? Ruta de los ficheros fuente (junto a este .ps1) ??????????????????????????
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Get-DefaultLanHost {
    try {
        $ip = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop |
            Where-Object {
                $_.IPAddress -notlike '127.*' -and
                $_.IPAddress -notlike '169.254.*' -and
                $_.PrefixOrigin -ne 'WellKnown'
            } |
            Select-Object -First 1 -ExpandProperty IPAddress

        if (-not [string]::IsNullOrWhiteSpace($ip)) {
            return $ip
        }
    } catch {
    }

    return '192.168.1.116'
}

# ?? Preguntas de configuracion ???????????????????????????????????????????????
$installDir = Read-Host "Directorio de instalacion [$defaultInstallDir]"
if ([string]::IsNullOrWhiteSpace($installDir)) { $installDir = $defaultInstallDir }

$apiKey = ""
while ([string]::IsNullOrWhiteSpace($apiKey)) {
    $apiKey = Read-Host "API_KEY (obligatoria, minimo 8 caracteres)"
    if ($apiKey.Length -lt 8) {
        Write-Host "  La API_KEY debe tener al menos 8 caracteres." -ForegroundColor Red
        $apiKey = ""
    }
}

$portStr = Read-Host "Puerto [3210]"
if ([string]::IsNullOrWhiteSpace($portStr)) { $portStr = "3210" }
$port = [int]$portStr

$allowedOrigins = Read-Host "Origenes CORS permitidos [https://confiteriadelcarmen.xtd.es]"
if ([string]::IsNullOrWhiteSpace($allowedOrigins)) {
    $allowedOrigins = "https://confiteriadelcarmen.xtd.es"
}

$defaultLanHost = Get-DefaultLanHost
$httpsHostsInput = Read-Host "Hosts/IPs HTTPS del bridge [127.0.0.1,localhost,$defaultLanHost]"
if ([string]::IsNullOrWhiteSpace($httpsHostsInput)) {
    $httpsHostsInput = "127.0.0.1,localhost,$defaultLanHost"
}

$httpsHosts = @(
    $httpsHostsInput -split ',' |
        ForEach-Object { $_.Trim() } |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
        Select-Object -Unique
)

$publicHost = $httpsHosts |
    Where-Object { $_ -ne '127.0.0.1' -and $_ -ne 'localhost' } |
    Select-Object -First 1

if ([string]::IsNullOrWhiteSpace($publicHost)) {
    $publicHost = '127.0.0.1'
}

Write-Host ""
Write-Host "Configuracion:" -ForegroundColor Green
Write-Host "  Directorio : $installDir"
Write-Host "  Puerto     : $port"
Write-Host "  CORS       : $allowedOrigins"
Write-Host "  Host bind  : 0.0.0.0 (local y LAN)"
Write-Host "  HTTPS SANs : $($httpsHosts -join ', ')"
Write-Host "  URL publica: https://${publicHost}:$($port + 1)"
Write-Host ""

# ?? Crear directorio de instalacion ?????????????????????????????????????????
if (-not (Test-Path $installDir)) {
    New-Item -ItemType Directory -Path $installDir | Out-Null
    Write-Host "Directorio creado: $installDir" -ForegroundColor Green
}

$logsDir = Join-Path $installDir "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}

# ?? Copiar ficheros del servicio ??????????????????????????????????????????????
$filesToCopy = @($serviceExeName, "send-raw.ps1", "icon-green.ico", "icon-red.ico")
foreach ($f in $filesToCopy) {
    $src = Join-Path $ScriptDir $f
    if (Test-Path $src) {
        Copy-Item $src $installDir -Force
        Write-Host "  Copiado: $f" -ForegroundColor Green
    } else {
        Write-Host "  [AVISO] No encontrado: $f (omitido)" -ForegroundColor Yellow
    }
}

# Copiar nssm.exe si existe junto al instalador
$nssmSrc = Join-Path $ScriptDir "nssm.exe"
if (Test-Path $nssmSrc) {
    Copy-Item $nssmSrc $installDir -Force
    Write-Host "  Copiado: nssm.exe" -ForegroundColor Green
}

# ?? Descargar e instalar mkcert ???????????????????????????????????????????????
Write-Host ""
Write-Host "Configurando HTTPS local con mkcert..." -ForegroundColor Cyan

$mkcertExe = Join-Path $installDir "mkcert.exe"

if (-not (Test-Path $mkcertExe)) {
    Write-Host "  Descargando mkcert v1.4.4..."
    $mkcertUrl = "https://github.com/FiloSottile/mkcert/releases/download/v1.4.4/mkcert-v1.4.4-windows-amd64.exe"
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $mkcertUrl -OutFile $mkcertExe -UseBasicParsing
        Write-Host "  mkcert descargado OK" -ForegroundColor Green
    } catch {
        Write-Host "  [ERROR] No se pudo descargar mkcert: $_" -ForegroundColor Red
        Write-Host "  Descargalo manualmente desde https://github.com/FiloSottile/mkcert/releases"
        Write-Host "  y coloca mkcert.exe en $installDir"
        $mkcertExe = $null
    }
}

if ($mkcertExe -and (Test-Path $mkcertExe)) {
    # Instalar la CA en el trust store de Windows y Chrome
    Write-Host "  Instalando CA local (mkcert -install)..."
    Push-Location $installDir
    & $mkcertExe -install 2>&1 | ForEach-Object { Write-Host "    $_" }

    $certFile = Join-Path $installDir 'cash_drawer_service.pem'
    $keyFile  = Join-Path $installDir 'cash_drawer_service-key.pem'

    Write-Host "  Generando certificado para: $($httpsHosts -join ', ')..."
    & $mkcertExe -cert-file $certFile -key-file $keyFile @httpsHosts 2>&1 | ForEach-Object { Write-Host "    $_" }
    Pop-Location

    if ((Test-Path $certFile) -and (Test-Path $keyFile)) {
        Write-Host "  Certificado HTTPS generado OK" -ForegroundColor Green
        $certEnvKey  = 'cash_drawer_service-key.pem'
        $certEnvCert = 'cash_drawer_service.pem'
    } else {
        Write-Host "  [AVISO] No se encontraron los ficheros .pem. El servicio arrancara en HTTP." -ForegroundColor Yellow
        $certEnvKey  = ""
        $certEnvCert = ""
    }
} else {
    $certEnvKey  = ""
    $certEnvCert = ""
}

# ?? Generar .env ?????????????????????????????????????????????????????????????
Write-Host ""
Write-Host "Generando .env..." -ForegroundColor Cyan

$envContent = @"
API_KEY=$apiKey
PORT=$port
HOST=0.0.0.0
PUBLIC_HOST=$publicHost
ALLOWED_ORIGINS=$allowedOrigins
DEFAULT_PRINTER=
CERT_KEY=$certEnvKey
CERT_CERT=$certEnvCert
"@

$envPath = Join-Path $installDir ".env"
Set-Content -Path $envPath -Value $envContent -Encoding UTF8
Write-Host "  .env creado en $envPath" -ForegroundColor Green

# ?? Regla de Firewall ?????????????????????????????????????????????????????????
Write-Host ""
Write-Host "Configurando Firewall..." -ForegroundColor Cyan

foreach ($legacyRuleName in $legacyFirewallRuleNames + $ruleName) {
    $existingRule = Get-NetFirewallRule -DisplayName $legacyRuleName -ErrorAction SilentlyContinue
    if ($existingRule) {
        Write-Host "  Regla de firewall '$legacyRuleName' ya existe, actualizando..." -ForegroundColor Yellow
        Remove-FirewallRuleIfExists -Name $legacyRuleName
    }
}

$exePath = Join-Path $installDir $serviceExeName
New-NetFirewallRule `
    -DisplayName $ruleName `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort @($port, ($port + 1)) `
    -Action Allow `
    -Profile @("Domain","Private","Public") `
    -Program $exePath `
    -Description "Cash Drawer Service: servicio local ESC/POS para cajon portamonedas" | Out-Null

Write-Host "  Regla de firewall creada para puertos $port (HTTP) y $($port+1) (HTTPS)" -ForegroundColor Green

# ?? Instalar como servicio Windows con NSSM ???????????????????????????????????
$nssmExe = Join-Path $installDir "nssm.exe"
if (Test-Path $nssmExe) {
    Write-Host ""
    Write-Host "Instalando servicio Windows con NSSM..." -ForegroundColor Cyan

    $serviceExe  = Join-Path $installDir $serviceExeName

    # Eliminar servicio previo si existe
    foreach ($legacyServiceName in $legacyServiceNames + $serviceName) {
        Remove-ServiceIfExists -Name $legacyServiceName -NssmExe $nssmExe
    }
    Start-Sleep -Milliseconds 1500

    & $nssmExe install       $serviceName $serviceExe
    & $nssmExe set           $serviceName AppDirectory   $installDir
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
    if ($status -eq "Running") {
        Write-Host "  Servicio '$serviceName' instalado y arrancado correctamente" -ForegroundColor Green
    } else {
        Write-Host "  [AVISO] Servicio instalado pero estado: $status. Revisa los logs en $logsDir" -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "[AVISO] nssm.exe no encontrado. El servicio no se instalara automaticamente." -ForegroundColor Yellow
    Write-Host "        Descarga nssm desde https://nssm.cc/download y coloca nssm.exe junto a install.ps1"
    Write-Host "        Luego ejecuta install-service.ps1 manualmente."
}

# ?? Resumen final ?????????????????????????????????????????????????????????????
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Instalacion completada" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
$httpsPort = $port + 1
Write-Host "  HTTP  (local/LAN) : http://${publicHost}:${port}"
if ($certEnvCert) {
    Write-Host "  HTTPS (publico): https://${publicHost}:${httpsPort}" -ForegroundColor Green
}
Write-Host "  Directorio    : $installDir"
Write-Host ""
if ($certEnvCert) {
    Write-Host "  Configurar en Odoo TPV -> URL del bridge:" -ForegroundColor Cyan
    Write-Host "    https://${publicHost}:${httpsPort}" -ForegroundColor White
    Write-Host ""
    Write-Host "  IMPORTANTE: Chrome ya confia en el certificado local (mkcert CA)." -ForegroundColor Green
    Write-Host "  Si usas Firefox, abrelo y ejecuta: mkcert -install" -ForegroundColor Yellow
} else {
    Write-Host "  [AVISO] Sin HTTPS. El navegador bloqueara peticiones HTTP desde Odoo HTTPS." -ForegroundColor Red
    Write-Host "  Ejecuta install.ps1 de nuevo con mkcert.exe presente para habilitar HTTPS." -ForegroundColor Yellow
}
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Read-Host "Pulsa INTRO para cerrar"

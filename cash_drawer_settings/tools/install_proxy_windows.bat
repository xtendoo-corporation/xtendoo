@echo off
:: =============================================================================
:: install_proxy_windows.bat — Instala y configura el proxy de cajón en Windows
:: =============================================================================
:: Instala pywin32, copia el proxy a %APPDATA% y crea un acceso directo en
:: Inicio para que arranque automáticamente con el usuario.
::
:: Ejecutar como Administrador.
:: =============================================================================

setlocal EnableDelayedExpansion

echo.
echo ====================================================
echo   Cash Drawer Proxy - Instalador para Windows
echo ====================================================
echo.

:: Verificar que Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no está instalado o no está en el PATH.
    echo         Descárgalo de https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Python encontrado:
python --version

:: Instalar pywin32
echo.
echo [INFO] Instalando pywin32 (para win32print)...
pip install pywin32 --quiet
if errorlevel 1 (
    echo [WARN] No se pudo instalar pywin32. El proxy usará "copy /b" como alternativa.
) else (
    echo [OK] pywin32 instalado.
)

:: Directorio de instalación
set "INSTALL_DIR=%APPDATA%\CashDrawerProxy"
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: Copiar el proxy
set "SCRIPT_DIR=%~dp0"
copy /y "%SCRIPT_DIR%cash_drawer_proxy.py" "%INSTALL_DIR%\cash_drawer_proxy.py" >nul
echo [OK] Proxy copiado a %INSTALL_DIR%

:: Crear script de inicio (VBScript invisible)
set "VBS=%INSTALL_DIR%\start_proxy.vbs"
(
  echo Set WshShell = CreateObject("WScript.Shell"^)
  echo WshShell.Run "python ""%INSTALL_DIR%\cash_drawer_proxy.py"" --port 7070", 0, False
) > "%VBS%"
echo [OK] Script de inicio creado: %VBS%

:: Crear acceso directo en Inicio (autoarranque)
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT=%STARTUP%\CashDrawerProxy.lnk"
set "PS_CMD=powershell -NoProfile -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%SHORTCUT%');$s.TargetPath='wscript.exe';$s.Arguments='\"%VBS%\"';$s.Description='Cash Drawer Proxy';$s.Save()""
%PS_CMD%
if errorlevel 1 (
    echo [WARN] No se pudo crear el acceso directo en Inicio.
    echo        Inicia manualmente: python "%INSTALL_DIR%\cash_drawer_proxy.py"
) else (
    echo [OK] Acceso directo creado en Inicio. El proxy arrancará con Windows.
)

:: Arrancar el proxy ahora
echo.
echo [INFO] Iniciando el proxy en segundo plano...
start "" wscript.exe "%VBS%"

echo.
echo ====================================================
echo   Instalación completada.
echo   El proxy escucha en http://localhost:7070
echo   Prueba en tu navegador: http://localhost:7070/status
echo ====================================================
echo.
pause
endlocal


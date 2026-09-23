@echo off
REM ============================================================
REM  Maouse - Conectar APK de desenvolvimento ao PC (dev client)
REM  BOTAO DIREITO neste ficheiro > "Executar como administrador"
REM  (sao precisas regras de firewall -> pede permissao UAC: "Sim")
REM ============================================================
cd /d "%~dp0"

echo [1/3] A criar regras de firewall (Metro 8081 TCP + License 8000 TCP + Expo Discovery UDP)...
netsh advfirewall firewall delete rule name="Maouse Metro 8081 (TCP)" >nul 2>nul
netsh advfirewall firewall add rule name="Maouse Metro 8081 (TCP)" dir=in action=allow protocol=TCP localport=8081 profile=private >nul
netsh advfirewall firewall add rule name="Maouse Metro 8081 (TCP) Pub" dir=in action=allow protocol=TCP localport=8081 profile=public >nul

netsh advfirewall firewall delete rule name="Maouse License 8000 (TCP)" >nul 2>nul
netsh advfirewall firewall add rule name="Maouse License 8000 (TCP)" dir=in action=allow protocol=TCP localport=8000 profile=private >nul
netsh advfirewall firewall add rule name="Maouse License 8000 (TCP) Pub" dir=in action=allow protocol=TCP localport=8000 profile=public >nul

netsh advfirewall firewall delete rule name="Maouse Expo Discovery 61120 (UDP)" >nul 2>nul
netsh advfirewall firewall add rule name="Maouse Expo Discovery 61120 (UDP)" dir=in action=allow protocol=UDP localport=61120 profile=private >nul
netsh advfirewall firewall add rule name="Maouse Expo Discovery 61121 (UDP)" dir=in action=allow protocol=UDP localport=61121 profile=private >nul
echo    OK.

echo [2/3] IP deste PC - para introduzires manualmente no telemovel:
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do set LANIP=%%a
if not defined LANIP for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do set LANIP=%%a
if defined LANIP (
  set LANIP=%LANIP: =%
  echo    No telemovel - Dev Launcher - "Enter URL manually":
  echo        exp://%LANIP%:8081
)

echo [3/3] A arrancar o Metro (deixa esta janela ABERTA)...
call npx expo start --dev-client
echo.
echo Metro parado. Podes fechar esta janela.
pause

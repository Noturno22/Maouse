@echo off
setlocal EnableExtensions
REM ============================================================
REM  Maouse - Conectar o APK de desenvolvimento ao PC (dev client)
REM
REM  USO: BOTAO DIREITO neste ficheiro > "Executar como administrador"
REM       (sao precisas regras de firewall -> UAC: "Sim")
REM
REM  Portas abertas:
REM    8081/TCP  Metro (bundler)          <- o APK dev falha SEM esta
REM    8765/TCP  PC remoto (WebSocket)    <- gestos nao chegam ao PC SEM esta
REM    8000/TCP  license-server
REM    61120-61121/UDP  Expo discovery
REM ============================================================
cd /d "%~dp0"

set "P_METRO=8081"
set "P_REMOTE=8765"
set "P_LIC=8000"
set "RULE_PREFIX=Maouse"

echo ============================================================
echo  Maouse - preparar ligacao do APK dev
echo ============================================================
echo.

REM ------------------------------------------------------------
REM [0] Privilegios de administrador (obrigatorio para o firewall)
REM ------------------------------------------------------------
net session >nul 2>&1
if errorlevel 1 (
  echo [FALHA] Precisas de executar como ADMINISTRADOR.
  echo         Botao direito neste ficheiro ^> "Executar como administrador".
  echo         ^(O Windows Firewall bloqueia o Metro sem estas regras.^)
  echo.
  pause
  exit /b 1
)
echo [OK] Administrador.
echo.

REM ------------------------------------------------------------
REM [1] Limpar regras antigas (por prefixo, evita duplicados)
REM ------------------------------------------------------------
echo [1/4] A remover regras de firewall antigas...
for %%P in (8081 8000 8765 61120 61121) do (
  netsh advfirewall firewall delete rule name="%RULE_PREFIX% Metro %%P" >nul 2>&1
  netsh advfirewall firewall delete rule name="%RULE_PREFIX% Remote %%P" >nul 2>&1
  netsh advfirewall firewall delete rule name="%RULE_PREFIX% License %%P" >nul 2>&1
  netsh advfirewall firewall delete rule name="%RULE_PREFIX% Discovery %%P" >nul 2>&1
)
echo       OK.
echo.

REM ------------------------------------------------------------
REM [2] Abrir portas.  profile=any: a rede Wi-Fi do Windows e
REM     normalmente "Publica" e nao "Privada" - cobrir so "private"
REM     deixava o Metro bloqueado.
REM ------------------------------------------------------------
echo [2/4] A abrir portas no Windows Firewall...

call :AddRule "%RULE_PREFIX% Metro %P_METRO%"   TCP %P_METRO%   "Metro (bundler) - APK dev"
call :AddRule "%RULE_PREFIX% Remote %P_REMOTE%" TCP %P_REMOTE%   "PC remoto (WebSocket) - gestos"
call :AddRule "%RULE_PREFIX% License %P_LIC%"   TCP %P_LIC%     "license-server (entitle IAP)"
call :AddRule "%RULE_PREFIX% Discovery 61120"   UDP 61120       "Expo discovery"
call :AddRule "%RULE_PREFIX% Discovery 61121"   UDP 61121       "Expo discovery"

echo.
echo       A verificar as regras...
call :CheckRule "%RULE_PREFIX% Metro %P_METRO%"   FAIL
call :CheckRule "%RULE_PREFIX% Remote %P_REMOTE%" FAIL
call :CheckRule "%RULE_PREFIX% License %P_LIC%"   FAIL
call :CheckRule "%RULE_PREFIX% Discovery 61120"   FAIL
call :CheckRule "%RULE_PREFIX% Discovery 61121"   FAIL
if "%FAIL%"=="1" (
  echo.
  echo [FALHA] Nao foi possivel criar as regras. Confirma o antivirus.
  pause
  exit /b 1
)
echo       Todas as portas estao abertas ^(8081, 8765, 8000^).
echo.

REM ------------------------------------------------------------
REM [3] Descobrir o IP certo deste PC.
REM     O bug antigo: findstr /c:"IPv4" devolvia TAMBEM os
REM     enderecos APIPA 169.254.x.x (Bluetooth, Ethernet) e o
REM     ultimo da lista ganhava - imprimindo um IP inalcancavel.
REM     Agora: usa a interface que tem a rota por omissao (a LAN real)
REM     e descarta 169.254.* / 127.*.
REM ------------------------------------------------------------
echo [3/4] A descobrir o IP deste PC na LAN...
set "PSOUT=%TEMP%\maouse_lanip.txt"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$r=Get-NetRoute -AddressFamily IPv4 -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue | Sort-Object RouteMetric | Select-Object -First 1; (Get-NetIPAddress -AddressFamily IPv4 -InterfaceIndex $r.InterfaceIndex -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress -notlike '169.254.*' -and $_.IPAddress -notlike '127.*' } | Select-Object -First 1).IPAddress" > "%PSOUT%" 2>nul

set "LANIP="
for /f "usebackq tokens=* delims=" %%i in ("%PSOUT%") do set "LANIP=%%i"
del /q "%PSOUT%" >nul 2>&1

if not defined LANIP goto :NOIP

echo       IP LAN: %LANIP%
echo.
echo  ------------------------------------------------------
echo   No telemovel: Dev Launcher - "Enter URL manually":
echo       exp://%LANIP%:%P_METRO%
echo.
echo   E o PC remoto (separado do Metro):
echo       host: %LANIP%      porta: %P_REMOTE%
echo  ------------------------------------------------------
echo.

REM ------------------------------------------------------------
REM [4] Metro. --host lan = binds 0.0.0.0 (alcançavel pela LAN).
REM     Sem isto o Metro so escuta em localhost e o telemóvel
REM     nunca liga, mesmo com o firewall aberto.
REM ------------------------------------------------------------
echo [4/4] A arrancar o Metro (deixa esta janela ABERTA)...
echo.
call npx expo start --dev-client --host lan
echo.
echo Metro parado. Podes fechar esta janela.
pause
exit /b 0

REM ------------------------------------------------------------
:CheckRule
REM  %1=nome da regra   %2=variavel acumuladora de falhas
netsh advfirewall firewall show rule name="%~1" >nul 2>&1
if errorlevel 1 (
  echo       [FALHOU] %~1
  set "%~2=1"
)
exit /b 0

:AddRule
REM  %1=nome  %2=TCP|UDP  %3=porta  %4=descricao
netsh advfirewall firewall add rule name="%~1" dir=in action=allow protocol=%~2 localport=%~3 profile=any enable=yes >nul 2>&1
if errorlevel 1 (
  echo       [ERRO] %~1
  exit /b 1
)
echo       [OK] %~4  %~3/%~2
exit /b 0

:NOIP
echo [FALHA] Nao encontrei um IP de LAN valido.
echo         O PC tem de estar ligado a uma rede (Wi-Fi/cabo) com DHCP.
echo         Se so tens IP 169.254.x.x, nao ha LAN - liga o Wi-Fi.
echo.
pause
exit /b 1

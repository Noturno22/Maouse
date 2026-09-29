@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Corre setup.bat primeiro.
    exit /b 1
)

rem ── Certificado de assinatura digital (opcional) ──────────────────────
rem O build assina automaticamente quando existe um certificado .pfx.
rem A prioridade para detetar o certificado e:
rem   1. Argumento   : build.bat <pfx_path> <pfx_pass>
rem   2. Variaveis   : PFX_PATH e PFX_PASS
rem   3. Local fixo  : cert\maouse.pfx   (password = PFX_PASS ou vazia)
rem Sem certificado o build continua, mas o .exe/instalador ficam NAO assinados
rem (SmartScreen/AV vao avisar). Obter um cert EV e o passo comercial em falta.
set "PFX_PATH=%~1"
set "PFX_PASS=%~2"
if not defined PFX_PASS if defined PFX_PASS_ENV set "PFX_PASS=%PFX_PASS_ENV%"
if not defined PFX_PATH if exist "cert\maouse.pfx" set "PFX_PATH=%CD%\cert\maouse.pfx"
if defined PFX_PATH if not exist "%PFX_PATH%" (
    echo AVISO: PFX_PATH nao existe: %PFX_PATH%
    set "PFX_PATH="
)

rem ── Assinatura cloud eSigner (SSL.com) ─────────────────────────────────
rem Alternativa ao .pfx para certificado EV no eSigner (a chave fica na
rem nuvem SSL.com - a SSL nao emite .pfx). Pre-requisitos:
rem   1. Descarregar o CodeSignTool (Windows, inclui Java) em
rem      https://www.ssl.com/downloads/  e descompactar (ex.: C:\tools\CodeSignTool).
rem   2. Enroll do certificado no eSigner no portal SSL.com (pedido "eSigner Ready").
rem   3. Definir as variaveis abaixo. Se ESIGNER_USERNAME e ESIGNER_PASSWORD
rem      estiverem definidos, o build usa o CodeSignTool (eSigner).
rem        ESIGNER_PATH         = pasta onde esta o CodeSignTool
rem        ESIGNER_USERNAME     = e-mail da conta SSL.com
rem        ESIGNER_PASSWORD     = password da conta SSL.com
rem        ESIGNER_CREDENTIAL_ID = opcional, so se tiver mais de um certificado
rem        ESIGNER_TOTP_SECRET  = opcional. Se definido, a assinatura e
rem                               automatica (sem OTP). Se nao, o CodeSignTool
rem                               pede o OTP da app autenticadora na hora.
rem      Nota: com este script, a password nao pode conter o carater '!'.
set "ESIGNER_BAT="
if defined ESIGNER_PATH if exist "%ESIGNER_PATH%\CodeSignTool.bat" set "ESIGNER_BAT=%ESIGNER_PATH%\CodeSignTool.bat"
if not defined ESIGNER_BAT if exist "%CD%\tools\CodeSignTool\CodeSignTool.bat" set "ESIGNER_BAT=%CD%\tools\CodeSignTool\CodeSignTool.bat"
if not defined ESIGNER_BAT if exist "C:\tools\CodeSignTool\CodeSignTool.bat" set "ESIGNER_BAT=C:\tools\CodeSignTool\CodeSignTool.bat"
set "USE_ESIGNER=0"
if defined ESIGNER_USERNAME if defined ESIGNER_PASSWORD if defined ESIGNER_BAT set "USE_ESIGNER=1"
if defined ESIGNER_USERNAME if not defined ESIGNER_BAT echo AVISO: ESIGNER_USERNAME definido mas o CodeSignTool.bat nao foi encontrado.

rem ── Assinatura por thumbprint (YubiKey FIPS ou eSigner CKA) ────────────
rem Se o certificado estiver carregado no Windows Certificate Store (token
rem YubiKey FIPS ligado ao PC, ou o eSigner CKA instalado), basta definir
rem CERT_THUMBPRINT para assinar por thumbprint com o signtool nativo.
set "USE_THUMBPRINT=0"
if defined CERT_THUMBPRINT set "USE_THUMBPRINT=1"

rem Deteta o signtool (Windows SDK / Inno Setup).
set "SIGNTOOL="
for %%K in (
    "C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x86\signtool.exe"
    "C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe"
    "C:\Program Files (x86)\Windows Kits\10\bin\10.0.19041.0\x86\signtool.exe"
    "C:\Program Files (x86)\Windows Kits\10\bin\10.0.19041.0\x64\signtool.exe"
) do if not defined SIGNTOOL if exist "%%~K" set "SIGNTOOL=%%~K"

if defined PFX_PATH (
    echo [ASSINATURA] Certificado encontrado: %PFX_PATH%
) else (
    echo [ASSINATURA] Sem certificado - o .exe/instalador nao serao assinados.
)

rem ── Inspeção pré-build: URL real do license-server gravado? ────────────
rem Impede distribuir um .exe que aponta para o placeholder (não ativa licenças).
rem Para forçar um build de dev/QA: define MAOUSE_ALLOW_PLACEHOLDER_URL=1 no ambiente.
.venv\Scripts\python.exe tools\check_prod_license_url.py
if errorlevel 1 (
    echo.
    echo ABORTO: grava o URL real do Render em core\licensing.py antes de fazer
    echo release. Ver docs\DESKTOP_LICENSE_URL.md. Para dev/QA define
    echo MAOUSE_ALLOW_PLACEHOLDER_URL=1 no ambiente antes de correr build.bat.
    exit /b 1
)

echo [1/6] A instalar PyInstaller ...
.venv\Scripts\python.exe -m pip install --upgrade -r requirements-build.txt -q
if errorlevel 1 exit /b 1

echo [2/6] A gerar icone (.ico) ...
.venv\Scripts\python.exe tools\generate_ico.py
if errorlevel 1 exit /b 1

echo [3/6] A gerar metadados de versao (version_info.txt) ...
.venv\Scripts\python.exe tools\gen_version_info.py
if errorlevel 1 exit /b 1

echo [4/6] A construir executavel (pode demorar varios minutos) ...
.venv\Scripts\python.exe -m PyInstaller maouse.spec --noconfirm
if errorlevel 1 exit /b 1
rem Modelos críticos (hand_landmarker.task, gesture_mlp.npz) entram pelo
rem maouse.spec. Vosk/Piper são descarregados em %LOCALAPPDATA%\Maouse.
xcopy /E /I /Y assets\fonts "dist\Maouse\assets\fonts" >nul
xcopy /E /I /Y assets\brand "dist\Maouse\assets\brand" >nul

rem ── Assinar o Maouse.exe (antes de o empacotar no instalador) ───────
if "%USE_ESIGNER%"=="1" (
    echo [5/6] A assinar Maouse.exe - eSigner cloud (CodeSignTool) ...
    set "ESIGNER_TARGET=%CD%\dist\Maouse\Maouse.exe"
    call :esign
    if errorlevel 1 echo AVISO: falhou a assinatura via eSigner - a continuar sem ela.
) else if "%USE_THUMBPRINT%"=="1" (
    if defined SIGNTOOL (
        echo [5/6] A assinar Maouse.exe - thumbprint %CERT_THUMBPRINT% ...
        "%SIGNTOOL%" sign /fd SHA256 /tr http://ts.ssl.com /td SHA256 /sha1 "%CERT_THUMBPRINT%" "dist\Maouse\Maouse.exe"
        if errorlevel 1 echo AVISO: falhou a assinatura do Maouse.exe - a continuar sem ela.
    ) else (
        echo [5/6] Assinatura do Maouse.exe ignorada.
    )
) else if defined PFX_PATH (
    if defined SIGNTOOL (
        echo [5/6] A assinar Maouse.exe - SHA256 + timestamp ...
        "%SIGNTOOL%" sign /f "%PFX_PATH%" /p "%PFX_PASS%" /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /d "Maouse" "dist\Maouse\Maouse.exe"
        if errorlevel 1 echo AVISO: falhou a assinatura do Maouse.exe - a continuar sem ela.
    ) else (
        echo [5/6] Assinatura do Maouse.exe ignorada.
    )
) else (
    echo [5/6] Assinatura do Maouse.exe ignorada.
)

echo [6/6] A gerar instalador 1-clique (Inno Setup) ...
set "ISCC=C:\Users\Luar Studio Angola\AppData\Local\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
    echo ATENCAO: Inno Setup nao encontrado em "%ISCC%"
    echo O instalador nao foi gerado, mas o Maouse.exe esta em dist\Maouse\
) else (
    if "%USE_ESIGNER%"=="1" (
        "%ISCC%" installer.iss
    ) else if "%USE_THUMBPRINT%"=="1" (
        "%ISCC%" installer.iss
    ) else if defined PFX_PATH (
        rem Assinar o instalador, reutilizando o mesmo certificado.
        "%ISCC%" installer.iss /DPfxPath="%PFX_PATH%" /DPfxPass="%PFX_PASS%"
    ) else (
        "%ISCC%" installer.iss
    )
    if errorlevel 1 exit /b 1
    if "%USE_ESIGNER%"=="1" (
        echo [6/6] A assinar instalador - eSigner cloud (CodeSignTool) ...
        set "ESIGNER_TARGET=%CD%\dist\Maouse-Setup-1.0.0.exe"
        call :esign
        if errorlevel 1 echo AVISO: falhou a assinatura do instalador via eSigner - a continuar sem ela.
    )
    if "%USE_THUMBPRINT%"=="1" (
        echo [6/6] A assinar instalador - thumbprint %CERT_THUMBPRINT% ...
        "%SIGNTOOL%" sign /fd SHA256 /tr http://ts.ssl.com /td SHA256 /sha1 "%CERT_THUMBPRINT%" "dist\Maouse-Setup-1.0.0.exe"
        if errorlevel 1 echo AVISO: falhou a assinatura do instalador por thumbprint - a continuar sem ela.
    )
)

echo.
echo Build concluido:
echo   Executavel: dist\Maouse\Maouse.exe
echo   Instalador: dist\Maouse-Setup-1.0.0.exe
if "%USE_ESIGNER%"=="1" (
    echo   Assinado: SIM ^(eSigner ^- confirmar no portal SSL.com^)
) else if "%USE_THUMBPRINT%"=="1" (
    echo   Assinado: SIM ^(thumbprint %CERT_THUMBPRINT%^)
) else if defined PFX_PATH (
    echo   Assinado: SIM
) else (
    echo   Assinado: NAO  ^(activa o eSigner ou usa uma YubiKey FIPS para remover o aviso SmartScreen^)
)
endlocal
exit /b 0

rem ── Sub-rotina: assinar %ESIGNER_TARGET% com o CodeSignTool ─────────────
rem Uso: set "ESIGNER_TARGET=<ficheiro>" & call :esign
:esign
set "ESIGNER_ARGS=-username=%ESIGNER_USERNAME% -password=%ESIGNER_PASSWORD%"
if defined ESIGNER_CREDENTIAL_ID set "ESIGNER_ARGS=%ESIGNER_ARGS% -credential_id=%ESIGNER_CREDENTIAL_ID%"
if defined ESIGNER_TOTP_SECRET set "ESIGNER_ARGS=%ESIGNER_ARGS% -totp_secret=%ESIGNER_TOTP_SECRET%"
call "%ESIGNER_BAT%" sign %ESIGNER_ARGS% -input_file_path="%ESIGNER_TARGET%" -override=true
exit /b %errorlevel%

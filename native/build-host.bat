@echo off
setlocal enabledelayedexpansion

rem Compila o host RFCOMM (C++/WinRT). Ver native\maouse-bluetooth-host.cpp.
rem
rem Porque e preciso: a porta RFCOMM do Windows vive em WinRT
rem (Windows.Devices.Bluetooth.Rfcomm). O Python nao a alcanca, porque
rem socket.AF_BLUETOOTH e bt_socket so existem no Linux. Este exe e quem a
rem segura e fala com o Python por stdin/stdout.
rem
rem Dependencias: Visual Studio Build Tools com o workload C++, e o Windows 10/11 SDK.
rem
rem NOTA sobre o estilo: este script nao usa blocos if (...) aninhados. O parser
rem do cmd conta os parenteses de "Program Files (x86)" mesmo dentro de aspas e
rem falha com "'. was unexpected at this time'". Por isso os ramos sao labels e
rem os caminhos usam !VAR! (expansao em tempo de execucao, que o parser nao
rem volta a analisar) em vez de %VAR%.

cd /d "%~dp0.."

set "VSX86=C:\Program Files (x86)\Microsoft Visual Studio"
set "VS64=C:\Program Files\Microsoft Visual Studio"
set "KITROOT=C:\Program Files (x86)\Windows Kits\10"

rem --- 1) localizar e activar o ambiente do Visual Studio --------------------
echo [procura] vcvars64.bat
set "VCVARS="
for /f "delims=" %%F in ('dir /b /s /o-d "!VSX86!\vcvars64.bat" 2^>nul') do if not defined VCVARS set "VCVARS=%%F"
if not defined VCVARS for /f "delims=" %%F in ('dir /b /s /o-d "!VS64!\vcvars64.bat" 2^>nul') do if not defined VCVARS set "VCVARS=%%F"
if not defined VCVARS goto sem_vcvars

echo [ok] vcvars64: !VCVARS!
rem vcvars define INCLUDE e LIB (MSVC, ucrt, um, shared, winrt, cppwinrt) e poe
rem cl.exe no PATH. Por isso o comando de compilacao so precisa de /Ibuild\winrt.
call "!VCVARS!" >nul
if errorlevel 1 goto erro_ambiente

rem --- 2) projecao C++/WinRT -------------------------------------------------
rem O codigo inclui <winrt/...>. A projecao tem de existir ANTES de build\winrt
rem entrar no /I: sem ela o compilador usa a do SDK, que vem incompleta e da
rem "nao e um membro de RfcommServiceProvider".
if exist "build\winrt\winrt\Windows.Foundation.h" goto escolher_alvo

echo [procura] cppwinrt.exe e Windows.winmd
set "CPPWINRT="
for /f "delims=" %%D in ('dir /b /o-d /ad "!KITROOT!\bin" 2^>nul') do if not defined CPPWINRT if exist "!KITROOT!\bin\%%D\x64\cppwinrt.exe" set "CPPWINRT=!KITROOT!\bin\%%D\x64\cppwinrt.exe"
if not defined CPPWINRT goto sem_cppwinrt

set "WINMD="
for /f "delims=" %%D in ('dir /b /o-d /ad "!KITROOT!\UnionMetadata" 2^>nul') do if not defined WINMD if exist "!KITROOT!\UnionMetadata\%%D\Windows.winmd" set "WINMD=!KITROOT!\UnionMetadata\%%D\Windows.winmd"
if not defined WINMD goto sem_winmd

echo [gerar] "!CPPWINRT!" -input "!WINMD!" -output build\winrt
"!CPPWINRT!" -input "!WINMD!" -output "build\winrt"
if errorlevel 1 goto erro_cppwinrt

rem --- 3) escoler o que compilar --------------------------------------------
rem O alvo por omissao e so o host: e o que o produto precisa, e o `build.bat`
rem chama este script sem argumentos. As ferramentas de diagnostico sao um alvo
rem a parte para nao entrarem no caminho do build de distribuicao.
rem
rem   build-host.bat        -> so o host (o que o build.bat quer)
rem   build-host.bat tools  -> o cliente de teste e a sonda de radio
rem   build-host.bat all    -> os tres
:escolher_alvo
set "ALVO=%~1"
if "%ALVO%"=="" set "ALVO=host"

:alvos
if not exist "build\rfcomm-host" mkdir "build\rfcomm-host"

if /i "%ALVO%"=="host" goto alvo_host
if /i "%ALVO%"=="tools" goto alvo_tools
if /i "%ALVO%"=="all" goto alvo_all
echo [ERRO] alvo desconhecido: "%ALVO%"  (use: host ^| tools ^| all)
exit /b 1

:alvo_host
set "FONTE=native\maouse-bluetooth-host.cpp"
set "SAIDA=build\rfcomm-host\maouse-bluetooth-host.exe"
call :compilar_um
if errorlevel 1 goto erro_compilacao
echo [ok] !SAIDA!
exit /b 0

:alvo_tools
rem O cliente e a referencia que o Fortune vai implementar no Android; a sonda
rem de radio e a unica forma de distinguir "adaptador partido" de "radio
rem desligado", que devolvem o mesmo HRESULT.
set "FONTE=native\rfcomm-test-client.cpp"
set "SAIDA=build\rfcomm-host\rfcomm-test-client.exe"
call :compilar_um
if errorlevel 1 goto erro_compilacao

set "FONTE=native\bluetooth-radio-probe.cpp"
set "SAIDA=build\rfcomm-host\bt-radio-probe.exe"
call :compilar_um
if errorlevel 1 goto erro_compilacao
echo [ok] build\rfcomm-host\rfcomm-test-client.exe
echo [ok] build\rfcomm-host\bt-radio-probe.exe
exit /b 0

:alvo_all
set "FONTE=native\maouse-bluetooth-host.cpp"
set "SAIDA=build\rfcomm-host\maouse-bluetooth-host.exe"
call :compilar_um
if errorlevel 1 goto erro_compilacao
set "FONTE=native\rfcomm-test-client.cpp"
set "SAIDA=build\rfcomm-host\rfcomm-test-client.exe"
call :compilar_um
if errorlevel 1 goto erro_compilacao
set "FONTE=native\bluetooth-radio-probe.cpp"
set "SAIDA=build\rfcomm-host\bt-radio-probe.exe"
call :compilar_um
if errorlevel 1 goto erro_compilacao
echo [ok] build\rfcomm-host\maouse-bluetooth-host.exe
echo [ok] build\rfcomm-host\rfcomm-test-client.exe
echo [ok] build\rfcomm-host\bt-radio-probe.exe
exit /b 0

rem Compila um alvo. O fonte tem de vir ANTES de /link: tudo o que segue /link
rem vai para o linker, e o cl.exe ficaria sem ficheiro fonte (erro D8003).
:compilar_um
echo [compilar] !FONTE!
rem /std:c++17 e nao c++latest: a projecao do SDK 10.0.19041 usa
rem <experimental/coroutine>, que com coroutines C++20 activas da erro STL1010
rem e faz cascade em wait_get/wait_for. Este SDK e antigo, o MSVC e novo.
rem _SILENCE_EXPERIMENTAL_COROUTINE_DEPRECATION_WARNINGS: o MSVC 14.51 turned
rem <experimental/coroutine> em erro (STL1011) e e o proprio compilador que manda
rem definir esta macro. Sem ela os erros a seguir (wait_get, C2440) sao cascata
rem do cabecalho da projecao, nao do nosso codigo.
cl.exe /nologo /std:c++17 /EHsc /W3 /utf-8 /DUNICODE /D_UNICODE /D_SILENCE_EXPERIMENTAL_COROUTINE_DEPRECATION_WARNINGS /Ibuild\winrt /Fe!SAIDA! /Fo!SAIDA!.obj !FONTE! /link windowsapp.lib
if errorlevel 1 exit /b 1
exit /b 0

rem --- ramos de erro ---------------------------------------------------------
:sem_vcvars
echo [ERRO] vcvars64.bat nao encontrado.
echo        Instala "Visual Studio Build Tools" com o workload C++.
exit /b 1

:erro_ambiente
echo [ERRO] falhou ao preparar o ambiente de compilacao.
exit /b 1

:sem_cppwinrt
echo [ERRO] cppwinrt.exe nao encontrado - Windows SDK em falta?
exit /b 1

:sem_winmd
echo [ERRO] Windows.winmd nao encontrado - Windows SDK em falta?
exit /b 1

:erro_cppwinrt
echo [ERRO] cppwinrt falhou ao gerar a projecao.
exit /b 1

:erro_compilacao
echo [ERRO] compilacao falhou.
exit /b 1
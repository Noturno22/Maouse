@echo off
setlocal
set "DIR=%~dp0"
set "PYW=%DIR%.venv\Scripts\pythonw.exe"
set "MAIN=%DIR%main.py"

if not exist "%PYW%" (
    echo ERRO: pythonw.exe nao encontrado em %PYW%
    echo Corre primeiro setup.bat
    pause
    exit /b 1
)

rem Instalacoes anteriores (antes de 2026-09-29) criaram "AirMouse JARVIS".
rem Criar a nova sem tirar a antiga deixa o utilizador com DUAS tarefas em
rem ONLOGON -> a aplicacao arranca duas vezes. O uninstall_startup.bat apaga
rem as duas, mas ninguem e obrigado a correr o uninstall antes do install.
schtasks /Query /TN "AirMouse JARVIS" >nul 2>&1
if not errorlevel 1 (
    echo Tarefa da instalacao anterior encontrada a remover.
    schtasks /Delete /TN "AirMouse JARVIS" /F >nul
)

schtasks /Create /F /TN "Maouse JARVIS" /SC ONLOGON /RL LIMITED /TR "\"%PYW%\" \"%MAIN%\" --tray"
if errorlevel 1 (
    echo Falhou a criacao da tarefa.
    pause
    exit /b 1
)
echo.
echo Mãouse arrancara automaticamente com o Windows (modo invisivel + bandeja).
echo Para remover: corre uninstall_startup.bat
pause

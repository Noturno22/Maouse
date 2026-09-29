@echo off
setlocal
rem O nome da tarefa tambem mudou no rename de 2026-09-29 (AirMouse -> Maouse).
rem Apagar so a nova nao apaga a que o utilizador ja tem: quem instalou antes fica
rem com as duas tarefas em ONLOGON e arranca a aplicacao duas vezes. Por isso as
rem duas, e o "removido" so e dito se alguma foi mesmo removida.
set "OK=0"

schtasks /Query /TN "Maouse JARVIS" >nul 2>&1
if not errorlevel 1 (
    schtasks /Delete /TN "Maouse JARVIS" /F >nul
    if errorlevel 1 (
        echo AVISO: a tarefa "Maouse JARVIS" existe mas nao consegui remove-la.
        echo Tenta manualmente: schtasks /Delete /TN "Maouse JARVIS" /F
    ) else (
        echo Removida: "Maouse JARVIS"
        set /a OK=1
    )
)

schtasks /Query /TN "AirMouse JARVIS" >nul 2>&1
if not errorlevel 1 (
    schtasks /Delete /TN "AirMouse JARVIS" /F >nul
    if errorlevel 1 (
        echo AVISO: a tarefa "AirMouse JARVIS" da instalacao anterior existe
        echo mas nao consegui remove-la. Tenta manualmente:
        echo    schtasks /Delete /TN "AirMouse JARVIS" /F
    ) else (
        echo Removida: "AirMouse JARVIS" - instalacao anterior
        set /a OK=1
    )
)

echo.
if %OK%==0 (
    echo Nao havia tarefa de arranque automatico com estes nomes.
) else (
    echo Arranque automatico removido.
)
rem Os dados do utilizador NAO sao apagados, e sao dois sitios diferentes:
rem   %LOCALAPPDATA%\Maouse\  -> settings e logs (config.py, core/log.py)
rem   %APPDATA%\Maouse\       -> license.json (core/licensing.py)
rem Apagar as pastas seria levar a licenca com o uninstall.
pause

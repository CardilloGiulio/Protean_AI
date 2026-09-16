@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PYTHON_EXE=.venv\Scripts\python.exe"
set "ASSISTANT_EXE=src\protean_workspace\assistant_shell\node_modules\electron\dist\electron.exe"

if not exist "%PYTHON_EXE%" goto :install_required
if not exist "%ASSISTANT_EXE%" goto :install_required
goto :start

:install_required
echo Protean Workspace or its Virtual Assistant runtime is not fully installed.
echo Running the single installer now...
call install.bat
if errorlevel 1 exit /b 1
if not exist "%PYTHON_EXE%" goto :verification_failed
if not exist "%ASSISTANT_EXE%" goto :verification_failed

:start

echo Starting Protean Workspace at http://127.0.0.1:8000
echo Press Ctrl+C in this window to stop the server.
echo.
start "" "http://127.0.0.1:8000"
"%PYTHON_EXE%" -m uvicorn protean_workspace.main:app --host 127.0.0.1 --port 8000
exit /b %ERRORLEVEL%

:verification_failed
echo ERROR: Installation returned success but a required runtime is still missing.
echo Re-extract the complete ZIP and run install.bat again.
pause
exit /b 1

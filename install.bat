@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo        Protean Workspace - Installer
echo ========================================
echo.

if not exist "pyproject.toml" goto :project_missing
if not exist "requirements-lock.txt" goto :project_missing
if not exist "src\protean_workspace\assistant_shell\package-lock.json" goto :project_missing

where py.exe >nul 2>&1
if not errorlevel 1 goto :use_py
where python.exe >nul 2>&1
if errorlevel 1 goto :python_missing
set "PYTHON_CMD=python.exe"
goto :python_ready

:use_py
set "PYTHON_CMD=py.exe"

:python_ready
%PYTHON_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 goto :python_old

where node.exe >nul 2>&1
if errorlevel 1 goto :node_missing
where npm.cmd >nul 2>&1
if errorlevel 1 goto :npm_missing
node.exe -e "const [a,b]=process.versions.node.split('.').map(Number); process.exit(a>22||(a===22&&b>=12)?0:1)"
if errorlevel 1 goto :node_old

if exist ".venv\Scripts\python.exe" goto :venv_ready
echo [1/5] Creating Python virtual environment...
%PYTHON_CMD% -m venv .venv
if errorlevel 1 goto :failed
goto :pip_upgrade

:venv_ready
echo [1/5] Python virtual environment already exists.

:pip_upgrade
echo [2/5] Updating pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :failed

echo [3/5] Installing locked Python dependencies...
".venv\Scripts\python.exe" -m pip install --requirement requirements-lock.txt
if errorlevel 1 goto :failed

echo [4/5] Installing Protean Workspace...
".venv\Scripts\python.exe" -m pip install --no-deps --no-build-isolation -e .
if errorlevel 1 goto :failed

echo [5/5] Installing locked Virtual Assistant desktop runtime...
pushd "src\protean_workspace\assistant_shell"
call npm.cmd ci --no-audit --no-fund
if errorlevel 1 goto :assistant_install_failed
node.exe "node_modules\electron\install.js"
if errorlevel 1 goto :assistant_binary_install_failed
if not exist "node_modules\electron\dist\electron.exe" goto :assistant_binary_missing
"node_modules\electron\dist\electron.exe" --version >nul 2>&1
if errorlevel 1 goto :assistant_binary_failed
popd

echo.
echo ========================================
echo Installation verified successfully.
echo Python workspace: READY
echo Virtual Assistant: READY
echo Run start.bat to launch Protean Workspace.
echo ========================================
echo.
pause
exit /b 0

:assistant_install_failed
popd
echo.
echo ERROR: npm could not install the locked Electron runtime.
goto :failed

:assistant_binary_install_failed
popd
echo.
echo ERROR: Electron's platform executable could not be downloaded or extracted.
goto :failed

:assistant_binary_missing
popd
echo.
echo ERROR: npm finished but Electron was not installed at the required path.
goto :failed

:assistant_binary_failed
popd
echo.
echo ERROR: Electron was installed but its executable could not be started.
goto :failed

:project_missing
echo ERROR: Required Protean project files are missing.
echo Project directory: %CD%
echo Re-extract the complete ZIP, then run install.bat again.
pause
exit /b 1

:python_missing
echo ERROR: Python was not found in PATH.
echo Install Python 3.11 or newer, then run install.bat again.
pause
exit /b 1

:python_old
echo ERROR: Protean Workspace requires Python 3.11 or newer.
%PYTHON_CMD% --version
pause
exit /b 1

:node_missing
echo ERROR: Node.js was not found in PATH.
echo Install Node.js 22.12 or newer, then run install.bat again.
pause
exit /b 1

:npm_missing
echo ERROR: npm.cmd was not found in PATH.
echo Repair or reinstall Node.js 22.12 or newer, then run install.bat again.
pause
exit /b 1

:node_old
echo ERROR: Virtual Assistant requires Node.js 22.12 or newer.
node.exe --version
pause
exit /b 1

:failed
echo.
echo Installation did not complete. Protean is not marked ready.
echo Correct the error above and run this same install.bat again.
pause
exit /b 1

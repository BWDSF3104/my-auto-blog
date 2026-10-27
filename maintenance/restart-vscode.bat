@echo off
setlocal
rem VS Code graceful close + relaunch batch (no force kill)
rem usage:
rem   restart-vscode.bat            (Y/N confirm. current dir is restart target)
rem   restart-vscode.bat --yes      (non-interactive, for agent)
rem   restart-vscode.bat --dry-run  (identify only, no changes)
rem   restart-vscode.bat --self-test cwd  (new window open/close self-test)
set "MODE="
if /i "%~1" equ "" set "MODE=ask"
if /i "%~1" equ "--yes" set "MODE=execute"
if /i "%~1" equ "--dry-run" set "MODE=dry-run"
if /i "%~1" equ "--self-test" set "MODE=self-test"
if "%MODE%" equ "" (
  echo usage restart-vscode.bat --yes --dry-run --self-test cwd
  echo no arg mode requires interactive Y N confirm
  exit /b 2
)
if "%MODE%" equ "self-test" (
  if /i "%~2" equ "" (
    echo self-test needs cwd as 2nd arg
    exit /b 1
  )
  python "%~dp0vscode_graceful_restart.py" --self-test "%~2"
  exit /b %errorlevel%
)
if "%MODE%" equ "dry-run" (
  python "%~dp0vscode_graceful_restart.py" --dry-run "%cd%"
  exit /b %errorlevel%
)
if "%MODE%" equ "ask" (
  set /p confirm=Close VS Code normally and relaunch? Y or N default N: 
  if /i "%confirm%" neq "Y" (
    echo cancel
    exit /b 1
  )
)
if "%MODE%" equ "execute" (
  rem KI-20261028-01: detached pythonw launch, so no console window is created
  rem and cmd exits immediately (its window closes). Results go to the report file.
  where pythonw >nul 2>&1
  if errorlevel 1 (
    python "%~dp0vscode_graceful_restart.py" "%cd%"
    exit /b %errorlevel%
  )
  start "" /b pythonw "%~dp0vscode_graceful_restart.py" "%cd%"
  exit /b 0
)
python "%~dp0vscode_graceful_restart.py" "%cd%"
exit /b %errorlevel%

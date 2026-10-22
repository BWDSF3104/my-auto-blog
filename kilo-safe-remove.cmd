@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass ^
  -File "%~dp0maintenance\safe-remove.ps1" %*

exit /b %ERRORLEVEL%
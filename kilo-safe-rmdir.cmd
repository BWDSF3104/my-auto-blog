@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass ^
  -File "%~dp0maintenance\safe-rmdir.ps1" %*

exit /b %ERRORLEVEL%

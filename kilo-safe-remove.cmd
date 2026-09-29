@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass ^
  -File "%~dp0.kilo\scripts\safe-remove.ps1" %*

exit /b %ERRORLEVEL%
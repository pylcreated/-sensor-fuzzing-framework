@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0sf-longrun.ps1" %*
set "EXIT_CODE=%ERRORLEVEL%"
if /I "%~1"=="--no-pause" goto :end
echo.
if "%EXIT_CODE%"=="0" (
  echo [OK] Long-run script completed.
) else (
  echo [ERROR] Long-run failed, exit code: %EXIT_CODE%
)
echo Press any key to close this window...
pause >nul
:end
endlocal & exit /b %EXIT_CODE%

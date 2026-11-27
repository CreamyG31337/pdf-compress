@echo off
setlocal enabledelayedexpansion

set "UV=%USERPROFILE%\.local\bin\uv.exe"
set "SCRIPT=%~dp0compress_pdf.py"

:: No file dropped — show usage hint
if "%~1"=="" (
    echo Drag and drop one or more PDF files onto this script to compress them.
    echo.
    echo Output is saved next to each original file as "filename_compressed.pdf"
    echo.
    pause
    exit /b 0
)

:: Check uv is present
if not exist "%UV%" (
    echo ERROR: uv not found at %UV%
    echo.
    echo Install it by running this in PowerShell:
    echo   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 ^| iex"
    echo.
    pause
    exit /b 1
)

:: Process every dropped file
set ERRORS=0
for %%F in (%*) do (
    echo ----------------------------------------
    echo Input:  %%~nxF
    "%UV%" run "%SCRIPT%" "%%~F"
    if !errorlevel! neq 0 set /a ERRORS+=1
)

echo ----------------------------------------
if %ERRORS%==0 (
    echo All done.
) else (
    echo Done with %ERRORS% error(s^) — scroll up to see details.
)
echo.
pause

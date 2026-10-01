@echo off
setlocal EnableExtensions
chcp 65001 >nul 2>&1
title DiffLens - Pembanding Gambar

rem ============================================================
rem  Peluncur aplikasi DiffLens
rem  - Membuat virtual environment lokal (.venv) bila belum ada
rem  - Memasang dependency dari requirements.txt
rem  - Menjalankan aplikasi
rem  Catatan: file ini memakai CRLF dan menghindari blok kurung
rem  agar tidak salah parse di cmd.exe
rem ============================================================

rem Pindah ke folder tempat file .bat ini berada
cd /d "%~dp0"

set "VENV_DIR=.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "REQ=requirements.txt"

echo.
echo ============================================================
echo   DiffLens - Pembanding Gambar
echo ============================================================
echo.

rem --- 1. Cari interpreter Python yang tersedia ---
set "SYS_PY="
where python >nul 2>&1 && set "SYS_PY=python"
if defined SYS_PY goto python_found
where py >nul 2>&1 && set "SYS_PY=py"
:python_found
if not defined SYS_PY goto no_python

rem --- 2. Buat venv bila belum ada ---
if exist "%VENV_PY%" goto have_venv

echo [1/3] Membuat virtual environment di "%VENV_DIR%" ...
%SYS_PY% -m venv "%VENV_DIR%"
if errorlevel 1 goto venv_failed

echo [2/3] Memperbarui pip ...
"%VENV_PY%" -m pip install --upgrade pip

echo [3/3] Memasang dependency. Butuh internet, sekali saja.
"%VENV_PY%" -m pip install -r "%REQ%"
if errorlevel 1 goto dep_failed
goto run_app

:have_venv
rem venv sudah ada, pastikan dependency lengkap
"%VENV_PY%" -c "import PySide6, PIL, numpy" >nul 2>&1
if not errorlevel 1 goto run_app
echo [i] Dependency belum lengkap, memasang dari "%REQ%" ...
"%VENV_PY%" -m pip install -r "%REQ%"
if errorlevel 1 goto dep_failed
goto run_app

rem --- 3. Jalankan aplikasi ---
:run_app
echo.
echo Menjalankan aplikasi ...
echo.
"%VENV_PY%" "run.py" %*
set "EXITCODE=%ERRORLEVEL%"
if not "%EXITCODE%"=="0" goto app_failed
goto done

:no_python
echo [ERROR] Python tidak ditemukan di PATH.
echo         Install Python 3.10+ dari https://www.python.org/downloads/
echo         dan pastikan opsi "Add Python to PATH" dicentang.
echo.
pause
endlocal
exit /b 1

:venv_failed
echo [ERROR] Gagal membuat virtual environment.
pause
endlocal
exit /b 1

:dep_failed
echo [ERROR] Gagal memasang dependency.
pause
endlocal
exit /b 1

:app_failed
echo.
echo [ERROR] Aplikasi berhenti dengan kode %EXITCODE%.
pause
endlocal
exit /b %EXITCODE%

:done
endlocal
exit /b 0

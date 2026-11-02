@echo off
rem Buka dasbor Meja Saham (K91): klik-ganda berkas ini. Tutup jendela ini untuk berhenti.
cd /d "%~dp0"
rem Data kerja nyata ada di .uji-data\mejasaham (bukan %LOCALAPPDATA%\MejaSaham). MEJASAHAM_DATA
rem yang sudah dipasang di lingkungan tetap menang, begitu juga --folder-data.
if not defined MEJASAHAM_DATA set "MEJASAHAM_DATA=%~dp0.uji-data\mejasaham"
if not exist ".venv\Scripts\python.exe" (
  echo MejaSaham: .venv belum ada. Jalankan dulu: python -m venv .venv lalu pasang requirements.txt
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m mejasaham %*
if errorlevel 1 pause

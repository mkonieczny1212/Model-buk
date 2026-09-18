@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Model Buk v0.7.0 Server - PORT 8010 - NIE ZAMYKAJ

echo ================================================
echo          MODEL BUK v0.7.0 - START APLIKACJI
echo ================================================
echo.

set "PY="
py -3.12 -c "import sys" >nul 2>nul && set "PY=py -3.12"
if not defined PY (
  python -c "import sys; sys.exit(sys.version_info[:2] != (3,12))" >nul 2>nul && set "PY=python"
)
if not defined PY (
  if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" set PY="%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
)

if not defined PY (
  echo [BLAD] Nie znaleziono Python 3.12.
  echo Zainstaluj Python 3.12 i uruchom plik ponownie.
  echo.
  pause
  exit /b 1
)

echo [1/6] Python:
%PY% --version
if errorlevel 1 goto :error

echo.
echo [2/6] Przygotowanie srodowiska .venv...
if not exist ".venv\Scripts\python.exe" (
  %PY% -m venv .venv
  if errorlevel 1 goto :error
) else (
  echo Srodowisko juz istnieje - pomijam tworzenie.
)

echo.
echo [3/6] Instalacja / aktualizacja bibliotek...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q --upgrade pip
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements-lock.txt
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q --no-deps -e .
if errorlevel 1 goto :error

echo.
".venv\Scripts\python.exe" scripts\artifact_manifest.py
if errorlevel 1 goto :error

echo [4/6] Sprawdzam live data...
if defined API_FOOTBALL_KEY (
  echo API-Football: klucz skonfigurowany; dostep do danych sprawdzi aplikacja
) else (
  echo API-Football: brak klucza - aplikacja wystartuje w trybie historycznym/manualnym.
  echo Aby wlaczyc live data, uruchom USTAW_API_FOOTBALL.bat.
)

echo.
echo [5/6] Uruchamiam serwer Model Buk...
echo Serwer bedzie dzialal w TYM oknie. Nie zamykaj go podczas korzystania z aplikacji.

echo.
echo [6/6] Przegladarka otworzy sie automatycznie za kilka sekund...
set "MODEL_BUK_PORT=8010"
start "" /b .venv\Scripts\python.exe -c "import time,webbrowser; time.sleep(4); webbrowser.open('http://127.0.0.1:8010/?v=070')"

".venv\Scripts\python.exe" -m model_buk.web.api
if errorlevel 1 goto :error
exit /b 0

:error
echo.
echo ================================================
echo [BLAD] Nie udalo sie uruchomic Model Buk.
echo Zrob screenshot tego okna i wyslij mi go w ChatGPT.
echo ================================================
pause
exit /b 1


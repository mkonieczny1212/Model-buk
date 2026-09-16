@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Model Buk - dodatkowe API

echo ================================================
echo        MODEL BUK - DODATKOWE ZRODLA DANYCH
echo ================================================
echo.
echo Klucze sa zapisywane TYLKO jako zmienne srodowiskowe Windows.
echo Nie sa dopisywane do kodu, ZIP-a ani repozytorium GitHub.
echo.

set /p FOOTY=FootyStats API key (Enter = pomin): 
if not "%FOOTY%"=="" (
  setx FOOTYSTATS_API_KEY "%FOOTY%" >nul
  echo [OK] FOOTYSTATS_API_KEY zapisany.
)

set /p SPORT=Sportmonks API token (Enter = pomin): 
if not "%SPORT%"=="" (
  setx SPORTMONKS_API_TOKEN "%SPORT%" >nul
  echo [OK] SPORTMONKS_API_TOKEN zapisany.
)

echo.
echo Zamknij wszystkie okna Model Buk i uruchom ponownie URUCHOM_MODEL_BUK.bat.
echo.
pause

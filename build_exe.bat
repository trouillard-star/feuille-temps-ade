@echo off
:: ============================================================
::  Build — Groupe ADE Feuille de Temps
::  Développé par Thierry Rouillard
::  Lance ce script depuis le dossier du projet
:: ============================================================

echo.
echo  [ADE] Build FeuilleTemps_ADE.exe
echo  ================================
echo.

:: Vérifie que PyInstaller est installé
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo  Installation de PyInstaller...
    pip install pyinstaller
)

:: Vérifie que reportlab est installé
python -c "import reportlab" >nul 2>&1
if errorlevel 1 (
    echo  Installation de reportlab...
    pip install reportlab
)

:: Nettoie les builds précédents
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "FeuilleTemps_ADE.spec" del "FeuilleTemps_ADE.spec"

:: Build — un seul fichier exe, pas de console, icône si présente
if exist "ade_icon.ico" (
    python -m PyInstaller ^
        --onefile ^
        --windowed ^
        --name "FeuilleTemps_ADE" ^
        --icon "ade_icon.ico" ^
        --add-data "version.json;." ^
        feuille_temps.py
) else (
    python -m PyInstaller ^
        --onefile ^
        --windowed ^
        --name "FeuilleTemps_ADE" ^
        --add-data "version.json;." ^
        feuille_temps.py
)

if errorlevel 1 (
    echo.
    echo  [ERREUR] Build échoué.
    pause
    exit /b 1
)

echo.
echo  ============================================================
echo  [OK] dist\FeuilleTemps_ADE.exe créé avec succès !
echo.
echo  Prochaines étapes :
echo   1. Mets à jour version.json avec la nouvelle version
echo   2. Commit + push sur GitHub
echo   3. Crée un GitHub Release et uploade le .exe
echo  ============================================================
echo.
pause

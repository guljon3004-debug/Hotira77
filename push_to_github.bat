@echo off
chcp 65001 > nul
title GitHub-ga yuklash (Hotira77)
color 0B

echo ======================================================
echo       HOTIRA77 BOTINI GITHUB-GA YUKLASH (PUSH)
echo ======================================================
echo.

set PATH=C:\Users\PC\AppData\Local\Microsoft\WinGet\Packages\Git.MinGit_Microsoft.Winget.Source_8wekyb3d8bbwe\cmd;%PATH%

echo Repozitoriy: https://github.com/guljon3004-debug/Hotira77
echo.

git add -A
git status
echo.
set /p COMMIT_MSG="O'zgarishlar izohi (Enter bosing): "
if "%COMMIT_MSG%"=="" set COMMIT_MSG="Hotira77 boti to'liq qayta tiklandi va yangilandi"

git commit -m "%COMMIT_MSG%"
echo.
echo GitHub-ga yuklanmoqda...
git push -u origin main

echo.
if %errorlevel% equ 0 (
    echo [OK] Barcha kodlar GitHub-ga muvaffaqiyatli yuklandi!
    echo Havola: https://github.com/guljon3004-debug/Hotira77
) else (
    echo [XATOLIK] Yuklashda muammo yuz berdi.
)
echo.
pause

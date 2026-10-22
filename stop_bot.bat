@echo off
chcp 65001 > nul
title Botni to'xtatish
color 0C

echo ======================================================
echo                BOTNI TO'XTATISH
echo ======================================================
echo.
echo Orqa fonda ishlayotgan bot jarayonlari to'xtatilmoqda...

schtasks /end /tn "SmartOfficeBot" >nul 2>&1
wmic process where "commandline like '%%run_loop.bat%%'" delete >nul 2>&1
wmic process where "commandline like '%%bot.py%%'" delete >nul 2>&1

echo.
echo [OK] Bot muvaffaqiyatli to'xtatildi!
echo.
pause

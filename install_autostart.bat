@echo off
chcp 65001 > nul
title Avto-yuklashga qo'shish

echo ======================================================
echo   BOTNI KOMPYUTER YOQILISHIDA ISHGA TUSHIRISH (24/7)
echo ======================================================
echo.

set SCRIPT_DIR=%~dp0
set VBS_PATH=%SCRIPT_DIR%run_background.vbs
set STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup

powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%STARTUP_FOLDER%\SmartOfficeBot.lnk'); $s.TargetPath = '%VBS_PATH%'; $s.WorkingDirectory = '%SCRIPT_DIR%'; $s.Save()"

if %errorlevel% equ 0 (
    echo [OK] Muvaffaqiyatli qo'shildi!
    echo Endi kompyuter yoqilganda bot orqa fonda avtomatik ishga tushadi.
) else (
    echo [XATOLIK] Qo'shib bo'lmadi.
)

echo.
pause

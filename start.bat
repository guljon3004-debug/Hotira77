@echo off
chcp 65001 > nul
title Xotira va Eslatmalar Boti (@Hotira77_bot)
color 0B

echo ======================================================
echo       XOTIRA VA SHAXSIY ESLATMALAR BOTI (@Hotira77_bot)
echo ======================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [XATOLIK] Python tizimda topilmadi!
    pause
    exit /b
)

:loop
echo [%date% %time%] Bot ishga tushirilmoqda...
python bot.py
echo.
echo [OGOHLANTIRISH] Bot to'xtadi yoki internet uzildi. 5 soniyadan keyin qayta ishga tushadi...
echo To'xtatish uchun ushbu oynani yoping yoki Ctrl + C bosing.
ping 127.0.0.1 -n 6 >nul
goto loop

Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\PC\Desktop\xotira_bot"
WshShell.Run chr(34) & "C:\Users\PC\Desktop\xotira_bot\run_loop.bat" & chr(34), 0, False

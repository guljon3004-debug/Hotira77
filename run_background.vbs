Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\PC\Desktop\xotira_bot"
WshShell.Run "cmd.exe /c ""C:\Users\PC\Desktop\xotira_bot\run_loop.bat""", 0, False

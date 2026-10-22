Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\PC\Desktop\smart_office_bot"
WshShell.Run "cmd.exe /c run_loop.bat", 0, False


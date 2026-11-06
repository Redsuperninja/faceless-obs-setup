# Builds Stream Launcher.exe in the project folder. Run from anywhere: .\scripts\build_launcher.ps1
Set-Location (Split-Path $PSScriptRoot)
$py = ".venv\Scripts\python.exe"
& $py -m pip install pyinstaller
& $py -m PyInstaller --onefile --noconsole --name "Stream Launcher" --distpath . --workpath "$env:TEMP\launcher-build" --specpath "$env:TEMP\launcher-build" scripts\launcher.py

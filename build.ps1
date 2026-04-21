# Clean previous build artifacts
Write-Host "Cleaning build, dist and installer folders..." -ForegroundColor Yellow
if (Test-Path "build")     { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist")      { Remove-Item -Recurse -Force "dist" }
if (Test-Path "installer") { Remove-Item -Recurse -Force "installer" }

# Build exe with PyInstaller
Write-Host "Building exe with PyInstaller..." -ForegroundColor Yellow
pyinstaller --onedir --noconsole `
  --collect-all pythonnet `
  --collect-all clr_loader `
  --add-data "static/css;static/css" `
  --add-data "static/js;static/js" `
  --add-data "templates;templates" `
  --add-data "image;image" `
  --add-data "icon.ico;." `
  --icon=icon.ico `
  --name="SSM Manager" `
  --clean app.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller failed. Aborting." -ForegroundColor Red
    exit 1
}

# Build installer with Inno Setup
Write-Host "Building installer with Inno Setup..." -ForegroundColor Yellow
$iscc = "C:\Users\mauro\AppData\Local\Programs\Inno Setup 6\ISCC.exe"
& $iscc installer.iss

if ($LASTEXITCODE -ne 0) {
    Write-Host "Inno Setup failed." -ForegroundColor Red
    exit 1
}

Write-Host "Done! Installer ready in: installer\SSM-Manager-v2.0-setup.exe" -ForegroundColor Green

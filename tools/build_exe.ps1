<#
Build a single-file Windows executable.

Prereq: run this from the repo root on Windows with Python 3.12 available.
It creates/reuses .venv, installs runtime + build dependencies, generates the
icon, and writes dist\ColourTodo.exe.
#>
[CmdletBinding()]
param(
    [string]$Python = "",
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not $Python) {
    $venvPython = Join-Path $Root ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        $Python = $venvPython
    } else {
        $Python = "python"
    }
}

if (-not $SkipInstall) {
    & $Python -m pip install --disable-pip-version-check -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "runtime dependency install failed" }
    & $Python -m pip install --disable-pip-version-check pyinstaller
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller install failed" }
}

& $Python tools\make_icon.py
if ($LASTEXITCODE -ne 0) { throw "icon generation failed" }

& $Python -m PyInstaller `
    --noconfirm --clean --onedir --windowed `
    --name ColourTodo `
    --icon assets\colour_todo.ico `
    --add-data "assets;assets" `
    --collect-submodules pystray `
    --hidden-import pystray._win32 `
    main.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed" }

$folder = Join-Path $Root "dist\ColourTodo"
$zip = Join-Path $Root "dist\ColourTodo-win64.zip"
Compress-Archive -Path (Join-Path $folder "*") -DestinationPath $zip -Force

Write-Host ""
Write-Host "Built: $folder\ColourTodo.exe"
Write-Host "Zip:   $zip"

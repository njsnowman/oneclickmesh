$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

py -3 -m pip install -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw 'Could not install build dependencies.' }

py -3 -m PyInstaller --noconfirm --clean packaging/one-click-mesh.spec
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }

Write-Host "Built: $repoRoot\dist\One-Click-Mesh.exe"

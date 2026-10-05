$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$testRoot = Join-Path (Get-Location).Path '.pytest_temp'
New-Item -ItemType Directory -Path $testRoot -Force | Out-Null
$testRun = Join-Path $testRoot ([guid]::NewGuid().ToString())
& .\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp $testRun @args
exit $LASTEXITCODE

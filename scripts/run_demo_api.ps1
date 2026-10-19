$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
# Serve the SYNTHETIC scored demo built by scripts/build_demo.py. The demo database and model
# settings apply to this API process only; .env stays unchanged (secrets/tokens still come from it).
$demoEnv = 'private_data\demo\backend.env'
if (-not (Test-Path $demoEnv)) { throw 'Run .\.venv\Scripts\python.exe -m scripts.build_demo first' }
foreach ($line in Get-Content $demoEnv) {
    if ($line -match '^(AGROGAMI_[A-Z_]+)=(.*)$') { Set-Item -Path ("Env:" + $Matches[1]) -Value $Matches[2] }
}
& .\.venv\Scripts\python.exe -m uvicorn agrogami.api.app:app --host 127.0.0.1 --port 8000 --no-access-log
exit $LASTEXITCODE

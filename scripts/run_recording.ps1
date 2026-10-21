$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
# Video-recording copy of the SYNTHETIC demo: a fresh copy of the demo database on ports 8100 (API)
# and 8601 (UI), so on-camera SMS submissions never touch the public site's data. Each run starts clean.
# Uses its own reviewer token (private_data\recording\recording.env, gitignored), granted Rahim + abstention only.
$demo = 'private_data\demo'; $rec = 'private_data\recording'
if (-not (Test-Path "$demo\agrogami-demo.db")) { throw 'Run .\.venv\Scripts\python.exe -m scripts.build_demo first' }
foreach ($port in 8100, 8601) {
    if (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue) { throw "Port $port is in use; close the previous recording windows first" }
}
New-Item -ItemType Directory -Force $rec | Out-Null
Remove-Item -Recurse -Force "$rec\agrogami-recording.db", "$rec\private" -ErrorAction SilentlyContinue
$demoPy = $demo -replace '\\', '/'; $recPy = $rec -replace '\\', '/'
& .\.venv\Scripts\python.exe -c "import sqlite3; s=sqlite3.connect('$demoPy/agrogami-demo.db'); d=sqlite3.connect('$recPy/agrogami-recording.db'); s.backup(d); d.close(); s.close()"
if ($LASTEXITCODE -ne 0) { throw 'Could not copy the demo database' }
Copy-Item -Recurse "$demo\private" "$rec\private"
if (-not (Test-Path "$rec\recording.env") -or (Get-Item "$rec\recording.env").Length -eq 0) {
    & .\.venv\Scripts\python.exe -c @"
import json, secrets, sys
sys.path.insert(0, 'src')
from agrogami.synthetic.identities import RAHIM_APPLICANT_ID, ABSTENTION_APPLICANT_ID
token = secrets.token_urlsafe(24)
tokens = json.dumps({token: 'reviewer'})
grants = json.dumps({token: [str(RAHIM_APPLICANT_ID), str(ABSTENTION_APPLICANT_ID)]})
open('$recPy/recording.env', 'w', encoding='utf-8').write(
    '# Recording copy only. Private: never commit or publish.\n'
    + 'AGROGAMI_DEMO_TOKENS=' + tokens + '\n'
    + 'AGROGAMI_APPLICANT_GRANTS=' + grants + '\n')
"@
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the recording credential' }
}
foreach ($line in (Get-Content "$demo\backend.env") + (Get-Content "$rec\recording.env")) {
    if ($line -match '^(AGROGAMI_[A-Z_]+)=(.*)$') { Set-Item -Path ("Env:" + $Matches[1]) -Value $Matches[2] }
}
$env:AGROGAMI_ENV = 'demo'
$env:AGROGAMI_LOCAL_DEMO_MODE = 'false'
$env:AGROGAMI_MCP_ENABLED = 'false'
$env:AGROGAMI_DATABASE_URL = "sqlite:///$($rec -replace '\\','/')/agrogami-recording.db"
$env:AGROGAMI_PRIVATE_DATA_DIR = "$rec\private"
$env:AGROGAMI_API_URL = 'http://127.0.0.1:8100'
$env:AGROGAMI_PUBLIC_API_URL = 'http://127.0.0.1:8100'
$python = (Resolve-Path '.\.venv\Scripts\python.exe').Path
Start-Process -FilePath $python -ArgumentList '-m', 'uvicorn', 'agrogami.api.app:app', '--host', '127.0.0.1', '--port', '8100', '--no-access-log'
Start-Process -FilePath $python -ArgumentList '-m', 'streamlit', 'run', 'src/agrogami/ui/app.py', '--server.address=127.0.0.1', '--server.port=8601', '--server.headless=true', '--browser.gatherUsageStats=false'
$token = (Get-Content "$rec\recording.env" | Where-Object { $_ -match '^AGROGAMI_DEMO_TOKENS=' }) -replace '^AGROGAMI_DEMO_TOKENS=\{"([^"]+)".*$', '$1'
Write-Host "Recording copy: UI http://127.0.0.1:8601 (API 8100). Reviewer credential for the recording: $token"
Write-Host 'Close the two new windows when done. The public site and its data are untouched.'

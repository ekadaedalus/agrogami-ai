param([switch]$WithTunnel)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
# Serve the SYNTHETIC scored demo for the public tunnel (agrogami.jmmn.tech).
# API and UI bind to 127.0.0.1 only; cloudflared publishes them. Prism is not started.
# Settings: the demo database/model (private_data\demo\backend.env), then deployment mode,
# tokens and grants (private_data\deploy\deploy.env). Both files are gitignored; .env is untouched.
foreach ($file in 'private_data\demo\backend.env', 'private_data\deploy\deploy.env') {
    if (-not (Test-Path $file)) { throw "Missing $file (run scripts.build_demo and create the deploy settings first)" }
    foreach ($line in Get-Content $file) {
        if ($line -match '^(AGROGAMI_[A-Z_]+)=(.*)$') { Set-Item -Path ("Env:" + $Matches[1]) -Value $Matches[2] }
    }
}
if ($env:AGROGAMI_LOCAL_DEMO_MODE -ne 'false') { throw 'Refusing to publish: AGROGAMI_LOCAL_DEMO_MODE must be false' }
$python = (Resolve-Path '.\.venv\Scripts\python.exe').Path
Start-Process -FilePath $python -ArgumentList '-m', 'uvicorn', 'agrogami.api.app:app', '--host', '127.0.0.1', '--port', '8000', '--no-access-log'
Start-Process -FilePath $python -ArgumentList '-m', 'streamlit', 'run', 'src/agrogami/ui/app.py', '--server.address=127.0.0.1', '--server.port=8501', '--server.headless=true', '--browser.gatherUsageStats=false'
Write-Host 'API on http://127.0.0.1:8000 and UI on http://127.0.0.1:8501 started in their own windows. Close those windows to stop.'
if ($WithTunnel) {
    # Named tunnel "agrogami" from %USERPROFILE%\.cloudflared\config.yml; started only after deployment mode is confirmed above.
    $cloudflared = (Get-Command cloudflared -ErrorAction SilentlyContinue).Source
    if (-not $cloudflared) { $cloudflared = "${env:ProgramFiles(x86)}\cloudflared\cloudflared.exe" }
    Start-Process -FilePath $cloudflared -ArgumentList 'tunnel', 'run', 'agrogami'
    Write-Host 'Cloudflare tunnel "agrogami" started in its own window. Close it to take the site offline.'
}

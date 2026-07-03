<#
    FinVigil AI — one-click dev startup.
    Starts the FastAPI backend and Next.js frontend, each in its own
    terminal window, then opens the app in the browser.

    Run from a PowerShell prompt:  .\start.ps1
    Or right-click -> "Run with PowerShell".
#>

$ErrorActionPreference = "Stop"

$root        = $PSScriptRoot
$backendDir  = Join-Path $root "backend"
$frontendDir = Join-Path $root "frontend"
$venvActivate = Join-Path $backendDir "venv\Scripts\Activate.ps1"
$nodeDir     = "C:\Program Files\nodejs"

Write-Host "FinVigil AI - starting dev environment..." -ForegroundColor Cyan

# --- Sanity checks -----------------------------------------------------
if (-not (Test-Path $venvActivate)) {
    Write-Host "ERROR: backend venv not found at $venvActivate" -ForegroundColor Red
    Write-Host "Set it up first: cd backend; python -m venv venv; .\venv\Scripts\pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}
if (-not (Test-Path (Join-Path $frontendDir "package.json"))) {
    Write-Host "ERROR: frontend project not found at $frontendDir" -ForegroundColor Red
    exit 1
}

# --- 1. Backend: FastAPI in its own window ------------------------------
Write-Host "Starting backend (FastAPI, http://127.0.0.1:8000) ..." -ForegroundColor Green

$backendCommand = "Set-Location -Path `"$backendDir`"; & `"$venvActivate`"; uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
Start-Process powershell.exe -ArgumentList @("-NoExit", "-Command", $backendCommand)

# --- 2. Frontend: Next.js in its own window ------------------------------
Write-Host "Starting frontend (Next.js, http://localhost:3000) ..." -ForegroundColor Green

# Explicitly prepend Node's install dir so this new window's npm/node
# resolve correctly even if PATH hasn't refreshed system-wide yet.
$frontendCommand = "`$env:Path = `"$nodeDir;`" + `$env:Path; Set-Location -Path `"$frontendDir`"; npm run dev"
Start-Process powershell.exe -ArgumentList @("-NoExit", "-Command", $frontendCommand)

# --- 3. Wait for the frontend to come up, then open the browser ---------
Write-Host "Waiting for frontend to be ready..." -ForegroundColor Yellow

$maxWaitSeconds = 30
$elapsed = 0
$ready = $false

while ($elapsed -lt $maxWaitSeconds) {
    Start-Sleep -Seconds 2
    $elapsed += 2
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        $ready = $true
        break
    } catch {
        # not ready yet, keep polling
    }
}

if ($ready) {
    Write-Host "Frontend is up. Opening browser..." -ForegroundColor Green
} else {
    Write-Host "Frontend didn't respond within $maxWaitSeconds s - opening browser anyway (it may still be compiling)." -ForegroundColor Yellow
}

Start-Process "http://localhost:3000"

Write-Host ""
Write-Host "FinVigil AI is starting up:" -ForegroundColor Cyan
Write-Host "  Backend:  http://127.0.0.1:8000  (docs at /docs)"
Write-Host "  Frontend: http://localhost:3000"
Write-Host ""
Write-Host "Two terminal windows were opened for the servers - close them to stop." -ForegroundColor DarkGray

try {
    Read-Host "Press Enter to close this launcher window"
} catch {
    # Non-interactive session (e.g. run via Task Scheduler, or a
    # non-interactive shell) - nothing to wait on, just exit cleanly.
}

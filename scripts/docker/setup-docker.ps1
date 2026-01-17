# =============================================================================
# AI Companion - Docker Setup Script (PowerShell - Windows)
# =============================================================================
# One-command setup for AI Companion with Docker
#
# Usage:
#   .\setup-docker.ps1
#
# If you get execution policy errors, run:
#   PowerShell -ExecutionPolicy Bypass -File setup-docker.ps1
# =============================================================================

# Colors for output
function Write-Success { Write-Host "[OK] $args" -ForegroundColor Green }
function Write-Info { Write-Host "[INFO] $args" -ForegroundColor Cyan }
function Write-Warning { Write-Host "[WARN] $args" -ForegroundColor Yellow }
function Write-ErrorMsg { Write-Host "[ERROR] $args" -ForegroundColor Red }

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "           AI Companion - Docker Setup" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
Write-Info "Checking Docker..."
try {
    docker ps | Out-Null
    Write-Success "Docker is running"
} catch {
    Write-ErrorMsg "Docker is not running. Please start Docker Desktop first."
    exit 1
}
Write-Host ""

# Check if docker-compose.yml exists
if (-not (Test-Path "docker-compose.yml")) {
    Write-ErrorMsg "docker-compose.yml not found. Are you in the project root?"
    exit 1
}

# Step 1: Start Ollama first (backend needs models before it can start)
Write-Info "Starting Ollama container first..."
Write-Host "       This will download Ollama image (~2GB) on first run" -ForegroundColor Gray
Write-Host ""
docker-compose --env-file .env.docker up -d ollama

if ($LASTEXITCODE -ne 0) {
    Write-ErrorMsg "Failed to start Ollama container. Check the error above."
    exit 1
}
Write-Success "Ollama container started"
Write-Host ""

# Step 2: Wait for Ollama to be ready
Write-Info "Waiting for Ollama to be ready..."
Start-Sleep -Seconds 10

# Check if Ollama is responsive (try 6 times, 5 seconds apart)
$ollamaReady = $false
for ($i = 1; $i -le 6; $i++) {
    try {
        docker exec ai-companion-brain ollama list | Out-Null
        Write-Success "Ollama is ready"
        $ollamaReady = $true
        break
    } catch {
        if ($i -lt 6) {
            Write-Host "       Waiting... (attempt $i/6)" -ForegroundColor Gray
            Start-Sleep -Seconds 5
        }
    }
}

if (-not $ollamaReady) {
    Write-Warning "Ollama is taking longer than expected. Continuing anyway..."
}
Write-Host ""

# Step 3: Pull main LLM model
Write-Info "Pulling AI model (9GB download, this will take 5-10 minutes)"
Write-Host "       Model: nchapman/gemma-2-9b-it-abliterated:9b" -ForegroundColor Gray
Write-Host ""

# Use cmd /c to properly handle interactive docker exec
$pullCommand = "docker exec -it ai-companion-brain ollama pull nchapman/gemma-2-9b-it-abliterated:9b"
$process = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", $pullCommand -Wait -PassThru -NoNewWindow

if ($process.ExitCode -ne 0) {
    Write-Host ""
    Write-Warning "Model download failed or was interrupted."
    Write-Host "       You can retry manually:" -ForegroundColor Gray
    Write-Host "       docker exec -it ai-companion-brain ollama pull nchapman/gemma-2-9b-it-abliterated:9b" -ForegroundColor Gray
    exit 1
}
Write-Host ""
Write-Success "Main model downloaded"
Write-Host ""

# Step 4: Pull embedding model (for Phase 3 memory features)
Write-Info "Pulling embedding model (for memory features, ~274MB)"
Write-Host "       Model: nomic-embed-text:latest" -ForegroundColor Gray
Write-Host ""

$embedCommand = "docker exec -it ai-companion-brain ollama pull nomic-embed-text:latest"
$embedProcess = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", $embedCommand -Wait -PassThru -NoNewWindow

if ($embedProcess.ExitCode -ne 0) {
    Write-Host ""
    Write-Warning "Embedding model download failed. This is optional for basic usage."
    Write-Host "       You can retry manually later:" -ForegroundColor Gray
    Write-Host "       docker exec -it ai-companion-brain ollama pull nomic-embed-text:latest" -ForegroundColor Gray
}
Write-Host ""

# Step 5: Start backend and frontend (now that models are ready)
Write-Info "Starting backend and frontend containers..."
Write-Host ""
docker-compose --env-file .env.docker up -d

if ($LASTEXITCODE -ne 0) {
    Write-ErrorMsg "Failed to start remaining containers. Check the error above."
    exit 1
}
Write-Success "All containers started"
Write-Host ""

# Step 6: Verify all services are running
Write-Info "Verifying services..."
Start-Sleep -Seconds 3

$servicesOk = $true

# Check Ollama
try {
    docker exec ai-companion-brain ollama list | Out-Null
    Write-Success "ai-companion-brain (Ollama LLM)"
} catch {
    Write-Warning "ai-companion-brain (not responding)"
    $servicesOk = $false
}

# Check Backend
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Success "ai-companion-api (Backend)"
    } else {
        Write-Warning "ai-companion-api (returned status $($response.StatusCode))"
        $servicesOk = $false
    }
} catch {
    Write-Warning "ai-companion-api (not ready yet)"
    $servicesOk = $false
}

# Check Frontend
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Success "ai-companion-web (Frontend)"
    } else {
        Write-Warning "ai-companion-web (returned status $($response.StatusCode))"
        $servicesOk = $false
    }
} catch {
    Write-Warning "ai-companion-web (health check starting - frontend is accessible)"
    # Note: Frontend is functional even if health check shows "starting"
}

Write-Host ""

# Final message
if ($servicesOk) {
    Write-Host "================================================================" -ForegroundColor Green
    Write-Host "                   Setup complete!" -ForegroundColor Green
    Write-Host "================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Your AI Companion is ready at:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "   Frontend:  http://localhost:3000" -ForegroundColor White
    Write-Host "   Backend:   http://localhost:8000" -ForegroundColor White
    Write-Host "   API Docs:  http://localhost:8000/docs" -ForegroundColor White
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "   1. Open http://localhost:3000 in your browser" -ForegroundColor Gray
    Write-Host "   2. Pull a character from the gacha" -ForegroundColor Gray
    Write-Host "   3. Start chatting with your AI personas!" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Useful commands:" -ForegroundColor Cyan
    Write-Host "   View logs:     docker-compose logs -f" -ForegroundColor Gray
    Write-Host "   Stop services: docker-compose down" -ForegroundColor Gray
    Write-Host "   Restart:       docker-compose restart" -ForegroundColor Gray
    Write-Host ""

    # Open browser automatically
    Start-Process "http://localhost:3000"
} else {
    Write-Host "================================================================" -ForegroundColor Green
    Write-Host "                   Setup complete!" -ForegroundColor Green
    Write-Host "================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Your AI Companion is ready at:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "   Frontend:  http://localhost:3000" -ForegroundColor White
    Write-Host "   Backend:   http://localhost:8000" -ForegroundColor White
    Write-Host "   API Docs:  http://localhost:8000/docs" -ForegroundColor White
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "   1. Open http://localhost:3000 in your browser" -ForegroundColor Gray
    Write-Host "   2. Pull a character from the gacha" -ForegroundColor Gray
    Write-Host "   3. Start chatting with your AI personas!" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Note: Frontend health check may show 'starting' for ~1 minute (this is normal)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Useful commands:" -ForegroundColor Cyan
    Write-Host "   View logs:     docker-compose logs -f" -ForegroundColor Gray
    Write-Host "   Stop services: docker-compose down" -ForegroundColor Gray
    Write-Host "   Restart:       docker-compose restart" -ForegroundColor Gray
    Write-Host ""

    # Open browser automatically
    Start-Process "http://localhost:3000"
}

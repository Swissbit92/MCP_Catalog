# =============================================================================
# MCP Coordinator - Docker Setup Test Script (PowerShell)
# =============================================================================
# Tests that Docker Compose stack is running correctly with SQLite
#
# Usage:
#   .\test_docker_setup.ps1
# =============================================================================

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "MCP Coordinator Docker Setup Test" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

function Pass {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Fail {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor Red
    exit 1
}

function Warn {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor Yellow
}

# Check if Docker is running
Write-Host "1. Checking Docker..." -ForegroundColor White
try {
    docker ps | Out-Null
    Pass "Docker is running"
} catch {
    Fail "Docker is not running. Please start Docker Desktop."
}
Write-Host ""

# Check if docker-compose.yml exists
Write-Host "2. Checking docker-compose.yml..." -ForegroundColor White
if (Test-Path "docker-compose.yml") {
    Pass "docker-compose.yml found"
} else {
    Fail "docker-compose.yml not found. Are you in the project root?"
}
Write-Host ""

# Check if .env.docker exists
Write-Host "3. Checking .env.docker..." -ForegroundColor White
if (Test-Path ".env.docker") {
    Pass ".env.docker found"
} else {
    Warn ".env.docker not found (optional, will use defaults)"
}
Write-Host ""

# Check if data directory exists
Write-Host "4. Checking data directory..." -ForegroundColor White
if (Test-Path "data") {
    Pass "Data directory exists"
} else {
    Write-Host "Creating data directory..." -ForegroundColor Gray
    New-Item -ItemType Directory -Path "data" | Out-Null
    Pass "Created data directory"
}
Write-Host ""

# Check if containers are running
Write-Host "5. Checking running containers..." -ForegroundColor White
$containers = docker-compose ps
if ($containers -match "Up") {
    Pass "Containers are running"
} else {
    Warn "Containers not running. Starting stack..."
    docker-compose --env-file .env.docker up -d
    Write-Host "Waiting for services to start (30 seconds)..." -ForegroundColor Gray
    Start-Sleep -Seconds 30
}
Write-Host ""

# Check individual services
Write-Host "6. Checking service health..." -ForegroundColor White

if ($containers -match "mcp_ollama.*Up") {
    Pass "Ollama container is running"
} else {
    Fail "Ollama container is not running"
}

if ($containers -match "mcp_backend.*Up") {
    Pass "Backend container is running"
} else {
    Fail "Backend container is not running"
}

if ($containers -match "mcp_frontend.*Up") {
    Pass "Frontend container is running"
} else {
    Fail "Frontend container is not running"
}
Write-Host ""

# Check backend health endpoint
Write-Host "7. Checking service health status..." -ForegroundColor White
Start-Sleep -Seconds 5

Write-Host "Checking backend health endpoint..." -ForegroundColor Gray
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Pass "Backend health check passed"
    } else {
        Warn "Backend health check returned status $($response.StatusCode)"
    }
} catch {
    Warn "Backend health check failed (may still be starting up)"
    Write-Host "   Waiting 30 more seconds..." -ForegroundColor Gray
    Start-Sleep -Seconds 30
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
        Pass "Backend health check passed (after wait)"
    } catch {
        Fail "Backend health check failed"
    }
}
Write-Host ""

# Check frontend
Write-Host "Checking frontend..." -ForegroundColor Gray
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Pass "Frontend is accessible"
    }
} catch {
    Warn "Frontend not accessible yet (may still be building)"
}
Write-Host ""

# Check Ollama
Write-Host "Checking Ollama..." -ForegroundColor Gray
try {
    $ollamaList = docker exec mcp_ollama ollama list 2>&1
    Pass "Ollama is responsive"

    # Check if model is pulled
    if ($ollamaList -match "dolphin-llama3:8b") {
        Pass "Model 'dolphin-llama3:8b' is available"
    } elseif ($ollamaList -match "llama3.1") {
        Pass "Model 'llama3.1:latest' is available"
    } else {
        Warn "No LLM model found"
        Write-Host "   Run: docker exec -it mcp_ollama ollama pull dolphin-llama3:8b" -ForegroundColor Gray
    }
} catch {
    Fail "Ollama is not responsive"
}
Write-Host ""

# Check data persistence
Write-Host "8. Checking data persistence..." -ForegroundColor White
if (Test-Path "data\chats.db") {
    Pass "SQLite database exists (data\chats.db)"
    $size = (Get-Item "data\chats.db").Length / 1KB
    Write-Host "   Database size: $([math]::Round($size, 2)) KB" -ForegroundColor Gray
} else {
    Warn "SQLite database not created yet (normal for first run)"
}
Write-Host ""

# Check persona files
Write-Host "9. Checking persona files..." -ForegroundColor White
if (Test-Path "personas") {
    $personaFiles = Get-ChildItem "personas\*.json" -ErrorAction SilentlyContinue
    Pass "Found $($personaFiles.Count) persona files"

    if (Test-Path "personas\_summaries") {
        $summaryFiles = Get-ChildItem "personas\_summaries\*.json" -ErrorAction SilentlyContinue
        if ($summaryFiles.Count -gt 0) {
            Pass "Found $($summaryFiles.Count) persona summaries (cache)"
        } else {
            Warn "No persona summaries yet (will be auto-generated)"
        }
    }
} else {
    Fail "Personas directory not found"
}
Write-Host ""

# Test API endpoints
Write-Host "10. Testing API endpoints..." -ForegroundColor White
try {
    $healthResponse = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 5
    if ($healthResponse.status -eq "ok") {
        Pass "Health endpoint returns 'ok'"

        # Try to get personas
        try {
            $personasResponse = Invoke-RestMethod -Uri "http://localhost:8000/personas" -TimeoutSec 5
            if ($personasResponse.personas) {
                Pass "Personas endpoint working"
            }
        } catch {
            Warn "Personas endpoint returned unexpected response"
        }
    } else {
        Fail "Health endpoint not returning 'ok'"
    }
} catch {
    Fail "Cannot connect to API endpoints"
}
Write-Host ""

# Final summary
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Test Summary" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Pass "Docker Compose stack is running"
Pass "All core services are operational"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host "1. Open http://localhost:3000 in your browser" -ForegroundColor Gray
Write-Host "2. Pull an LLM model if not done:" -ForegroundColor Gray
Write-Host "   docker exec -it mcp_ollama ollama pull dolphin-llama3:8b" -ForegroundColor Gray
Write-Host "3. Start chatting with personas!" -ForegroundColor Gray
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor White
Write-Host "  - View logs: docker-compose logs -f" -ForegroundColor Gray
Write-Host "  - Restart: docker-compose restart" -ForegroundColor Gray
Write-Host "  - Stop: docker-compose down" -ForegroundColor Gray
Write-Host "  - Backup: Copy-Item data\chats.db data\chats.db.backup" -ForegroundColor Gray
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan

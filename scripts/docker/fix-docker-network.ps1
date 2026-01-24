# =============================================================================
# MCP Coordinator - Docker Network Troubleshooter
# =============================================================================
# Fixes common Docker networking issues including orphaned network references
# Usage: .\fix-docker-network.ps1 [options]
# Options:
#   -Quick       Quick fix (recommended) - stops, cleans, restarts
#   -Nuclear     Full cleanup - removes everything and rebuilds
#   -Verify      Only verify current state without making changes
# =============================================================================

param(
    [switch]$Quick,
    [switch]$Nuclear,
    [switch]$Verify
)

# Color output helpers
function Write-Success { param($Message) Write-Host "✓ $Message" -ForegroundColor Green }
function Write-Error { param($Message) Write-Host "✗ $Message" -ForegroundColor Red }
function Write-Info { param($Message) Write-Host "ℹ $Message" -ForegroundColor Cyan }
function Write-Warning { param($Message) Write-Host "⚠ $Message" -ForegroundColor Yellow }
function Write-Step { param($Message) Write-Host "`n▶ $Message" -ForegroundColor Yellow }

# Check if Docker is running
function Test-DockerRunning {
    try {
        docker version | Out-Null
        return $true
    } catch {
        return $false
    }
}

# Verify Docker Compose file exists
function Test-DockerComposeFile {
    return Test-Path "docker-compose.yml"
}

# Get container status
function Get-MCPContainerStatus {
    $containers = @("ai-companion-brain", "ai-companion-api", "ai-companion-web")
    $status = @{}

    foreach ($container in $containers) {
        $result = docker ps -a --filter "name=$container" --format "{{.Status}}" 2>$null
        $status[$container] = if ($result) { $result } else { "Not Found" }
    }

    return $status
}

# Get network status
function Get-MCPNetworkStatus {
    $network = docker network ls --filter "name=mcp" --format "{{.Name}}" 2>$null
    return $network
}

# Verify environment
function Test-Environment {
    Write-Step "Checking environment..."

    if (-not (Test-DockerRunning)) {
        Write-Error "Docker is not running. Please start Docker Desktop and try again."
        exit 1
    }
    Write-Success "Docker is running"

    if (-not (Test-DockerComposeFile)) {
        Write-Error "docker-compose.yml not found. Please run this script from the MCP_Catalog directory."
        exit 1
    }
    Write-Success "Found docker-compose.yml"

    if (-not (Test-Path ".env.docker")) {
        Write-Warning ".env.docker not found. Will use default environment variables."
    } else {
        Write-Success "Found .env.docker"
    }
}

# Display current status
function Show-CurrentStatus {
    Write-Step "Current Status"

    Write-Info "Containers:"
    $status = Get-MCPContainerStatus
    foreach ($container in $status.Keys) {
        $statusText = $status[$container]
        if ($statusText -match "Up") {
            Write-Host "  $container : " -NoNewline
            Write-Host "$statusText" -ForegroundColor Green
        } elseif ($statusText -eq "Not Found") {
            Write-Host "  $container : " -NoNewline
            Write-Host "$statusText" -ForegroundColor Gray
        } else {
            Write-Host "  $container : " -NoNewline
            Write-Host "$statusText" -ForegroundColor Yellow
        }
    }

    Write-Info "`nNetworks:"
    $networks = docker network ls --filter "name=mcp" --format "{{.Name}}" 2>$null
    if ($networks) {
        foreach ($net in $networks) {
            Write-Host "  $net" -ForegroundColor Green
        }
    } else {
        Write-Host "  No MCP networks found" -ForegroundColor Gray
    }

    Write-Info "`nOrphaned Networks:"
    $orphaned = docker network ls --filter "dangling=true" --format "{{.Name}}" 2>$null
    if ($orphaned) {
        foreach ($net in $orphaned) {
            Write-Host "  $net" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  None" -ForegroundColor Green
    }
}

# Quick Fix - Recommended approach
function Invoke-QuickFix {
    Write-Step "Executing Quick Fix..."

    Write-Info "Step 1/4: Stopping containers..."
    docker-compose down 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Containers stopped"
    } else {
        Write-Warning "Some containers may not have stopped cleanly (this is okay)"
    }

    Write-Info "Step 2/4: Pruning orphaned networks..."
    $pruned = docker network prune -f 2>&1
    Write-Success "Network cleanup complete"

    Write-Info "Step 3/4: Starting services..."
    docker-compose --env-file .env.docker up -d 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Services started"
    } else {
        Write-Error "Failed to start services. Check logs with: docker-compose logs"
        exit 1
    }

    Write-Info "Step 4/4: Waiting for health checks (40s)..."
    Start-Sleep -Seconds 40

    Write-Success "Quick fix complete!"
}

# Nuclear Option - Full cleanup and rebuild
function Invoke-NuclearFix {
    Write-Step "Executing Nuclear Fix..."
    Write-Warning "This will rebuild all containers from scratch."

    $confirm = Read-Host "Continue? (yes/no)"
    if ($confirm -ne "yes") {
        Write-Info "Aborted."
        exit 0
    }

    Write-Info "Step 1/7: Stopping all MCP containers..."
    docker stop ai-companion-brain ai-companion-api ai-companion-web 2>$null
    Write-Success "Containers stopped"

    Write-Info "Step 2/7: Removing containers..."
    docker rm ai-companion-brain ai-companion-api ai-companion-web 2>$null
    Write-Success "Containers removed"

    Write-Info "Step 3/7: Removing MCP network..."
    docker network rm mcp_catalog_mcp-network 2>$null
    Write-Success "Network removed"

    Write-Info "Step 4/7: Pruning all orphaned networks..."
    docker network prune -f | Out-Null
    Write-Success "Orphaned networks cleaned"

    Write-Info "Step 5/7: Rebuilding images..."
    docker-compose --env-file .env.docker build --no-cache 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Images rebuilt"
    } else {
        Write-Error "Failed to rebuild images"
        exit 1
    }

    Write-Info "Step 6/7: Starting services..."
    docker-compose --env-file .env.docker up -d 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Services started"
    } else {
        Write-Error "Failed to start services"
        exit 1
    }

    Write-Info "Step 7/7: Waiting for health checks (40s)..."
    Start-Sleep -Seconds 40

    Write-Success "Nuclear fix complete!"
}

# Verify services are working
function Test-Services {
    Write-Step "Verifying Services..."

    Write-Info "Container Status:"
    $status = Get-MCPContainerStatus
    $allUp = $true
    foreach ($container in $status.Keys) {
        $statusText = $status[$container]
        if ($statusText -match "Up") {
            Write-Success "$container is running"
        } else {
            Write-Error "$container is not running: $statusText"
            $allUp = $false
        }
    }

    Write-Info "`nNetwork Status:"
    $network = Get-MCPNetworkStatus
    if ($network) {
        Write-Success "Network '$network' exists"
    } else {
        Write-Error "MCP network not found"
        $allUp = $false
    }

    Write-Info "`nHealth Checks:"

    # Test backend
    Write-Host "  Backend API: " -NoNewline
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5 -UseBasicParsing 2>$null
        if ($response.StatusCode -eq 200) {
            Write-Host "✓ Healthy" -ForegroundColor Green
        } else {
            Write-Host "✗ Unhealthy (HTTP $($response.StatusCode))" -ForegroundColor Red
            $allUp = $false
        }
    } catch {
        Write-Host "✗ Not responding" -ForegroundColor Red
        $allUp = $false
    }

    # Test frontend
    Write-Host "  Frontend: " -NoNewline
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:3000" -TimeoutSec 5 -UseBasicParsing 2>$null
        if ($response.StatusCode -eq 200) {
            Write-Host "✓ Healthy" -ForegroundColor Green
        } else {
            Write-Host "✗ Unhealthy (HTTP $($response.StatusCode))" -ForegroundColor Red
            $allUp = $false
        }
    } catch {
        Write-Host "✗ Not responding" -ForegroundColor Red
        $allUp = $false
    }

    # Test Ollama
    Write-Host "  Ollama LLM: " -NoNewline
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:11434" -TimeoutSec 5 -UseBasicParsing 2>$null
        Write-Host "✓ Healthy" -ForegroundColor Green
    } catch {
        Write-Host "✗ Not responding" -ForegroundColor Red
        $allUp = $false
    }

    if ($allUp) {
        Write-Success "`nAll services are healthy!"
        Write-Info "`nAccess URLs:"
        Write-Host "  Frontend: " -NoNewline -ForegroundColor Cyan
        Write-Host "http://localhost:3000" -ForegroundColor White
        Write-Host "  Backend API: " -NoNewline -ForegroundColor Cyan
        Write-Host "http://localhost:8000/docs" -ForegroundColor White
        Write-Host "  Ollama: " -NoNewline -ForegroundColor Cyan
        Write-Host "http://localhost:11434" -ForegroundColor White
    } else {
        Write-Error "`nSome services are unhealthy. Check logs with:"
        Write-Host "  docker-compose logs -f" -ForegroundColor Yellow
    }

    return $allUp
}

# Main script execution
Write-Host @"

╔════════════════════════════════════════════════════════════════╗
║  MCP Coordinator - Docker Network Troubleshooter              ║
║  Fixes orphaned networks and container connectivity issues    ║
╚════════════════════════════════════════════════════════════════╝

"@ -ForegroundColor Cyan

Test-Environment

# Default to Quick fix if no option specified
if (-not $Quick -and -not $Nuclear -and -not $Verify) {
    $Quick = $true
}

Show-CurrentStatus

if ($Verify) {
    Write-Info "`nVerify mode - no changes will be made"
    Test-Services
    exit 0
}

if ($Quick) {
    Invoke-QuickFix
} elseif ($Nuclear) {
    Invoke-NuclearFix
}

Write-Host ""
Test-Services

Write-Host "`n" -NoNewline
Write-Info "Troubleshooting complete!"
Write-Host ""

# [REFERENCE ONLY — Windows] Dev helper from the original Windows environment.
# Superseded on the macOS deployment by launchd (com.nephilim.backend / com.nephilim.frontend)
# and the npm scripts in package.json. Kept for Windows reference; not used on macOS.

try {
    $resp = Invoke-WebRequest -Uri 'http://localhost:8000/health' -TimeoutSec 5
    Write-Host "BACKEND UP: $($resp.Content)"
} catch {
    Write-Host "BACKEND DOWN: $($_.Exception.Message)"
}

try {
    $resp = Invoke-WebRequest -Uri 'http://localhost:8000/docs' -TimeoutSec 5
    Write-Host "BACKEND DOCS UP: status $($resp.StatusCode)"
} catch {
    Write-Host "BACKEND DOCS DOWN"
}

try {
    $resp = Invoke-WebRequest -Uri 'http://localhost:3001' -TimeoutSec 5
    Write-Host "FRONTEND UP: status $($resp.StatusCode), content length $($resp.Content.Length)"
} catch {
    Write-Host "FRONTEND DOWN: $($_.Exception.Message)"
}

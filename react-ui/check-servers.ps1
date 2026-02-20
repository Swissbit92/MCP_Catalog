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

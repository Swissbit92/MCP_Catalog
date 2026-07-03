# [REFERENCE ONLY — Windows] Dev helper from the original Windows environment.
# Superseded on the macOS deployment by launchd (com.nephilim.backend / com.nephilim.frontend)
# and the npm scripts in package.json. Kept for Windows reference; not used on macOS.

$maxWait = 90
$interval = 5
$elapsed = 0

Write-Host "Checking if port 3001 is up..."

while ($elapsed -lt $maxWait) {
    $conn = Get-NetTCPConnection -LocalPort 3001 -State Listen -ErrorAction SilentlyContinue
    if ($conn) {
        Write-Host "PORT 3001 IS LISTENING after ${elapsed}s"
        # Try HTTP request
        try {
            $resp = Invoke-WebRequest -Uri 'http://localhost:3001' -TimeoutSec 5 -UseBasicParsing
            Write-Host "HTTP 3001 OK: status $($resp.StatusCode)"
        } catch {
            Write-Host "HTTP 3001 not yet responding to HTTP"
        }
        break
    }
    Write-Host "Waiting... ${elapsed}s elapsed"
    Start-Sleep -Seconds $interval
    $elapsed += $interval
}

if ($elapsed -ge $maxWait) {
    Write-Host "TIMEOUT: port 3001 never came up after ${maxWait}s"
    # Show log tail
    $logFile = "C:\Users\rzehn\AppData\Local\Temp\react-frontend.log"
    if (Test-Path $logFile) {
        Write-Host "=== Last 30 lines of log ==="
        Get-Content $logFile -Tail 30
    } else {
        Write-Host "Log file not found at $logFile"
    }
}

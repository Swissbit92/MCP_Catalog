# [REFERENCE ONLY — Windows] Dev helper from the original Windows environment.
# Superseded on the macOS deployment by launchd (com.nephilim.backend / com.nephilim.frontend)
# and the npm scripts in package.json. Kept for Windows reference; not used on macOS.

$ports = @(8000, 3001, 3000, 11434)
$connections = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue
foreach ($port in $ports) {
    $match = $connections | Where-Object { $_.LocalPort -eq $port }
    if ($match) {
        $proc = Get-Process -Id $match.OwningProcess -ErrorAction SilentlyContinue
        Write-Host "PORT $port : LISTENING (PID $($match.OwningProcess) - $($proc.ProcessName))"
    } else {
        Write-Host "PORT $port : NOT LISTENING"
    }
}

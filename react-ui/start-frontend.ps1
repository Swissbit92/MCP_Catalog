$logFile = "C:\Users\rzehn\AppData\Local\Temp\react-frontend.log"
$workDir = "C:\Users\rzehn\desktop\MCP_Catalog\react-ui"

$proc = Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c", "cd /d $workDir && set PORT=3001 && npx react-scripts start >> $logFile 2>&1" `
    -WindowStyle Hidden `
    -PassThru

Write-Host "Started frontend process PID: $($proc.Id)"
Write-Host "Log file: $logFile"

$urls = @(
    'http://localhost:8000/health',
    'http://localhost:8000/',
    'http://localhost:8000/docs',
    'http://localhost:8000/personas'
)
foreach ($url in $urls) {
    try {
        $resp = Invoke-WebRequest -Uri $url -TimeoutSec 8 -UseBasicParsing
        Write-Host "OK [$($resp.StatusCode)] $url : $($resp.Content.Substring(0, [Math]::Min(120, $resp.Content.Length)))"
    } catch {
        Write-Host "FAIL $url : $($_.Exception.Message)"
    }
}

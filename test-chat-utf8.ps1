# PowerShell script to test chat API with proper UTF-8 encoding
# Set console output encoding to UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# Test the chat endpoint
$body = @{
    userId = "u1"
    message = "hello"
    timezone = "Asia/Hebron"
    dialect = "pal"
} | ConvertTo-Json

$headers = @{
    "Authorization" = "Bearer x"
    "Content-Type" = "application/json; charset=utf-8"
}

try {
    # Use Invoke-RestMethod which handles JSON and UTF-8 better
    $response = Invoke-RestMethod -Uri "http://localhost:8000/v1/chat" -Method POST -Body $body -Headers $headers -ContentType "application/json; charset=utf-8"
    
    Write-Host "`n=== Response ===" -ForegroundColor Green
    Write-Host "Reply: $($response.reply)" -ForegroundColor Cyan
    Write-Host "Needs Clarification: $($response.needsClarification)" -ForegroundColor Yellow
    Write-Host "Request ID: $($response.requestId)" -ForegroundColor Gray
    
    # Also display as JSON to verify encoding
    Write-Host "`n=== JSON Response ===" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 10 | Out-String -Width 200
    
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $reader.BaseStream.Position = 0
        $reader.DiscardBufferedData()
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response: $responseBody" -ForegroundColor Yellow
    }
}

# PowerShell script to test chat API with proper UTF-8 encoding
# Set console output encoding to UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# Clear any previous errors
$Error.Clear()

Write-Host "`n=== Testing Chat API ===" -ForegroundColor Cyan
Write-Host ""

# Test the chat endpoint
$body = @{
    userId = "u1"
    message = "hello"
    timezone = "Asia/Hebron"
    dialect = "pal"
} | ConvertTo-Json -Compress

$headers = @{
    "Authorization" = "Bearer x"
    "Content-Type" = "application/json; charset=utf-8"
}

try {
    Write-Host "Sending request to http://localhost:8000/v1/chat..." -ForegroundColor Yellow
    
    # Use Invoke-RestMethod which handles JSON and UTF-8 better
    $response = Invoke-RestMethod `
        -Uri "http://localhost:8000/v1/chat" `
        -Method POST `
        -Body $body `
        -Headers $headers `
        -ContentType "application/json; charset=utf-8"
    
    Write-Host "`n=== Response ===" -ForegroundColor Green
    Write-Host "Reply: $($response.reply)" -ForegroundColor Cyan
    Write-Host "Needs Clarification: $($response.needsClarification)" -ForegroundColor Yellow
    Write-Host "Request ID: $($response.requestId)" -ForegroundColor Gray
    
    # Also display as JSON to verify encoding
    Write-Host "`n=== Full JSON Response ===" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 10
    
} catch {
    Write-Host "`n=== Error Occurred ===" -ForegroundColor Red
    Write-Host "Error Type: $($_.Exception.GetType().FullName)" -ForegroundColor Red
    Write-Host "Error Message: $($_.Exception.Message)" -ForegroundColor Red
    
    # Try to get response body if available
    if ($_.Exception.Response) {
        try {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $reader.BaseStream.Position = 0
            $reader.DiscardBufferedData()
            $responseBody = $reader.ReadToEnd()
            Write-Host "`nResponse Body:" -ForegroundColor Yellow
            Write-Host $responseBody -ForegroundColor Yellow
        } catch {
            Write-Host "Could not read response body: $_" -ForegroundColor Red
        }
    }
    
    Write-Host "`nFull Error Details:" -ForegroundColor Red
    $_
}

Write-Host "`n=== Test Complete ===" -ForegroundColor Cyan

param(
    [Parameter(Mandatory = $true)]
    [string]$Prompt,
    [string]$ApiBase = "http://localhost:8000"
)

$response = Invoke-RestMethod -Method Post -Uri "$ApiBase/jobs" `
    -ContentType "text/plain; charset=utf-8" `
    -Body $Prompt

$response | ConvertTo-Json -Depth 5

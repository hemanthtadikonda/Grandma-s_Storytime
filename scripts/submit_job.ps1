param(
    [Parameter(Mandatory = $true)]
    [string]$Prompt,
    [string]$TemplateId = "kids_moral_v1",
    [string]$ApiBase = "http://localhost:8000"
)

$body = @{
    prompt              = $Prompt
    template_id         = $TemplateId
    duration_target_sec = 60
    content_source      = "original"
} | ConvertTo-Json

$response = Invoke-RestMethod -Method Post -Uri "$ApiBase/jobs" -Body $body -ContentType "application/json"
$response | ConvertTo-Json -Depth 5

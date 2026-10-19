param(
    [Parameter(Mandatory = $true)]
    [string]$JobId,
    [string]$ApiBase = "http://localhost:8000",
    [int]$IntervalSec = 3
)

while ($true) {
    $job = Invoke-RestMethod -Uri "$ApiBase/jobs/$JobId"
    $job | ConvertTo-Json -Depth 5
    if ($job.status -in @("done", "failed")) {
        break
    }
    Start-Sleep -Seconds $IntervalSec
}

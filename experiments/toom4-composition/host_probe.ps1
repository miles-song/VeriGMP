$ErrorActionPreference = 'Stop'
$first = @{}
Get-Process | Where-Object { $_.Id -ne $PID -and $null -ne $_.CPU } | ForEach-Object {
    $first[$_.Id] = @{ Name = $_.ProcessName; CPU = $_.CPU }
}
$watch = [System.Diagnostics.Stopwatch]::StartNew()
Start-Sleep -Seconds 1
$rows = @(Get-Process | Where-Object { $_.Id -ne $PID -and $null -ne $_.CPU -and $first.ContainsKey($_.Id) } | ForEach-Object {
    $percentage = 100 * ($_.CPU - $first[$_.Id].CPU) / $watch.Elapsed.TotalSeconds
    if ($percentage -gt 0) { @{ Id = $_.Id; Name = $_.ProcessName; CPUPercent = $percentage } }
})
@{ Status = 'pass'; Rows = $rows; Seconds = $watch.Elapsed.TotalSeconds } | ConvertTo-Json -Depth 4 -Compress

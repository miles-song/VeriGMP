param(
    [Parameter(Mandatory = $true)][string]$Output,
    [int]$IntervalSeconds = 2
)

if ($IntervalSeconds -lt 2 -or (Test-Path -LiteralPath $Output)) {
    throw 'Use a new output file and a sampling interval of at least two seconds.'
}
while ($true) {
    $row = [ordered]@{
        utc = [DateTime]::UtcNow.ToString('o')
        processors = @(Get-CimInstance Win32_Processor | Select-Object DeviceID, LoadPercentage, CurrentClockSpeed, MaxClockSpeed, NumberOfLogicalProcessors)
        system = Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor -Filter "Name='_Total'" | Select-Object PercentProcessorTime
        memory = Get-CimInstance Win32_OperatingSystem | Select-Object FreePhysicalMemory, TotalVisibleMemorySize
        processes = @(Get-Process | Select-Object Id, ProcessName, CPU)
    }
    if ($null -eq $row.system -or $row.processors.Count -eq 0) {
        throw 'Windows CPU telemetry is unavailable.'
    }
    $row | ConvertTo-Json -Depth 5 -Compress | Add-Content -LiteralPath $Output -Encoding utf8
    Start-Sleep -Seconds $IntervalSeconds
}

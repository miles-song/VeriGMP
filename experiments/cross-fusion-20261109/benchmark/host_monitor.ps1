param(
    [Parameter(Mandatory = $true)][string]$Output,
    [Parameter(Mandatory = $true)][string]$StopFile
)

$ErrorActionPreference = 'Stop'
if (Test-Path -LiteralPath $Output) { throw 'Output must be a new file.' }
if (Test-Path -LiteralPath $StopFile) { throw 'Stop marker already exists.' }
if ([IntPtr]::Size -ne 8) { throw 'The process snapshot requires 64-bit PowerShell.' }

# Native process snapshots include CPU counters even for protected processes.
Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;

public static class CrossFusionHostSnapshot {
    [StructLayout(LayoutKind.Sequential)] struct UnicodeString {
        public ushort Length, MaximumLength;
        public IntPtr Buffer;
    }
    [StructLayout(LayoutKind.Sequential)] struct ProcessInfo {
        public uint NextEntryOffset, NumberOfThreads;
        public long WorkingSetPrivateSize;
        public uint HardFaultCount, NumberOfThreadsHighWatermark;
        public ulong CycleTime;
        public long CreateTime, UserTime, KernelTime;
        public UnicodeString ImageName;
        public int BasePriority;
        public IntPtr UniqueProcessId, InheritedFromUniqueProcessId;
    }
    [StructLayout(LayoutKind.Sequential)] struct ProcessorInfo {
        public long IdleTime, KernelTime, UserTime, DpcTime, InterruptTime;
        public uint InterruptCount;
    }
    [StructLayout(LayoutKind.Sequential)] struct MemoryStatus {
        public uint Length, MemoryLoad;
        public ulong TotalPhysical, AvailablePhysical, TotalPageFile, AvailablePageFile;
        public ulong TotalVirtual, AvailableVirtual, AvailableExtendedVirtual;
    }
    [DllImport("ntdll.dll")] static extern int NtQuerySystemInformation(
        int informationClass, IntPtr buffer, int length, out int returnLength);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool GlobalMemoryStatusEx(ref MemoryStatus status);
    public sealed class ProcessRow {
        public long pid, start_100ns, cpu_100ns;
        public string name;
    }
    public sealed class CpuRow {
        public long idle_100ns, kernel_100ns, user_100ns;
    }
    public sealed class MemoryRow {
        public uint load_percent;
        public ulong total_physical, available_physical, total_pagefile, available_pagefile;
    }
    public static ProcessRow[] Processes() {
        int size = 1024 * 1024, used, status;
        while (true) {
            IntPtr data = Marshal.AllocHGlobal(size);
            try {
                status = NtQuerySystemInformation(5, data, size, out used);
                if (unchecked((uint)status) == 0xC0000004) { size = Math.Max(size * 2, used + 65536); continue; }
                if (status != 0) throw new Exception("process snapshot NTSTATUS " + status);
                var rows = new List<ProcessRow>();
                int offset = 0;
                while (true) {
                    var info = (ProcessInfo)Marshal.PtrToStructure(IntPtr.Add(data, offset), typeof(ProcessInfo));
                    string name = info.ImageName.Buffer == IntPtr.Zero ? "" :
                        Marshal.PtrToStringUni(info.ImageName.Buffer, info.ImageName.Length / 2);
                    rows.Add(new ProcessRow { pid = info.UniqueProcessId.ToInt64(),
                        start_100ns = info.CreateTime, cpu_100ns = info.UserTime + info.KernelTime, name = name });
                    if (info.NextEntryOffset == 0) break;
                    offset += checked((int)info.NextEntryOffset);
                    if (offset >= used) throw new Exception("invalid process snapshot offset");
                }
                return rows.ToArray();
            } finally { Marshal.FreeHGlobal(data); }
        }
    }
    public static CpuRow[] Cpus() {
        int stride = Marshal.SizeOf(typeof(ProcessorInfo)), size = Environment.ProcessorCount * stride, used;
        for (int attempt = 0; attempt < 3; attempt++) {
            IntPtr data = Marshal.AllocHGlobal(size);
            try {
                int status = NtQuerySystemInformation(8, data, size, out used);
                if (unchecked((uint)status) == 0xC0000004 && used > 0) { size = used; continue; }
                if (status != 0 || used <= 0 || used % stride != 0)
                    throw new Exception("invalid processor snapshot: status=" + status + ", bytes=" + used + ", stride=" + stride);
                var rows = new List<CpuRow>();
                for (int offset = 0; offset < used; offset += stride) {
                    var cpu = (ProcessorInfo)Marshal.PtrToStructure(IntPtr.Add(data, offset), typeof(ProcessorInfo));
                    rows.Add(new CpuRow { idle_100ns = cpu.IdleTime, kernel_100ns = cpu.KernelTime, user_100ns = cpu.UserTime });
                }
                return rows.ToArray();
            } finally { Marshal.FreeHGlobal(data); }
        }
        throw new Exception("processor count changed repeatedly");
    }
    public static MemoryRow Memory() {
        var state = new MemoryStatus();
        state.Length = (uint)Marshal.SizeOf(typeof(MemoryStatus));
        if (!GlobalMemoryStatusEx(ref state)) throw new Exception("memory snapshot unavailable");
        return new MemoryRow { load_percent = state.MemoryLoad, total_physical = state.TotalPhysical,
            available_physical = state.AvailablePhysical, total_pagefile = state.TotalPageFile,
            available_pagefile = state.AvailablePageFile };
    }
}
'@

$file = [System.IO.File]::Open($Output, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::Read)
$writer = New-Object System.IO.StreamWriter($file, (New-Object System.Text.UTF8Encoding($false)))
$writer.AutoFlush = $true
$clock = [Diagnostics.Stopwatch]::StartNew()
$deadline = 0L
function Write-WslInventory([string]$phase) {
    $result = (& wsl.exe --list --verbose 2>&1 | Out-String).Replace([string][char]0, '')
    $exitCode = $LASTEXITCODE
    $power = (& powercfg.exe /getactivescheme 2>&1 | Out-String).Trim()
    $powerExit = $LASTEXITCODE
    $row = [ordered]@{ record = 'wsl_inventory'; phase = $phase;
        utc = [DateTime]::UtcNow.ToString('o'); exit_code = $exitCode; output = $result;
        power_exit_code = $powerExit; power_plan = $power;
        os_version = [Environment]::OSVersion.VersionString;
        cpu_name = (Get-ItemProperty 'HKLM:\HARDWARE\DESCRIPTION\System\CentralProcessor\0').ProcessorNameString }
    $writer.WriteLine(($row | ConvertTo-Json -Depth 3 -Compress))
    if ($exitCode -ne 0 -or $powerExit -ne 0) { throw 'Could not enumerate WSL distributions or host power plan.' }
}
try {
    Write-WslInventory 'before'
    $clock.Restart()
    while ($true) {
        $start = [DateTime]::UtcNow.ToString('o')
        $started = $clock.ElapsedMilliseconds
        $processes = @([CrossFusionHostSnapshot]::Processes())
        $cpus = @([CrossFusionHostSnapshot]::Cpus())
        $memory = [CrossFusionHostSnapshot]::Memory()
        $monitor = @($processes | Where-Object { $_.pid -eq $PID })
        if ($monitor.Count -ne 1) { throw 'Host monitor identity missing from process snapshot.' }
        $row = [ordered]@{
            record = 'sample'
            utc_start = $start
            utc_end = [DateTime]::UtcNow.ToString('o')
            monotonic_ms = $started
            processes = $processes
            monitor = @{ pid = $monitor[0].pid; start_100ns = $monitor[0].start_100ns }
            cpus = $cpus
            memory = $memory
            throttling = 'unknown: no reliable temperature or actual frequency source'
        }
        $writer.WriteLine(($row | ConvertTo-Json -Depth 5 -Compress))
        if (Test-Path -LiteralPath $StopFile) { break }
        $deadline += 1000
        $delay = $deadline - $clock.ElapsedMilliseconds
        if ($delay -gt 0) { Start-Sleep -Milliseconds $delay }
    }
    Write-WslInventory 'after'
} finally { $writer.Dispose() }

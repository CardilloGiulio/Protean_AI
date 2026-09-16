param(
    [ValidateRange(10, 1440)]
    [int]$DurationMinutes = 60,
    [ValidateRange(1, 60)]
    [int]$SampleSeconds = 5,
    [ValidateRange(1, 4096)]
    [int]$MaxElectronWorkingSetGrowthMB = 300,
    [ValidateRange(1, 4096)]
    [int]$MaxElectronPrivateGrowthMB = 300
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Artifacts = Join-Path $ProjectRoot "artifacts"
$ElectronMain = Join-Path $ProjectRoot "src\protean_workspace\assistant_shell\main.js"

if ($env:OS -ne "Windows_NT") {
    throw "This native certification harness must run on Windows."
}
if (-not (Test-Path $ElectronMain)) {
    throw "Electron main.js was not found under the project root."
}

$MainText = Get-Content -Raw $ElectronMain
$SecurityChecks = @(
    $MainText -match "contextIsolation:\s*true",
    $MainText -match "nodeIntegration:\s*false",
    $MainText -match "sandbox:\s*true"
)
if ($SecurityChecks -contains $false) {
    throw "Electron security settings are incomplete."
}

$InitialElectron = @(Get-Process -Name electron -ErrorAction SilentlyContinue)
if ($InitialElectron.Count -eq 0) {
    throw "No Electron process is running. Launch Rei's Virtual Assistant first."
}
$InitialIds = @($InitialElectron.Id)
$BaselineWorking = [double](($InitialElectron | Measure-Object WorkingSet64 -Sum).Sum)
$BaselinePrivate = [double](($InitialElectron | Measure-Object PrivateMemorySize64 -Sum).Sum)
$PeakWorking = $BaselineWorking
$PeakPrivate = $BaselinePrivate
$PeakHandles = [int](($InitialElectron | Measure-Object HandleCount -Sum).Sum)
$Deadline = (Get-Date).AddMinutes($DurationMinutes)
$Samples = [System.Collections.Generic.List[object]]::new()
$Failure = $null

New-Item -ItemType Directory -Force -Path $Artifacts | Out-Null
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$CsvPath = Join-Path $Artifacts "windows-electron-soak-$Stamp.csv"
$SummaryPath = Join-Path $Artifacts "windows-electron-soak-$Stamp.txt"

while ((Get-Date) -lt $Deadline) {
    $Electron = @(Get-Process -Id $InitialIds -ErrorAction SilentlyContinue)
    if ($Electron.Count -eq 0) {
        $Failure = "All Electron processes from the tested Assistant session exited."
        break
    }
    $Working = [double](($Electron | Measure-Object WorkingSet64 -Sum).Sum)
    $Private = [double](($Electron | Measure-Object PrivateMemorySize64 -Sum).Sum)
    $Cpu = [double](($Electron | Measure-Object CPU -Sum).Sum)
    $Handles = [int](($Electron | Measure-Object HandleCount -Sum).Sum)
    $PeakWorking = [Math]::Max($PeakWorking, $Working)
    $PeakPrivate = [Math]::Max($PeakPrivate, $Private)
    $PeakHandles = [Math]::Max($PeakHandles, $Handles)
    $Samples.Add([pscustomobject]@{
        timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
        process_count = $Electron.Count
        working_set_mb = [Math]::Round($Working / 1MB, 2)
        private_mb = [Math]::Round($Private / 1MB, 2)
        handles = $Handles
        cpu_seconds = [Math]::Round($Cpu, 2)
    })
    Start-Sleep -Seconds $SampleSeconds
}

$Samples | Export-Csv -NoTypeInformation -Encoding UTF8 $CsvPath
$WorkingGrowthMB = [Math]::Round(($PeakWorking - $BaselineWorking) / 1MB, 2)
$PrivateGrowthMB = [Math]::Round(($PeakPrivate - $BaselinePrivate) / 1MB, 2)
if (-not $Failure -and $WorkingGrowthMB -gt $MaxElectronWorkingSetGrowthMB) {
    $Failure = "Working-set growth exceeded the configured threshold."
}
if (-not $Failure -and $PrivateGrowthMB -gt $MaxElectronPrivateGrowthMB) {
    $Failure = "Private-memory growth exceeded the configured threshold."
}

$Result = if ($Failure) { "FAIL" } else { "PASS" }
$Lines = @(
    "Protean Workspace RC2 Windows/Electron soak: $Result",
    "Completed UTC: $((Get-Date).ToUniversalTime().ToString('o'))",
    "Duration requested: $DurationMinutes minutes",
    "Samples recorded: $($Samples.Count)",
    "Initial Electron PIDs: $($InitialIds -join ', ')",
    "Peak working-set growth: $WorkingGrowthMB MB (limit $MaxElectronWorkingSetGrowthMB MB)",
    "Peak private-memory growth: $PrivateGrowthMB MB (limit $MaxElectronPrivateGrowthMB MB)",
    "Peak handles: $PeakHandles",
    "Electron security: contextIsolation=true; nodeIntegration=false; sandbox=true",
    "Failure: $(if ($Failure) { $Failure } else { 'none' })",
    "Evidence CSV: $CsvPath"
)
$Lines | Set-Content -Encoding UTF8 $SummaryPath
$Lines | ForEach-Object { Write-Host $_ }
if ($Failure) { exit 1 }

param(
    [Parameter(Mandatory=$true)][string]$Installation,
    [string]$Package = (Split-Path -Parent $PSScriptRoot),
    [switch]$Rollback
)
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'verify-package.ps1') -Package $Package | Out-Null
$target = [IO.Path]::GetFullPath($Installation)
if (-not (Test-Path -LiteralPath (Join-Path $target 'data\cathedra.db') -PathType Leaf)) { throw 'Select the Office installation containing its existing database.' }
$receipt = Join-Path $target ('data\update-receipt-' + [guid]::NewGuid().ToString('N') + '.json')
$arguments = @('--update-target', ('"' + $target + '"'), '--maintenance-result', ('"' + $receipt + '"'))
if ($Rollback) { $arguments += '--rollback-update' }
$process = Start-Process -FilePath (Join-Path $Package 'Cathedra FSDP.exe') -ArgumentList $arguments -WindowStyle Hidden -PassThru -Wait
if ($process.ExitCode -ne 0) {
    $detail = 'Keep the existing database and recovery files; review the update receipt.'
    if (Test-Path -LiteralPath $receipt -PathType Leaf) {
        $failure = Get-Content -LiteralPath $receipt -Raw | ConvertFrom-Json
        if ($failure.detail) { $detail = $failure.detail }
        elseif ($failure.message) { $detail = $failure.message }
    }
    throw ('Update stopped: ' + $detail + ' Receipt: ' + $receipt)
}
Get-Content -LiteralPath $receipt -Raw

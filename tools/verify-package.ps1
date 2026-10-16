param([string]$Package = (Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference = 'Stop'
$Package = [IO.Path]::GetFullPath($Package).TrimEnd('\')
$manifest = Get-Content -LiteralPath (Join-Path $Package 'release-manifest.json') -Raw | ConvertFrom-Json
if ($manifest.product -ne 'fsdp' -or $manifest.version -ne (Get-Content (Join-Path $Package 'VERSION') -Raw).Trim()) { throw 'Release identity does not match.' }
if (-not $manifest.runtime_files -or $manifest.runtime_files.Count -lt 4) { throw 'A complete runtime manifest is required.' }
$seen = @{}
$rootFiles = @('Cathedra FSDP.exe', 'VERSION', 'APP_PRODUCT', 'tools\verify-package.ps1', 'tools\office-smoke.ps1', 'tools\protect-local-installation.ps1', 'tools\update-office.ps1')
foreach ($entry in $manifest.runtime_files) {
    $relative = $entry.path.Replace('/', '\')
    if ($seen.ContainsKey($relative)) { throw 'Duplicate manifest path.' }
    $seen[$relative] = $true
    $path = [IO.Path]::GetFullPath((Join-Path $Package $relative))
    if (-not $path.StartsWith($Package + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe manifest path.' }
    if ($relative -notin $rootFiles -and -not $relative.StartsWith('_internal\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Unexpected manifest scope.' }
    $ancestor = $path
    while ($ancestor -ne $Package) {
        if ((Get-Item -LiteralPath $ancestor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Linked release paths are not supported.' }
        $ancestor = Split-Path -Parent $ancestor
    }
    $file = Get-Item -LiteralPath $path
    if ($file.PSIsContainer -or $file.Length -ne $entry.size -or (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $entry.sha256) { throw "Release verification failed: $relative" }
}
$actual = $rootFiles
foreach ($entry in Get-ChildItem -LiteralPath (Join-Path $Package '_internal') -Force -Recurse) {
    if ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Linked release paths are not supported.' }
    if (-not $entry.PSIsContainer) { $actual += $entry.FullName.Substring($Package.Length + 1) }
}
if ($actual.Count -ne $seen.Count -or @($actual | Where-Object { -not $seen.ContainsKey($_) }).Count) { throw 'Unexpected bundled runtime files.' }
if ((Get-Content (Join-Path $Package '_internal\frontend\dist\release-version.txt') -Raw).Trim() -ne $manifest.version) { throw 'Frontend version does not match.' }
if ((Get-Content (Join-Path $Package 'APP_PRODUCT') -Raw).Trim() -ne 'fsdp') { throw 'Invalid product.' }
[pscustomobject]@{ verified = $true; version = $manifest.version; runtime_files = $actual.Count } | ConvertTo-Json

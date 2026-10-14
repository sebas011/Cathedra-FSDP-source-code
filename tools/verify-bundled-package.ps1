param(
    [Parameter(Mandatory=$true)][string]$Package,
    [Parameter(Mandatory=$true)][string]$ResultDirectory
)
$ErrorActionPreference = 'Stop'
$Package = [IO.Path]::GetFullPath($Package)
$ResultDirectory = [IO.Path]::GetFullPath($ResultDirectory)
New-Item -ItemType Directory -Path $ResultDirectory -Force | Out-Null
$result = Join-Path $ResultDirectory ('bundled-inventory-' + [guid]::NewGuid().ToString('N') + '.json')
$arguments = @('--verify-package', ('"' + $Package + '"'), '--maintenance-result', ('"' + $result + '"'))
$process = Start-Process -FilePath (Join-Path $Package 'Cathedra FSDP.exe') -ArgumentList $arguments -WindowStyle Hidden -PassThru -Wait
if (-not (Test-Path -LiteralPath $result -PathType Leaf)) { throw 'Bundled verifier did not produce a result.' }
$verification = Get-Content -LiteralPath $result -Raw | ConvertFrom-Json
if ($process.ExitCode -ne 0 -or $verification.verified -ne $true -or $verification.database_accessed -ne $false) { throw ('Bundled verifier failed: ' + $verification.detail) }
$manifest = Get-Content -LiteralPath (Join-Path $Package 'release-manifest.json') -Raw | ConvertFrom-Json
if ($verification.version -ne $manifest.version -or $verification.runtime_files -ne $manifest.runtime_files.Count) { throw 'Bundled verifier identity/count differs from the manifest.' }
$verification | ConvertTo-Json

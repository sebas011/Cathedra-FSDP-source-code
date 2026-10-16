param(
    [Parameter(Mandatory=$true)][string]$Archive,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedSha256
)
$ErrorActionPreference = 'Stop'
$file = Get-Item -LiteralPath $Archive
if ($file.PSIsContainer) { throw 'Select the downloaded application ZIP file.' }
$actual = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
if ($actual -ne $ExpectedSha256) { throw 'Download hash differs. Keep the existing Office app and download the correct archive again.' }
[pscustomobject]@{
    verified = $true
    file = $file.Name
    sha256 = $actual.ToLowerInvariant()
    publisher_authenticated = $false
} | ConvertTo-Json

param([string]$Package = (Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'verify-package.ps1') -Package $Package | Out-Null
$Package = [IO.Path]::GetFullPath($Package)
$listener = New-Object Net.Sockets.TcpListener([Net.IPAddress]::Loopback, 0)
$listener.Start()
$port = $listener.LocalEndpoint.Port
$listener.Stop()
$temporary = Join-Path ([IO.Path]::GetTempPath()) ('cathedra-office-check-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temporary | Out-Null
$oldPath = $env:PATH
$oldSetup = $env:CATHEDRA_SETUP_TOKEN
$env:PATH = "$env:SystemRoot\System32;$env:SystemRoot;$env:SystemRoot\System32\WindowsPowerShell\v1.0"
$env:CATHEDRA_SETUP_TOKEN = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
$setup = $env:CATHEDRA_SETUP_TOKEN
$process = $null
$passed = $false
$base = "http://127.0.0.1:$port/api/v1"
function Call-Api([string]$Path, [string]$Method='Get', [hashtable]$Headers=@{}, $Body=$null) {
    $arguments = @{ Uri = "$base$Path"; Method = $Method; Headers = $Headers; TimeoutSec = 15; UseBasicParsing = $true }
    if ((Get-Command Invoke-RestMethod).Parameters.ContainsKey('SkipHeaderValidation')) { $arguments.SkipHeaderValidation = $true }
    if ($null -ne $Body) { $arguments.Body = ($Body | ConvertTo-Json -Depth 8); $arguments.ContentType = 'application/json' }
    Invoke-RestMethod @arguments
}
try {
    $process = Start-Process -FilePath (Join-Path $Package 'Cathedra FSDP.exe') -ArgumentList '--no-browser','--port',$port,'--data-dir',('"' + $temporary + '"') -WindowStyle Hidden -PassThru
    $deadline = (Get-Date).AddSeconds(30)
    $health = $null
    $startupError = ''
    while ((Get-Date) -lt $deadline) {
        try { $health = Call-Api '/health'; break } catch { $startupError = $_.Exception.Message; if ($process.HasExited) { break }; Start-Sleep -Milliseconds 250 }
    }
    $expected = (Get-Content (Join-Path $Package 'VERSION') -Raw).Trim()
    if (-not $health -or $health.product -ne 'fsdp' -or $health.release_version -ne $expected -or -not $health.desktop_mode) { throw ("Packaged startup failed. Health check: " + $startupError) }
    $credentials = @{username='office-smoke';password='synthetic-office-check-123'}
    $session = Call-Api '/auth/setup' 'Post' @{'X-Cathedra-Setup'=$setup} $credentials
    $headers = @{Authorization="Bearer $($session.token)"}
    $scholar = Call-Api '/fsdp' 'Post' $headers @{name='Synthetic Office Check';participations=@(@{program_name='Smoke Program';status='On Going';grant_type='Full Scholarship'});requirements=@()}
    if (-not $scholar.id -or $scholar.participations.Count -ne 1) { throw 'Scholar/grant creation failed.' }
    $snapshot = Call-Api '/maintenance/backups' 'Post' $headers
    Call-Api ("/fsdp/" + $scholar.id) 'Delete' (@{Authorization=$headers.Authorization;'If-Match'=[string]$scholar.revision}) | Out-Null
    $restore = Call-Api '/maintenance/restore' 'Post' $headers @{filename=$snapshot.filename}
    if (-not $restore.safety_backup) { throw 'Restore did not retain a safety backup.' }
    $denied = $false
    try { Call-Api '/fsdp/page' 'Get' $headers | Out-Null } catch { $denied = [int]$_.Exception.Response.StatusCode -eq 401 }
    if (-not $denied) { throw 'Restored sessions were not revoked.' }
    $session = Call-Api '/auth/login' 'Post' @{} $credentials
    $headers = @{Authorization="Bearer $($session.token)"}
    $directory = Call-Api '/fsdp/page' 'Get' $headers
    if ($directory.total -ne 1) { throw 'Restored record totals differ.' }
    Call-Api '/desktop/exit' 'Post' $headers | Out-Null
    if (-not $process.WaitForExit(15000) -or $process.ExitCode -ne 0) { throw 'Graceful shutdown failed.' }
    $lock = [IO.File]::Open((Join-Path $temporary '.cathedra.lock'), 'Open', 'ReadWrite', 'ReadWrite')
    try { $lock.Lock(0,1); $lock.Unlock(0,1) } finally { $lock.Dispose() }
    $passed = $true
    [pscustomobject]@{ passed=$true; version=$expected; python_or_node_required=$false; restore_checked=$true; shutdown_checked=$true; clean_pc_certified=$false; host=$env:COMPUTERNAME } | ConvertTo-Json
} finally {
    $env:PATH = $oldPath
    $env:CATHEDRA_SETUP_TOKEN = $oldSetup
    if ($process -and -not $process.HasExited) { Stop-Process -Id $process.Id -Force; $process.WaitForExit(10000) | Out-Null }
    if ($passed) {
        $resolved = [IO.Path]::GetFullPath($temporary)
        $parent = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')
        if ((Split-Path -Parent $resolved) -ne $parent -or -not (Split-Path -Leaf $resolved).StartsWith('cathedra-office-check-')) { throw 'Unsafe cleanup path.' }
        if ((Get-Item -LiteralPath $resolved).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Refusing linked cleanup.' }
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}

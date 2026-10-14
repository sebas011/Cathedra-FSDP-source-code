#Requires -Version 7.0
param(
  [Parameter(Mandatory=$true)][string]$ReleaseFolder,
  [string]$OldBackup
)
$ErrorActionPreference = 'Stop'
if ($OldBackup) { Write-Warning 'Legacy backup rejection is covered by backend restore tests; this command checks the current packaged release.' }
& (Join-Path (Split-Path -Parent $PSScriptRoot) 'desktop/verify-release.ps1') -ReleaseFolder $ReleaseFolder
if (-not $?) { throw 'Packaged release verification failed.' }

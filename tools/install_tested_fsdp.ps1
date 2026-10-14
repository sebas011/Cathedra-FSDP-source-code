# Historical one-off 0.5.9 -> 0.5.10 development installation only.
# For current installations use tools/update-office.ps1 with a verified update package.
param(
  [Parameter(Mandatory=$true)][string]$Stage,
  [Parameter(Mandatory=$true)][string]$Target,
  [Parameter(Mandatory=$true)][string]$Archive,
  [Parameter(Mandatory=$true)][string]$Python
)
$ErrorActionPreference='Stop'
$Stage=[IO.Path]::GetFullPath($Stage).TrimEnd('\')
$Target=[IO.Path]::GetFullPath($Target).TrimEnd('\')
$Archive=[IO.Path]::GetFullPath($Archive).TrimEnd('\')
$allowed='C:\Users\rodia\Desktop\Project\Cathedra-FSDP'
if ($Target -ne $allowed -or (Get-Content "$Target\APP_PRODUCT" -Raw).Trim() -ne 'fsdp') { throw 'The installation destination is not the authorized FSDP application.' }
if ((Get-Content "$Target\VERSION" -Raw).Trim() -ne '0.5.9') { throw 'The original release changed; review it before installing.' }
$release=Join-Path $Stage 'desktop\release\Cathedra FSDP'
$manifest=Get-Content "$release\release-manifest.json" -Raw | ConvertFrom-Json
if ($manifest.version -ne '0.5.10' -or (Get-FileHash "$release\Cathedra FSDP.exe").Hash -ne $manifest.executable_sha256) { throw 'The tested release manifest does not match the staged executable.' }
& (Join-Path $Stage 'tools/verify-package.ps1') -Package $release
if (Get-NetTCPConnection -LocalPort 8101 -State Listen -ErrorAction SilentlyContinue) { throw 'FSDP is still running. Close its service before installation.' }
if (Get-Process | Where-Object {$_.Path -eq "$Target\Cathedra FSDP.exe"}) { throw 'The FSDP process is still running.' }
New-Item -ItemType Directory -Path $Archive -Force | Out-Null
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$sourceArchive=Join-Path $Archive "fsdp-source-before-0.5.10-$stamp.zip"
$runtimeArchive=Join-Path $Archive "fsdp-runtime-before-0.5.10-$stamp.zip"
$backup=Join-Path $Target "data\backups\cathedra-protected-before-0.5.10-$stamp.db"
$lock=[IO.File]::Open("$Target\data\.cathedra.lock",[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::ReadWrite)
$locked=$false
$replaced=$false
$oldInternal=Join-Path $Target '._internal-before-0.5.10'
$oldDist=Join-Path $Target 'frontend\._dist-before-0.5.10'
$oldExe=Join-Path $Target 'Cathedra-FSDP-before-0.5.10.exe'
$sourceFolders=@('backend','frontend','desktop','docs','tools','.github')
$exclude='\\(node_modules|dist|__pycache__|\.venv|\.pytest_cache|\.ruff_cache|build|release)\\|\.(db|db-wal|db-shm|pyc|exe|spec|tsbuildinfo)$|\\\.env$'
function Source-Files([string]$Root) {
  @($sourceFolders | ForEach-Object { $folder=Join-Path $Root $_; if(Test-Path $folder){Read-SourceFolder $folder} }) +
  @('VERSION','APP_PRODUCT','README.md','pyproject.toml','.gitignore' | ForEach-Object {Get-Item -LiteralPath (Join-Path $Root $_)})
}
function Read-SourceFolder([string]$Folder) {
  foreach($entry in Get-ChildItem -LiteralPath $Folder -Force){
    if($entry.LinkType){continue}
    if($entry.PSIsContainer){
      if($entry.Name -notin @('node_modules','dist','__pycache__','.venv','.pytest_cache','.ruff_cache','build','release')){Read-SourceFolder $entry.FullName}
    } elseif($entry.FullName -notmatch $exclude){$entry}
  }
}
function Archive-Files([string]$Path, $Files) {
  $zip=[IO.Compression.ZipFile]::Open($Path,[IO.Compression.ZipArchiveMode]::Create)
  try { foreach($file in $Files){$relative=$file.FullName.Substring($Target.Length+1).Replace('\','/');[IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip,$file.FullName,$relative,[IO.Compression.CompressionLevel]::Optimal)|Out-Null} }
  finally {$zip.Dispose()}
}
function Remove-CheckedDirectory([string]$Path) {
  $resolved=[IO.Path]::GetFullPath($Path)
  if(-not $resolved.StartsWith($Target+'\',[StringComparison]::OrdinalIgnoreCase) -or $resolved -notin @("$Target\_internal",$oldInternal,"$Target\frontend\dist",$oldDist)) {throw 'Refusing an unsafe cleanup path.'}
  if(Test-Path -LiteralPath $resolved){if((Get-Item $resolved).LinkType){throw 'Refusing recursive cleanup of a linked directory.'};Remove-Item -LiteralPath $resolved -Recurse -Force}
}
try {
  $lock.Lock(0,1);$locked=$true
  foreach($path in @($oldInternal,$oldDist,$oldExe)){if(Test-Path -LiteralPath $path){throw 'A previous incomplete replacement needs review.'}}
  $database=Join-Path $Target 'data\cathedra.db'
  $beforeHash=(Get-FileHash $database).Hash
  New-Item -ItemType Directory -Path (Split-Path $backup -Parent) -Force | Out-Null
  & $Python -c "import sqlite3,sys; from pathlib import Path; source=sqlite3.connect(Path(sys.argv[1]).resolve().as_uri()+'?mode=ro',uri=True); target=sqlite3.connect(sys.argv[2]); source.backup(target); assert target.execute('PRAGMA integrity_check').fetchone()[0]=='ok'; assert target.execute('PRAGMA foreign_key_check').fetchall()==[]; source.close(); target.close(); print('Protected database snapshot verified')" $database $backup
  if($LASTEXITCODE -ne 0){throw 'The pre-update snapshot failed verification.'}
  Archive-Files $sourceArchive (Source-Files $Target)
  $runtimeFiles=@(Get-Item "$Target\Cathedra FSDP.exe","$Target\VERSION","$Target\APP_PRODUCT","$Target\release-manifest.json")+@(Get-ChildItem "$Target\_internal" -Recurse -File)
  if(Test-Path "$Target\frontend\dist"){$runtimeFiles+=@(Get-ChildItem "$Target\frontend\dist" -Recurse -File)}
  Archive-Files $runtimeArchive $runtimeFiles
  Rename-Item -LiteralPath "$Target\_internal" -NewName (Split-Path $oldInternal -Leaf)
  $replaced=$true
  Move-Item -LiteralPath "$Target\Cathedra FSDP.exe" -Destination $oldExe
  if(Test-Path "$Target\frontend\dist"){Rename-Item -LiteralPath "$Target\frontend\dist" -NewName (Split-Path $oldDist -Leaf)}
  Copy-Item -LiteralPath "$release\_internal" -Destination $Target -Recurse
  Copy-Item -LiteralPath "$release\Cathedra FSDP.exe" -Destination "$Target\Cathedra FSDP.exe"
  Copy-Item -LiteralPath "$Stage\frontend\dist" -Destination "$Target\frontend" -Recurse
  foreach($removedRelative in @('frontend\src\pages\FsdpMonitoringPage.tsx','frontend\src\utils\workspaceContext.ts')) {
    $removedPath=[IO.Path]::GetFullPath((Join-Path $Target $removedRelative))
    if(-not $removedPath.StartsWith($Target+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Unsafe obsolete source path.'}
    if(Test-Path -LiteralPath $removedPath){Remove-Item -LiteralPath $removedPath -Force}
  }
  $copied=@()
  foreach($file in (Source-Files $Stage)){
    $relative=$file.FullName.Substring($Stage.Length+1)
    $destination=Join-Path $Target $relative
    New-Item -ItemType Directory -Path (Split-Path $destination -Parent) -Force | Out-Null
    Copy-Item -LiteralPath $file.FullName -Destination $destination -Force
    if((Get-FileHash $file.FullName).Hash -ne (Get-FileHash $destination).Hash){throw "Source verification failed: $relative"}
    $copied+=@{path=$relative;sha256=(Get-FileHash $destination).Hash}
  }
  Copy-Item -LiteralPath "$release\release-manifest.json" -Destination "$Target\release-manifest.json" -Force
  $permissionReceipt=Join-Path $Stage "permissions-before-restriction-0.5.10-$stamp.json"
  & (Join-Path $Target 'tools/protect-local-installation.ps1') -Target $Target -Apply -Receipt $permissionReceipt -HeldDataLock $lock
  & (Join-Path $Target 'tools/verify-package.ps1') -Package $Target
  if((Get-FileHash $database).Hash -ne $beforeHash){throw 'The office database unexpectedly changed during installation.'}
  if((Get-FileHash "$Target\Cathedra FSDP.exe").Hash -ne $manifest.executable_sha256){throw 'The installed executable differs from the tested release.'}
  $installation=@{version='0.5.10';installed_at=(Get-Date).ToUniversalTime().ToString('o');database_sha256_before=$beforeHash;database_sha256_after=(Get-FileHash $database).Hash;backup=$backup;source_archive=$sourceArchive;runtime_archive=$runtimeArchive;source_files=$copied;permission_receipt=$permissionReceipt;schema_migration='Migration 8 adds explicit personnel type and graduated-program education entries at next startup. Existing saved fields and recorded outcomes are preserved; graduation years are never inferred.'}
  $installation|ConvertTo-Json -Depth 6|Set-Content "$Target\docs\INSTALLATION_MANIFEST_0.5.10.json"
  Remove-CheckedDirectory $oldInternal
  Remove-CheckedDirectory $oldDist
  Remove-Item -LiteralPath $oldExe -Force
  Write-Host 'Installed Cathedra FSDP 0.5.10; office database hash is unchanged.'
  Write-Host "Protected backup: $backup"
} catch {
  if($replaced){
    if(Test-Path $oldInternal){Remove-CheckedDirectory "$Target\_internal";Rename-Item -LiteralPath $oldInternal -NewName '_internal'}
    if(Test-Path $oldExe){if(Test-Path "$Target\Cathedra FSDP.exe"){Remove-Item -LiteralPath "$Target\Cathedra FSDP.exe" -Force};Move-Item -LiteralPath $oldExe -Destination "$Target\Cathedra FSDP.exe"}
    if(Test-Path $oldDist){Remove-CheckedDirectory "$Target\frontend\dist";Rename-Item -LiteralPath $oldDist -NewName 'dist'}
    if(Test-Path $sourceArchive){[IO.Compression.ZipFile]::ExtractToDirectory($sourceArchive,$Target,$true)}
    if(Test-Path $runtimeArchive){[IO.Compression.ZipFile]::ExtractToDirectory($runtimeArchive,$Target,$true)}
    foreach($metadata in @("$Target\docs\INSTALLATION_MANIFEST_0.5.10.json")){if(Test-Path -LiteralPath $metadata){Remove-Item -LiteralPath $metadata -Force}}
  }
  throw
} finally {if($locked){$lock.Unlock(0,1)};$lock.Dispose()}



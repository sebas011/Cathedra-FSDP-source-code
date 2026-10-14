param([string]$Drive = 'C:')
$ErrorActionPreference = 'Stop'
if ($Drive -notmatch '^[A-Za-z]:$') { throw 'Use a Windows drive letter, such as C:.' }
$result = [ordered]@{ drive = $Drive; protection = 'UNVERIFIED'; method = 'Windows BitLocker'; external_veracrypt_does_not_cover_this_drive = $true }
try {
    $volume = Get-BitLockerVolume -MountPoint $Drive -ErrorAction Stop
    if ([string]$volume.ProtectionStatus -eq 'On' -and [string]$volume.VolumeStatus -eq 'FullyEncrypted') { $result.protection = 'PROTECTED' }
    else { $result.protection = 'NOT_CONFIRMED_PROTECTED' }
    $result.volume_status = [string]$volume.VolumeStatus
    $result.protection_status = [string]$volume.ProtectionStatus
} catch { $result.note = 'Could not read protection status. Check Manage BitLocker in Windows; do not share recovery keys.' }
$result | ConvertTo-Json

param(
    [Parameter(Mandatory=$true)][string]$Target,
    [switch]$Apply,
    [string]$Receipt,
    [System.IO.FileStream]$HeldDataLock
)
$ErrorActionPreference = 'Stop'
if (-not ('CathedraAccessRules' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
public static class CathedraAccessRules {
    [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    static extern bool ConvertStringSecurityDescriptorToSecurityDescriptor(
        string text, uint revision, out IntPtr descriptor, out uint size);
    [DllImport("advapi32.dll", SetLastError = true)]
    static extern bool GetSecurityDescriptorDacl(
        IntPtr descriptor, out bool present, out IntPtr dacl, out bool defaulted);
    [DllImport("advapi32.dll", CharSet = CharSet.Unicode)]
    static extern uint SetNamedSecurityInfo(
        string path, uint type, uint information, IntPtr owner, IntPtr group,
        IntPtr dacl, IntPtr sacl);
    [DllImport("kernel32.dll")]
    static extern IntPtr LocalFree(IntPtr memory);
    public static void Apply(string path, string sddl, bool protect) {
        IntPtr descriptor;
        uint size;
        if (!ConvertStringSecurityDescriptorToSecurityDescriptor(sddl, 1, out descriptor, out size))
            throw new Win32Exception(Marshal.GetLastWin32Error(), path);
        try {
            bool present, defaulted;
            IntPtr dacl;
            if (!GetSecurityDescriptorDacl(descriptor, out present, out dacl, out defaulted))
                throw new Win32Exception(Marshal.GetLastWin32Error(), path);
            if (!present || dacl == IntPtr.Zero)
                throw new InvalidOperationException("A non-null access list is required: " + path);
            uint result = SetNamedSecurityInfo(path, 1, 4u | (protect ? 0x80000000u : 0x20000000u),
                IntPtr.Zero, IntPtr.Zero, dacl, IntPtr.Zero);
            if (result != 0) throw new Win32Exception((int)result, path);
        } finally { LocalFree(descriptor); }
    }
}
'@
}
function Set-AccessRules([string]$Path, $Security) {
    [CathedraAccessRules]::Apply(
        $Path,
        $Security.GetSecurityDescriptorSddlForm([Security.AccessControl.AccessControlSections]::Access),
        $Security.AreAccessRulesProtected
    )
}
$Target = [IO.Path]::GetFullPath($Target).TrimEnd('\')
if ($Target -eq [IO.Path]::GetPathRoot($Target).TrimEnd('\') -or -not (Test-Path (Join-Path $Target 'APP_PRODUCT'))) { throw 'Choose the FSDP application folder, not a drive root.' }
if ((Get-Content (Join-Path $Target 'APP_PRODUCT') -Raw).Trim() -ne 'fsdp') { throw 'Only the FSDP product is supported.' }
$identity = [Security.Principal.WindowsIdentity]::GetCurrent().User
$allowed = @($identity.Value, 'S-1-5-18', 'S-1-5-32-544')
$items = @(Get-Item -LiteralPath $Target -Force) + @(Get-ChildItem -LiteralPath $Target -Force -Recurse)
foreach ($item in $items) {
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Linked installation paths must be reviewed before changing permissions.' }
}
$before = @($items | ForEach-Object { [pscustomobject]@{ path = $_.FullName; sddl = (Get-Acl -LiteralPath $_.FullName).Sddl } })
if ($Apply) {
    if (-not $Receipt -or (Test-Path -LiteralPath $Receipt)) { throw 'Choose a new permission-receipt file.' }
    $Receipt = [IO.Path]::GetFullPath($Receipt)
    if ($Receipt.StartsWith($Target + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Keep the permission receipt outside the installation.' }
    if (Get-Process | Where-Object { $_.Path -eq (Join-Path $Target 'Cathedra FSDP.exe') }) { throw 'Close FSDP before changing its permissions.' }
    $lockPath = Join-Path $Target 'data\.cathedra.lock'
    $lock = $null
    if ($HeldDataLock) {
        if (-not $HeldDataLock.CanWrite -or
            [IO.Path]::GetFullPath($HeldDataLock.Name) -ne [IO.Path]::GetFullPath($lockPath)) {
            throw 'The held lock must be the writable FSDP data lock.'
        }
    } elseif (Test-Path $lockPath) {
        $lock = [IO.File]::Open($lockPath, [IO.FileMode]::Open, [IO.FileAccess]::ReadWrite, [IO.FileShare]::ReadWrite)
        try { $lock.Lock(0,1) } catch { $lock.Dispose(); throw 'The FSDP data directory is still in use.' }
    }
    try {
        foreach ($item in $items) {
            $security = Get-Acl -LiteralPath $item.FullName
            if ($item.PSIsContainer) {
                $inheritance = [Security.AccessControl.InheritanceFlags]'ContainerInherit, ObjectInherit'
            } else {
                $inheritance = [Security.AccessControl.InheritanceFlags]::None
            }
            $security.SetAccessRuleProtection($true, $false)
            foreach ($existingRule in @($security.Access)) {
                $security.RemoveAccessRuleSpecific($existingRule) | Out-Null
            }
            foreach ($sid in $allowed) {
                $principal = New-Object Security.Principal.SecurityIdentifier($sid)
                $rule = New-Object Security.AccessControl.FileSystemAccessRule($principal, 'FullControl', $inheritance, 'None', 'Allow')
                $security.AddAccessRule($rule)
            }
            Set-AccessRules $item.FullName $security
        }
        $before | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $Receipt -Encoding UTF8
        $receiptAcl = Get-Acl -LiteralPath $Receipt
        $receiptAcl.SetAccessRuleProtection($true, $false)
        foreach ($existingRule in @($receiptAcl.Access)) {
            $receiptAcl.RemoveAccessRuleSpecific($existingRule) | Out-Null
        }
        foreach ($sid in $allowed) {
            $rule = New-Object Security.AccessControl.FileSystemAccessRule((New-Object Security.Principal.SecurityIdentifier($sid)), 'FullControl', 'Allow')
            $receiptAcl.AddAccessRule($rule)
        }
        Set-AccessRules $Receipt $receiptAcl
    } catch {
        foreach ($entry in $before) {
            $security = Get-Acl -LiteralPath $entry.path
            $security.SetSecurityDescriptorSddlForm(
                $entry.sddl, [Security.AccessControl.AccessControlSections]::Access
            )
            Set-AccessRules $entry.path $security
        }
        throw
    } finally {
        if ($lock) { $lock.Unlock(0,1); $lock.Dispose() }
    }
}
$violations = @()
foreach ($item in $items) {
    foreach ($rule in (Get-Acl -LiteralPath $item.FullName).Access) {
        $sid = $rule.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value
        if ($rule.AccessControlType -eq 'Allow' -and $sid -notin $allowed) {
            $violations += [pscustomobject]@{ path = $item.FullName; sid = $sid; rights = $rule.FileSystemRights.ToString() }
        }
    }
}
[pscustomobject]@{ restricted = ($violations.Count -eq 0); files_checked = $items.Count; allowed_sids = $allowed; violations = $violations } | ConvertTo-Json -Depth 5
if ($violations.Count) { throw 'Installation permissions are not restricted to the owner, SYSTEM and administrators.' }

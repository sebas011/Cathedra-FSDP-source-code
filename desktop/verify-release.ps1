#Requires -Version 7.0
param(
  [Parameter(Mandatory = $true)]
  [string]$ReleaseFolder,
  [int]$Port = 0,
  [string]$Python = ''
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$product = (Get-Content -LiteralPath (Join-Path $root 'APP_PRODUCT') -Raw).Trim()
$applicationName = 'Cathedra FSDP'
$application = Join-Path $ReleaseFolder "$applicationName.exe"
$versionFile = Join-Path (Split-Path -Parent $PSScriptRoot) 'VERSION'

if (-not (Test-Path -LiteralPath $application)) {
  throw "Cathedra.exe was not found in $ReleaseFolder."
}
if (-not (Test-Path -LiteralPath $versionFile)) {
  throw 'The Cathedra VERSION file is missing.'
}

$expectedVersion = (Get-Content -LiteralPath $versionFile -Raw).Trim()
$frontendVersionFile = Join-Path $ReleaseFolder '_internal\frontend\dist\release-version.txt'
if (-not (Test-Path -LiteralPath $frontendVersionFile) -or (Get-Content -LiteralPath $frontendVersionFile -Raw).Trim() -ne $expectedVersion) {
  throw "Packaged frontend assets do not match Cathedra $expectedVersion."
}
$listener = $null
if ($Port -eq 0) {
  $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
  $listener.Start()
  $Port = ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port
  $listener.Stop()
}
$verificationDataDirectory = Join-Path ([System.IO.Path]::GetTempPath()) ("cathedra-release-" + [guid]::NewGuid().ToString())
New-Item -ItemType Directory -Path $verificationDataDirectory | Out-Null
$previousSetupCode = $env:CATHEDRA_SETUP_TOKEN
$env:CATHEDRA_SETUP_TOKEN = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
$setupCode = $env:CATHEDRA_SETUP_TOKEN
$process = Start-Process -FilePath $application -ArgumentList '--no-browser', '--port', $Port, '--data-dir', $verificationDataDirectory -WindowStyle Hidden -PassThru
$env:CATHEDRA_SETUP_TOKEN = $previousSetupCode

try {
  $deadline = (Get-Date).AddSeconds(30)
  $health = $null
  while ((Get-Date) -lt $deadline) {
    try {
      $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/v1/health" -TimeoutSec 2
      break
    } catch {
      Start-Sleep -Milliseconds 250
    }
  }

  $identityBytes=[Text.Encoding]::UTF8.GetBytes([IO.Path]::GetFullPath($verificationDataDirectory).ToLowerInvariant())
  $expectedIdentity=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($identityBytes)).ToLowerInvariant().Substring(0,16)
  if ($null -eq $health -or $health.status -ne 'ok' -or $health.release_version -ne $expectedVersion -or $health.product -ne $product -or $health.data_directory_identity -ne $expectedIdentity -or $health.desktop_mode -ne $true) {
    $reportedVersion = if ($null -eq $health) { 'no response' } else { $health.release_version }
    throw "The packaged Cathedra application did not return the expected release health check. Expected $expectedVersion; received $reportedVersion."
  }
  $accountStatus = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/v1/auth/status" -TimeoutSec 5
  if ($accountStatus.setup_required -ne $true) {
    throw 'The packaged Cathedra application did not start with a clean administrator setup.'
  }
  $databasePath = Join-Path $verificationDataDirectory 'cathedra.db'
  if (-not (Test-Path -LiteralPath $databasePath)) {
    throw 'The packaged Cathedra application did not create its isolated database.'
  }
  $frontend = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/" -TimeoutSec 5
  if ($frontend.StatusCode -ne 200 -or $frontend.Content -notmatch '<title>Cathedra</title>') {
    throw 'The packaged Cathedra application did not serve its frontend.'
  }
  $base = "http://127.0.0.1:$Port/api/v1"
  function Assert-Status([string]$Uri, [int]$Expected, [string]$Method = 'Get', [hashtable]$RequestHeaders = @{}, [string]$Body = '') {
    $arguments = @{ Uri = $Uri; Method = $Method; Headers = $RequestHeaders; SkipHttpErrorCheck = $true; SkipHeaderValidation = $true; TimeoutSec = 10 }
    if ($Body) { $arguments['Body'] = $Body; $arguments['ContentType'] = 'application/json' }
    $response = Invoke-WebRequest @arguments
    if ([int]$response.StatusCode -ne $Expected) { throw "Expected $Expected for $Method $Uri; received $($response.StatusCode)." }
  }
  Assert-Status "$base/fsdp/page" 401
  Assert-Status "$base/faculty-profiles" 404
  $session = Invoke-RestMethod -Uri "$base/auth/setup" -Method Post -ContentType 'application/json' -Headers @{ 'X-Cathedra-Setup' = $setupCode } -Body (@{ username = 'release-check'; password = 'synthetic-release-password-123' } | ConvertTo-Json)
  $headers = @{ Authorization = "Bearer $($session.token)" }
  $originalHeaders = $headers.Clone()
  $payload = @{ name = 'Release Check Scholar'; department='CAS'; profile_remarks='Whole profile check'; personnel_type='Faculty'; tenure_years=5.5; education=@(@{degree='Bachelor of Science';level="Bachelor’s"},@{degree='Master of Science';level="Master’s"}); participations = @(@{ program_name = 'Current Program'; remarks='Annual grant check'; start_academic_year='2026-2027'; start_term='Summer'; delivering_hei = 'Release Check University'; status = 'On Going'; case_status='Closed'; start_date='2018-01-01'; end_date='2020-01-01'; contract_completed_on='2020-01-01'; grant_type = 'Full Scholarship'; end_term = 'Second Semester'; end_academic_year = '2026-2027' }, @{ program_name = 'Completed Program'; status = 'Graduated'; graduation_date='2025-06-15'; case_status='Open' }); requirements = @() }
  $created = Invoke-RestMethod -Uri "$base/fsdp" -Method Post -ContentType 'application/json' -Headers $headers -Body ($payload | ConvertTo-Json -Depth 5)
  $nameMatches = Invoke-RestMethod -Uri "$base/fsdp/name-matches?name=Release%20Check%20Scholar" -Headers $headers
  if ($nameMatches.Count -ne 1 -or $nameMatches[0].id -ne $created.id) { throw 'Packaged name advisory failed.' }
  $selfMatches = Invoke-RestMethod -Uri "$base/fsdp/name-matches?name=Release%20Check%20Scholar&exclude_id=$($created.id)" -Headers $headers
  if ($selfMatches.Count -ne 0) { throw 'Packaged self-exclusion failed.' }
  $history = Invoke-RestMethod -Uri "$base/activity/scholars/$($created.id)?page_size=1" -Headers $headers
  if ($history.total -lt 3 -or $history.items.Count -ne 1) { throw 'Packaged scholar history failed.' }
  $headers['If-Match'] = '-1'
  Assert-Status "$base/fsdp/$($created.id)" 409 'Put' $headers ($payload | ConvertTo-Json -Depth 5)
  $headers.Remove('If-Match')
  $csv = Invoke-WebRequest -Uri "$base/fsdp/report.csv?status=On%20Going&start_academic_year=2026-2027" -Headers $headers
  if ($csv.Content -notmatch 'Current Program' -or $csv.Content -match ',Completed Program,') { throw 'Packaged scoped CSV failed.' }
  $route = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/fsdp/$($created.id)/edit"
  if ($route.Content -notmatch '<title>Cathedra</title>') { throw 'Packaged nested frontend route failed.' }
  $analytics = Invoke-RestMethod -Uri "$base/fsdp/analytics" -Headers $headers
  if ($analytics.scholars -ne 1 -or $analytics.grants -ne 2 -or ($analytics.statuses | Measure-Object -Property count -Sum).Sum -ne 1) { throw 'Packaged analytics reconciliation failed.' }
  $payback=Invoke-RestMethod -Uri "$base/fsdp/payback" -Headers $headers
  if($payback.scholar_counts.'Payback review' -ne 1 -or $payback.scholar_counts.Completed -ne 1){throw 'Packaged contract classification or independent Closed-case follow-up failed.'}
  if($created.participations[0].contract_completed_on -ne '2020-01-01' -or $created.participations[0].grace_ends_on -ne '2023-01-01'){throw 'Packaged contract date persistence failed.'}
  $paybackCsv=Invoke-WebRequest -Uri "$base/fsdp/payback.csv?attention=Payback%20action" -Headers $headers
  if($paybackCsv.Content -notmatch 'Current Program' -or $paybackCsv.Content -match 'Completed Program'){throw 'Packaged payback CSV scope failed.'}
  $report = Invoke-RestMethod -Uri "$base/fsdp/report?status=On%20Going&start_academic_year=2026-2027" -Headers $headers
  if ($report.total -ne 1 -or $report.items[0].participations.Count -ne 1 -or $report.status_counts.Completed -ne 0) { throw 'Packaged filtered report regression.' }
  $options = Invoke-RestMethod -Uri "$base/fsdp/report-options" -Headers $headers
  if ($options.delivering_heis.Count -ne 1 -or $options.delivering_heis[0] -ne 'Release Check University') { throw 'Packaged report filter options regression.' }
  $assessment = Invoke-RestMethod -Uri "$base/fsdp/payback" -Headers $headers
  if ($assessment.items.Count -lt 1) { throw "Packaged contract assessment is missing." }
  if($created.education.Count -ne 3 -or $created.tenure_years -ne 5.5 -or $created.participations[0].end_term -ne '2nd') {throw 'Packaged education, tenure or canonical terms failed.'}
  if($created.personnel_type -ne 'Faculty' -or $created.current_status -ne 'On Going' -or $created.participations[0].start_term -ne 'Summer'){throw 'Packaged explicit personnel or latest status failed.'}
  if($created.department -ne 'CAS' -or $created.profile_remarks -ne 'Whole profile check' -or $created.participations[0].remarks -ne 'Annual grant check' -or $csv.Content -notmatch 'Profile Remarks' -or $csv.Content -notmatch 'Whole profile check'){throw 'Packaged affiliation or separate profile remarks failed.'}
  if($created.name -cne 'RELEASE CHECK SCHOLAR' -or $created.profile_remarks -cne 'WHOLE PROFILE CHECK' -or $created.participations[0].remarks -cne 'ANNUAL GRANT CHECK'){throw 'Packaged uppercase record entry failed.'}
  $completedEducation=@($created.education | Where-Object {$_.degree -eq 'COMPLETED PROGRAM'})
  if($created.participations[1].status -cne 'Completed' -or $created.participations[1].graduation_date -ne '2025-06-15' -or $created.participations[0].case_status -cne 'Closed' -or $completedEducation.Count -ne 1 -or $completedEducation[0].graduation_year -ne '2025'){throw 'Packaged Completed education, graduation date or case persistence failed.'}
  if($analytics.recent_scholars.Count -ne 1 -or $analytics.recent_scholars[0].id -ne $created.id){throw 'Packaged recently added scholars failed.'}
  Assert-Status "$base/verification" 404 'Get' $headers
  Assert-Status "$base/grant-review" 404 'Get' $headers
  $programCopy=Invoke-RestMethod -Uri "$base/fsdp/programs/$($created.participations[0].program_id)/duplicate" -Method Post -Headers $headers
  if($programCopy.name -ne 'Current Program (Copy)'){throw 'Packaged program copy failed.'}
  $headers['If-Match']=[string]$created.revision
  $created=Invoke-RestMethod -Uri "$base/fsdp/$($created.id)/grants/$($created.participations[0].id)/duplicate" -Method Post -Headers $headers -SkipHeaderValidation
  $headers.Remove('If-Match')
  if($created.participations[2].start_date -or $created.participations[2].end_date -or $created.participations[2].contract_completed_on -or $created.participations[2].graduation_date -or $created.participations[2].status -ne 'On Going' -or $created.participations[2].case_status -ne 'Open' -or $created.participations[2].remarks -cne 'ANNUAL GRANT CHECK'){throw 'Packaged annual dates, case and remarks copy failed.'}
  if($created.participations.Count -ne 3 -or $created.participations[2].id -eq $created.participations[0].id){throw 'Packaged independent grant copy failed.'}
  $logHeaders=$headers.Clone();$logHeaders['Idempotency-Key']=[guid]::NewGuid().ToString()
  $logBody=@{scholar_id=$created.id;entry_type='Document transferred';note='Certificate sent';document_name='Completion certificate';from_department='FSDP';to_department='HRMO'} | ConvertTo-Json
  $log=Invoke-RestMethod -Uri "$base/office-logs" -Method Post -ContentType 'application/json' -Headers $logHeaders -Body $logBody
  $retriedLog=Invoke-RestMethod -Uri "$base/office-logs" -Method Post -ContentType 'application/json' -Headers $logHeaders -Body $logBody
  $logPage=Invoke-RestMethod -Uri "$base/office-logs?scholar_id=$($created.id)&entry_type=Document%20transferred" -Headers $headers
  if($log.id -ne $retriedLog.id -or $logPage.total -ne 1 -or $log.note -cne 'CERTIFICATE SENT' -or $log.to_department -cne 'HRMO' -or $log.username -cne 'release-check'){throw 'Packaged office log author, uppercase or duplicate retry protection failed.'}
  Assert-Status "$base/office-logs/$($log.id)" 405 'Delete' $headers
  $logCsv=Invoke-WebRequest -Uri "$base/office-logs/export.csv?scholar_id=$($created.id)" -Headers $headers
  if($logCsv.Content -notmatch 'Recorded By' -or $logCsv.Content -notmatch 'CERTIFICATE SENT'){throw 'Packaged office log CSV failed.'}
  $snapshot = Invoke-RestMethod -Uri "$base/maintenance/backups" -Method Post -Headers $headers
  if (-not $snapshot.filename) { throw 'Packaged verified backup failed.' }
  Assert-Status "$base/maintenance/backups/$($snapshot.filename)/review" 422 'Post' $headers '{"copied_off_device":false}'
  Invoke-RestMethod -Uri "$base/maintenance/backups/$($snapshot.filename)/review" -Method Post -ContentType 'application/json' -Headers $headers -Body '{"copied_off_device":true,"restore_tested":false}' | Out-Null
  $maintenance = Invoke-RestMethod -Uri "$base/maintenance/status" -Headers $headers
  if ($maintenance.backup_due -ne $false -or $maintenance.recovery_review.administrator_reported -ne $true -or $maintenance.recovery_review.restore_tested -ne $false) { throw 'Packaged recovery attestation failed.' }
  $headers['If-Match'] = [string]$created.revision
  Invoke-RestMethod -Uri "$base/fsdp/$($created.id)" -Method Delete -Headers $headers -SkipHeaderValidation | Out-Null
  $headers.Remove('If-Match')
  $restored = Invoke-RestMethod -Uri "$base/maintenance/restore" -Method Post -ContentType 'application/json' -Headers $headers -Body (@{ filename = $snapshot.filename } | ConvertTo-Json)
  if (-not $restored.safety_backup) { throw 'Packaged restore safety backup failed.' }
  Assert-Status "$base/fsdp/page" 401 'Get' $originalHeaders
  $session = Invoke-RestMethod -Uri "$base/auth/login" -Method Post -ContentType 'application/json' -Body (@{ username = 'release-check'; password = 'synthetic-release-password-123' } | ConvertTo-Json)
  $headers = @{ Authorization = "Bearer $($session.token)" }
  $records = Invoke-RestMethod -Uri "$base/fsdp/page" -Headers $headers
  if ($records.total -ne 1) { throw 'Packaged restore did not recover scholar history.' }
  $restoredLogs=Invoke-RestMethod -Uri "$base/office-logs?scholar_id=$($created.id)" -Headers $headers
  if($restoredLogs.total -ne 1 -or $restoredLogs.items[0].id -ne $log.id){throw 'Packaged restore did not recover the office log.'}
  Invoke-RestMethod -Uri "$base/desktop/exit" -Method Post -Headers $headers | Out-Null
  if (-not $process.WaitForExit(10000)) { throw 'Packaged graceful exit failed.' }
  if ($process.ExitCode -ne 0) { throw 'Packaged shutdown did not exit successfully.' }
  $dataLock=[IO.File]::Open((Join-Path $verificationDataDirectory '.cathedra.lock'),[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::ReadWrite)
  try {$dataLock.Lock(0,1);$dataLock.Unlock(0,1)} finally {$dataLock.Dispose()}
  if ($Python) {
    & $Python -c "import sqlite3, sys; db = sqlite3.connect(sys.argv[1]); assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'; assert db.execute('PRAGMA foreign_key_check').fetchall() == []; assert db.execute('SELECT COUNT(*) FROM scholars').fetchone()[0] == 1; print('Packaged persisted database verified')" $databasePath
    if ($LASTEXITCODE -ne 0) { throw 'Packaged persisted database validation failed.' }
  }
} finally {
  if (-not $process.HasExited) {
    Stop-Process -Id $process.Id -Force
  }
  $resolvedVerification = [System.IO.Path]::GetFullPath($verificationDataDirectory)
  $temporaryRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()).TrimEnd('\') + '\'
  if ($resolvedVerification.StartsWith($temporaryRoot, [System.StringComparison]::OrdinalIgnoreCase) -and (Split-Path -Leaf $resolvedVerification).StartsWith('cathedra-release-')) {
    Remove-Item -LiteralPath $resolvedVerification -Recurse -Force -ErrorAction SilentlyContinue
  }
}

Write-Host "Release verification passed for Cathedra $expectedVersion."



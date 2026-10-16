#Requires -Version 7.0
param(
  [string]$Python = (Join-Path (Split-Path -Parent $PSScriptRoot) 'backend/.venv/Scripts/python.exe'),
  [string]$Node = 'node',
  [string]$SigningCertificateThumbprint,
  [switch]$InstallDependencies
)
$ErrorActionPreference = 'Stop'
$Node = (Get-Command $Node -ErrorAction Stop).Source
$root = Split-Path -Parent $PSScriptRoot
$product = (Get-Content -LiteralPath (Join-Path $root 'APP_PRODUCT') -Raw).Trim()
if ($product -ne 'fsdp') { throw 'Configure one split product before packaging.' }
$name = 'Cathedra FSDP'
$frontend = Join-Path $root 'frontend'
$seed = Join-Path $PSScriptRoot 'build/seed/cathedra-seed.db'
$version = (Get-Content (Join-Path $root 'VERSION') -Raw).Trim()
$versionResource = Join-Path $PSScriptRoot 'build/windows-version.txt'
& $Python (Join-Path $root 'tools/verify_build_inputs.py') (Join-Path $root 'backend/constraints-win-py314.txt') --node $Node --runtime-only
if ($LASTEXITCODE -ne 0) { throw 'Build runtime differs from the release baseline.' }
New-Item -ItemType Directory -Path (Join-Path $PSScriptRoot 'build') -Force | Out-Null
if ($InstallDependencies) {
  & $Python -m pip install -r (Join-Path $root 'backend/requirements-dev.txt') -r (Join-Path $PSScriptRoot 'requirements-build.txt') -c (Join-Path $root 'backend/constraints-win-py314.txt')
  if ($LASTEXITCODE -ne 0) { throw 'Constrained dependency installation failed.' }
}
& $Python (Join-Path $root 'tools/verify_build_inputs.py') (Join-Path $root 'backend/constraints-win-py314.txt') --node $Node
if ($LASTEXITCODE -ne 0) { throw 'Build dependencies differ from the release constraints.' }
& $Python (Join-Path $root 'tools/verify_current_docs.py')
if ($LASTEXITCODE -ne 0) { throw 'Current documentation contracts failed.' }
& $Python -m ruff check (Join-Path $root 'backend/app') (Join-Path $root 'backend/tests') (Join-Path $PSScriptRoot 'run_cathedra.py') (Join-Path $PSScriptRoot 'office_update.py') --config (Join-Path $root 'pyproject.toml')
if ($LASTEXITCODE -ne 0) { throw 'Backend static checks failed.' }
$previousDataDirectory = $env:CATHEDRA_DATA_DIR
$env:CATHEDRA_DATA_DIR = Join-Path $PSScriptRoot 'build/test-data'
Push-Location (Join-Path $root 'backend')
try {
  & $Python -m pytest tests -q -p no:cacheprovider --rootdir=. --basetemp (Join-Path $PSScriptRoot ('build/test-tmp-' + [guid]::NewGuid().ToString('N')))
  if ($LASTEXITCODE -ne 0) { throw 'Backend regression tests failed.' }
} finally {
  Pop-Location
  $env:CATHEDRA_DATA_DIR = $previousDataDirectory
}
Push-Location $frontend
try {
  & $Node (Join-Path (Split-Path -Parent $Node) 'node_modules/npm/bin/npm-cli.js') ci --cache (Join-Path $PSScriptRoot 'build/npm-cache') --no-audit --no-fund
  if ($LASTEXITCODE -ne 0) { throw 'Locked frontend dependency installation failed.' }
  & $Node 'node_modules/typescript/bin/tsc' -p tsconfig.tests.json
  if ($LASTEXITCODE -ne 0) { throw 'Test typecheck failed.' }
  & $Node --no-experimental-webstorage 'node_modules/vitest/vitest.mjs' run --config vitest.config.ts --configLoader runner
  if ($LASTEXITCODE -ne 0) { throw 'Frontend regression tests failed.' }
  & $Node 'node_modules/typescript/bin/tsc' -b
  if ($LASTEXITCODE -ne 0) { throw 'TypeScript failed.' }
  & $Node 'node_modules/vite/bin/vite.js' build --configLoader runner
  if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
} finally { Pop-Location }
& $Python (Join-Path $root 'backend/create_install_seed.py') $seed
if ($LASTEXITCODE -ne 0) { throw 'Clean seed verification failed.' }
& $Python (Join-Path $root 'tools/windows_version.py') $version $versionResource
if ($LASTEXITCODE -ne 0) { throw 'Windows version metadata failed.' }
& $Python -m PyInstaller --noconfirm --clean --noconsole --onedir --name $name --version-file $versionResource --distpath (Join-Path $PSScriptRoot 'release') --workpath (Join-Path $PSScriptRoot 'build/pyinstaller') --specpath $PSScriptRoot --paths (Join-Path $root 'backend') --add-data "$(Join-Path $frontend 'dist');frontend/dist" --add-data "$seed;backend" --add-data "$(Join-Path $root 'VERSION');." --add-data "$(Join-Path $root 'APP_PRODUCT');." (Join-Path $PSScriptRoot 'run_cathedra.py')
if ($LASTEXITCODE -ne 0) { throw 'Packaging failed.' }
if ($SigningCertificateThumbprint) {
  if ($SigningCertificateThumbprint -notmatch '^[a-fA-F0-9]{40}$') { throw 'Invalid signing certificate thumbprint.' }
  $certificate = Get-Item -LiteralPath ('Cert:\CurrentUser\My\' + $SigningCertificateThumbprint)
  $signature = Set-AuthenticodeSignature -FilePath (Join-Path $PSScriptRoot "release/$name/$name.exe") -Certificate $certificate -HashAlgorithm SHA256
  if ($signature.Status -ne 'Valid') { throw 'Executable signing verification failed.' }
}

& (Join-Path $PSScriptRoot 'verify-release.ps1') -ReleaseFolder (Join-Path $PSScriptRoot "release/$name") -Python $Python
if ($LASTEXITCODE -ne 0) { throw 'Packaged smoke check failed.' }
$release = Join-Path $PSScriptRoot "release/$name"
Copy-Item (Join-Path $root 'VERSION'), (Join-Path $root 'APP_PRODUCT') $release -Force
New-Item -ItemType Directory (Join-Path $release 'tools') -Force | Out-Null
foreach ($tool in @('verify-package.ps1', 'office-smoke.ps1', 'protect-local-installation.ps1', 'update-office.ps1')) { Copy-Item (Join-Path $root "tools/$tool") (Join-Path $release 'tools') -Force }
& $Python (Join-Path $root 'tools/release_manifest.py') create $release --source $root --python (& $Python --version) --node (& $Node --version)
if ($LASTEXITCODE -ne 0) { throw 'Complete release manifest generation failed.' }
& (Join-Path $root 'tools/verify-package.ps1') -Package $release
& (Join-Path $root 'tools/verify-bundled-package.ps1') -Package $release -ResultDirectory (Join-Path $PSScriptRoot 'build/bundled-inventory')
& $Python (Join-Path $root 'tools/verify_current_docs.py') --package $release
if ($LASTEXITCODE -ne 0) { throw 'Package/documentation identities disagree.' }

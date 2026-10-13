param(
    [string]$Python = 'python',
    [string]$ExpectedTag = ''
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
$previousDiagnosticHome = $env:HARPIE_HOME
$previousQtPlatform = $env:QT_QPA_PLATFORM
try {
    $appVersion = (& $Python -c 'from version import __version__; print(__version__)').Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read the application version.' }
    if ($appVersion -notmatch '^\d+\.\d+\.\d+$') { throw 'Invalid application version.' }
    if ($ExpectedTag -and $ExpectedTag -ne "v$appVersion") { throw 'The tag does not match version.py.' }
    & $Python -B -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw 'Regression tests failed.' }
    & $Python tools/write_version.py
    if ($LASTEXITCODE -ne 0) { throw 'Version generation failed.' }
    & $Python tools/build_icons.py
    if ($LASTEXITCODE -ne 0) { throw 'Icon generation failed.' }
    & $Python -m PyInstaller --clean --noconfirm harpie.spec
    if ($LASTEXITCODE -ne 0) { throw 'Executable build failed.' }

    $diagnosticRoot = Join-Path $projectRoot ('.review/release-check-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $diagnosticRoot -Force | Out-Null
    $env:HARPIE_HOME = $diagnosticRoot
    $env:QT_QPA_PLATFORM = 'offscreen'
    $check = Start-Process -FilePath (Join-Path $projectRoot 'dist/Harpie.exe') -ArgumentList '--self-check' -WindowStyle Hidden -PassThru
    if (-not $check.WaitForExit(60000)) {
        $check.Kill()
        throw 'Executable diagnostic timed out.'
    }
    $check.Refresh()
    if ($check.ExitCode -ne 0) { throw 'Executable diagnostic failed.' }
    $report = Get-Content -LiteralPath (Join-Path $diagnosticRoot 'self-check.json') -Raw | ConvertFrom-Json
    if (-not ($report.startup -and $report.encrypted_key -and $report.assets -and $report.font)) {
        throw 'Executable startup, cryptography, assets, or font check failed.'
    }
    if ($report.version -ne $appVersion) { throw 'Executable version mismatch.' }
    & $Python tools/package_release.py
    if ($LASTEXITCODE -ne 0) { throw 'Packaging failed.' }
    & $Python tools/release_notes.py | Set-Content -LiteralPath dist/release/RELEASE_NOTES.md -Encoding UTF8
    if ($LASTEXITCODE -ne 0) { throw 'Release notes generation failed.' }
    Write-Host "Verified Harpie $appVersion. Release assets are in dist/release."
} finally {
    $env:HARPIE_HOME = $previousDiagnosticHome
    $env:QT_QPA_PLATFORM = $previousQtPlatform
    Pop-Location
}

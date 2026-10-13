param([string]$Python = 'python', [string]$Iscc = '')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    $appVersion = (& $Python -c 'from version import __version__; print(__version__)').Trim()
    if ($LASTEXITCODE -ne 0 -or $appVersion -notmatch '^\d+\.\d+\.\d+$') { throw 'Invalid application version.' }
    if (-not $Iscc) {
        $command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
        $Iscc = if ($command) { $command.Source } else { Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6/ISCC.exe' }
    }
    if (-not (Test-Path -LiteralPath $Iscc -PathType Leaf)) { throw 'Install Inno Setup 6, or pass -Iscc with the compiler path.' }
    $archive = Join-Path $projectRoot "dist/release/Harpie-$appVersion-windows-x64.zip"
    if (-not (Test-Path -LiteralPath $archive -PathType Leaf)) { throw 'Build the portable release first.' }
    $stage = Join-Path $projectRoot ('.review/installer-stage-' + [guid]::NewGuid().ToString('N'))
    Expand-Archive -LiteralPath $archive -DestinationPath $stage
    & $Iscc "/DAppVersion=$appVersion" "/DPackageDir=$stage" installer/harpie.iss
    if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed.' }
    $installer = Join-Path $projectRoot "dist/release/Harpie-$appVersion-setup-x64.exe"
    $hash = (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash.ToLowerInvariant()
    $zipHash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
    Set-Content -LiteralPath dist/release/SHA256SUMS.txt -Value @("$zipHash  Harpie-$appVersion-windows-x64.zip", "$hash  Harpie-$appVersion-setup-x64.exe") -Encoding ASCII
    Write-Host "Installer created: $installer"
} finally { Pop-Location }

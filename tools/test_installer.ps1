param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Run installer smoke tests only on a disposable GitHub Actions runner.' }
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
$previousDiagnosticHome = $env:HARPIE_HOME
try {
    $appVersion = (& $Python -c 'from version import __version__; print(__version__)').Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read the version.' }
    $installer = Join-Path $projectRoot "dist/release/Harpie-$appVersion-setup-x64.exe"
    $testRoot = Join-Path $env:RUNNER_TEMP ('harpie-installer-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $testRoot -Force | Out-Null
    $env:HARPIE_HOME = Join-Path $testRoot 'home'
    $sshData = Join-Path $env:HARPIE_HOME '.ssh'
    New-Item -ItemType Directory -Path $sshData -Force | Out-Null
    $marker = Join-Path $sshData 'keep.txt'
    Set-Content -LiteralPath $marker -Value 'User data must survive uninstallation.'

    function Run-HiddenProcess([string]$File, [string]$Arguments) {
        $process = Start-Process -FilePath $File -ArgumentList $Arguments -WindowStyle Hidden -PassThru
        if (-not $process.WaitForExit(60000)) { $process.Kill(); throw 'Installer smoke test timed out.' }
        $process.Refresh()
        if ($process.ExitCode -ne 0) { throw "Smoke test process exited with $($process.ExitCode)." }
    }

    foreach ($locale in @('en', 'fr')) {
        $installDir = Join-Path $testRoot ("install-$locale")
        Run-HiddenProcess $installer ('/VERYSILENT /SUPPRESSMSGBOXES /SP- /NORESTART /TASKS="" /LANG=' + $locale + ' /DIR="' + $installDir + '"')
        $executable = Join-Path $installDir 'Harpie.exe'
        $uninstaller = Join-Path $installDir 'unins000.exe'
        if (-not ((Test-Path -LiteralPath $executable) -and (Test-Path -LiteralPath $uninstaller))) { throw 'Installed executable or uninstaller is missing.' }
        $shortcut = Join-Path $env:APPDATA 'Microsoft/Windows/Start Menu/Programs/Harpie/Harpie.lnk'
        if (-not (Test-Path -LiteralPath $shortcut)) { throw 'Start menu shortcut is missing.' }
        Run-HiddenProcess $executable ("--self-check --language $locale")
        $report = Get-Content -LiteralPath (Join-Path $env:HARPIE_HOME 'self-check.json') -Raw | ConvertFrom-Json
        if (-not ($report.startup -and $report.font -and $report.assets -and $report.encrypted_key -and $report.version -eq $appVersion)) { throw 'Installed application diagnostic failed.' }
        $resolvedUninstaller = [IO.Path]::GetFullPath($uninstaller)
        $resolvedTestRoot = [IO.Path]::GetFullPath($testRoot).TrimEnd('\') + '\'
        if (-not $resolvedUninstaller.StartsWith($resolvedTestRoot, [StringComparison]::OrdinalIgnoreCase)) { throw 'Uninstaller path is outside the disposable test directory.' }
        Run-HiddenProcess $uninstaller '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART'
        if (Test-Path -LiteralPath $executable) { throw 'Uninstallation left the executable behind.' }
        if (Test-Path -LiteralPath $shortcut) { throw 'Uninstallation left the Start menu shortcut behind.' }
        if (-not (Test-Path -LiteralPath $marker)) { throw 'Uninstallation removed user SSH data.' }
        Write-Host "Verified $locale installation, startup, and uninstallation; user data preserved."
    }
} finally {
    $env:HARPIE_HOME = $previousDiagnosticHome
    Pop-Location
}

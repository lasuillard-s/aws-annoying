<#
.SYNOPSIS
    Uninstalls AWS Session Manager Plugin from Windows.

.DESCRIPTION
    This script attempts to uninstall AWS Session Manager Plugin using multiple approaches:
    1. Registry-based uninstallation (searches both 64-bit and 32-bit uninstall keys)
    2. Direct removal of installation directories as a fallback

.EXAMPLE
    .\Uninstall-SessionManagerPlugin.ps1

.NOTES
    This script is primarily used in CI workflows to ensure a clean test environment.
#>

[CmdletBinding()]
param()

Write-Host "Starting AWS Session Manager Plugin uninstallation..."

# Uninstall Session Manager Plugin using registry-based approach
# Search in both 64-bit and 32-bit uninstall registry keys
$uninstallPaths = @(
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*"
)

foreach ($path in $uninstallPaths) {
    $apps = Get-ItemProperty $path -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -like "*Session Manager*" }
    foreach ($app in $apps) {
        if ($app.UninstallString) {
            Write-Host "Found Session Manager Plugin, running uninstaller: $($app.UninstallString)"
            $uninstallCmd = $app.UninstallString
            if ($uninstallCmd -match "msiexec") {
                # MSI-based uninstallation
                Start-Process msiexec.exe -ArgumentList "/x $($app.PSChildName) /qn /norestart" -Wait -NoNewWindow
            } else {
                # EXE-based uninstallation
                Start-Process cmd.exe -ArgumentList "/c $uninstallCmd /quiet" -Wait -NoNewWindow
            }
        }
    }
}

# Remove the installation directory directly to ensure clean state (fallback)
$installPaths = @(
    "$env:ProgramFiles\Amazon\SessionManagerPlugin",
    "${env:ProgramFiles(x86)}\Amazon\SessionManagerPlugin"
)

foreach ($installPath in $installPaths) {
    if (Test-Path $installPath) {
        Write-Host "Removing installation directory: $installPath"
        Remove-Item -Path $installPath -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# Verify uninstallation
$smpPath = Get-Command session-manager-plugin -ErrorAction SilentlyContinue
if ($smpPath) {
    Write-Host "WARNING: session-manager-plugin still found at: $($smpPath.Source)"
    exit 1
} else {
    Write-Host "session-manager-plugin successfully removed"
    exit 0
}

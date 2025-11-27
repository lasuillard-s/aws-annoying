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
    # Use specific pattern to match only AWS Session Manager Plugin
    $apps = Get-ItemProperty $path -ErrorAction SilentlyContinue | Where-Object {
        $_.DisplayName -like "*Session Manager Plugin*" -or
        $_.DisplayName -like "*AWS Session Manager*" -or
        $_.Publisher -like "*Amazon*" -and $_.DisplayName -like "*Session Manager*"
    }
    foreach ($app in $apps) {
        if ($app.UninstallString) {
            Write-Host "Found: $($app.DisplayName)"
            Write-Host "Running uninstaller: $($app.UninstallString)"
            $uninstallCmd = $app.UninstallString

            if ($uninstallCmd -match "msiexec") {
                # MSI-based uninstallation - extract ProductCode from UninstallString
                if ($uninstallCmd -match "\{[A-F0-9-]+\}") {
                    $productCode = $matches[0]
                    Write-Host "Uninstalling MSI with ProductCode: $productCode"
                    Start-Process msiexec.exe -ArgumentList "/x $productCode /qn /norestart" -Wait -NoNewWindow
                } else {
                    # Fallback: use registry key name if it looks like a GUID
                    $keyName = $app.PSChildName
                    if ($keyName -match "^\{[A-F0-9-]+\}$") {
                        Write-Host "Uninstalling MSI with key name: $keyName"
                        Start-Process msiexec.exe -ArgumentList "/x $keyName /qn /norestart" -Wait -NoNewWindow
                    }
                }
            }
            # Note: EXE-based uninstaller with /quiet flag is unreliable for this plugin,
            # so we rely on the directory removal fallback below instead
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

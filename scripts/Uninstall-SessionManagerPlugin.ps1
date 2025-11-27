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

function Uninstall-ViaRegistry {
    <#
    .SYNOPSIS
        Uninstalls AWS Session Manager Plugin using registry-based approach.
    #>
    [CmdletBinding()]
    param()

    Write-Host "Attempting registry-based uninstallation..."

    $uninstallPaths = @(
        "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
        "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*"
    )

    foreach ($path in $uninstallPaths) {
        # Use specific pattern to match only AWS Session Manager Plugin
        $apps = Get-ItemProperty $path -ErrorAction SilentlyContinue | Where-Object {
            ($_.DisplayName -like "*Session Manager Plugin*") -or
            ($_.DisplayName -like "*AWS Session Manager*") -or
            (($_.Publisher -like "*Amazon*") -and ($_.DisplayName -like "*Session Manager*"))
        }

        foreach ($app in $apps) {
            if ($app.UninstallString) {
                Write-Host "Found: $($app.DisplayName)"
                Write-Host "Running uninstaller: $($app.UninstallString)"
                $uninstallCmd = $app.UninstallString

                if ($uninstallCmd -match "msiexec") {
                    Invoke-MsiUninstall -UninstallString $uninstallCmd -RegistryKeyName $app.PSChildName
                }
                # Note: EXE-based uninstaller with /quiet flag is unreliable for this plugin,
                # so we rely on the directory removal fallback instead
            }
        }
    }
}

function Invoke-MsiUninstall {
    <#
    .SYNOPSIS
        Invokes MSI-based uninstallation using msiexec.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$UninstallString,

        [Parameter(Mandatory = $true)]
        [string]$RegistryKeyName
    )

    # MSI-based uninstallation - extract ProductCode from UninstallString (case-insensitive for hex digits)
    if ($UninstallString -match "\{[A-Fa-f0-9-]+\}") {
        $productCode = $matches[0]
        Write-Host "Uninstalling MSI with ProductCode: $productCode"
        $process = Start-Process msiexec.exe -ArgumentList "/x $productCode /qn /norestart" -Wait -NoNewWindow -PassThru
        if ($process.ExitCode -ne 0 -and $process.ExitCode -ne 1605) {
            Write-Host "WARNING: MSI uninstallation failed with exit code: $($process.ExitCode)"
        }
    } else {
        # Fallback: use registry key name if it looks like a GUID (case-insensitive for hex digits)
        if ($RegistryKeyName -match "^\{[A-Fa-f0-9-]+\}$") {
            Write-Host "Uninstalling MSI with key name: $RegistryKeyName"
            $process = Start-Process msiexec.exe -ArgumentList "/x $RegistryKeyName /qn /norestart" -Wait -NoNewWindow -PassThru
            if ($process.ExitCode -ne 0 -and $process.ExitCode -ne 1605) {
                Write-Host "WARNING: MSI uninstallation failed with exit code: $($process.ExitCode)"
            }
        }
    }
}

function Remove-InstallationDirectories {
    <#
    .SYNOPSIS
        Removes AWS Session Manager Plugin installation directories directly.
    #>
    [CmdletBinding()]
    param()

    Write-Host "Removing installation directories..."

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
}

function Test-PluginRemoved {
    <#
    .SYNOPSIS
        Verifies that the AWS Session Manager Plugin has been removed.
    .OUTPUTS
        Returns $true if the plugin is removed, $false otherwise.
    #>
    [CmdletBinding()]
    param()

    Write-Host "Verifying uninstallation..."

    # Check for the executable directly in known installation paths
    $exePaths = @(
        "$env:ProgramFiles\Amazon\SessionManagerPlugin\bin\session-manager-plugin.exe",
        "${env:ProgramFiles(x86)}\Amazon\SessionManagerPlugin\bin\session-manager-plugin.exe"
    )

    $foundExe = $false
    foreach ($exePath in $exePaths) {
        if (Test-Path $exePath) {
            Write-Host "WARNING: session-manager-plugin executable still found at: $exePath"
            $foundExe = $true
        }
    }

    return -not $foundExe
}

function Invoke-Uninstall {
    <#
    .SYNOPSIS
        Main entrypoint function that orchestrates the uninstallation process.
    #>
    [CmdletBinding()]
    param()

    Write-Host "Starting AWS Session Manager Plugin uninstallation..."

    # Step 1: Try registry-based uninstallation
    Uninstall-ViaRegistry

    # Step 2: Remove installation directories as fallback
    Remove-InstallationDirectories

    # Step 3: Verify uninstallation
    if (Test-PluginRemoved) {
        Write-Host "session-manager-plugin successfully removed"
        return 0
    } else {
        Write-Host "WARNING: session-manager-plugin could not be fully removed"
        return 1
    }
}

# Execute the uninstallation
$exitCode = Invoke-Uninstall
exit $exitCode

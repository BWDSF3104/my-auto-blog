[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string[]]$Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# maintenance/safe-rmdir.ps1
# Any folder inside the project is deletable (git-tracked content is
# recoverable via git; untracked temp content is disposable by design).
$projectRootFull = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))

# Recycle Bin deletion via the VB wrapper (managed .NET):
#   [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile / DeleteDirectory
#   + RecycleOption.SendToRecycleBin
# SHFileOperation (P/Invoke) was found to fail nondeterministically for
# directory deletion from a console PowerShell context without a message
# loop (ret=2/87/124 mixed), so the managed wrapper is used instead
# (verified 10/10 success).
# Note: the wrapper does not expose FOF_NOAUTORECYCLE, so it may fall back
# to a silent permanent delete when the Recycle Bin cannot hold the item
# (pre-existing Windows behavior).
Add-Type -AssemblyName Microsoft.VisualBasic

function Send-ToRecycleBin {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TargetPath
    )

    # Recycle Bin moves can transiently fail while real-time antivirus
    # scanning or indexing holds the item. Retry while the target
    # still exists.
    $script:RecycleLastError = ''
    $maxAttempts = 3
    $attempt = 0

    $isDir = $false
    if (Test-Path -LiteralPath $TargetPath -PathType Container) {
        $isDir = $true
    }

    while ($true) {
        $attempt++
        try {
            if ($isDir) {
                [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory(
                    $TargetPath,
                    [Microsoft.VisualBasic.FileIO.UIOption]::OnlyErrorDialogs,
                    [Microsoft.VisualBasic.FileIO.RecycleOption]::SendToRecycleBin)
            }
            else {
                [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile(
                    $TargetPath,
                    [Microsoft.VisualBasic.FileIO.UIOption]::OnlyErrorDialogs,
                    [Microsoft.VisualBasic.FileIO.RecycleOption]::SendToRecycleBin)
            }
            return $true
        }
        catch {
            $script:RecycleLastError = $_.Exception.Message
            # Target is gone: another process removed it, treat as success.
            if (-not (Test-Path -LiteralPath $TargetPath)) {
                return $true
            }
            if ($attempt -ge $maxAttempts) {
                return $false
            }
            Start-Sleep -Seconds $attempt
        }
    }
}

function Get-NormalizedFullPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$InputPath
    )

    $resolved = Resolve-Path -LiteralPath $InputPath -ErrorAction Stop
    return [System.IO.Path]::GetFullPath($resolved.Path)
}

function Test-InProject {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FullPath
    )

    $rootWithSeparator = $projectRootFull.TrimEnd('\') + '\'

    return $FullPath.StartsWith(
        $rootWithSeparator,
        [System.StringComparison]::OrdinalIgnoreCase
    )
}

foreach ($target in $Path) {

    # Resolve path: absolute paths used as-is, relative paths resolved from project root
    $resolvePath = $target
    if (-not [System.IO.Path]::IsPathRooted($target)) {
        $resolvePath = Join-Path $projectRootFull $target
    }

    try {
        $item = Get-Item -LiteralPath $resolvePath -Force -ErrorAction Stop
        $fullPath = Get-NormalizedFullPath $resolvePath
    }
    catch {
        Write-Error "Target does not exist: $target"
        exit 1
    }

    # Files are not allowed (use safe-remove.cmd instead)
    if (-not $item.PSIsContainer) {
        Write-Error "This script is for directories only: $fullPath"
        exit 1
    }

    # Symbolic links are not allowed
    if ($item.LinkType -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        Write-Error "Deleting symbolic links is not allowed: $fullPath"
        exit 1
    }

    # Outside project is not allowed
    if (-not (Test-InProject $fullPath)) {
        Write-Error "Deleting outside project is not allowed: $fullPath"
        exit 1
    }

    # Get relative path from project root
    $rootPrefix = $projectRootFull.TrimEnd('\') + '\'
    $relativePath = $fullPath.Substring($rootPrefix.Length)

    # Prevent deleting the project root itself
    if ([string]::IsNullOrEmpty($relativePath)) {
        Write-Error "Deleting project root is not allowed"
        exit 1
    }

    # Block protected areas
    if ($relativePath -eq '.git' -or
        $relativePath.StartsWith('.git\') -or
        $relativePath -eq '.kilo' -or
        $relativePath.StartsWith('.kilo\')) {

        Write-Error "Deleting protected area is not allowed: $relativePath"
        exit 1
    }

    Write-Host "Sent to Recycle Bin: $relativePath"
    if (-not (Send-ToRecycleBin $fullPath)) {
        Write-Error "Failed to send to Recycle Bin ($script:RecycleLastError): $relativePath"
        exit 1
    }
}

exit 0

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string[]]$Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# .kilo/scripts/safe-rmdir.ps1
# Any folder inside the project is deletable (git-tracked content is
# recoverable via git; untracked temp content is disposable by design).
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$projectRootFull = [System.IO.Path]::GetFullPath($projectRoot)

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

    Write-Host "Deleted: $relativePath"
    Remove-Item -LiteralPath $fullPath -Recurse -Force
}

exit 0

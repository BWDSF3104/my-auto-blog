[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string[]]$Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# .kilo/scripts/safe-remove.ps1
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

    try {
        $item = Get-Item -LiteralPath $target -Force -ErrorAction Stop
        $fullPath = Get-NormalizedFullPath $target
    }
    catch {
        Write-Error "対象が存在しないため削除を中止しました: $target"
        exit 1
    }

    # ディレクトリ削除は禁止
    if ($item.PSIsContainer) {
        Write-Error "ディレクトリ削除は禁止されています: $fullPath"
        exit 1
    }

    # シンボリックリンク等は安全のため禁止
    if ($item.LinkType -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        Write-Error "シンボリックリンク/再解析ポイントの削除は禁止されています: $fullPath"
        exit 1
    }

    # プロジェクト外は禁止
    if (-not (Test-InProject $fullPath)) {
        Write-Error "プロジェクト外への削除は禁止されています: $fullPath"
        exit 1
    }

    # プロジェクトルート直下の特殊領域を保護
    $rootPrefix = $projectRootFull.TrimEnd('\') + '\'
    if ($fullPath.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        $relativePath = $fullPath.Substring($rootPrefix.Length)
    }
    else {
        $relativePath = $fullPath
    }

    if ($relativePath -eq '.git' -or
        $relativePath.StartsWith('.git\') -or
        $relativePath -eq '.kilo' -or
        $relativePath.StartsWith('.kilo\')) {

        Write-Error "保護された領域の削除は禁止されています: $relativePath"
        exit 1
    }

    Write-Host "削除: $relativePath"
    Remove-Item -LiteralPath $fullPath -Force
}

exit 0
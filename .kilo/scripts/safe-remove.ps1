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

# ゴミ箱削除は VB ラッパー (managed .NET) で実施。
#   [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile / DeleteDirectory
#   + RecycleOption.SendToRecycleBin
# SHFileOperation (P/Invoke) はメッセージループのないコンソール PowerShell
# 環境でディレクトリ削除が非決定的に失敗する (ret=2/87/124 混在) ことを
# 検証で確認したため、安定した managed ラッパーへ移行 (検証 10/10 成功)。
# 注: ラッパーは FOF_NOAUTORECYCLE を公開しないため、ゴミ箱容量超過時に
# 静かな恒久削除へフォールバックし得る (既存の Windows 挙動)。
Add-Type -AssemblyName Microsoft.VisualBasic

function Send-ToRecycleBin {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TargetPath
    )

    # ゴミ箱への移動は、リアルタイム AV スキャン・インデクサが対象を
    # 保持中の間で一時的に失敗し得る。対象が存在する限りリトライする。
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
            # 対象が消えた場合は他プロセスが削除済みとみなして成功とする
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

    # Resolve path relative to project root, not cwd
    $resolvePath = $target
    if (-not [System.IO.Path]::IsPathRooted($target)) {
        $resolvePath = Join-Path $projectRootFull $target
    }

    try {
        $item = Get-Item -LiteralPath $resolvePath -Force -ErrorAction Stop
        $fullPath = Get-NormalizedFullPath $resolvePath
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

    Write-Host "ゴミ箱に移動: $relativePath"
    if (-not (Send-ToRecycleBin $fullPath)) {
        Write-Error "ゴミ箱への移動に失敗しました（$script:RecycleLastError）: $relativePath"
        exit 1
    }
}

exit 0
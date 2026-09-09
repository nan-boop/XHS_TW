param(
    [string]$Root = "",
    [string]$PythonPath = "",
    [string]$OutputDir = "",
    [string]$SessionFile = "",
    [int]$Port = 8765,
    [switch]$NoOpen
)

$ErrorActionPreference = "Stop"
$skillDir = Split-Path -Parent $PSScriptRoot
$bootstrap = Join-Path $PSScriptRoot "bootstrap_spider_xhs_runtime.ps1"

if ($Root) {
    & $bootstrap -Root $Root -PythonPath $PythonPath -InstallPrerequisites
    $resolvedRoot = [IO.Path]::GetFullPath($Root)
} else {
    & $bootstrap -PythonPath $PythonPath -InstallPrerequisites
    if ($env:XHS_SPIDER_ROOT) {
        $resolvedRoot = [IO.Path]::GetFullPath($env:XHS_SPIDER_ROOT)
    } else {
        $searchRoots = Get-PSDrive -PSProvider FileSystem | Where-Object Name -ne "C" | ForEach-Object Root
        $resolvedRoot = Get-ChildItem -Path $searchRoots -Directory -Filter "Spider_XHS" -Recurse -Depth 4 -ErrorAction SilentlyContinue |
            Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName "xhs_utils") } |
            Select-Object -First 1 -ExpandProperty FullName
    }
}

if (-not $resolvedRoot -or -not (Test-Path -LiteralPath $resolvedRoot)) {
    throw "Spider_XHS root could not be resolved after bootstrap."
}

$venvPython = Join-Path $resolvedRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "Spider_XHS virtual-environment Python was not found: $venvPython"
}

if (-not $OutputDir) {
    $drive = Get-PSDrive -PSProvider FileSystem | Where-Object Name -ne "C" | Sort-Object Name | Select-Object -First 1
    if (-not $drive) { throw "No non-C drive is available for QR output." }
    $OutputDir = Join-Path $drive.Root "Codex\xhs_login_panel_qr"
}

$panel = Join-Path $PSScriptRoot "creator_login_panel.py"
$panelArgs = @($panel, "--root", $resolvedRoot, "--output-dir", $OutputDir, "--port", $Port)
if ($SessionFile) { $panelArgs += @("--session-file", $SessionFile) }
if ($NoOpen) { $panelArgs += "--no-open" }
& $venvPython @panelArgs
exit $LASTEXITCODE

param(
    [string]$Root = "",
    [string]$PythonPath = "",
    [switch]$CheckOnly,
    [switch]$InstallPrerequisites
)

$ErrorActionPreference = "Stop"
$repoUrl = "https://github.com/cv-cat/Spider_XHS.git"

function Refresh-ProcessPath {
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $paths = @($machinePath, $userPath) | Where-Object { $_ }
    if ($paths) { $env:Path = $paths -join ";" }
}

function Find-Executable([string[]]$Names, [string[]]$Candidates) {
    foreach ($name in $Names) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) { return $command.Source }
    }
    foreach ($candidate in $Candidates) {
        if (Test-Path -LiteralPath $candidate) { return (Resolve-Path -LiteralPath $candidate).Path }
    }
    return $null
}

function Resolve-Python([string]$Requested) {
    if ($Requested) {
        $command = Get-Command $Requested -ErrorAction SilentlyContinue
        if ($command) { return $command.Source }
        if (Test-Path -LiteralPath $Requested) { return (Resolve-Path -LiteralPath $Requested).Path }
        throw "Python not found: $Requested"
    }
    $python = Find-Executable @("python", "py") @(
        "$env:LocalAppData\Programs\Python\Python312\python.exe",
        "$env:LocalAppData\Programs\Python\Python311\python.exe",
        "$env:ProgramFiles\Python312\python.exe",
        "$env:ProgramFiles\Python311\python.exe"
    )
    if ($python) { return $python }
    if ($InstallPrerequisites) {
        $winget = Get-Command winget -ErrorAction SilentlyContinue
        if ($winget) {
            & $winget.Source install --id Python.Python.3.12 -e --accept-package-agreements --accept-source-agreements *> $null
            Refresh-ProcessPath
            $python = Find-Executable @("python", "py") @(
                "$env:LocalAppData\Programs\Python\Python312\python.exe",
                "$env:LocalAppData\Programs\Python\Python311\python.exe",
                "$env:ProgramFiles\Python312\python.exe",
                "$env:ProgramFiles\Python311\python.exe"
            )
            if ($python) { return $python }
        }
    }
    throw "Python was not found. Automatic installation was unavailable or unsuccessful; install Python 3.10+ or pass -PythonPath."
}

function Ensure-Node {
    $node = Find-Executable @("node") @(
        "$env:ProgramFiles\nodejs\node.exe",
        "$env:LocalAppData\Programs\nodejs\node.exe"
    )
    $npm = Find-Executable @("npm", "npm.cmd") @(
        "$env:ProgramFiles\nodejs\npm.cmd",
        "$env:LocalAppData\Programs\nodejs\npm.cmd"
    )
    if ($node -and $npm) { return @($node, $npm) }
    if ($node -and (Test-Path -LiteralPath (Join-Path $root "node_modules"))) {
        return @($node, "")
    }
    if ($InstallPrerequisites) {
        $winget = Get-Command winget -ErrorAction SilentlyContinue
        if ($winget) {
            & $winget.Source install --id OpenJS.NodeJS.LTS -e --accept-package-agreements --accept-source-agreements *> $null
            Refresh-ProcessPath
            $node = Find-Executable @("node") @(
                "$env:ProgramFiles\nodejs\node.exe",
                "$env:LocalAppData\Programs\nodejs\node.exe"
            )
            $npm = Find-Executable @("npm", "npm.cmd") @(
                "$env:ProgramFiles\nodejs\npm.cmd",
                "$env:LocalAppData\Programs\nodejs\npm.cmd"
            )
            if ($node -and $npm) { return @($node, $npm) }
        }
    }
    throw "Node.js and npm were not found. Automatic installation was unavailable or unsuccessful; install Node.js LTS and rerun this script."
}

function Resolve-Root([string]$Requested) {
    if ($Requested) { $candidate = [IO.Path]::GetFullPath($Requested) }
    elseif ($env:XHS_SPIDER_ROOT) { $candidate = [IO.Path]::GetFullPath($env:XHS_SPIDER_ROOT) }
    else {
        $searchRoots = Get-PSDrive -PSProvider FileSystem | Where-Object Name -ne "C" | ForEach-Object Root
        $existing = Get-ChildItem -Path $searchRoots -Directory -Filter "Spider_XHS" -Recurse -Depth 4 -ErrorAction SilentlyContinue |
            Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName "xhs_utils") } |
            Sort-Object @{ Expression = { if (Test-Path -LiteralPath (Join-Path $_.FullName "node_modules")) { 0 } else { 1 } } } |
            Select-Object -First 1
        if ($existing) { $candidate = $existing.FullName }
        else {
            $drive = Get-PSDrive -PSProvider FileSystem | Where-Object Name -ne "C" | Sort-Object Name | Select-Object -First 1
            if (-not $drive) { throw "No non-C drive is available for Spider_XHS." }
            $candidate = Join-Path $drive.Root "Codex\Spider_XHS"
        }
    }
    if ([IO.Path]::GetPathRoot($candidate) -match "^[Cc]:\\$") {
        throw "Spider_XHS must be stored on a non-C drive. Choose another -Root path."
    }
    return $candidate
}

$root = Resolve-Root $Root
$python = Resolve-Python $PythonPath
$checker = Join-Path $PSScriptRoot "check_spider_xhs_runtime.py"

if ($CheckOnly) {
    if (-not (Test-Path -LiteralPath $root)) { throw "Spider_XHS directory not found: $root" }
    & $python $checker --root $root
    exit $LASTEXITCODE
}

$nodeTools = Ensure-Node
$nodePath = $nodeTools[0]
$npmPath = $nodeTools[1]
$git = Get-Command git -ErrorAction SilentlyContinue

if (-not (Test-Path -LiteralPath (Join-Path $root "xhs_utils"))) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $root) | Out-Null
    if ($git) {
        & $git.Source clone --depth 1 $repoUrl $root
    }
    else {
        $parent = Split-Path -Parent $root
        $zip = Join-Path $parent "Spider_XHS-download.zip"
        $stage = Join-Path $parent "Spider_XHS-download"
        Invoke-WebRequest -UseBasicParsing -Uri "https://github.com/cv-cat/Spider_XHS/archive/refs/heads/master.zip" -OutFile $zip
        if (Test-Path -LiteralPath $stage) { throw "Temporary download directory already exists: $stage" }
        Expand-Archive -LiteralPath $zip -DestinationPath $stage
        $extracted = Get-ChildItem -LiteralPath $stage -Directory | Select-Object -First 1
        if (-not $extracted) { throw "Spider_XHS ZIP did not contain a project directory." }
        Move-Item -LiteralPath $extracted.FullName -Destination $root
        Remove-Item -LiteralPath $zip -Force
        Remove-Item -LiteralPath $stage -Recurse -Force
    }
}

$venv = Join-Path $root ".venv"
$venvPython = Join-Path $venv "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    & $python -m venv $venv
}
& $venvPython -m pip install -r (Join-Path $root "requirements.txt")
# The current Spider_XHS Creator transport uses the chrome150 profile, which
# is not present in the repository's older curl_cffi pin.
& $venvPython -m pip install "curl_cffi>=0.16.2,<0.17"
& $venvPython -m pip install "Pillow>=10"
Push-Location $root
try {
    if ($npmPath) {
        & $npmPath install
    }
    else {
        Write-Output "npm unavailable; reusing existing node_modules."
    }
}
finally {
    Pop-Location
}
& $venvPython $checker --root $root
if ($LASTEXITCODE -ne 0) { throw "Spider_XHS runtime validation failed." }
Write-Output "Spider_XHS runtime ready: $root"

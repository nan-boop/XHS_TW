[CmdletBinding()]
param(
    [switch]$CheckOnly
)

$ErrorActionPreference = 'Stop'
$skillRoot = Split-Path -Parent $PSScriptRoot
$vendorRoot = Join-Path $skillRoot 'vendor'
$vendors = @(
    @{
        Name = 'zhongcao'
        Url = 'https://github.com/1-SKILL/zhongcao.git'
    },
    @{
        Name = 'xiaohongshu-skills'
        Url = 'https://github.com/vivy-yi/xiaohongshu-skills.git'
    }
)

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw 'Git is required to manage the vendored copywriting skills.'
}

New-Item -ItemType Directory -Force -Path $vendorRoot | Out-Null

foreach ($vendor in $vendors) {
    $target = Join-Path $vendorRoot $vendor.Name
    $gitDir = Join-Path $target '.git'

    if (-not (Test-Path -LiteralPath $gitDir)) {
        if ($CheckOnly) {
            throw "Missing vendor checkout: $target"
        }
        git clone --depth 1 $vendor.Url $target
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to clone $($vendor.Name)."
        }
    }
    elseif (-not $CheckOnly) {
        git -C $target pull --ff-only
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to update $($vendor.Name)."
        }
    }

    $commit = git -C $target rev-parse HEAD
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to read commit for $($vendor.Name)."
    }
    [pscustomobject]@{
        Name = $vendor.Name
        Path = $target
        Commit = $commit.Trim()
    }
}

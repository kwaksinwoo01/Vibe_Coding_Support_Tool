#requires -Version 5.1
[CmdletBinding()]
param(
    [switch]$Install,
    [string]$NormalPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw 'Python launcher (py.exe) was not found. Install Python 3.11 or later.'
}

$venv = Join-Path $projectRoot '.venv'
$python = Join-Path $venv 'Scripts\python.exe'

if (-not (Test-Path -LiteralPath $python)) {
    & py -3.11 -m venv $venv
}

if ($Install) {
    & $python -m pip install --upgrade pip
    & $python -m pip install -e '.[test]'
}

$arguments = @('-m', 'word_editor')
if (-not [string]::IsNullOrWhiteSpace($NormalPath)) {
    $arguments += @('--normal-path', $NormalPath)
}

& $python @arguments
exit $LASTEXITCODE

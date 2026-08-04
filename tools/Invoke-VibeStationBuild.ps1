#requires -Version 5.1
[CmdletBinding()]
param(
    [string]$PythonPath,
    [switch]$RecreateVenv,
    [switch]$SkipInstall
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$env:PYTHONHOME = $null
$env:PYTHONPATH = $null

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$versionFile = Join-Path $repositoryRoot '.python-version'
$requirementsFile = Join-Path $repositoryRoot 'requirements.txt'
$specFile = Join-Path $repositoryRoot 'vibeStation.spec'
$venv = Join-Path $repositoryRoot '.venv'
$venvPython = Join-Path $venv 'Scripts\python.exe'

foreach ($requiredFile in @($versionFile, $requirementsFile, $specFile)) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
        throw "Required build file is missing: $requiredFile"
    }
}

$requiredVersion = [version](Get-Content -LiteralPath $versionFile -Raw).Trim()

function Get-PythonVersion {
    param([Parameter(Mandatory = $true)] [string]$Executable)

    if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) { return $null }
    $probe = 'import sys; print(chr(46).join(map(str,sys.version_info[:3])))'
    try {
        $output = @($probe | & $Executable - 2>&1)
        if ($LASTEXITCODE -ne 0) { return $null }
        return [version]([string]($output | Select-Object -Last 1)).Trim()
    }
    catch { return $null }
}

function Find-RequiredPython {
    $candidates = New-Object 'System.Collections.Generic.List[string]'
    foreach ($candidate in @(
        $PythonPath,
        (Join-Path $env:ProgramFiles 'Python314\python.exe'),
        $(if ($env:LOCALAPPDATA) {
            Join-Path $env:LOCALAPPDATA 'Programs\Python\Python314\python.exe'
        })
    )) {
        if (-not [string]::IsNullOrWhiteSpace($candidate)) {
            $fullPath = [System.IO.Path]::GetFullPath($candidate)
            if (-not $candidates.Contains($fullPath)) { [void]$candidates.Add($fullPath) }
        }
    }

    foreach ($commandName in @('python3.exe', 'python.exe', 'python3', 'python')) {
        $command = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($null -ne $command -and -not [string]::IsNullOrWhiteSpace($command.Source)) {
            $fullPath = [System.IO.Path]::GetFullPath($command.Source)
            if (-not $candidates.Contains($fullPath)) { [void]$candidates.Add($fullPath) }
        }
    }

    foreach ($candidate in $candidates) {
        if ((Get-PythonVersion -Executable $candidate) -eq $requiredVersion) {
            return $candidate
        }
    }
    return $null
}

function Remove-RepositoryVenv {
    if (-not (Test-Path -LiteralPath $venv -PathType Container)) { return }

    $resolvedRepository = [System.IO.Path]::GetFullPath($repositoryRoot).TrimEnd('\')
    $resolvedVenv = [System.IO.Path]::GetFullPath($venv).TrimEnd('\')
    if (
        [System.IO.Path]::GetDirectoryName($resolvedVenv) -ne $resolvedRepository -or
        [System.IO.Path]::GetFileName($resolvedVenv) -ne '.venv'
    ) {
        throw "Refusing to remove unexpected virtual environment path: $resolvedVenv"
    }

    Write-Host "Removing incompatible repository virtual environment: $resolvedVenv"
    Remove-Item -LiteralPath $resolvedVenv -Recurse -Force
}

Set-Location $repositoryRoot
$venvVersion = Get-PythonVersion -Executable $venvPython
if ($RecreateVenv -or $venvVersion -ne $requiredVersion) {
    $basePython = Find-RequiredPython
    if ([string]::IsNullOrWhiteSpace($basePython)) {
        throw (
            "Python $requiredVersion was not found. Install that exact version or pass " +
            '-PythonPath "C:\Path\To\python.exe".'
        )
    }

    Remove-RepositoryVenv
    Write-Host "Creating repository .venv with Python ${requiredVersion}: $basePython"
    & $basePython -m venv $venv
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create repository .venv. Exit code: $LASTEXITCODE"
    }
}

if ((Get-PythonVersion -Executable $venvPython) -ne $requiredVersion) {
    throw "Repository .venv is not running Python ${requiredVersion}: $venvPython"
}

Write-Host "Repository Python: $venvPython ($requiredVersion)"
if (-not $SkipInstall) {
    & $venvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $venvPython -m pip install -r $requirementsFile
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

& $venvPython -m PyInstaller $specFile
exit $LASTEXITCODE

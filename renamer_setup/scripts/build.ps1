param(
    [switch]$SkipTests,
    [switch]$SkipPythonInstall
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$EncodingVerifier = Join-Path $PSScriptRoot 'verify_text_encoding.ps1'
if (-not (Test-Path -LiteralPath $EncodingVerifier)) {
    throw "Encoding verifier not found: $EncodingVerifier"
}

& powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File $EncodingVerifier
if ($LASTEXITCODE -ne 0) {
    throw 'UTF-8 BOM validation failed.'
}

function New-PythonCandidate {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Executable,
        [string[]]$PrefixArguments = @()
    )

    [pscustomobject]@{
        Executable      = $Executable
        PrefixArguments = [string[]]$PrefixArguments
        Version         = ''
    }
}

function Test-PythonCandidate {
    param(
        [Parameter(Mandatory = $true)]
        [psobject]$Candidate
    )

    $executable = [string]$Candidate.Executable
    if (-not $executable) {
        return $false
    }

    # Microsoft Store 앱 실행 별칭은 실제 Python이 아니며 실행 시 WinGet/Store를 열 수 있습니다.
    $windowsAppsRoot = Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps'
    if ($executable.StartsWith($windowsAppsRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $false
    }

    if (-not (Test-Path -LiteralPath $executable)) {
        return $false
    }

    $prefixArguments = @($Candidate.PrefixArguments)
    $versionScript = @'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
raise SystemExit(0 if sys.version_info >= (3, 11) else 9)
'@

    try {
        $versionOutput = & $executable @prefixArguments -c $versionScript 2>$null
        $exitCode = $LASTEXITCODE
    }
    catch {
        return $false
    }

    if ($exitCode -ne 0) {
        return $false
    }

    $versionLine = $versionOutput | Select-Object -Last 1
    if ($null -eq $versionLine) {
        return $false
    }

    $Candidate.Version = ([string]$versionLine).Trim()
    return $true
}

function Get-RegistryPythonExecutables {
    $registryRoots = @(
        'HKCU:\Software\Python\PythonCore',
        'HKLM:\Software\Python\PythonCore',
        'HKLM:\Software\WOW6432Node\Python\PythonCore'
    )

    foreach ($registryRoot in $registryRoots) {
        if (-not (Test-Path -LiteralPath $registryRoot)) {
            continue
        }

        foreach ($versionKey in Get-ChildItem -LiteralPath $registryRoot -ErrorAction SilentlyContinue) {
            $installPathKey = Join-Path $versionKey.PSPath 'InstallPath'
            if (-not (Test-Path -LiteralPath $installPathKey)) {
                continue
            }

            try {
                $installPath = (Get-Item -LiteralPath $installPathKey).GetValue('')
            }
            catch {
                continue
            }

            if ($installPath) {
                $pythonPath = Join-Path ([string]$installPath) 'python.exe'
                if (Test-Path -LiteralPath $pythonPath) {
                    Write-Output $pythonPath
                }
            }
        }
    }
}

function Get-PythonCandidates {
    $candidates = @()

    $pyLauncher = Get-Command 'py.exe' -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        $candidates += New-PythonCandidate -Executable $pyLauncher.Source -PrefixArguments @('-3.11')
        $candidates += New-PythonCandidate -Executable $pyLauncher.Source -PrefixArguments @('-3')
    }

    foreach ($commandName in @('python.exe', 'python3.exe', 'python')) {
        $command = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($command -and $command.Source) {
            $candidates += New-PythonCandidate -Executable $command.Source
        }
    }

    foreach ($pythonPath in Get-RegistryPythonExecutables) {
        $candidates += New-PythonCandidate -Executable $pythonPath
    }

    $searchRoots = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Python'),
        $env:ProgramFiles,
        ${env:ProgramFiles(x86)},
        'C:\'
    ) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }

    foreach ($searchRoot in $searchRoots) {
        $directoryPattern = if ($searchRoot -eq 'C:\') { 'Python*' } else { 'Python*' }
        foreach ($directory in Get-ChildItem -LiteralPath $searchRoot -Directory -Filter $directoryPattern -ErrorAction SilentlyContinue) {
            $pythonPath = Join-Path $directory.FullName 'python.exe'
            if (Test-Path -LiteralPath $pythonPath) {
                $candidates += New-PythonCandidate -Executable $pythonPath
            }
        }
    }

    return $candidates
}

function Find-Python {
    $seen = @{}

    foreach ($candidate in @(Get-PythonCandidates)) {
        $prefixText = (@($candidate.PrefixArguments) -join ' ')
        $key = (([string]$candidate.Executable) + '|' + $prefixText).ToLowerInvariant()
        if ($seen.ContainsKey($key)) {
            continue
        }
        $seen[$key] = $true

        if (Test-PythonCandidate -Candidate $candidate) {
            $displayCommand = ([string]$candidate.Executable)
            if ($prefixText) {
                $displayCommand += ' ' + $prefixText
            }
            Write-Host "Using Python $($candidate.Version): $displayCommand" -ForegroundColor Green
            return $candidate
        }
    }

    return $null
}

function Refresh-ProcessPath {
    $machinePath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = @($machinePath, $userPath) -join ';'
}

function Install-BuildPython {
    if ($SkipPythonInstall) {
        return $false
    }

    $winget = Get-Command 'winget.exe' -ErrorAction SilentlyContinue
    if (-not $winget) {
        return $false
    }

    Write-Host ''
    Write-Host 'Python 3.11 이상을 찾지 못했습니다.' -ForegroundColor Yellow
    Write-Host 'WinGet으로 빌드용 Python 설치를 시도합니다.' -ForegroundColor Yellow

    & $winget.Source source update --name winget | Out-Host

    foreach ($packageId in @('Python.Python.3.12', 'Python.Python.3.11')) {
        Write-Host "Installing $packageId ..."
        & $winget.Source install `
            --id $packageId `
            --exact `
            --source winget `
            --scope user `
            --silent `
            --disable-interactivity `
            --accept-package-agreements `
            --accept-source-agreements | Out-Host

        Refresh-ProcessPath
        $installedPython = Find-Python
        if ($installedPython) {
            $script:PythonCommand = $installedPython
            return $true
        }
    }

    return $false
}

function Invoke-Python {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Arguments
    )

    $executable = [string]$script:PythonCommand.Executable
    $prefixArguments = @($script:PythonCommand.PrefixArguments)

    & $executable @prefixArguments @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed: $($Arguments -join ' ')"
    }
}

$script:PythonCommand = Find-Python
if (-not $script:PythonCommand) {
    [void](Install-BuildPython)
}

if (-not $script:PythonCommand) {
    throw @'
실제로 실행 가능한 Python 3.11 이상을 찾지 못했습니다.
Windows의 앱 실행 별칭 python.exe는 빌드용 Python으로 사용하지 않습니다.

다음 명령 중 하나로 Python을 설치한 뒤 새 PowerShell을 열어 다시 실행하세요.
  winget install --id Python.Python.3.12 --exact --source winget
  winget install --id Python.Python.3.11 --exact --source winget

자동 설치를 원하지 않는 경우 build.ps1 -SkipPythonInstall 옵션을 사용할 수 있습니다.
'@
}

$Venv = Join-Path $ProjectRoot '.venv-build'
$VenvPython = Join-Path $Venv 'Scripts\python.exe'

if (Test-Path -LiteralPath $Venv) {
    $venvCandidate = New-PythonCandidate -Executable $VenvPython
    if (-not (Test-PythonCandidate -Candidate $venvCandidate)) {
        Write-Host 'Removing incomplete or invalid build virtual environment...' -ForegroundColor Yellow
        Remove-Item -LiteralPath $Venv -Recurse -Force
    }
}

if (-not (Test-Path -LiteralPath $VenvPython)) {
    Write-Host 'Creating build virtual environment...'
    Invoke-Python -m venv $Venv
}

$venvCandidate = New-PythonCandidate -Executable $VenvPython
if (-not (Test-PythonCandidate -Candidate $venvCandidate)) {
    throw "Virtual environment Python is invalid: $VenvPython"
}

$Python = $VenvPython

& $Python -m pip install --upgrade pip setuptools wheel
if ($LASTEXITCODE -ne 0) {
    throw 'Failed to upgrade build packaging tools.'
}

& $Python -m pip install -e '.[build]'
if ($LASTEXITCODE -ne 0) {
    throw 'Failed to install project build dependencies.'
}

if (-not $SkipTests) {
    & $Python -m pytest -q
    if ($LASTEXITCODE -ne 0) {
        throw 'Tests failed.'
    }
}

Remove-Item -Recurse -Force -ErrorAction SilentlyContinue `
    (Join-Path $ProjectRoot 'build'), `
    (Join-Path $ProjectRoot 'dist\classifier')

& $Python -m PyInstaller --noconfirm classifier.spec
if ($LASTEXITCODE -ne 0) {
    throw 'PyInstaller build failed.'
}

$MakensisCandidates = @(
    (Get-Command makensis.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
    "$env:ProgramFiles(x86)\NSIS\makensis.exe",
    "$env:ProgramFiles\NSIS\makensis.exe"
) | Where-Object { $_ -and (Test-Path $_) }

$Makensis = $MakensisCandidates | Select-Object -First 1
if (-not $Makensis) {
    throw 'NSIS makensis.exe를 찾을 수 없습니다. NSIS 3.x를 설치하세요.'
}

Push-Location (Join-Path $ProjectRoot 'installer')
try {
    & $Makensis `
        '/INPUTCHARSET' `
        'UTF8' `
        '/OUTPUTCHARSET' `
        'UTF8SIG' `
        'ReNamer_Setup.nsi'
    if ($LASTEXITCODE -ne 0) {
        throw 'NSIS build failed.'
    }
}
finally {
    Pop-Location
}

$Installer = Join-Path $ProjectRoot 'dist\ReNamer_Setup.exe'
if (-not (Test-Path $Installer)) {
    throw "Installer output not found: $Installer"
}

Write-Host ''
Write-Host 'Build successful:' -ForegroundColor Green
Write-Host $Installer

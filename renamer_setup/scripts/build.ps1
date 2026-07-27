param(
    [switch]$SkipTests,
    [switch]$AllowPythonInstall
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
    if (-not $executable -or -not (Test-Path -LiteralPath $executable)) {
        return $false
    }

    # WindowsApps의 python.exe/python3.exe는 Store 실행 별칭일 수 있습니다.
    # py.exe는 실제 Python Launcher일 수 있으므로 WindowsApps에 있어도 실행 검증합니다.
    $windowsAppsRoot = Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps'
    $fileName = [System.IO.Path]::GetFileName($executable)
    $isStorePythonAlias =
        $executable.StartsWith(
            $windowsAppsRoot,
            [System.StringComparison]::OrdinalIgnoreCase
        ) -and
        ($fileName -in @('python.exe', 'python3.exe', 'pythonw.exe'))

    if ($isStorePythonAlias) {
        return $false
    }

    $prefixArguments = @($Candidate.PrefixArguments)
    $versionProbe = 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"); raise SystemExit(0 if (3, 11) <= sys.version_info[:2] <= (3, 13) else 9)'

    try {
        $versionOutput = & $executable @prefixArguments -c $versionProbe 2>$null
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

    # 현재 활성화된 가상환경을 가장 먼저 사용합니다.
    if ($env:VIRTUAL_ENV) {
        $activeVenvPython = Join-Path $env:VIRTUAL_ENV 'Scripts\python.exe'
        if (Test-Path -LiteralPath $activeVenvPython) {
            $candidates += New-PythonCandidate -Executable $activeVenvPython
        }
    }

    # 사용자가 설치한 Python 3.13을 명시적으로 최우선 탐색합니다.
    $pyLauncher = Get-Command 'py.exe' -ErrorAction SilentlyContinue
    if ($pyLauncher -and $pyLauncher.Source) {
        foreach ($selector in @('-3.13', '-3.12', '-3.11', '-3')) {
            $candidates += New-PythonCandidate `
                -Executable $pyLauncher.Source `
                -PrefixArguments @($selector)
        }
    }

    $knownUserInstallPaths = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe')
    )
    foreach ($pythonPath in $knownUserInstallPaths) {
        if (Test-Path -LiteralPath $pythonPath) {
            $candidates += New-PythonCandidate -Executable $pythonPath
        }
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
            $displayCommand = [string]$candidate.Executable
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
    if (-not $AllowPythonInstall) {
        return $false
    }

    $winget = Get-Command 'winget.exe' -ErrorAction SilentlyContinue
    if (-not $winget) {
        return $false
    }

    Write-Host ''
    Write-Host 'Python 3.11~3.13을 찾지 못했습니다.' -ForegroundColor Yellow
    Write-Host 'AllowPythonInstall 옵션에 따라 WinGet 설치를 시도합니다.' -ForegroundColor Yellow

    $logPath = Join-Path $ProjectRoot 'python-install.log'
    foreach ($packageId in @('Python.Python.3.13', 'Python.Python.3.12', 'Python.Python.3.11')) {
        Write-Host "Installing $packageId ..."

        $arguments = @(
            'install',
            '--id', $packageId,
            '--exact',
            '--source', 'winget',
            '--scope', 'user',
            '--silent',
            '--disable-interactivity',
            '--accept-package-agreements',
            '--accept-source-agreements'
        )

        $process = Start-Process `
            -FilePath $winget.Source `
            -ArgumentList $arguments `
            -Wait `
            -PassThru `
            -NoNewWindow `
            -RedirectStandardOutput $logPath `
            -RedirectStandardError ($logPath + '.error')

        Refresh-ProcessPath
        $installedPython = Find-Python
        if ($installedPython) {
            $script:PythonCommand = $installedPython
            return $true
        }

        Write-Host "WinGet exit code: $($process.ExitCode). Log: $logPath" -ForegroundColor Yellow
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
실행 가능한 Python 3.11~3.13을 찾지 못했습니다.
WindowsApps의 python.exe 실행 별칭은 빌드용 Python으로 사용하지 않습니다.

Python 3.13이 설치되어 있다면 다음 명령이 성공하는지 확인하세요.
  py -3.13 --version
  py -3.13 -c "import sys; print(sys.executable)"

자동 설치는 기본적으로 실행하지 않습니다. 필요한 경우에만 다음처럼 실행하세요.
  .\scripts\build.ps1 -AllowPythonInstall
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

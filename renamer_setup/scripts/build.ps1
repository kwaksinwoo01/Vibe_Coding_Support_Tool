param(
    [switch]$SkipTests,
    [string]$PythonPath = '',
    [string]$CorrespondentFile = ''
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

function Resolve-CorrespondentInput {
    $explicitInput = -not [string]::IsNullOrWhiteSpace($CorrespondentFile)
    if ($explicitInput) {
        $candidate = [Environment]::ExpandEnvironmentVariables($CorrespondentFile)
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            throw ('The specified CorrespondentFile was not found: {0}' -f $candidate)
        }
    }
    else {
        $candidate = Join-Path $ProjectRoot 'private\correspondent.txt'
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            Write-Host 'No private correspondent input found; the installer will create an empty list.' -ForegroundColor Yellow
            return $null
        }
    }

    $resolved = (Resolve-Path -LiteralPath $candidate).Path
    $bytes = [System.IO.File]::ReadAllBytes($resolved)
    $hasUtf8Bom =
        $bytes.Length -ge 3 -and
        $bytes[0] -eq 0xEF -and
        $bytes[1] -eq 0xBB -and
        $bytes[2] -eq 0xBF
    if (-not $hasUtf8Bom) {
        throw ('CorrespondentFile must be UTF-8 with BOM: {0}' -f $resolved)
    }

    $strictUtf8 = [System.Text.UTF8Encoding]::new($true, $true)
    try {
        $text = $strictUtf8.GetString($bytes, 3, $bytes.Length - 3)
    }
    catch {
        throw ('CorrespondentFile contains invalid UTF-8: {0}' -f $resolved)
    }

    $entryCount = @(
        $text -split '\r\n?|\n' |
            Where-Object {
                $line = $_.Trim()
                $line -and -not $line.StartsWith('#')
            }
    ).Count
    if ($entryCount -eq 0) {
        throw ('CorrespondentFile has no usable entries: {0}' -f $resolved)
    }

    Write-Host ('Private correspondent input enabled ({0} entries).' -f $entryCount) -ForegroundColor Green
    return $resolved
}

$EmbeddedCorrespondentFile = Resolve-CorrespondentInput

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

function Test-PythonExecutable {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Executable
    )

    if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
        return $false
    }

    try {
        $version = & $Executable -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>$null
        $exitCode = $LASTEXITCODE
    }
    catch {
        return $false
    }

    if ($exitCode -ne 0 -or -not $version) {
        return $false
    }

    $versionText = ([string]($version | Select-Object -Last 1)).Trim()
    $parsedVersion = $null
    if (-not [Version]::TryParse($versionText, [ref]$parsedVersion)) {
        return $false
    }

    if ($parsedVersion.Major -ne 3) {
        return $false
    }

    if ($parsedVersion.Minor -lt 11 -or $parsedVersion.Minor -gt 13) {
        return $false
    }

    Write-Host ('Using Python {0}: {1}' -f $versionText, $Executable) -ForegroundColor Green
    return $true
}

function Resolve-PythonFromLauncher {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Selector
    )

    $launcher = Get-Command 'py.exe' -ErrorAction SilentlyContinue
    if (-not $launcher) {
        $launcher = Get-Command 'py' -ErrorAction SilentlyContinue
    }
    if (-not $launcher) {
        return $null
    }

    try {
        $resolved = & $launcher.Source $Selector -c "import sys; print(sys.executable)" 2>$null
        $exitCode = $LASTEXITCODE
    }
    catch {
        return $null
    }

    if ($exitCode -ne 0 -or -not $resolved) {
        return $null
    }

    $resolvedPath = ([string]($resolved | Select-Object -Last 1)).Trim()
    if (Test-PythonExecutable -Executable $resolvedPath) {
        return $resolvedPath
    }

    return $null
}

function Resolve-BuildPython {
    if ($PythonPath) {
        $explicitPath = [Environment]::ExpandEnvironmentVariables($PythonPath)
        if (Test-PythonExecutable -Executable $explicitPath) {
            return (Resolve-Path -LiteralPath $explicitPath).Path
        }
        throw ('The specified PythonPath is not a supported Python 3.11-3.13 executable: {0}' -f $explicitPath)
    }

    if ($env:VIRTUAL_ENV) {
        $activeVenvPython = Join-Path $env:VIRTUAL_ENV 'Scripts\python.exe'
        if (Test-PythonExecutable -Executable $activeVenvPython) {
            return (Resolve-Path -LiteralPath $activeVenvPython).Path
        }
    }

    foreach ($selector in @('-3.13', '-3.12', '-3.11', '-3')) {
        $launcherPython = Resolve-PythonFromLauncher -Selector $selector
        if ($launcherPython) {
            return $launcherPython
        }
    }

    $knownPaths = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe')
    )

    foreach ($knownPath in $knownPaths) {
        if (Test-PythonExecutable -Executable $knownPath) {
            return (Resolve-Path -LiteralPath $knownPath).Path
        }
    }

    foreach ($commandName in @('python.exe', 'python3.exe', 'python')) {
        $command = Get-Command $commandName -ErrorAction SilentlyContinue
        if (-not $command -or -not $command.Source) {
            continue
        }

        $candidate = [string]$command.Source
        $windowsAppsRoot = Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps'
        if ($candidate.StartsWith($windowsAppsRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            continue
        }

        if (Test-PythonExecutable -Executable $candidate) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    return $null
}

$BuildPython = Resolve-BuildPython
if (-not $BuildPython) {
    throw @'
실행 가능한 Python 3.11~3.13을 찾지 못했습니다.

Python 3.13의 실제 경로를 직접 지정해 다시 실행하세요.
  .\scripts\build.ps1 -PythonPath "C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe"

경로 확인 명령:
  py -3.13 -c "import sys; print(sys.executable)"
'@
}

$Venv = Join-Path $ProjectRoot '.venv-build'
$VenvPython = Join-Path $Venv 'Scripts\python.exe'

if (Test-Path -LiteralPath $Venv) {
    if (-not (Test-PythonExecutable -Executable $VenvPython)) {
        Write-Host 'Removing incomplete or invalid build virtual environment...' -ForegroundColor Yellow
        Remove-Item -LiteralPath $Venv -Recurse -Force
    }
}

if (-not (Test-Path -LiteralPath $VenvPython)) {
    Write-Host 'Creating build virtual environment...'
    & $BuildPython -m venv $Venv
    if ($LASTEXITCODE -ne 0) {
        throw ('Failed to create build virtual environment with: {0}' -f $BuildPython)
    }
}

if (-not (Test-PythonExecutable -Executable $VenvPython)) {
    throw ('Virtual environment Python is invalid: {0}' -f $VenvPython)
}

& $VenvPython -m pip install --upgrade pip setuptools wheel
if ($LASTEXITCODE -ne 0) {
    throw 'Failed to upgrade build packaging tools.'
}

& $VenvPython -m pip install -e '.[build]'
if ($LASTEXITCODE -ne 0) {
    throw 'Failed to install project build dependencies.'
}

if (-not $SkipTests) {
    & $VenvPython -m pytest -q
    if ($LASTEXITCODE -ne 0) {
        throw 'Tests failed.'
    }
}

$Installer = Join-Path $ProjectRoot 'dist\ReNamer_Setup_7.3.exe'
$LegacyInstaller = Join-Path $ProjectRoot 'dist\ReNamer_Setup.exe'

Remove-Item -Recurse -Force -ErrorAction SilentlyContinue `
    (Join-Path $ProjectRoot 'build'), `
    (Join-Path $ProjectRoot 'dist\classifier'), `
    $Installer, `
    $LegacyInstaller

& $VenvPython -m PyInstaller --noconfirm classifier.spec
if ($LASTEXITCODE -ne 0) {
    throw 'PyInstaller build failed.'
}

$MakensisCandidates = @(
    (Get-Command makensis.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
    "${env:ProgramFiles(x86)}\NSIS\makensis.exe",
    "$env:ProgramFiles\NSIS\makensis.exe"
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }

$Makensis = $MakensisCandidates | Select-Object -First 1
if (-not $Makensis) {
    throw 'NSIS makensis.exe를 찾을 수 없습니다. NSIS 3.x를 설치하세요.'
}

Push-Location (Join-Path $ProjectRoot 'installer')
try {
    $MakensisArguments = @(
        '/INPUTCHARSET',
        'UTF8',
        '/OUTPUTCHARSET',
        'UTF8SIG'
    )
    if ($EmbeddedCorrespondentFile) {
        $MakensisArguments += ('/DCORRESPONDENT_SOURCE_FILE={0}' -f $EmbeddedCorrespondentFile)
    }
    $MakensisArguments += 'ReNamer_Setup.nsi'

    & $Makensis @MakensisArguments
    if ($LASTEXITCODE -ne 0) {
        throw 'NSIS build failed.'
    }
}
finally {
    Pop-Location
}

if (-not (Test-Path -LiteralPath $Installer)) {
    throw ('Installer output not found: {0}' -f $Installer)
}

Write-Host ''
Write-Host 'Build successful:' -ForegroundColor Green
Write-Host $Installer

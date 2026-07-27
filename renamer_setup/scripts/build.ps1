param(
    [switch]$SkipTests
)

$ErrorActionPreference = 'Stop'
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

function Find-Python {
    foreach ($candidate in @('py.exe', 'python.exe', 'python')) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($command) {
            if ($candidate -eq 'py.exe') {
                return @($command.Source, '-3.11')
            }
            return @($command.Source)
        }
    }
    throw 'Python 3.11 이상을 찾을 수 없습니다.'
}

function Invoke-Python {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)

    $executable = $script:PythonCommand[0]
    $prefixArguments = @()
    if ($script:PythonCommand.Count -gt 1) {
        $prefixArguments = $script:PythonCommand[1..($script:PythonCommand.Count - 1)]
    }

    & $executable @prefixArguments @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed: $($Arguments -join ' ')"
    }
}

$script:PythonCommand = Find-Python
$Venv = Join-Path $ProjectRoot '.venv-build'

if (-not (Test-Path (Join-Path $Venv 'Scripts\python.exe'))) {
    Write-Host 'Creating build virtual environment...'
    Invoke-Python -m venv $Venv
}

$Python = Join-Path $Venv 'Scripts\python.exe'
$Pip = Join-Path $Venv 'Scripts\pip.exe'

& $Python -m pip install --upgrade pip setuptools wheel
& $Pip install -e '.[build]'

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

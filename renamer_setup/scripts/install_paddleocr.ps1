param(
    [Parameter(Mandatory = $true)]
    [string]$InstallRoot
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$env:PYTHONHOME = $null
$env:PYTHONPATH = $null

$InstallRoot = [Environment]::ExpandEnvironmentVariables($InstallRoot)
$SupportDir = Join-Path $InstallRoot 'support'
$ToolsDir = Join-Path $InstallRoot 'tools'
$EnvironmentDir = Join-Path $ToolsDir 'paddleocr-env'
$EnvironmentPython = Join-Path $EnvironmentDir 'Scripts\python.exe'
$Runner = Join-Path $SupportDir 'paddleocr_runner.py'
$LogPath = Join-Path $SupportDir 'paddleocr-install.log'
$HealthResult = Join-Path $SupportDir 'paddleocr-health.json'

New-Item -ItemType Directory -Force -Path $SupportDir, $ToolsDir | Out-Null

function Write-InstallLog {
    param([string]$Message)
    $line = '[{0}] {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
    Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8
    Write-Host $line
}

trap {
    $failureMessage = $_.Exception.Message
    Write-InstallLog "PaddleOCR 설치 실패: $failureMessage"
    Write-Error $failureMessage
    exit 1
}

function Test-Python {
    param([string]$Executable)
    if (-not $Executable -or -not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
        return $false
    }
    try {
        & $Executable -c 'import sys; raise SystemExit(0 if sys.version_info[:3] == (3, 14, 6) else 1)'
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

function Find-Python {
    foreach ($selector in @('-V:3.14', '-3.14')) {
        $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
        if ($launcher) {
            $candidate = & $launcher.Source $selector -c 'import sys; print(sys.executable)' 2>$null
            if ($LASTEXITCODE -eq 0 -and (Test-Python -Executable $candidate)) {
                return ([string]$candidate).Trim()
            }
        }
    }

    foreach ($candidate in @(
        (Join-Path $env:ProgramFiles 'Python314\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python314\python.exe'),
        $(if ((Get-Command python3.exe -ErrorAction SilentlyContinue)) {
            (Get-Command python3.exe).Source
        }),
        $(if ((Get-Command python.exe -ErrorAction SilentlyContinue)) {
            (Get-Command python.exe).Source
        })
    )) {
        if (Test-Python -Executable $candidate) {
            return $candidate
        }
    }
    return $null
}

if (-not (Test-Path -LiteralPath $Runner -PathType Leaf)) {
    throw "PaddleOCR runner not found: $Runner"
}

Write-InstallLog 'PaddleOCR ONNX 보조 엔진 설치를 시작합니다.'
$BasePython = Find-Python
if (-not $BasePython) {
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if (-not $winget) {
        throw 'Python 3.14.6과 winget을 찾을 수 없습니다.'
    }
    Write-InstallLog 'Python 3.14 사용자 설치를 시작합니다. 설치 후 정확히 3.14.6인지 검증합니다.'
    & $winget.Source install `
        --id Python.Python.3.14 `
        --exact `
        --scope user `
        --silent `
        --disable-interactivity `
        --accept-package-agreements `
        --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "Python 3.14 설치에 실패했습니다. exit_code=$LASTEXITCODE"
    }
    $BasePython = Find-Python
}
if (-not $BasePython) {
    throw '설치 후 Python 실행 파일을 찾을 수 없습니다.'
}

Write-InstallLog "Python을 확인했습니다. path=$BasePython"
if (-not (Test-Python -Executable $EnvironmentPython)) {
    if (Test-Path -LiteralPath $EnvironmentDir) {
        Remove-Item -LiteralPath $EnvironmentDir -Recurse -Force
    }
    & $BasePython -m venv $EnvironmentDir
    if ($LASTEXITCODE -ne 0) {
        throw 'PaddleOCR 가상 환경 생성에 실패했습니다.'
    }
}

& $EnvironmentPython -m pip install --upgrade pip setuptools wheel
if ($LASTEXITCODE -ne 0) {
    throw 'PaddleOCR 패키징 도구 설치에 실패했습니다.'
}

& $EnvironmentPython -m pip install 'paddleocr==3.7.0' 'onnxruntime>=1.23,<2'
if ($LASTEXITCODE -ne 0) {
    throw 'PaddleOCR ONNX 패키지 설치에 실패했습니다.'
}

Write-InstallLog '한국어 OCR 모델을 준비합니다. 최초 실행은 모델 다운로드로 오래 걸릴 수 있습니다.'
& $EnvironmentPython $Runner --health --language korean --output $HealthResult
if ($LASTEXITCODE -ne 0) {
    throw "PaddleOCR 모델 초기화에 실패했습니다. 결과=$HealthResult"
}

Write-InstallLog 'PaddleOCR ONNX 보조 엔진 설치가 완료되었습니다.'
Write-Host ''
Write-Host '설치가 완료되었습니다. 이 창을 닫아도 됩니다.' -ForegroundColor Green

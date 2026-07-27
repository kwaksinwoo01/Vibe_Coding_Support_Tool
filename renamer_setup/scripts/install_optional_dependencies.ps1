param(
    [Parameter(Mandatory = $true)]
    [string]$InstallRoot
)

$ErrorActionPreference = 'Continue'
$ProgressPreference = 'SilentlyContinue'

$SupportDir = Join-Path $InstallRoot 'support'
$ToolsDir = Join-Path $InstallRoot 'tools'
$TessDataDir = Join-Path $ToolsDir 'tessdata'
$LogPath = Join-Path $SupportDir 'dependency-install.log'

New-Item -ItemType Directory -Force -Path $SupportDir, $ToolsDir, $TessDataDir | Out-Null

function Write-InstallLog {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
    Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8
    Write-Output $line
}

function Test-Executable {
    param(
        [string[]]$Commands,
        [string[]]$Paths
    )

    foreach ($path in $Paths) {
        if ($path -and (Test-Path -LiteralPath $path)) {
            return $true
        }
    }

    foreach ($command in $Commands) {
        if (Get-Command $command -ErrorAction SilentlyContinue) {
            return $true
        }
    }
    return $false
}

function Install-WingetPackage {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PackageId,
        [Parameter(Mandatory = $true)]
        [string]$Description
    )

    if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) {
        Write-InstallLog "winget_missing: $Description 자동 설치를 건너뜁니다."
        return $false
    }

    Write-InstallLog "$Description 자동 설치를 시작합니다. package=$PackageId"
    & winget.exe install `
        --id $PackageId `
        --exact `
        --silent `
        --disable-interactivity `
        --accept-package-agreements `
        --accept-source-agreements

    if ($LASTEXITCODE -eq 0) {
        Write-InstallLog "$Description 설치가 완료되었습니다."
        return $true
    }

    & winget.exe list --id $PackageId --exact | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-InstallLog "$Description 은(는) 이미 설치되어 있습니다."
        return $true
    }

    Write-InstallLog "$Description 설치에 실패했습니다. exit_code=$LASTEXITCODE"
    return $false
}

function Download-TessData {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Language
    )

    $destination = Join-Path $TessDataDir "$Language.traineddata"
    if (Test-Path -LiteralPath $destination) {
        Write-InstallLog "tessdata_exists: $Language"
        return
    }

    $url = "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/$Language.traineddata"
    try {
        Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $destination
        Write-InstallLog "tessdata_downloaded: $Language"
    }
    catch {
        Write-InstallLog "tessdata_download_failed: $Language - $($_.Exception.Message)"
    }
}

function Sync-TesseractRuntime {
    $sourceCandidates = @(
        (Join-Path $env:ProgramFiles 'Tesseract-OCR'),
        (Join-Path ${env:ProgramFiles(x86)} 'Tesseract-OCR')
    )
    $source = $sourceCandidates | Where-Object {
        $_ -and (Test-Path -LiteralPath (Join-Path $_ 'tesseract.exe'))
    } | Select-Object -First 1

    if (-not $source) {
        Write-InstallLog 'tesseract_runtime_copy_skipped: 설치 경로를 찾지 못했습니다.'
        return
    }

    $destination = Join-Path $ToolsDir 'tesseract'
    New-Item -ItemType Directory -Force -Path $destination | Out-Null
    Copy-Item -Path (Join-Path $source '*') -Destination $destination -Recurse -Force

    $destinationTessData = Join-Path $destination 'tessdata'
    New-Item -ItemType Directory -Force -Path $destinationTessData | Out-Null
    Get-ChildItem -LiteralPath $TessDataDir -Filter '*.traineddata' -ErrorAction SilentlyContinue |
        Copy-Item -Destination $destinationTessData -Force

    Write-InstallLog "tesseract_runtime_copied: $destination"
}

Write-InstallLog "dependency bootstrap started. root=$InstallRoot"

$pdftotextBundled = @(
    (Join-Path $ToolsDir 'poppler\Library\bin\pdftotext.exe'),
    (Join-Path $ToolsDir 'poppler\bin\pdftotext.exe')
)
if (-not (Test-Executable -Commands @('pdftotext.exe', 'pdftotext') -Paths $pdftotextBundled)) {
    [void](Install-WingetPackage -PackageId 'oschwartz10612.Poppler' -Description 'Poppler PDF 도구')
}
else {
    Write-InstallLog 'Poppler PDF 도구를 확인했습니다.'
}

$tesseractBundled = @(
    (Join-Path $ToolsDir 'tesseract\tesseract.exe'),
    (Join-Path $ToolsDir 'Tesseract-OCR\tesseract.exe'),
    (Join-Path $env:ProgramFiles 'Tesseract-OCR\tesseract.exe')
)
if (-not (Test-Executable -Commands @('tesseract.exe', 'tesseract') -Paths $tesseractBundled)) {
    [void](Install-WingetPackage -PackageId 'UB-Mannheim.TesseractOCR' -Description 'Tesseract OCR')
}
else {
    Write-InstallLog 'Tesseract OCR을 확인했습니다.'
}

Download-TessData -Language 'kor'
Download-TessData -Language 'eng'
Sync-TesseractRuntime

$excelPaths = @(
    (Join-Path $env:ProgramFiles 'Microsoft Office\root\Office16\EXCEL.EXE'),
    (Join-Path ${env:ProgramFiles(x86)} 'Microsoft Office\root\Office16\EXCEL.EXE')
)
$excelRegistry = Get-ItemProperty `
    'Registry::HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\excel.exe' `
    -ErrorAction SilentlyContinue
$excelAvailable = ($null -ne $excelRegistry) -or (Test-Executable -Commands @('excel.exe') -Paths $excelPaths)

$libreOfficePaths = @(
    (Join-Path $env:ProgramFiles 'LibreOffice\program\soffice.exe'),
    (Join-Path ${env:ProgramFiles(x86)} 'LibreOffice\program\soffice.exe')
)
$libreOfficeAvailable = Test-Executable -Commands @('soffice.exe', 'soffice') -Paths $libreOfficePaths

if ($excelAvailable) {
    Write-InstallLog 'Microsoft Excel을 확인했습니다. Excel 렌더링 폴백을 사용합니다.'
}
elseif ($libreOfficeAvailable) {
    Write-InstallLog 'LibreOffice를 확인했습니다. LibreOffice 렌더링 폴백을 사용합니다.'
}
else {
    [void](Install-WingetPackage -PackageId 'TheDocumentFoundation.LibreOffice' -Description 'LibreOffice')
}

Write-InstallLog 'dependency bootstrap completed.'
exit 0

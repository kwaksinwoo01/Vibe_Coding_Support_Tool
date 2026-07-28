$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ProjectRoot = Split-Path -Parent $PSScriptRoot

$RequiredBomFiles = @(
    'installer\ReNamer_Setup.nsi',
    'scripts\build.ps1',
    'scripts\install_optional_dependencies.ps1',
    'scripts\install_paddleocr.ps1',
    'scripts\verify_text_encoding.ps1',
    'renamer\7.4_자동이름 변경 시스템.pas'
)

$Failed = $false
$StrictUtf8 = [System.Text.UTF8Encoding]::new($true, $true)

foreach ($relativePath in $RequiredBomFiles) {
    $path = Join-Path $ProjectRoot $relativePath

    if (-not (Test-Path -LiteralPath $path)) {
        Write-Host "Required source file not found: $relativePath" -ForegroundColor Red
        $Failed = $true
        continue
    }

    $bytes = [System.IO.File]::ReadAllBytes($path)
    $hasUtf8Bom =
        $bytes.Length -ge 3 -and
        $bytes[0] -eq 0xEF -and
        $bytes[1] -eq 0xBB -and
        $bytes[2] -eq 0xBF

    if (-not $hasUtf8Bom) {
        Write-Host "UTF-8 BOM is missing: $relativePath" -ForegroundColor Red
        $Failed = $true
        continue
    }

    try {
        [void]$StrictUtf8.GetString($bytes)
        Write-Host "UTF-8 BOM OK: $relativePath" -ForegroundColor Green
    }
    catch {
        Write-Host "Invalid UTF-8 content: $relativePath - $($_.Exception.Message)" -ForegroundColor Red
        $Failed = $true
    }
}

if ($Failed) {
    Write-Host ''
    Write-Host 'Encoding validation failed.' -ForegroundColor Red
    Write-Host 'Save the reported files as UTF-8 with BOM and run the build again.'
    exit 1
}

Write-Host ''
Write-Host 'All required installer sources use UTF-8 BOM.' -ForegroundColor Green
exit 0

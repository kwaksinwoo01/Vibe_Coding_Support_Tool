#requires -Version 5.1
[CmdletBinding()]
param(
    [switch]$Install,
    [switch]$RecreateVenv,
    [switch]$Diagnose,
    [string]$NormalPath,
    [string]$PythonPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$minimumPythonVersion = [version]'3.10.0'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repositoryRoot = Split-Path -Parent $projectRoot
Set-Location $projectRoot

function Add-UniqueCandidate {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [System.Collections.Generic.List[string]]$Candidates,

        [AllowNull()]
        [string]$Candidate
    )

    if ([string]::IsNullOrWhiteSpace($Candidate)) {
        return
    }

    $expanded = [Environment]::ExpandEnvironmentVariables($Candidate.Trim())
    try {
        if ([System.IO.Path]::IsPathRooted($expanded)) {
            $resolved = [System.IO.Path]::GetFullPath($expanded)
        }
        else {
            $command = Get-Command $expanded -ErrorAction SilentlyContinue
            if ($null -eq $command -or [string]::IsNullOrWhiteSpace($command.Source)) {
                return
            }
            $resolved = [System.IO.Path]::GetFullPath($command.Source)
        }
    }
    catch {
        return
    }

    if (-not $Candidates.Contains($resolved)) {
        [void]$Candidates.Add($resolved)
    }
}

function Get-PythonCandidates {
    param([AllowNull()] [string]$RequestedPythonPath)

    $candidates = New-Object 'System.Collections.Generic.List[string]'
    Add-UniqueCandidate -Candidates $candidates -Candidate $RequestedPythonPath

    if (-not [string]::IsNullOrWhiteSpace($env:VIRTUAL_ENV)) {
        Add-UniqueCandidate `
            -Candidates $candidates `
            -Candidate (Join-Path $env:VIRTUAL_ENV 'Scripts\python.exe')
    }

    Add-UniqueCandidate `
        -Candidates $candidates `
        -Candidate (Join-Path $projectRoot '.venv\Scripts\python.exe')

    Add-UniqueCandidate `
        -Candidates $candidates `
        -Candidate (Join-Path $repositoryRoot '.venv\Scripts\python.exe')

    foreach ($commandName in @('python.exe', 'python3.exe', 'python', 'python3')) {
        $command = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($null -ne $command -and -not [string]::IsNullOrWhiteSpace($command.Source)) {
            Add-UniqueCandidate -Candidates $candidates -Candidate $command.Source
        }
    }

    foreach ($root in @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Python'),
        (Join-Path $env:ProgramFiles 'Python'),
        $(if (${env:ProgramFiles(x86)}) {
            Join-Path ${env:ProgramFiles(x86)} 'Python'
        })
    )) {
        if ([string]::IsNullOrWhiteSpace($root) -or -not (Test-Path -LiteralPath $root)) {
            continue
        }

        Get-ChildItem `
            -LiteralPath $root `
            -Directory `
            -Filter 'Python3*' `
            -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending |
            ForEach-Object {
                Add-UniqueCandidate `
                    -Candidates $candidates `
                    -Candidate (Join-Path $_.FullName 'python.exe')
            }
    }

    $pyCommand = Get-Command py.exe -ErrorAction SilentlyContinue
    if (
        $null -ne $pyCommand -and
        -not [string]::IsNullOrWhiteSpace($pyCommand.Source) -and
        $pyCommand.Source -notlike '*\Microsoft\WindowsApps\*'
    ) {
        try {
            foreach ($line in @(& $pyCommand.Source -0p 2>$null)) {
                $match = [regex]::Match(
                    [string]$line,
                    '([A-Za-z]:\\[^\r\n]*?python(?:\.exe)?)\s*$'
                )
                if ($match.Success) {
                    Add-UniqueCandidate `
                        -Candidates $candidates `
                        -Candidate $match.Groups[1].Value
                }
            }
        }
        catch {}
    }

    return @($candidates)
}

function Test-PythonCandidate {
    param(
        [Parameter(Mandatory = $true)] [string]$Candidate,
        [Parameter(Mandatory = $true)] [version]$MinimumVersion
    )

    $result = [ordered]@{
        Candidate = $Candidate
        Path = $Candidate
        Valid = $false
        Version = $null
        Bits = $null
        WordComRegistered = $false
        WordClsid = ''
        Reason = ''
    }

    if (-not (Test-Path -LiteralPath $Candidate -PathType Leaf)) {
        $result.Reason = '파일이 존재하지 않습니다.'
        return [pscustomobject]$result
    }

    if ($Candidate -like '*\Microsoft\WindowsApps\*') {
        $result.Reason = 'WindowsApps 설치 별칭이므로 제외했습니다.'
        return [pscustomobject]$result
    }

    $probe = @'
import json
import os
import struct
import sys
import winreg

registered = False
clsid = ""
local_server = ""
server_path = ""
error = ""
try:
    with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"Word.Application\CLSID") as key:
        clsid = str(winreg.QueryValueEx(key, None)[0])
except OSError as exc:
    error = str(exc)

if clsid:
    try:
        with winreg.OpenKey(
            winreg.HKEY_CLASSES_ROOT,
            rf"CLSID\{clsid}\LocalServer32",
        ) as key:
            local_server = str(winreg.QueryValueEx(key, None)[0]).strip()
    except OSError as exc:
        error = str(exc)

if local_server:
    if local_server.startswith('"'):
        closing_quote = local_server.find('"', 1)
        if closing_quote > 1:
            server_path = local_server[1:closing_quote]
    else:
        executable_end = local_server.lower().find(".exe")
        if executable_end >= 0:
            server_path = local_server[:executable_end + 4]
    server_path = os.path.expandvars(server_path)

registered = bool(clsid and server_path and os.path.isfile(server_path))
if clsid and server_path and not registered:
    error = f"Word COM server file does not exist: {server_path}"

print(json.dumps({
    "version": "{}.{}.{}".format(*sys.version_info[:3]),
    "executable": sys.executable,
    "bits": struct.calcsize("P") * 8,
    "word_com_registered": registered,
    "word_clsid": clsid,
    "word_local_server": local_server,
    "word_server_path": server_path,
    "registry_error": error,
}, ensure_ascii=False))
'@

    try {
        # Windows PowerShell 5.1 rewrites embedded quotes in native `-c`
        # arguments. Send the multi-line probe through stdin so Python receives
        # the source exactly as written.
        $output = @($probe | & $Candidate - 2>&1)
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) {
            $result.Reason = (
                '실행 실패(exit={0}): {1}' -f
                $exitCode,
                (($output | ForEach-Object { [string]$_ }) -join ' ')
            )
            return [pscustomobject]$result
        }

        $line = @(
            $output |
                ForEach-Object { [string]$_ } |
                Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
        ) | Select-Object -Last 1

        if ([string]::IsNullOrWhiteSpace($line)) {
            $result.Reason = '진단 결과가 비어 있습니다.'
            return [pscustomobject]$result
        }

        $info = $line | ConvertFrom-Json
        $version = [version][string]$info.version
        $result.Path = [string]$info.executable
        $result.Version = $version
        $result.Bits = [int]$info.bits
        $result.WordComRegistered = [bool]$info.word_com_registered
        $result.WordClsid = [string]$info.word_clsid

        if ($version -lt $MinimumVersion) {
            $result.Reason = (
                'Python {0}은 최소 요구 버전 {1}보다 낮습니다.' -f
                $version,
                $MinimumVersion
            )
            return [pscustomobject]$result
        }

        if (-not $result.WordComRegistered) {
            $serverPath = [string]$info.word_server_path
            if (
                -not [string]::IsNullOrWhiteSpace($serverPath) -and
                -not [System.IO.File]::Exists($serverPath)
            ) {
                $registryError = (
                    'Word COM 서버 파일이 없습니다: {0}. ' +
                    'Microsoft 365/Office 온라인 복구 또는 Word 재설치가 필요합니다.'
                ) -f $serverPath
            }
            else {
                $registryError = [string]$info.registry_error
            }
            if ([string]::IsNullOrWhiteSpace($registryError)) {
                $registryError = (
                    'Python {0}비트 레지스트리 뷰에서 완전한 Word.Application COM 등록을 ' +
                    '찾지 못했습니다.'
                ) -f $result.Bits
            }
            $result.Reason = $registryError
            return [pscustomobject]$result
        }

        $result.Valid = $true
        $result.Reason = '사용 가능'
        return [pscustomobject]$result
    }
    catch {
        $result.Reason = "진단 예외: $($_.Exception.Message)"
        return [pscustomobject]$result
    }
}

function Find-CompatiblePython {
    param(
        [AllowNull()] [string]$RequestedPythonPath,
        [Parameter(Mandatory = $true)] [version]$MinimumVersion
    )

    $results = @()
    $selected = $null
    foreach ($candidate in @(Get-PythonCandidates -RequestedPythonPath $RequestedPythonPath)) {
        $result = Test-PythonCandidate `
            -Candidate $candidate `
            -MinimumVersion $MinimumVersion
        $results += $result
        if ($null -eq $selected -and $result.Valid) {
            $selected = $result
        }
    }

    return [pscustomobject]@{
        Selected = $selected
        Results = @($results)
    }
}

function Show-PythonDiagnostics {
    param([Parameter(Mandatory = $true)] [object[]]$Results)

    if ($Results.Count -eq 0) {
        Write-Host '탐지된 Python 후보가 없습니다.'
        return
    }

    foreach ($item in $Results) {
        Write-Host (
            '[{0}] {1} | version={2} | bits={3} | WordCOM={4} | {5}' -f
            $(if ($item.Valid) { 'OK' } else { 'NO' }),
            $item.Candidate,
            $(if ($null -eq $item.Version) { '-' } else { $item.Version }),
            $(if ($null -eq $item.Bits) { '-' } else { $item.Bits }),
            $item.WordComRegistered,
            $item.Reason
        )
    }
}

function Invoke-CheckedPython {
    param(
        [Parameter(Mandatory = $true)] [string]$Executable,
        [Parameter(Mandatory = $true)] [AllowEmptyCollection()] [string[]]$Arguments,
        [Parameter(Mandatory = $true)] [string]$FailureMessage
    )

    & $Executable @Arguments
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        throw ('{0} Exit code: {1}' -f $FailureMessage, $exitCode)
    }
}

$discovery = Find-CompatiblePython `
    -RequestedPythonPath $PythonPath `
    -MinimumVersion $minimumPythonVersion

if ($Diagnose) {
    Show-PythonDiagnostics -Results $discovery.Results
    if ($null -eq $discovery.Selected) {
        exit 1
    }
    Write-Host ('선택될 Python: {0}' -f $discovery.Selected.Path)
    exit 0
}

$venv = Join-Path $projectRoot '.venv'
$venvPython = Join-Path $venv 'Scripts\python.exe'

if ($RecreateVenv -and (Test-Path -LiteralPath $venv)) {
    Write-Host '기존 word_editor 가상환경 제거'
    Remove-Item -LiteralPath $venv -Recurse -Force
}

if (Test-Path -LiteralPath $venvPython -PathType Leaf) {
    $venvInfo = Test-PythonCandidate `
        -Candidate $venvPython `
        -MinimumVersion $minimumPythonVersion

    if (-not $venvInfo.Valid) {
        throw (
            "현재 word_editor 가상환경을 사용할 수 없습니다:`r`n" +
            "  {0}`r`n  {1}`r`n`r`n" +
            '다음 명령으로 올바른 Python을 선택해 다시 생성하십시오:' + "`r`n" +
            '  .\run_word_editor.ps1 -Diagnose' + "`r`n" +
            '  .\run_word_editor.ps1 -Install -RecreateVenv'
        ) -f $venvPython, $venvInfo.Reason
    }
}
else {
    if ($null -eq $discovery.Selected) {
        $diagnostics = @(
            foreach ($item in $discovery.Results) {
                '  - {0}: {1}' -f $item.Candidate, $item.Reason
            }
        )
        if ($diagnostics.Count -eq 0) {
            $diagnostics = @('  - 탐지된 Python 후보가 없습니다.')
        }

        throw (
            "Word COM을 사용할 수 있는 Python {0} 이상을 찾지 못했습니다.`r`n" +
            "검사 결과:`r`n{1}`r`n`r`n" +
            "먼저 진단하십시오:`r`n  .\run_word_editor.ps1 -Diagnose`r`n`r`n" +
            'Word는 PowerShell에서 작동하지만 모든 Python 후보가 WordCOM=False라면 ' +
            'Office와 Python 비트 수가 다릅니다. Office와 같은 비트 수의 Python을 설치하십시오.'
        ) -f $minimumPythonVersion, ($diagnostics -join "`r`n")
    }

    $basePython = $discovery.Selected
    Write-Host (
        '가상환경 생성에 사용할 Python: {0} ({1}, {2}비트, Word COM 등록 확인)' -f
        $basePython.Path,
        $basePython.Version,
        $basePython.Bits
    )

    Invoke-CheckedPython `
        -Executable $basePython.Path `
        -Arguments @('-m', 'venv', $venv) `
        -FailureMessage 'word_editor 가상환경 생성에 실패했습니다.'
}

$venvPythonInfo = Test-PythonCandidate `
    -Candidate $venvPython `
    -MinimumVersion $minimumPythonVersion

if (-not $venvPythonInfo.Valid) {
    throw (
        "word_editor 가상환경의 Python을 사용할 수 없습니다:`r`n" +
        "  {0}`r`n  {1}" -f $venvPython, $venvPythonInfo.Reason
    )
}

Write-Host (
    'word_editor Python: {0} ({1}, {2}비트, Word COM 등록 확인)' -f
    $venvPythonInfo.Path,
    $venvPythonInfo.Version,
    $venvPythonInfo.Bits
)

if ($Install) {
    Write-Host 'pip와 word_editor 의존성 설치'
    Invoke-CheckedPython `
        -Executable $venvPython `
        -Arguments @('-m', 'pip', 'install', '--upgrade', 'pip') `
        -FailureMessage 'pip 업그레이드에 실패했습니다.'
    Invoke-CheckedPython `
        -Executable $venvPython `
        -Arguments @('-m', 'pip', 'install', '-e', '.[test]') `
        -FailureMessage 'word_editor 패키지 설치에 실패했습니다.'
}
else {
    & $venvPython -c 'import word_editor' 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw (
            "word_editor 패키지가 아직 설치되지 않았습니다.`r`n" +
            '다음 명령으로 최초 설치하십시오:' + "`r`n" +
            '  .\run_word_editor.ps1 -Install'
        )
    }
}

$arguments = @('-m', 'word_editor')
if (-not [string]::IsNullOrWhiteSpace($NormalPath)) {
    $arguments += @('--normal-path', $NormalPath)
}

& $venvPython @arguments
exit $LASTEXITCODE

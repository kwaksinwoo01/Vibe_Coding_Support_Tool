#requires -Version 5.1
[CmdletBinding()]
param(
    [switch]$Install,
    [switch]$RecreateVenv,
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
    param(
        [AllowNull()]
        [string]$RequestedPythonPath
    )

    $candidates = New-Object 'System.Collections.Generic.List[string]'

    Add-UniqueCandidate -Candidates $candidates -Candidate $RequestedPythonPath

    if (-not [string]::IsNullOrWhiteSpace($env:VIRTUAL_ENV)) {
        Add-UniqueCandidate `
            -Candidates $candidates `
            -Candidate (Join-Path $env:VIRTUAL_ENV 'Scripts\python.exe')
    }

    Add-UniqueCandidate `
        -Candidates $candidates `
        -Candidate (Join-Path $repositoryRoot '.venv\Scripts\python.exe')

    foreach ($commandName in @('python.exe', 'python3.exe', 'python', 'python3')) {
        $command = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($null -ne $command -and -not [string]::IsNullOrWhiteSpace($command.Source)) {
            Add-UniqueCandidate `
                -Candidates $candidates `
                -Candidate $command.Source
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
            $launcherOutput = @(& $pyCommand.Source -0p 2>$null)
            foreach ($line in $launcherOutput) {
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
        [Parameter(Mandatory = $true)]
        [string]$Candidate,

        [Parameter(Mandatory = $true)]
        [version]$MinimumVersion
    )

    $result = [ordered]@{
        Candidate = $Candidate
        Path = $Candidate
        Valid = $false
        Version = $null
        Executable = $null
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

    try {
        $output = @(
            & $Candidate -c (
                'import sys; print("{}.{}.{}|{}".format(' +
                'sys.version_info.major, sys.version_info.minor, ' +
                'sys.version_info.micro, sys.executable))'
            ) 2>&1
        )
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
            $result.Reason = '버전 확인 결과가 비어 있습니다.'
            return [pscustomobject]$result
        }

        $match = [regex]::Match(
            $line.Trim(),
            '^(\d+)\.(\d+)\.(\d+)\|(.+)$'
        )
        if (-not $match.Success) {
            $result.Reason = "버전 확인 결과를 해석할 수 없습니다: $line"
            return [pscustomobject]$result
        }

        $version = [version](
            '{0}.{1}.{2}' -f
            $match.Groups[1].Value,
            $match.Groups[2].Value,
            $match.Groups[3].Value
        )
        $executable = $match.Groups[4].Value.Trim()

        $result.Version = $version
        $result.Executable = $executable

        if ($version -lt $MinimumVersion) {
            $result.Reason = (
                'Python {0}은 최소 요구 버전 {1}보다 낮습니다.' -f
                $version,
                $MinimumVersion
            )
            return [pscustomobject]$result
        }

        $result.Valid = $true
        $result.Path = $executable
        $result.Reason = '사용 가능'
        return [pscustomobject]$result
    }
    catch {
        $result.Reason = "실행 예외: $($_.Exception.Message)"
        return [pscustomobject]$result
    }
}

function Find-CompatiblePython {
    param(
        [AllowNull()]
        [string]$RequestedPythonPath,

        [Parameter(Mandatory = $true)]
        [version]$MinimumVersion
    )

    $results = @()
    $selected = $null

    foreach ($candidate in @(Get-PythonCandidates -RequestedPythonPath $RequestedPythonPath)) {
        $result = Test-PythonCandidate `
            -Candidate $candidate `
            -MinimumVersion $MinimumVersion

        $results += $result

        if ($result.Valid) {
            $selected = $result
            break
        }
    }

    return [pscustomobject]@{
        Selected = $selected
        Results = @($results)
    }
}

function Invoke-CheckedPython {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Executable,

        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [string[]]$Arguments,

        [Parameter(Mandatory = $true)]
        [string]$FailureMessage
    )

    & $Executable @Arguments
    $exitCode = $LASTEXITCODE

    if ($exitCode -ne 0) {
        throw ('{0} Exit code: {1}' -f $FailureMessage, $exitCode)
    }
}

$venv = Join-Path $projectRoot '.venv'
$venvPython = Join-Path $venv 'Scripts\python.exe'

if ($RecreateVenv -and (Test-Path -LiteralPath $venv)) {
    Write-Host '기존 word_editor 가상환경 제거'
    Remove-Item -LiteralPath $venv -Recurse -Force
}

if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    $discovery = Find-CompatiblePython `
        -RequestedPythonPath $PythonPath `
        -MinimumVersion $minimumPythonVersion

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
            (
                "Python {0} 이상 실제 실행 파일을 찾지 못했습니다.`r`n" +
                "검사 결과:`r`n{1}`r`n`r`n" +
                "설치된 python.exe를 직접 지정할 수도 있습니다:`r`n" +
                '  .\run_word_editor.ps1 -Install -RecreateVenv ' +
                '-PythonPath "C:\Path\To\python.exe"'
            ) -f $minimumPythonVersion, ($diagnostics -join "`r`n")
        )
    }

    $basePython = $discovery.Selected

    Write-Host (
        '가상환경 생성에 사용할 Python: {0} ({1})' -f
        $basePython.Path,
        $basePython.Version
    )

    Invoke-CheckedPython `
        -Executable $basePython.Path `
        -Arguments @('-m', 'venv', $venv) `
        -FailureMessage 'word_editor 가상환경 생성에 실패했습니다.'

    if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
        throw (
            '가상환경 명령은 끝났지만 python.exe가 생성되지 않았습니다: {0}' -f
            $venvPython
        )
    }
}

$venvPythonInfo = Test-PythonCandidate `
    -Candidate $venvPython `
    -MinimumVersion $minimumPythonVersion

if (-not $venvPythonInfo.Valid) {
    throw (
        (
            "word_editor 가상환경의 Python을 사용할 수 없습니다: {0}`r`n{1}`r`n" +
            '-RecreateVenv 옵션으로 다시 생성하십시오.'
        ) -f $venvPython, $venvPythonInfo.Reason
    )
}

Write-Host (
    'word_editor Python: {0} ({1})' -f
    $venvPythonInfo.Path,
    $venvPythonInfo.Version
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

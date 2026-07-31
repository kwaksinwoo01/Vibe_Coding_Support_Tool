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

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repositoryRoot = Split-Path -Parent $projectRoot
Set-Location $projectRoot

function Test-PythonExecutable {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Candidate
    )

    if ([string]::IsNullOrWhiteSpace($Candidate)) {
        return $null
    }

    try {
        $resolved = [System.IO.Path]::GetFullPath(
            [Environment]::ExpandEnvironmentVariables($Candidate)
        )
    }
    catch {
        return $null
    }

    if (-not (Test-Path -LiteralPath $resolved -PathType Leaf)) {
        return $null
    }

    # Windows App Execution Alias stubs may launch an installer instead of
    # Python. Never execute those aliases from this bootstrapper.
    if ($resolved -like '*\Microsoft\WindowsApps\*') {
        return $null
    }

    try {
        $versionText = & $resolved -c (
            'import sys; print("{}.{}.{}".format(*sys.version_info[:3]))'
        ) 2>$null

        if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($versionText)) {
            return $null
        }

        $version = [version]([string]$versionText).Trim()
        if ($version -lt [version]'3.11.0') {
            return $null
        }

        return [pscustomobject]@{
            Path = $resolved
            Version = $version
        }
    }
    catch {
        return $null
    }
}

function Add-PythonCandidate {
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

    try {
        $expanded = [System.IO.Path]::GetFullPath(
            [Environment]::ExpandEnvironmentVariables($Candidate)
        )
    }
    catch {
        return
    }

    if (-not $Candidates.Contains($expanded)) {
        [void]$Candidates.Add($expanded)
    }
}

function Find-CompatiblePython {
    param(
        [AllowNull()]
        [string]$RequestedPythonPath
    )

    $candidates = New-Object 'System.Collections.Generic.List[string]'

    # An explicit path always has highest priority.
    Add-PythonCandidate -Candidates $candidates -Candidate $RequestedPythonPath

    # Reuse an already active virtual environment when possible.
    if (-not [string]::IsNullOrWhiteSpace($env:VIRTUAL_ENV)) {
        Add-PythonCandidate `
            -Candidates $candidates `
            -Candidate (Join-Path $env:VIRTUAL_ENV 'Scripts\python.exe')
    }

    # The repository may already have a shared development environment.
    Add-PythonCandidate `
        -Candidates $candidates `
        -Candidate (Join-Path $repositoryRoot '.venv\Scripts\python.exe')

    # Common per-user and system Python installation locations.
    foreach ($root in @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Python'),
        (Join-Path $env:ProgramFiles 'Python'),
        $(if (${env:ProgramFiles(x86)}) {
            Join-Path ${env:ProgramFiles(x86)} 'Python'
        })
    )) {
        if ([string]::IsNullOrWhiteSpace($root) -or -not (Test-Path $root)) {
            continue
        }

        Get-ChildItem `
            -LiteralPath $root `
            -Directory `
            -Filter 'Python3*' `
            -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending |
            ForEach-Object {
                Add-PythonCandidate `
                    -Candidates $candidates `
                    -Candidate (Join-Path $_.FullName 'python.exe')
            }
    }

    # PATH commands are accepted only when they resolve to real executables,
    # not WindowsApps installer aliases.
    foreach ($commandName in @('python.exe', 'python3.exe', 'python', 'python3')) {
        $command = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($null -ne $command -and -not [string]::IsNullOrWhiteSpace($command.Source)) {
            Add-PythonCandidate `
                -Candidates $candidates `
                -Candidate $command.Source
        }
    }

    # The classic Python launcher can list installed interpreter paths without
    # asking it to install a missing runtime. Ignore the WindowsApps alias.
    $pyCommand = Get-Command py.exe -ErrorAction SilentlyContinue
    if (
        $null -ne $pyCommand -and
        -not [string]::IsNullOrWhiteSpace($pyCommand.Source) -and
        $pyCommand.Source -notlike '*\Microsoft\WindowsApps\*'
    ) {
        try {
            $launcherOutput = & $pyCommand.Source -0p 2>$null
            foreach ($line in @($launcherOutput)) {
                $match = [regex]::Match(
                    [string]$line,
                    '([A-Za-z]:\\[^\r\n]*?python(?:\.exe)?)\s*$'
                )
                if ($match.Success) {
                    Add-PythonCandidate `
                        -Candidates $candidates `
                        -Candidate $match.Groups[1].Value
                }
            }
        }
        catch {}
    }

    foreach ($candidate in $candidates) {
        $result = Test-PythonExecutable -Candidate $candidate
        if ($null -ne $result) {
            return $result
        }
    }

    return $null
}

function Invoke-CheckedPython {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Executable,

        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,

        [Parameter(Mandatory = $true)]
        [string]$FailureMessage
    )

    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw ("{0} Exit code: {1}" -f $FailureMessage, $LASTEXITCODE)
    }
}

$venv = Join-Path $projectRoot '.venv'
$venvPython = Join-Path $venv 'Scripts\python.exe'

if ($RecreateVenv -and (Test-Path -LiteralPath $venv)) {
    Write-Host '기존 word_editor 가상환경 제거'
    Remove-Item -LiteralPath $venv -Recurse -Force
}

if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    $basePython = Find-CompatiblePython -RequestedPythonPath $PythonPath

    if ($null -eq $basePython) {
        throw @'
Python 3.11 이상 실제 실행 파일을 찾지 못했습니다.
WindowsApps의 py/python 설치 별칭은 자동 설치 실패를 일으킬 수 있어 사용하지 않습니다.

Python을 설치한 뒤 PowerShell을 새로 열어 다시 실행하거나, 설치된 python.exe를 직접 지정하십시오.
예:
  .\run_word_editor.ps1 -Install -PythonPath "C:\Path\To\Python312\python.exe"

설치 상태 확인:
  where.exe python
  where.exe py
'@
    }

    Write-Host (
        '가상환경 생성에 사용할 Python: {0} ({1})' -f `
            $basePython.Path,
            $basePython.Version
    )

    Invoke-CheckedPython `
        -Executable $basePython.Path `
        -Arguments @('-m', 'venv', $venv) `
        -FailureMessage 'word_editor 가상환경 생성에 실패했습니다.'

    if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
        throw (
            "가상환경 명령은 끝났지만 python.exe가 생성되지 않았습니다: {0}" -f `
                $venvPython
        )
    }
}

$venvPythonInfo = Test-PythonExecutable -Candidate $venvPython
if ($null -eq $venvPythonInfo) {
    throw (
        "word_editor 가상환경의 Python이 없거나 3.11 미만입니다: {0}. " +
        "-RecreateVenv 옵션으로 다시 생성하십시오."
    ) -f $venvPython
}

Write-Host (
    'word_editor Python: {0} ({1})' -f `
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
        throw @'
word_editor 패키지가 아직 설치되지 않았습니다.
다음 명령으로 최초 설치하십시오.
  .\run_word_editor.ps1 -Install
'@
    }
}

$arguments = @('-m', 'word_editor')
if (-not [string]::IsNullOrWhiteSpace($NormalPath)) {
    $arguments += @('--normal-path', $NormalPath)
}

& $venvPython @arguments
exit $LASTEXITCODE

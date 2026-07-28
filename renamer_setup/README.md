# ReNamer Document Classifier Setup

일반 사용자가 Python, Poppler, Tesseract, LibreOffice 경로를 직접 설정하지 않고 `ReNamer_Setup_7.3.exe` 하나로 문서 자동 분류 기능을 설치하기 위한 프로젝트입니다.

## 사용자 설치 흐름

1. `ReNamer_Setup_7.3.exe` 실행
2. 설치 화면에서 **기본 사용자 이름** 입력
3. 필요한 경우 추가 인식 이름을 쉼표로 입력
4. 설치 완료 후 ReNamer에서 `PascalScript` 규칙 추가
5. `Scripts` 메뉴에서 **`7.3_자동이름 변경 시스템.pas`** 선택
6. 이후 PDF/Excel/ODS 파일을 ReNamer에 넣어 사용

설치기는 다음 ReNamer 기본 스크립트 폴더를 자동으로 생성하고 PascalScript를 직접 배치합니다.

```text
%UserProfile%\Documents\den4b\ReNamer\Scripts\7.3_자동이름 변경 시스템.pas
```

사용자는 숨김 폴더인 `AppData`를 찾거나 `.txt` 확장자를 `.pas`로 변경할 필요가 없습니다.

## 핵심 설계

- Python 런타임과 `python-calamine`은 PyInstaller **onedir** 빌드에 포함합니다.
- 일반 사용자 PC에는 Python을 별도로 설치하지 않습니다.
- NSIS 설치기는 `%LOCALAPPDATA%\ReNamerDocumentClassifier`에 분류 엔진을 설치합니다.
- ReNamer PascalScript는 `%UserProfile%\Documents\den4b\ReNamer\Scripts`에 자동 설치합니다.
- 설치기 사용자 입력은 `config\user.ini`와 `config\names.txt`에 저장합니다.
- 거래처 키워드는 외부 파일 `config\correspondent.txt`에서 관리합니다. 배포자가 비공개 빌드 입력을 지정한 경우 신규 설치에만 기본 목록을 포함하고 업그레이드에서는 기존 파일을 보존합니다.
- `에아스텍`과 `ERSTEQ`은 본인 회사 키워드이므로 거래처로 출력하지 않습니다.
- ReNamer PascalScript는 고정 `NameList`를 사용하지 않고 설치기가 생성한 설정을 읽습니다.
- PDF 및 Excel/ODS 본문은 `classifier.exe`가 분석합니다.
- 판정 결과는 `QUOTE`, `TRANSACTION`, `UNKNOWN`, `ERROR` 중 하나만 표준 출력으로 반환합니다.
- 상세 진단은 `logs\classification.log`에 기록합니다.
- 판정 불가 문서는 원래 파일명을 유지합니다.

## 지원 문서

- PDF: `.pdf`
- Excel/ODS: `.xls`, `.xlsx`, `.xlsm`, `.xlsb`, `.ods`
- 이미지: 기존 규칙대로 `03.물품사진`

Excel 셀 값은 `python-calamine`으로 우선 읽습니다. `.xlsx`와 `.xlsm`은 OOXML 도형 텍스트와 포함 이미지도 추가 검사합니다. 셀/도형 검사로 판정하지 못하면 다음 순서로 렌더링을 시도합니다.

1. Microsoft Excel COM PDF 내보내기
2. LibreOffice headless PDF 변환
3. PDF 텍스트 추출
4. Tesseract OCR

## 프로젝트 구조

```text
renamer_setup/
├─ .editorconfig
├─ pyproject.toml
├─ classifier.spec
├─ launcher.py
├─ src/renamer_document_classifier/
│  ├─ __init__.py
│  ├─ classification.py
│  ├─ runtime_paths.py
│  ├─ names_config.py
│  ├─ correspondent_config.py
│  ├─ extractors.py
│  ├─ logging_utils.py
│  ├─ service.py
│  └─ cli.py
├─ renamer/
│  └─ 7.3_자동이름 변경 시스템.pas
├─ installer/
│  └─ ReNamer_Setup.nsi
├─ scripts/
│  ├─ build.ps1
│  ├─ install_optional_dependencies.ps1
│  └─ verify_text_encoding.ps1
└─ tests/
   ├─ test_classification.py
   ├─ test_names_config.py
   └─ test_correspondent_config.py
```

저장소와 설치 파일은 다음 7.3 스크립트 이름을 동일하게 사용합니다.

```text
7.3_자동이름 변경 시스템.pas
```

## 반드시 지켜야 하는 문자 인코딩

설치 화면과 PowerShell 메시지에 한글이 들어 있으므로 다음 파일은 반드시 **UTF-8 with BOM**으로 저장해야 합니다.

```text
installer/ReNamer_Setup.nsi
scripts/build.ps1
scripts/install_optional_dependencies.ps1
scripts/verify_text_encoding.ps1
renamer/7.3_자동이름 변경 시스템.pas
```

`ReNamer_Setup.nsi`에는 다음 두 설정이 함께 적용되어 있습니다.

```nsi
# -*- coding: utf-8 -*-
Unicode true
```

`build.ps1`은 NSIS를 다음 입력 문자셋으로 실행합니다.

```text
makensis.exe /INPUTCHARSET UTF8 /OUTPUTCHARSET UTF8SIG ReNamer_Setup.nsi
```

빌드 시작 시 `verify_text_encoding.ps1`가 각 파일의 첫 3바이트가 UTF-8 BOM인 `EF BB BF`인지 검사합니다. BOM이 제거된 파일이 하나라도 있으면 설치 파일을 만들지 않고 중단합니다.

VS Code에서 수정할 때 오른쪽 아래 인코딩 표시를 눌러 **Save with Encoding → UTF-8 with BOM**을 선택하세요. `renamer_setup/.editorconfig`를 지원하는 편집기는 해당 확장자를 자동으로 UTF-8 BOM으로 저장합니다.

## 로컬 빌드

설치 파일 컴파일은 개발자의 로컬 Windows 환경에서 수행합니다. GitHub Actions는 소스 인코딩과 단위 테스트만 검증하며 `ReNamer_Setup_7.3.exe`를 생성하지 않습니다.

### 필요 도구

- Windows 10 또는 Windows 11
- Python 3.11~3.13
- NSIS 3.x
- PowerShell 5.1 이상

### 1. 저장소 이동

```powershell
cd C:\path\to\Vibe_Coding_Support_Tool\renamer_setup
```

### 2. 인코딩만 먼저 검사

```powershell
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\verify_text_encoding.ps1
```

정상 결과:

```text
All required installer sources use UTF-8 BOM.
```

### 3. 설치 파일 전체 빌드

현재 저장소에서 Python 3.13 실제 경로를 지정해 7.3 설치 프로그램을 컴파일하는 권장 명령:

```powershell
cd C:\Users\user\Documents\github\Vibe_Coding_Support_Tool\renamer_setup

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\build.ps1 `
  -PythonPath "C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe"
```

이 명령은 인코딩 검사와 단위 테스트, `classifier.exe` 패키징, NSIS 컴파일을 순서대로 실행합니다. 에이전트가 빌드를 관찰할 필요 없이 개발자가 직접 실행하고 결과를 공유하는 협업 절차를 사용합니다.

거래처 기본 목록을 포함할 배포 빌드는 Git에서 제외되는 다음 파일을 UTF-8 BOM으로 작성합니다.

```text
private\correspondent.txt
```

한 줄에 한 업체 키워드를 입력한 뒤 기존 빌드 명령을 실행하면 자동으로 포함됩니다. 다른 위치의 비공개 파일을 사용할 때는 다음처럼 명시합니다.

```powershell
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\build.ps1 `
  -PythonPath "C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe" `
  -CorrespondentFile "C:\private\correspondent.txt"
```

입력 파일이 없으면 기존처럼 빈 거래처 목록으로 설치되는 일반 배포 빌드가 생성됩니다. 빌드 로그에는 업체명 대신 유효 항목 수만 표시됩니다. 실제 거래처 목록은 `.gitignore`로 제외되지만 완성된 설치 파일에서는 추출할 수 있으므로 비밀 저장소로 간주할 수 없습니다.

테스트를 생략해야 하는 임시 개발 빌드만 다음 옵션을 사용합니다.

```powershell
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\build.ps1 `
  -PythonPath "C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe" `
  -SkipTests
```

빌드 결과:

```text
dist\ReNamer_Setup_7.3.exe
```

## 설치 후 ReNamer 설정

1. ReNamer 실행
2. 규칙 목록에서 `PascalScript` 추가
3. PascalScript 편집기의 `Scripts` 메뉴 열기
4. `7.3_자동이름 변경 시스템.pas` 선택
5. 컴파일 확인 후 규칙 추가
6. 현재 규칙을 ReNamer Preset으로 저장

설치기는 시작 메뉴와 바탕 화면에도 `7.3 자동이름 변경 시스템` 바로가기를 생성합니다.

## 한글이 깨질 때 확인할 항목

1. `verify_text_encoding.ps1`가 성공했는지 확인합니다.
2. `installer\ReNamer_Setup.nsi` 첫 줄 앞에 UTF-8 BOM이 존재하는지 확인합니다.
3. NSIS 3.x를 사용하고 있는지 확인합니다.
4. `build.ps1`을 통하지 않고 NSIS GUI에서 직접 컴파일했다면 입력 문자셋이 UTF-8인지 확인합니다.
5. 이전에 생성한 `dist\ReNamer_Setup_7.3.exe`를 삭제한 뒤 다시 빌드합니다.

## 거래처 목록 관리

7.3은 문서 본문 또는 기존 파일명에서 등록된 거래처 키워드를 찾고 사용자 이름 바로 뒤에 배치합니다.

```text
문서종류_날짜_사용자_거래처_원본명.확장자
```

설치된 거래처 목록은 다음 외부 파일에서 관리합니다.

```text
%LOCALAPPDATA%\ReNamerDocumentClassifier\config\correspondent.txt
```

비공개 기본 목록을 포함한 설치기는 이 파일이 없는 신규 설치에만 내장 목록을 복사합니다. 파일이 이미 있는 업그레이드에서는 내용이 비어 있더라도 기존 파일을 덮어쓰지 않습니다. 내장 목록이 없는 일반 빌드는 파일이 없을 때 UTF-8 BOM 형식의 빈 파일을 생성합니다. 한 줄에 한 업체 키워드를 입력하며, 빈 줄과 `#`으로 시작하는 주석은 무시합니다.

검색 키워드와 파일명에 표시할 브랜드가 다르면 다음 별칭 형식을 사용합니다.

```text
검색 키워드 | 대체 검색 키워드 => 출력 브랜드명
써모피서사이언티픽 | 모피셔사이언티픽 | thermofisher.com => ThermoFisher Scientific
```

왼쪽 키워드 중 하나가 문서에 있으면 오른쪽 브랜드명을 `CORRESPONDENT`와 파일명에 사용합니다. `| 대체 검색 키워드`는 필요할 때만 추가합니다. 등록되지 않은 업체는 파일명에 추가하지 않고 `에아스텍`과 `ERSTEQ`은 본인 회사 키워드로 항상 제외합니다. 설치 후 시작 메뉴의 **거래처 목록 편집**으로 파일을 열 수 있으며 제거 작업도 이 개인정보성 설정 파일을 삭제하지 않습니다.

## 사용자 이름 변경

설치 후 시작 메뉴에서 다음 항목을 실행합니다.

```text
ReNamer Document Classifier > 사용자 설정 변경
```

`classifier.exe configure`가 작은 설정 창을 열어 기본 이름과 추가 인식 이름을 변경합니다. PascalScript를 다시 편집할 필요가 없습니다.

## 설치 위치

분류 엔진과 설정:

```text
%LOCALAPPDATA%\ReNamerDocumentClassifier\
├─ classifier\
├─ config\user.ini
├─ config\names.txt
├─ config\correspondent.txt
├─ logs\classification.log
├─ renamer\7.3_자동이름 변경 시스템.pas
└─ tools\
```

ReNamer에서 사용자가 선택하는 스크립트:

```text
%UserProfile%\Documents\den4b\ReNamer\Scripts\7.3_자동이름 변경 시스템.pas
```

제거 프로그램은 ReNamer Scripts 폴더에 설치한 해당 `.pas` 파일도 함께 삭제합니다.

## 배포 원칙

- 일반 사용자에게 `.py`, `.cmd`, 패키지 설치 명령을 직접 제공하지 않습니다.
- 일반 사용자는 `.txt` 확장자를 `.pas`로 변경하지 않습니다.
- 배포물은 로컬에서 빌드한 `ReNamer_Setup_7.3.exe` 하나를 기본으로 합니다.
- 소스 파일은 개발 및 유지보수 목적으로만 저장합니다.
- 설치 파일을 배포하기 전 한글 표시, 사용자 이름 저장, ReNamer Scripts 등록, 제거 기능을 실제 Windows PC에서 확인합니다.

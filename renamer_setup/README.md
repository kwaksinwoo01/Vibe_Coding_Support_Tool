# ReNamer Document Classifier Setup

일반 사용자가 Python, Poppler, Tesseract, LibreOffice 경로를 직접 설정하지 않고 `ReNamer_Setup.exe` 하나로 문서 자동 분류 기능을 설치하기 위한 프로젝트입니다.

## 사용자 설치 흐름

1. `ReNamer_Setup.exe` 실행
2. 설치 화면에서 **기본 사용자 이름** 입력
3. 필요한 경우 추가 인식 이름을 쉼표로 입력
4. 설치 완료 후 바탕 화면의 `ReNamer 문서 분류 스크립트`를 ReNamer PascalScript 규칙에 한 번 불러오기
5. 이후 PDF/Excel/ODS 파일을 ReNamer에 넣어 사용

사용자는 Python 소스나 설정 파일을 직접 수정하지 않습니다.

## 핵심 설계

- Python 런타임과 `python-calamine`은 PyInstaller **onedir** 빌드에 포함합니다.
- NSIS 설치기는 `%LOCALAPPDATA%\ReNamerDocumentClassifier`에 프로그램을 설치합니다.
- 설치기 사용자 입력은 `config\user.ini`에 저장합니다.
- ReNamer PascalScript는 고정 `NameList`를 사용하지 않고 이 설정을 읽습니다.
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
├─ pyproject.toml
├─ classifier.spec
├─ src/renamer_document_classifier/
│  ├─ __init__.py
│  ├─ classification.py
│  ├─ config.py
│  ├─ extractors.py
│  └─ cli.py
├─ renamer/
│  └─ renamer_document_classifier_7_2.txt
├─ installer/
│  └─ ReNamer_Setup.nsi
├─ scripts/
│  ├─ build.ps1
│  └─ bootstrap_dependencies.ps1
└─ tests/
   └─ test_classification.py
```

## 빌드

Windows PowerShell에서:

```powershell
cd renamer_setup
./scripts/build.ps1
```

필요 도구:

- Python 3.11 이상
- NSIS 3.x

빌드 결과:

```text
dist/ReNamer_Setup.exe
```

GitHub Actions의 `Build ReNamer Setup` 워크플로도 동일한 설치 파일을 아티팩트로 생성합니다.

## 사용자 이름 변경

설치 후 시작 메뉴에서 다음 항목을 실행합니다.

```text
ReNamer Document Classifier > 사용자 설정 변경
```

`classifier.exe configure`가 작은 설정 창을 열어 기본 이름과 추가 인식 이름을 변경합니다. PascalScript를 다시 편집할 필요가 없습니다.

## 설치 위치

```text
%LOCALAPPDATA%\ReNamerDocumentClassifier\
├─ classifier\
├─ config\user.ini
├─ logs\classification.log
├─ renamer\renamer_document_classifier_7_2.txt
└─ tools\
```

## 배포 원칙

- 일반 사용자에게 `.py`, `.cmd`, 패키지 설치 명령을 직접 제공하지 않습니다.
- 배포물은 `ReNamer_Setup.exe` 하나를 기본으로 합니다.
- 소스 파일은 개발 및 유지보수 목적으로만 저장합니다.

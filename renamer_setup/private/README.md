# 비공개 거래처 배포 입력

비공개 배포용 거래처 목록은 다음 파일에 작성합니다.

```text
renamer_setup\private\correspondent.txt
```

파일은 **UTF-8 with BOM**으로 저장합니다. 빈 줄과 `#`으로 시작하는 주석은
무시됩니다. 실제 `correspondent.txt`는 Git에서 제외되며 커밋하면 안 됩니다.

## 거래처 작성 규칙

검색된 이름을 그대로 파일명에 사용하려면 업체명을 한 줄에 하나씩 작성합니다.

```text
닥터바이오
나노바이오
에이티지코리아
```

문서에 표시되는 검색어와 파일명에 사용할 업체명이 다르면 `=>` 별칭 형식을
사용합니다. 같은 업체를 찾는 검색어가 여러 개면 `|`로 구분합니다.

```text
써모피서사이언티픽 | 모피셔사이언티픽 | thermofisher.com => ThermoFisher Scientific
```

두 형식은 한 파일 안에서 함께 사용할 수 있습니다.

```text
써모피서사이언티픽 | 모피셔사이언티픽 | thermofisher.com => ThermoFisher Scientific
닥터바이오
나노바이오
에이티지코리아
```

## 빌드 및 설치 시 동작

`scripts\build.ps1`은 이 파일이 존재하면 설치 프로그램에 자동으로 포함합니다.
다른 비공개 파일을 사용하려면 `-CorrespondentFile` 옵션으로 지정할 수 있습니다.

신규 설치에서는 내장 목록을 다음 런타임 파일로 복사합니다.

```text
%LOCALAPPDATA%\ReNamerDocumentClassifier\config\correspondent.txt
```

업그레이드 설치에서는 사용자가 편집한 기존 런타임 파일을 덮어쓰지 않습니다.
따라서 새 업체를 비공개 빌드 입력에 추가해도 기존 설치 환경에는 자동 반영되지
않으며, 설치된 런타임 파일에도 직접 추가해야 합니다.

빌드 결과는 `dist\ReNamer_Setup_7.3.exe`로 생성됩니다.

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

설치기는 내장 목록을 다음 배포 기본값 파일로 복사합니다.

```text
%LOCALAPPDATA%\ReNamerDocumentClassifier\support\correspondent.defaults.txt
```

신규 설치와 업그레이드 설치 모두 `sync-correspondents` 검증기를 실행합니다. 검증기는
이전 배포 기본값, 사용자가 편집한 `config\correspondent.txt`, 새 배포 기본값을
3-way 병합합니다. 사용자가 추가한 별칭과 표시 이름, 사용자가 삭제한 기본 별칭은
보존하면서 패치에서 추가·삭제한 기본 별칭을 반영합니다.

이전 기본값은 다음 파일에 저장됩니다.

```text
%LOCALAPPDATA%\ReNamerDocumentClassifier\config\correspondent.defaults.applied.txt
%LOCALAPPDATA%\ReNamerDocumentClassifier\config\correspondent.defaults.state.json
```

이 기능이 처음 적용되는 기존 설치는 이전 기본값이 없으므로 사용자 목록과 새 목록을
안전하게 합집합한 뒤 기준 스냅샷을 만듭니다. 병합 전 사용자 파일은
`config\correspondent-backups`에 백업합니다.

기본 별칭을 제거하는 패치를 만들려면 이 파일의 기존 규칙에서 해당 별칭을 삭제합니다.
예를 들어 `thermofisher.com`을 삭제한 다음 새 설치 프로그램을 빌드하면, 다음 설치에서
그 기본 별칭만 제거되고 사용자가 추가한 `Thermo`, `ThermoFisher` 같은 별칭은 유지됩니다.
패치 전후 규칙을 같은 업체로 연결할 수 있도록 표시 이름 또는 검색 별칭을 하나 이상
공통으로 유지해야 합니다.

빌드 결과는 `dist\ReNamer_Setup_7.4.1.exe`로 생성됩니다.

# -*- coding: utf-8 -*-
Unicode true

!include "MUI2.nsh"
!include "nsDialogs.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"

!define PRODUCT_NAME "ReNamer Document Classifier"
!define PRODUCT_VERSION "7.2.1"
!define PRODUCT_PUBLISHER "KWAKSINWOO"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\ReNamerDocumentClassifier.exe"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\ReNamerDocumentClassifier"
!define RENAMER_SCRIPT_NAME "7.0_자동이름 변경 시스템.pas"
!define RENAMER_SCRIPT_DIR "$DOCUMENTS\den4b\ReNamer\Scripts"

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "..\dist\ReNamer_Setup.exe"
InstallDir "$LOCALAPPDATA\ReNamerDocumentClassifier"
InstallDirRegKey HKCU "${PRODUCT_DIR_REGKEY}" ""
RequestExecutionLevel user
SetCompressor /SOLID lzma
SetCompressorDictSize 64

Var DefaultName
Var KnownNames
Var DefaultNameControl
Var KnownNamesControl
Var DependencyStatus

!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

!insertmacro MUI_PAGE_WELCOME
Page custom UserSettingsPageCreate UserSettingsPageLeave
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\classifier\classifier.exe"
!define MUI_FINISHPAGE_RUN_PARAMETERS "configure"
!define MUI_FINISHPAGE_RUN_TEXT "설치된 사용자 설정 확인 및 변경"
!define MUI_FINISHPAGE_SHOWREADME "${RENAMER_SCRIPT_DIR}\${RENAMER_SCRIPT_NAME}"
!define MUI_FINISHPAGE_SHOWREADME_TEXT "ReNamer용 '7.0 자동이름 변경 시스템' 스크립트 열기"
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "Korean"

Function .onInit
  StrCpy $DefaultName ""
  StrCpy $KnownNames "곽신우, 김민규, 이슬기, 임설와, 정우형, 박승주"
FunctionEnd

Function UserSettingsPageCreate
  nsDialogs::Create 1018
  Pop $0
  ${If} $0 == error
    Abort
  ${EndIf}

  !insertmacro MUI_HEADER_TEXT "사용자 이름 설정" "파일명에 적용할 기본 이름을 입력합니다."

  ${NSD_CreateLabel} 0 0 100% 24u "파일명에서 담당자 이름을 찾지 못한 경우 사용할 본인의 이름을 입력하세요."
  Pop $0

  ${NSD_CreateLabel} 0 32u 100% 12u "기본 사용자 이름 (필수)"
  Pop $0

  ${NSD_CreateText} 0 47u 100% 13u "$DefaultName"
  Pop $DefaultNameControl

  ${NSD_CreateLabel} 0 70u 100% 24u "파일명에서 인식할 다른 사람 이름을 쉼표로 구분해 입력하세요. 필요하지 않은 이름은 삭제할 수 있습니다."
  Pop $0

  ${NSD_CreateText} 0 99u 100% 26u "$KnownNames"
  Pop $KnownNamesControl

  ${NSD_CreateLabel} 0 134u 100% 34u "설치 후에는 시작 메뉴의 '사용자 설정 변경'에서 다시 수정할 수 있습니다. PascalScript 파일을 직접 편집할 필요가 없습니다."
  Pop $0

  nsDialogs::Show
FunctionEnd

Function UserSettingsPageLeave
  ${NSD_GetText} $DefaultNameControl $DefaultName
  ${NSD_GetText} $KnownNamesControl $KnownNames

  ${If} $DefaultName == ""
    MessageBox MB_ICONEXCLAMATION|MB_OK "기본 사용자 이름을 입력해야 합니다."
    Abort
  ${EndIf}
FunctionEnd

Section "MainProgram" SEC_MAIN
  SetShellVarContext current
  SetOverwrite on

  SetOutPath "$INSTDIR\classifier"
  File /r "..\dist\classifier\*.*"

  ; 유지보수용 내부 사본입니다.
  SetOutPath "$INSTDIR\renamer"
  Delete "$INSTDIR\renamer\renamer_document_classifier_7_2.txt"
  File "/oname=${RENAMER_SCRIPT_NAME}" "..\renamer\renamer_document_classifier_7_2.txt"

  ; 일반 사용자가 ReNamer에서 바로 찾을 수 있도록 기본 Scripts 폴더에 설치합니다.
  CreateDirectory "${RENAMER_SCRIPT_DIR}"
  SetOutPath "${RENAMER_SCRIPT_DIR}"
  File "/oname=${RENAMER_SCRIPT_NAME}" "..\renamer\renamer_document_classifier_7_2.txt"

  SetOutPath "$INSTDIR\support"
  File "..\scripts\install_optional_dependencies.ps1"

  SetOutPath "$INSTDIR\tools"
  File /nonfatal /r "..\vendor\tools\*.*"

  CreateDirectory "$INSTDIR\config"
  CreateDirectory "$INSTDIR\logs"
  CreateDirectory "$INSTDIR\temp"

  nsExec::ExecToStack '"$INSTDIR\classifier\classifier.exe" configure --default-name "$DefaultName" --known-names "$KnownNames"'
  Pop $0
  Pop $1
  ${If} $0 != 0
    MessageBox MB_ICONSTOP|MB_OK "사용자 설정 저장에 실패했습니다.$\r$\n$\r$\n$1"
    Abort
  ${EndIf}

  DetailPrint "문서 변환 보조 도구를 확인합니다."
  nsExec::ExecToStack 'powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "$INSTDIR\support\install_optional_dependencies.ps1" -InstallRoot "$INSTDIR"'
  Pop $0
  Pop $DependencyStatus
  DetailPrint "$DependencyStatus"

  WriteUninstaller "$INSTDIR\Uninstall.exe"

  WriteRegStr HKCU "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\classifier\classifier.exe"
  WriteRegStr HKCU "${PRODUCT_UNINST_KEY}" "DisplayName" "${PRODUCT_NAME}"
  WriteRegStr HKCU "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr HKCU "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
  WriteRegStr HKCU "${PRODUCT_UNINST_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${PRODUCT_UNINST_KEY}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegDWORD HKCU "${PRODUCT_UNINST_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${PRODUCT_UNINST_KEY}" "NoRepair" 1

  CreateDirectory "$SMPROGRAMS\ReNamer Document Classifier"
  CreateShortCut \
    "$SMPROGRAMS\ReNamer Document Classifier\사용자 설정 변경.lnk" \
    "$INSTDIR\classifier\classifier.exe" \
    "configure"
  CreateShortCut \
    "$SMPROGRAMS\ReNamer Document Classifier\분류 로그 열기.lnk" \
    "$INSTDIR\classifier\classifier.exe" \
    "open-log"
  CreateShortCut \
    "$SMPROGRAMS\ReNamer Document Classifier\분류 로그 초기화.lnk" \
    "$INSTDIR\classifier\classifier.exe" \
    "clear-log"
  CreateShortCut \
    "$SMPROGRAMS\ReNamer Document Classifier\7.0 자동이름 변경 시스템 스크립트.lnk" \
    "${RENAMER_SCRIPT_DIR}\${RENAMER_SCRIPT_NAME}"
  CreateShortCut \
    "$SMPROGRAMS\ReNamer Document Classifier\제거.lnk" \
    "$INSTDIR\Uninstall.exe"

  Delete "$DESKTOP\ReNamer 문서 분류 스크립트.lnk"
  CreateShortCut \
    "$DESKTOP\7.0 자동이름 변경 시스템.lnk" \
    "${RENAMER_SCRIPT_DIR}\${RENAMER_SCRIPT_NAME}"
SectionEnd

Section "Uninstall"
  SetShellVarContext current

  Delete "$DESKTOP\ReNamer 문서 분류 스크립트.lnk"
  Delete "$DESKTOP\7.0 자동이름 변경 시스템.lnk"
  RMDir /r "$SMPROGRAMS\ReNamer Document Classifier"

  Delete "${RENAMER_SCRIPT_DIR}\${RENAMER_SCRIPT_NAME}"

  DeleteRegKey HKCU "${PRODUCT_UNINST_KEY}"
  DeleteRegKey HKCU "${PRODUCT_DIR_REGKEY}"

  RMDir /r "$INSTDIR"
SectionEnd

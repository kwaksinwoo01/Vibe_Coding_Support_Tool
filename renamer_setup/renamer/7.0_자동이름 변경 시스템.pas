// 7.0 자동이름 변경 시스템
// ReNamer PascalScript
// 설치된 문서 분류기와 사용자 이름 설정을 사용합니다.

var
  AppRoot: WideString;
  ClassifierExe: WideString;
  NamesPath: WideString;
  BridgeLogPath: WideString;
  DefaultPersonName: WideString;
  KnownNames: TWideStringArray;
  ConfigLoaded: Boolean;
  OriginalBaseName: WideString;
  TempOriginalBaseName: WideString;
  FileExtension: WideString;
  DocumentType: WideString;
  PersonName: WideString;
  ExistingDate: WideString;
  ExistingDateToken: WideString;
  TakenDate: WideString;
  DateTime: TDateTime;


procedure AppendBridgeLog(const MessageText: WideString);
begin
  if Length(BridgeLogPath) = 0 then Exit;
  WideForceDirectories(AppRoot + 'logs\');
  FileAppendContent(
    BridgeLogPath,
    UTF8Encode(MessageText + #13#10)
  );
end;


function IsDigitChar(const C: WideChar): Boolean;
begin
  Result := (C >= '0') and (C <= '9');
end;


function IsDigitsAt(
  const S: WideString;
  StartPos: Integer;
  Count: Integer
): Boolean;
var
  Position: Integer;
begin
  Result := False;
  if StartPos < 1 then Exit;
  if Count < 1 then Exit;
  if StartPos + Count - 1 > Length(S) then Exit;

  for Position := StartPos to StartPos + Count - 1 do
  begin
    if not IsDigitChar(S[Position]) then Exit;
  end;

  Result := True;
end;


function IsValidMonthDayAt(
  const S: WideString;
  MonthStart: Integer;
  DayStart: Integer
): Boolean;
var
  MonthTens, MonthOnes: WideChar;
  DayTens, DayOnes: WideChar;
begin
  Result := False;
  if not IsDigitsAt(S, MonthStart, 2) then Exit;
  if not IsDigitsAt(S, DayStart, 2) then Exit;

  MonthTens := S[MonthStart];
  MonthOnes := S[MonthStart + 1];
  DayTens := S[DayStart];
  DayOnes := S[DayStart + 1];

  if MonthTens = '0' then
  begin
    if MonthOnes < '1' then Exit;
    if MonthOnes > '9' then Exit;
  end
  else if MonthTens = '1' then
  begin
    if MonthOnes < '0' then Exit;
    if MonthOnes > '2' then Exit;
  end
  else
    Exit;

  if DayTens = '0' then
  begin
    if DayOnes < '1' then Exit;
    if DayOnes > '9' then Exit;
  end
  else if (DayTens = '1') or (DayTens = '2') then
  begin
    if DayOnes < '0' then Exit;
    if DayOnes > '9' then Exit;
  end
  else if DayTens = '3' then
  begin
    if DayOnes < '0' then Exit;
    if DayOnes > '1' then Exit;
  end
  else
    Exit;

  Result := True;
end;


function IsDateBoundary(
  const S: WideString;
  StartPos: Integer;
  TokenLength: Integer
): Boolean;
begin
  Result := False;

  if StartPos > 1 then
  begin
    if IsDigitChar(S[StartPos - 1]) then Exit;
  end;

  if StartPos + TokenLength <= Length(S) then
  begin
    if IsDigitChar(S[StartPos + TokenLength]) then Exit;
  end;

  Result := True;
end;


function ExtractExistingDateToYYMMDD(
  const S: WideString;
  var SourceToken: WideString
): WideString;
var
  Position: Integer;
  SeparatorChar: WideChar;
begin
  Result := '';
  SourceToken := '';

  if Length(S) >= 10 then
  begin
    for Position := 1 to Length(S) - 9 do
    begin
      if IsDigitsAt(S, Position, 4) then
      begin
        SeparatorChar := S[Position + 4];
        if (
          (SeparatorChar = '-') or
          (SeparatorChar = '.') or
          (SeparatorChar = '_')
        ) and
          (S[Position + 7] = SeparatorChar) and
          IsDigitsAt(S, Position + 5, 2) and
          IsDigitsAt(S, Position + 8, 2) and
          IsValidMonthDayAt(S, Position + 5, Position + 8) and
          IsDateBoundary(S, Position, 10) then
        begin
          SourceToken := WideCopy(S, Position, 10);
          Result :=
            WideCopy(S, Position + 2, 2) +
            WideCopy(S, Position + 5, 2) +
            WideCopy(S, Position + 8, 2);
          Exit;
        end;
      end;
    end;
  end;

  if Length(S) >= 8 then
  begin
    for Position := 1 to Length(S) - 7 do
    begin
      if IsDigitsAt(S, Position, 8) and
        IsValidMonthDayAt(S, Position + 4, Position + 6) and
        IsDateBoundary(S, Position, 8) then
      begin
        SourceToken := WideCopy(S, Position, 8);
        Result := WideCopy(S, Position + 2, 6);
        Exit;
      end;
    end;
  end;

  if Length(S) >= 6 then
  begin
    for Position := 1 to Length(S) - 5 do
    begin
      if IsDigitsAt(S, Position, 6) and
        IsValidMonthDayAt(S, Position + 2, Position + 4) and
        IsDateBoundary(S, Position, 6) then
      begin
        SourceToken := WideCopy(S, Position, 6);
        Result := SourceToken;
        Exit;
      end;
    end;
  end;
end;


function CustomWideTrim(const S: WideString): WideString;
var
  FirstPosition, LastPosition: Integer;
begin
  FirstPosition := 1;
  while FirstPosition <= Length(S) do
  begin
    if (S[FirstPosition] <> ' ') and
      (S[FirstPosition] <> '_') and
      (S[FirstPosition] <> '-') then Break;
    Inc(FirstPosition);
  end;

  LastPosition := Length(S);
  while LastPosition >= FirstPosition do
  begin
    if (S[LastPosition] <> ' ') and
      (S[LastPosition] <> '_') and
      (S[LastPosition] <> '-') then Break;
    Dec(LastPosition);
  end;

  if LastPosition < FirstPosition then
    Result := ''
  else
    Result := WideCopy(
      S,
      FirstPosition,
      LastPosition - FirstPosition + 1
    );
end;


function NormalizeRemainder(const S: WideString): WideString;
begin
  Result := S;

  while WidePos('  ', Result) > 0 do
    Result := WideReplaceStr(Result, '  ', ' ');

  while WidePos('__', Result) > 0 do
    Result := WideReplaceStr(Result, '__', '_');

  while WidePos('_ ', Result) > 0 do
    Result := WideReplaceStr(Result, '_ ', '_');

  while WidePos(' _', Result) > 0 do
    Result := WideReplaceStr(Result, ' _', '_');

  Result := CustomWideTrim(Result);
end;


function RemoveDocumentLabels(const S: WideString): WideString;
begin
  Result := S;
  Result := WideReplaceStr(Result, '00.견적서', '');
  Result := WideReplaceStr(Result, '01.거래명세서', '');
  Result := WideReplaceStr(Result, '03.물품사진', '');
  Result := WideReplaceStr(Result, '구매기안서', '');
  Result := WideReplaceStr(Result, '견적서', '');
  Result := WideReplaceStr(Result, '견적', '');
  Result := WideReplaceStr(Result, '거래명세서', '');
  Result := WideReplaceStr(Result, '거래명세표', '');
  Result := WideReplaceStr(Result, '거래내역서', '');
  Result := WideReplaceStr(Result, '물품사진', '');
end;


procedure LoadNameConfig;
var
  Lines: TWideStringArray;
  SourceIndex, TargetIndex: Integer;
  Value: WideString;
begin
  if ConfigLoaded then Exit;

  ConfigLoaded := True;
  DefaultPersonName := '사용자';
  SetLength(KnownNames, 0);

  if not WideFileExists(NamesPath) then
  begin
    AppendBridgeLog('NAME_CONFIG_MISSING path=' + NamesPath);
    Exit;
  end;

  Lines := FileReadTextLines(NamesPath);
  if Length(Lines) = 0 then
  begin
    AppendBridgeLog('NAME_CONFIG_EMPTY path=' + NamesPath);
    Exit;
  end;

  Value := CustomWideTrim(Lines[0]);
  if Length(Value) > 0 then
    DefaultPersonName := Value;

  SetLength(KnownNames, Length(Lines));
  TargetIndex := 0;

  for SourceIndex := 0 to Length(Lines) - 1 do
  begin
    Value := CustomWideTrim(Lines[SourceIndex]);
    if Length(Value) > 0 then
    begin
      KnownNames[TargetIndex] := Value;
      Inc(TargetIndex);
    end;
  end;

  SetLength(KnownNames, TargetIndex);
end;


function DetectPersonName(
  const BaseName: WideString
): WideString;
var
  Position: Integer;
  Candidate: WideString;
begin
  LoadNameConfig;
  Result := DefaultPersonName;

  if Length(KnownNames) = 0 then Exit;

  for Position := 0 to Length(KnownNames) - 1 do
  begin
    Candidate := KnownNames[Position];
    if WidePos(
      WideLowerCase(Candidate),
      WideLowerCase(BaseName)
    ) > 0 then
    begin
      Result := Candidate;
      Exit;
    end;
  end;
end;


function IsImageExtension(
  const Extension: WideString
): Boolean;
begin
  Result :=
    (Extension = '.jpg') or
    (Extension = '.jpeg') or
    (Extension = '.png') or
    (Extension = '.gif') or
    (Extension = '.bmp') or
    (Extension = '.tif') or
    (Extension = '.tiff');
end;


function IsDocumentExtension(
  const Extension: WideString
): Boolean;
begin
  Result :=
    (Extension = '.pdf') or
    (Extension = '.xls') or
    (Extension = '.xlsx') or
    (Extension = '.xlsm') or
    (Extension = '.xlsb') or
    (Extension = '.ods');
end;


function IsAsciiText(const S: WideString): Boolean;
var
  Position: Integer;
begin
  Result := True;

  for Position := 1 to Length(S) do
  begin
    if S[Position] > '~' then
    begin
      Result := False;
      Exit;
    end;
  end;
end;


function PrepareConsoleDocumentPath(
  const SourcePath: WideString;
  const Extension: WideString;
  var TempCopyCreated: Boolean
): WideString;
var
  ShortPath: WideString;
  TempDirectory: WideString;
  TempPath: WideString;
begin
  Result := '';
  TempCopyCreated := False;

  if IsAsciiText(SourcePath) then
  begin
    Result := SourcePath;
    Exit;
  end;

  ShortPath := WideExtractShortPathName(SourcePath);
  if (Length(ShortPath) > 0) and IsAsciiText(ShortPath) then
  begin
    Result := ShortPath;
    Exit;
  end;

  TempDirectory := AppRoot + 'temp\';
  if not WideForceDirectories(TempDirectory) then
  begin
    AppendBridgeLog(
      'TEMP_DIRECTORY_FAILED path=' + TempDirectory
    );
    Exit;
  end;

  TempPath :=
    TempDirectory +
    'input_' + IntToStr(GetCurrentFileIndex) + Extension;

  if WideFileExists(TempPath) then
    WideDeleteFile(TempPath);

  if not WideCopyFile(SourcePath, TempPath, False) then
  begin
    AppendBridgeLog(
      'TEMP_COPY_FAILED source=' + SourcePath +
      ' destination=' + TempPath
    );
    Exit;
  end;

  TempCopyCreated := True;
  ShortPath := WideExtractShortPathName(TempPath);

  if (Length(ShortPath) > 0) and IsAsciiText(ShortPath) then
    Result := ShortPath
  else
    Result := TempPath;

  AppendBridgeLog(
    'TEMP_COPY_OK source=' + SourcePath +
    ' destination=' + Result
  );
end;


function ReadOutputValue(
  const OutputText: WideString;
  const Key: WideString
): WideString;
var
  Marker: WideString;
  StartPos, EndPos: Integer;
begin
  Result := '';
  Marker := Key + '=';
  StartPos := WidePos(Marker, OutputText);
  if StartPos = 0 then Exit;

  StartPos := StartPos + Length(Marker);
  EndPos := StartPos;

  while EndPos <= Length(OutputText) do
  begin
    if OutputText[EndPos] = #10 then Break;
    if OutputText[EndPos] = #13 then Break;
    Inc(EndPos);
  end;

  Result := CustomWideTrim(
    WideCopy(OutputText, StartPos, EndPos - StartPos)
  );
end;


function ClassifyDocument(
  const SourcePath: WideString;
  const OriginalFileName: WideString;
  const Extension: WideString
): WideString;
var
  LowerOriginalName: WideString;
  ConsoleInputPath: WideString;
  ConsoleExePath: WideString;
  SafeOriginalName: WideString;
  CommandLine: String;
  ConsoleOutput: String;
  OutputText: WideString;
  KindValue: WideString;
  TempCopyCreated: Boolean;
  ExitCode: Cardinal;
begin
  Result := 'NA';
  LowerOriginalName := WideLowerCase(OriginalFileName);

  if WidePos('견적', LowerOriginalName) > 0 then
  begin
    AppendBridgeLog(
      'CLASSIFY_FILENAME kind=QUOTE file=' + OriginalFileName
    );
    Result := '00.견적서';
    Exit;
  end;

  if (
    WidePos('거래명세', LowerOriginalName) > 0
  ) or (
    WidePos('거래내역', LowerOriginalName) > 0
  ) then
  begin
    AppendBridgeLog(
      'CLASSIFY_FILENAME kind=TRANSACTION file=' + OriginalFileName
    );
    Result := '01.거래명세서';
    Exit;
  end;

  if not WideFileExists(ClassifierExe) then
  begin
    AppendBridgeLog(
      'CLASSIFIER_MISSING path=' + ClassifierExe
    );
    Exit;
  end;

  TempCopyCreated := False;
  ConsoleOutput := '';

  ConsoleInputPath := PrepareConsoleDocumentPath(
    SourcePath,
    Extension,
    TempCopyCreated
  );

  if Length(ConsoleInputPath) = 0 then
  begin
    AppendBridgeLog(
      'INPUT_PATH_PREPARE_FAILED source=' + SourcePath
    );
    Exit;
  end;

  ConsoleExePath := WideExtractShortPathName(ClassifierExe);
  if Length(ConsoleExePath) = 0 then
    ConsoleExePath := ClassifierExe;

  SafeOriginalName := WideReplaceStr(
    OriginalFileName,
    '"',
    ''
  );

  CommandLine := UTF8Encode(
    '"' + ConsoleExePath + '"' +
    ' inspect --input "' + ConsoleInputPath + '"' +
    ' --original-name "' + SafeOriginalName + '"'
  );

  AppendBridgeLog(
    'CLASSIFIER_START source=' + SourcePath +
    ' input=' + ConsoleInputPath
  );

  ExitCode := ExecConsoleApp(CommandLine, ConsoleOutput);

  if TempCopyCreated then
    WideDeleteFile(ConsoleInputPath);

  AppendBridgeLog(
    'CLASSIFIER_EXIT code=' + IntToStr(ExitCode) +
    ' output=' + UTF8Decode(ConsoleOutput)
  );

  if ExitCode <> 0 then Exit;
  if Length(ConsoleOutput) = 0 then Exit;

  OutputText := UTF8Decode(ConsoleOutput);
  KindValue := WideUpperCase(
    ReadOutputValue(OutputText, 'KIND')
  );

  if KindValue = 'QUOTE' then
    Result := '00.견적서'
  else if KindValue = 'TRANSACTION' then
    Result := '01.거래명세서'
  else
    AppendBridgeLog(
      'CLASSIFIER_UNKNOWN kind=' + KindValue +
      ' source=' + SourcePath
    );
end;


begin
  AppRoot :=
    WideGetEnvironmentVar('LOCALAPPDATA') +
    '\ReNamerDocumentClassifier\';

  ClassifierExe :=
    AppRoot + 'classifier\classifier.exe';

  NamesPath :=
    AppRoot + 'config\names.txt';

  BridgeLogPath :=
    AppRoot + 'logs\pascal_bridge.log';

  OriginalBaseName :=
    WideExtractBaseName(FileName);

  FileExtension :=
    WideLowerCase(WideExtractFileExt(FileName));

  AppendBridgeLog(
    'PREVIEW_START path=' + FilePath +
    ' filename=' + FileName
  );

  if IsImageExtension(FileExtension) then
  begin
    if WidePos(
      '03.물품사진_',
      WideLowerCase(FileName)
    ) = 1 then
      Exit;

    DocumentType := '03.물품사진';
  end
  else if IsDocumentExtension(FileExtension) then
  begin
    DocumentType := ClassifyDocument(
      FilePath,
      FileName,
      FileExtension
    );

    if DocumentType = 'NA' then
    begin
      AppendBridgeLog(
        'PREVIEW_UNCHANGED reason=classification_failed path=' +
        FilePath
      );
      Exit;
    end;
  end
  else
  begin
    AppendBridgeLog(
      'PREVIEW_UNCHANGED reason=unsupported_extension extension=' +
      FileExtension
    );
    Exit;
  end;

  PersonName := DetectPersonName(OriginalBaseName);
  TempOriginalBaseName := OriginalBaseName;

  if Length(PersonName) > 0 then
  begin
    TempOriginalBaseName := WideReplaceStr(
      TempOriginalBaseName,
      PersonName,
      ''
    );
  end;

  ExistingDateToken := '';
  ExistingDate := ExtractExistingDateToYYMMDD(
    OriginalBaseName,
    ExistingDateToken
  );

  if Length(ExistingDate) > 0 then
    TakenDate := ExistingDate
  else
  begin
    DateTime := FileTimeModified(FilePath);
    TakenDate := FormatDateTime('yymmdd', DateTime);
  end;

  TempOriginalBaseName :=
    RemoveDocumentLabels(TempOriginalBaseName);

  if Length(ExistingDateToken) > 0 then
  begin
    TempOriginalBaseName := WideReplaceStr(
      TempOriginalBaseName,
      ExistingDateToken,
      ''
    );
  end;

  TempOriginalBaseName := WideReplaceStr(
    TempOriginalBaseName,
    '선생님',
    ''
  );

  TempOriginalBaseName := WideReplaceStr(
    TempOriginalBaseName,
    '연구원',
    ''
  );

  TempOriginalBaseName :=
    NormalizeRemainder(TempOriginalBaseName);

  FileName :=
    DocumentType + '_' +
    TakenDate + '_' +
    PersonName;

  if Length(TempOriginalBaseName) > 0 then
    FileName :=
      FileName + '_' + TempOriginalBaseName;

  FileName := FileName + FileExtension;

  AppendBridgeLog(
    'PREVIEW_RENAMED new_name=' + FileName
  );
end.

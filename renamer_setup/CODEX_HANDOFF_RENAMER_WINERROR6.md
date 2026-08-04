# Local Codex handoff: ReNamer PascalScript `WinError 6`

## Mission

Find and fix the actual root cause of the ReNamer integration failure in the local Windows environment.

The document classifier works when invoked directly from PowerShell, but fails when ReNamer PascalScript launches the installed `classifier.exe` through `ExecConsoleApp`.

Do not apply another speculative handle workaround. First reproduce the error locally and obtain the exact traceback/API call that raises `OSError: [WinError 6]`.

## Resolution verified on 2026-07-27

The failure had two connected causes:

1. The installer used the default value of the App Paths registry key as an
   install directory. That value is the full `classifier.exe` path, so every
   reinstall appended another `classifier` directory. New installers updated
   nested copies while ReNamer continued to run the stale executable at the
   documented path.
2. The stale pre-workaround executable called `subprocess.run` with inherited
   stdin. ReNamer `ExecConsoleApp` supplied an invalid standard-input handle.
   Python 3.13 failed before child-process creation at
   `subprocess.py:1364`, `_winapi.GetStdHandle(_winapi.STD_INPUT_HANDLE)`.

The exact reproduced traceback from the historical `f600bb2` runtime was:

```text
renamer_document_classifier/cli.py:192 main
renamer_document_classifier/service.py:40 inspect_document
renamer_document_classifier/extractors.py:468 extract_primary_text
renamer_document_classifier/extractors.py:143 extract_pdf_text
renamer_document_classifier/extractors.py:119 _run
subprocess.py:554 run
subprocess.py:1005 Popen.__init__
subprocess.py:1364 _get_handles
OSError: [WinError 6] 핸들이 잘못되었습니다
```

Process Monitor confirmed the boundary. In the failing historical run,
`classifier.exe` was created three times while `pdftotext.exe`,
`pdftoppm.exe`, and `tesseract.exe` were each created zero times. With the
verified fix, all four process types were created five times for five PDFs.

The minimal runtime fix is scoped to the external-tool boundary:
`extractors._run()` passes `stdin=subprocess.DEVNULL`. The global stdin
replacement, `subprocess.run` monkey patch, and custom `CreateProcessW`
implementation were removed. `launcher.py` now keeps only an earliest-possible
file diagnostic at `logs/launcher_runtime.log`.

The installer now reads `InstallLocation` from the uninstall registry key.
Version `7.2.4` was retained. A clean uninstall and reinstall produced matching
hashes:

```text
build classifier.exe:     F267EED48F5EE85FCA129E8D5C62F21E776BA13DE644FCE60A67B3DB7D9DF5D7
installed classifier.exe: F267EED48F5EE85FCA129E8D5C62F21E776BA13DE644FCE60A67B3DB7D9DF5D7
```

Direct PowerShell inspection returned `STATUS=OK`, `KIND=TRANSACTION`, and
exit code 0. Final ReNamer verification processed five PDFs, all with
`CLASSIFIER_EXIT code=0`; all five produced `KIND=TRANSACTION` and
`PREVIEW_RENAMED`. The ReNamer new-name column
visibly showed all five `01.거래명세서_...` previews. Tests passed (`13 passed`),
and both PyInstaller and NSIS builds succeeded.

The fifth PDF (`SAuthor26071620371.pdf`) is an image-only scan. Tesseract
`--psm 6` extracted 1,266 body characters but omitted the isolated title,
so the first verified build returned `KIND=UNKNOWN`. The same rendered image
with `--psm 3` extracted the transaction title at position 37 and classified
it as `TRANSACTION` with score 100. PDF OCR is now adaptive and stops as soon
as a classification succeeds:

```text
PSM 6 at 220 dpi
PSM 3 at 220 dpi
PSM 11 at 220 dpi
PSM 3 at 300 dpi grayscale
PSM 11 at 300 dpi grayscale
```

Each new OCR attempt is classified on its own before accumulated text is
classified, preventing a title found by a later mode from being pushed beyond
the 2,000-character title scan boundary. Existing PDFs still stop after PSM 6;
only the problem scan advanced to PSM 3. Tests passed (`13 passed`).

## Version 7.3 correspondent support verified on 2026-07-28

Version 7.3 adds a registered-correspondent segment after the person name:

```text
document_type_date_person_correspondent_original_name.extension
```

Private correspondent keywords are not packaged. The installer creates and
preserves an external UTF-8 BOM file only when it is missing:

```text
%LOCALAPPDATA%\ReNamerDocumentClassifier\config\correspondent.txt
```

Only entries from this file can be emitted. `에아스텍` and `ERSTEQ` are always
excluded as self-company names. The former `config.py` responsibilities are
split into `names_config.py`, `correspondent_config.py`, and shared
`runtime_paths.py`.

The 7.3 script compiled successfully inside the actual ReNamer rule editor.
Runtime previews verified both document-text and image-filename matching:

```text
01.거래명세서_260716_곽신우_<registered-pdf-vendor>_SAuthor20371.pdf
03.물품사진_260724_곽신우_<registered-image-vendor>_Container....jpg
```

With only the self-company name registered, the installed classifier returned
an empty `CORRESPONDENT=` and ReNamer omitted the segment. A silent upgrade
also preserved a sentinel correspondent file byte-for-byte. Tests passed
(`19 passed`), PyInstaller and NSIS succeeded, and final hashes matched:

```text
build classifier.exe:       9720A2657583396A420838723595167E29657CCCC6385422274C86BF56095CBA
installed classifier.exe:   9720A2657583396A420838723595167E29657CCCC6385422274C86BF56095CBA
repository 7.3 script:       5290D141549F2F50531F8C37357D8F00FF814601E0A5531AB094146AA86CEB9C
installed 7.3 script:        5290D141549F2F50531F8C37357D8F00FF814601E0A5531AB094146AA86CEB9C
```

## Repository and scope

## Uncommitted adaptive parallel OCR work (awaiting ReNamer validation)

The former sequential early-exit pipeline is being replaced without changing
the installer version. The intended runtime is:

1. render the first pages once at 300 DPI grayscale;
2. run Tesseract PSM 3/6/11 and PaddleOCR against the same images;
3. arbitrate independent classifications deterministically;
4. render at 400 DPI grayscale and run PSM 3/11 only when the 300 DPI arbiter
   still returns `UNKNOWN`.

`config\ocr_scheduler.ini` contains the `[ocr.scheduler]` resource budget.
Cross-process lock pools separately limit documents, Tesseract CPU processes,
and the PaddleOCR auxiliary lane. The current PaddleOCR ONNX distribution is
still CPU-backed, so it holds both an auxiliary slot and one CPU slot and runs
with one internal CPU thread. `gpu_workers` names the separately budgeted
auxiliary-engine lane and setting it to zero disables PaddleOCR. Other OCR engines and layout
analyzers are extension points only and are not reported as active engines.

Scheduler profile version 2 stores each tunable as `auto` by default. Runtime
resolution uses about 80% of logical processors, 25% of physical RAM, and a
CPU/memory-constrained document limit of at most four. Individual numeric
values remain manual overrides. Legacy numeric files are migrated per key:
values equal to the old generated defaults become `auto`, while changed values
remain numeric. The original is retained once as
`ocr_scheduler.ini.legacy-default.bak`.

This work must remain uncommitted and at version 7.4.1 until the user builds,
installs, and verifies it in actual ReNamer with multiple PDFs.

- Repository: `kwaksinwoo01/Vibe_Coding_Support_Tool`
- Branch policy: work directly on `main`; do not create a feature branch.
- Project scope: `renamer_setup/`
- Local build: Python 3.14.6, PyInstaller, NSIS
- Installed root: `%LOCALAPPDATA%\ReNamerDocumentClassifier`
- ReNamer script: `%USERPROFILE%\Documents\den4b\ReNamer\Scripts\7.4_자동이름 변경 시스템.pas`

## Confirmed working behavior

The installed classifier succeeds from PowerShell against a real PDF:

```text
STATUS=OK
KIND=TRANSACTION
PERSON=곽신우
QUOTE_SCORE=0
TRANSACTION_SCORE=100
REASON=transaction_title
METHODS=pdftotext | pdftoppm | tesseract
```

Dependency health also succeeds:

```text
STATUS=OK
PDFTOTEXT=<installed Poppler pdftotext.exe>
PDFTOPPM=<installed Poppler pdftoppm.exe>
TESSERACT=<installed tesseract.exe>
LIBREOFFICE=missing
```

LibreOffice being missing is not the cause for the tested PDFs.

## Confirmed failing behavior

In ReNamer, PascalScript successfully prepares an ASCII temporary copy and starts the classifier, but every tested PDF fails identically:

```text
PREVIEW_START ...
TEMP_COPY_OK ... destination=%LOCALAPPDATA%\ReNamerDocumentClassifier\temp\input_N.pdf
CLASSIFIER_START ...
CLASSIFIER_EXIT code=1 output=STATUS=ERROR
ERROR=OSError:[WinError 6] 핸들이 잘못되었습니다
PREVIEW_UNCHANGED reason=classification_failed ...
```

This repeats across multiple unrelated PDFs. `classification.log` is not created in the failing path.

The latest user-provided runtime log is available locally outside the repository as `pascal_bridge.log`; inspect the installed logs directly:

```powershell
$Root = "$env:LOCALAPPDATA\ReNamerDocumentClassifier"
Get-Content "$Root\logs\pascal_bridge.log" -Encoding UTF8 -Tail 300
Get-Content "$Root\logs\classifier_error.log" -Encoding UTF8 -Tail 300 -ErrorAction SilentlyContinue
Get-Content "$Root\logs\classification.log" -Encoding UTF8 -Tail 300 -ErrorAction SilentlyContinue
```

## Current implementation areas

Inspect these files first:

```text
renamer_setup/launcher.py
renamer_setup/src/renamer_document_classifier/cli.py
renamer_setup/src/renamer_document_classifier/service.py
renamer_setup/src/renamer_document_classifier/extractors.py
renamer_setup/src/renamer_document_classifier/logging_utils.py
renamer_setup/src/renamer_document_classifier/correspondent_sync.py
renamer_setup/renamer/7.4_자동이름 변경 시스템.pas
renamer_setup/installer/ReNamer_Setup.nsi
renamer_setup/assets/classifier_ico_pack.ico
renamer_setup/assets/correspondents_ico_pack.ico
renamer_setup/scripts/build.ps1
renamer_setup/classifier.spec
```

## Previous attempted fixes that did not solve the ReNamer runtime failure

Review these commits and do not assume their diagnoses were correct:

```text
2d41bf9 Provide a valid stdin handle for ReNamer classifier launches
f791cc9 Force valid stdin for ReNamer child processes
af494c8 Run ReNamer child tools with isolated Windows handles
0f29b2a Bump ReNamer installer to 7.2.4
59aeab5 Do not fail classification when log writing fails
ee62c7f Write full classifier tracebacks for ReNamer failures
```

The previous work tried:

1. replacing the process standard input handle with Windows `NUL`;
2. adding `stdin=subprocess.DEVNULL` to child processes;
3. monkey-patching `subprocess.run`;
4. launching Poppler/Tesseract with `CreateProcessW` and explicit standard handles;
5. ignoring optional classification-log write failures;
6. writing a full `classifier_error.log` traceback.

Despite these changes, ReNamer still reports the same generic `WinError 6`.

These changes may be incomplete, may not be present in the installed binary, or may be targeting the wrong call. Verify rather than extending them blindly.

## Mandatory first actions

### 1. Verify source, build output, and installed binary are identical

Run from the repository root:

```powershell
git status --short
git rev-parse HEAD
git log -12 --oneline

Get-FileHash .\renamer_setup\dist\classifier\classifier.exe -Algorithm SHA256
Get-FileHash "$env:LOCALAPPDATA\ReNamerDocumentClassifier\classifier\classifier.exe" -Algorithm SHA256
```

If the hashes differ, solve the stale-binary/install problem before debugging runtime behavior.

Also verify installer version and installation location:

```powershell
Get-ItemProperty `
  "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\ReNamerDocumentClassifier" |
  Format-List DisplayName, DisplayVersion, InstallLocation
```

### 2. Confirm the installed binary still works directly

Use one of the same PDFs that fails in ReNamer:

```powershell
$Classifier = "$env:LOCALAPPDATA\ReNamerDocumentClassifier\classifier\classifier.exe"
$Pdf = '<select an actual failing PDF locally>'

& $Classifier health
& $Classifier inspect --input $Pdf --original-name ([IO.Path]::GetFileName($Pdf))
```

Record exit code and output:

```powershell
$LASTEXITCODE
```

### 3. Obtain the exact traceback

Before another functional change, ensure the failing ReNamer invocation writes a complete traceback to:

```text
%LOCALAPPDATA%\ReNamerDocumentClassifier\logs\classifier_error.log
```

If it does not, add an earliest-possible file-only diagnostic boundary in `launcher.py` that does not depend on stdout/stderr. Record stages before and after:

```text
launcher_start
stdin_setup_start / complete
subprocess_guard_start / complete
cli_import_start / complete
cli_main_start
argparse_complete
inspect_start
path_resolve_complete
primary_extract_start / complete
ocr_start / complete
person_resolve_complete
classification_log_start / complete
cli_return
```

On every exception, write `traceback.format_exc()` to a local UTF-8 file. Do not rely only on text returned through ReNamer `ExecConsoleApp`.

### 4. Build a minimal ReNamer-host reproduction

Determine whether the failure is caused by:

- launching any PyInstaller console executable through `ExecConsoleApp`;
- Python startup/stream reconfiguration;
- opening/duplicating Windows handles;
- starting any child process;
- Poppler specifically;
- Tesseract specifically;
- logging/file I/O after classification;
- the current PascalScript command-line encoding or capture implementation.

Create the smallest temporary diagnostic executable or classifier subcommand needed, for example:

```text
classifier.exe diagnose-host
```

It should perform one step at a time and write results to a file:

1. write a file;
2. inspect `GetStdHandle` values and validity;
3. run a no-op child process;
4. run `cmd.exe /d /c exit 0`;
5. run `pdftotext -v`;
6. run `tesseract --version`;
7. capture output without using inherited handles.

Invoke that command from the actual ReNamer PascalScript environment.

### 5. Use Windows runtime evidence

Use Sysinternals Process Monitor if needed. Suggested filters:

```text
Process Name is classifier.exe
Process Name is pdftotext.exe
Process Name is pdftoppm.exe
Process Name is tesseract.exe
Result contains INVALID
Result contains DENIED
Operation is Process Create
Operation is CreateFile
```

Also inspect parent/child process creation, command lines, exit codes, and whether the expected child process is ever created.

If `WinError 6` occurs before a child process exists, the cause is inside the classifier host/bootstrap path, not Poppler/Tesseract.

## Important hypotheses to test, not assume

- The installed executable may not contain the latest `launcher.py` despite installer version changes.
- The exception may occur in the custom `CreateProcessW` wrapper itself, such as handle inheritance setup or cleanup.
- `sys.stdout`/`sys.stderr` stream reconfiguration may behave differently under ReNamer.
- `ExecConsoleApp` may supply a valid capture output but an invalid stderr/stdin combination.
- A file/logging operation may throw after successful extraction.
- Monkey-patching all `subprocess.run` calls may affect libraries unexpectedly.
- The safest architecture may be avoiding console capture entirely: launch a worker with no inherited handles, write a result file, wait for completion, then let PascalScript read that file.

The final design may replace `ExecConsoleApp` output capture with a request/result-file protocol if that is the most robust verified solution.

## Architectural fallback worth evaluating

If ReNamer's console host is fundamentally incompatible with the PyInstaller process chain, implement a file-based bridge:

1. PascalScript writes a request file or invokes a tiny launcher with only ASCII paths.
2. Launcher starts the classifier/worker detached with explicit valid handles.
3. Worker writes an atomic UTF-8 result file containing status, kind, person, diagnostics, and exit state.
4. PascalScript waits with a bounded timeout and reads the result file.
5. No Python stdout/stderr capture is required.

Do not select this fallback without first proving where the current failure occurs.

## Build and test commands

Use the existing deterministic build command:

```powershell
cd .\renamer_setup
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\build.ps1 `
  -PythonPath "C:\Program Files\Python314\python.exe"
```

Before a clean build:

```powershell
Remove-Item .\build -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item .\dist\classifier -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item .\dist\ReNamer_Setup_7.4.1.exe -Force -ErrorAction SilentlyContinue
```

The pytest temporary cleanup warning under an ESTsoft public temp directory is not the runtime failure. Tests have reported success before that cleanup warning.

The NSIS warning below is non-fatal for this local machine, but remains a packaging concern:

```text
7010: File: "..\vendor\tools\*.*" -> no files found
```

## Acceptance criteria

All items are required:

1. The exact API/function and source line causing `WinError 6` are documented with traceback or equivalent runtime evidence.
2. Installed classifier hash matches the newly built classifier hash.
3. Direct PowerShell `inspect` still returns `STATUS=OK`.
4. ReNamer preview is tested with at least four PDFs, including documents whose original names do not contain `견적` or `거래명세`.
5. `pascal_bridge.log` records:

```text
CLASSIFIER_EXIT code=0
STATUS=OK
KIND=QUOTE
```

or:

```text
CLASSIFIER_EXIT code=0
STATUS=OK
KIND=TRANSACTION
```

6. ReNamer's new-name preview is visibly populated with the expected prefix.
7. `classification.log` is created, or its absence is intentionally explained by a verified replacement logging design.
8. Unit tests pass.
9. PyInstaller and NSIS builds succeed.
10. Clean reinstall is tested and does not use stale binaries or stale PascalScript content.
11. No unrelated repository files are changed.

## Commit policy

- Work directly on `main` as requested by the user.
- Keep local changes uncommitted while investigating.
- Commit only after the ReNamer runtime acceptance criteria pass.
- Use a commit message that states the proven root cause, not merely the symptom.

## Required final report to the user

Return:

1. proven root cause;
2. exact evidence and failing source line/API;
3. files changed;
4. failed prior assumptions/workarounds removed or retained;
5. direct CLI test output;
6. ReNamer runtime test output for all tested PDFs;
7. build/install verification including hashes;
8. final commit SHA.

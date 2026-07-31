# Word Normal Style Editor architecture

## Goal

`word_editor/` replaces one-way PowerShell rebuild scripts with a stateful Windows desktop application. It reads every style in the user's current `Normal.dotm`, edits selected properties through Word COM, detects external changes, validates the resulting template, and performs property-level three-way merges with Word documents or templates.

## Safety model

1. The current `Normal.dotm` is the source of truth; unknown styles are preserved.
2. Every write uses the last loaded snapshot SHA and the expected old property value. If Word changed the same data in the meantime, the write is rejected and the user must refresh or merge.
3. Word creates a timestamped `.dotm` backup before a property patch is saved.
4. Validation runs after every write. Error-level validation restores the previous backup.
5. Style injection uses Word `OrganizerCopy` for selected styles. Full document refresh uses a temporary Normal template attachment plus `Document.UpdateStyles`.
6. The application never silently chooses one side of a conflict. Conflicting properties are shown as baseline / current Normal.dotm / document values.

## Modules

- `domain/models.py`: snapshots, styles, patch operations, conflicts, validation issues.
- `domain/diff.py`: Git-like property-level three-way merge.
- `domain/validation.py`: independent validators for references, ranges, list bindings, and snapshot integrity.
- `infrastructure/word_com.py`: attach-or-create Word session, read all styles, transactional property editing, style injection, document update, backup and restore.
- `infrastructure/file_watcher.py`: debounced monitoring of the user's Normal.dotm.
- `infrastructure/snapshot_store.py`: atomic UTF-8 JSON baseline and export storage.
- `services/editor_service.py`: use-case orchestration and optimistic concurrency.
- `ui/main_window.py`: all-style browser, live property editor, validation panel, and conflict merge panel.

## Live synchronization

The UI edits the loaded style and, when automatic application is enabled, submits the changed properties after an 800 ms debounce. The Word gateway attaches to an already running Word instance when possible; otherwise it opens a hidden instance. External saves to `Normal.dotm` trigger the file watcher and refresh the UI.

Word does not expose every in-memory style change as a filesystem event before the template is saved. Therefore “live” means immediate program-to-Word application and immediate refresh after Word saves the template. The optimistic concurrency check protects edits made in Word between UI refresh and apply.

## Three-way merge

- **Baseline**: the last state explicitly accepted by Word Editor.
- **Normal**: the current local `Normal.dotm`.
- **Document**: the selected `.docx`, `.docm`, `.dotx`, or `.dotm`.

For each style property:

- Normal equals document: keep it.
- Normal equals baseline: use document.
- Document equals baseline: keep Normal.
- Both changed differently: show a conflict and require a user choice.

New style creation and style deletion are shown by the merge model but are intentionally not applied automatically in the first MVP. This prevents accidental loss of built-in or manually created styles.

## Install and run

```powershell
cd word_editor
Set-ExecutionPolicy -Scope Process Bypass -Force
.\run_word_editor.ps1 -Install
```

Subsequent runs:

```powershell
.\run_word_editor.ps1
```

Requirements: Windows, desktop Microsoft Word, Python 3.11+, and a user account permitted to modify its Word template directory.

## Initial validation

```powershell
cd word_editor
.\.venv\Scripts\python.exe -m pytest
```

The unit tests do not require Word and cover the property-level merge and modular validators. COM integration must additionally be tested on the target Windows PC with Word closed, Word open, a modified `Normal.dotm`, and a conflicting document style.

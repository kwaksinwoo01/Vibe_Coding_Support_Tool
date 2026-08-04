# Word Style Editor architecture

## Goal

`word_editor/` replaces one-way PowerShell rebuild scripts with a stateful Windows desktop application. It can read and edit every style in the user's `Normal.dotm` or another selected `.docx`, `.docm`, `.dotx`, or `.dotm`, detects external changes, validates writes, and performs property-level three-way merges with another Word document or template.

## Safety model

1. The selected Word file is the source of truth; unknown styles are preserved.
2. Every write uses the last loaded snapshot SHA and the expected old property value. If Word changed the same data in the meantime, the write is rejected and the user must refresh or merge.
3. Word creates a timestamped backup of the selected file before a property patch is saved.
4. Validation runs after every write. Error-level validation restores the previous backup.
5. The property compatibility policy is enforced in both the UI and the service/COM layers. A disabled cell cannot be bypassed by another caller.
6. New property creation, property deletion, style creation, and style deletion are not exposed as direct editing operations.
7. Style injection uses Word `OrganizerCopy`. The source is the current editing target, not always `Normal.dotm`.
8. The application never silently chooses one side of a conflict. Conflicting properties are shown as baseline / current target / comparison document values.

## Editable targets

The user can switch the current editing target between:

- the user's `Normal.dotm`
- `.dotm` and `.dotx` templates
- `.docm` and `.docx` documents

Each target has an independent baseline JSON keyed by its resolved path. This prevents a `Normal.dotm` baseline from being used in a three-way merge for another document.

The file watcher follows the current target. External saves refresh the UI after the configured debounce interval.

## Style identity

Every style snapshot stores:

- `local_name`: the name displayed by the current Word language
- `original_name`: Word's non-localized/internal name when exposed by COM; otherwise the local name fallback
- `built_in_id`: Word's built-in style identifier when exposed by COM
- style type, built-in flag, and in-use flag

Identity fields are read-only metadata. Style renaming is not part of the property patch mechanism.

## Property compatibility policy

The application keeps all captured properties visible, but only compatible properties are editable.

- Font properties are editable for styles that expose them.
- Paragraph properties are editable only for paragraph, paragraph-only, and linked styles.
- `next_style`, automatic update, and same-style paragraph spacing are limited to paragraph-family styles.
- Built-in style inheritance and next-style structure are locked.
- Unknown, unsupported, list-binding, and metadata properties are read-only.

The policy lives in `domain/property_policy.py` and is rechecked before every COM write.

## Multi-style editing

The style list supports extended selection.

1. The property panel calculates the intersection of property names present in every selected style.
2. A property is editable only when the compatibility policy allows it for every selected style.
3. Equal values are shown normally.
4. Different values are shown as a mixed value.
5. Only mixed/common properties for which the user enters a replacement are patched across all selected styles.
6. Automatic 800 ms apply is limited to one selected style. Multi-style changes require the explicit batch-apply button.

## Modules

- `domain/models.py`: snapshots, local/original style identity, patch operations, conflicts, validation issues.
- `domain/diff.py`: Git-like property-level three-way merge.
- `domain/property_policy.py`: safe/editable property matrix and common-property intersection.
- `domain/validation.py`: independent validators for references, ranges, list bindings, and snapshot integrity.
- `infrastructure/word_com.py`: base Word object-model operations.
- `infrastructure/editable_word_com.py`: general Word target opening, per-file backups, target writes, and style injection.
- `infrastructure/robust_word_com.py`: architecture-aware COM startup and diagnostics.
- `infrastructure/file_watcher.py`: debounced monitoring of the current editing target.
- `infrastructure/snapshot_store.py`: atomic UTF-8 JSON baseline and export storage.
- `services/editor_service.py`: target selection, file-specific baselines, batch patches, validation, and optimistic concurrency.
- `ui/main_window.py`: target selector, all-style browser, safe property editor, multi-select batch editor, validation panel, and conflict merge panel.

## Live synchronization

For a single selected style, the UI can submit changed properties after an 800 ms debounce. Multi-style edits require an explicit apply action. The Word gateway attaches to an already running Word instance when possible; otherwise it opens a hidden instance. External saves to the selected file trigger the watcher and refresh the UI.

Word does not expose every in-memory style change as a filesystem event before the document or template is saved. Therefore “live” means immediate program-to-Word application and immediate refresh after Word saves the selected file. The optimistic concurrency check protects edits made in Word between UI refresh and apply.

## Three-way merge

- **Baseline**: the last state accepted for the current target file.
- **Current target**: the currently selected `.docx/.docm/.dotx/.dotm`.
- **Comparison document**: another selected Word file.

For each style property:

- current target equals comparison document: keep it.
- current target equals baseline: use the comparison document.
- comparison document equals baseline: keep the current target.
- both changed differently: show a conflict and require a user choice.

New style creation and style deletion are shown by the merge model but are intentionally not applied automatically. This prevents accidental loss of built-in or manually created styles.

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

Requirements: Windows, desktop Microsoft Word, Python 3.10+, and access to modify the selected Word file.

## Validation

```powershell
cd word_editor
.\.venv\Scripts\python.exe -m pytest
```

Pure tests cover property-level merge, modular validators, property compatibility, common-property intersection, and snapshot name-metadata compatibility. COM integration must additionally be tested on the target Windows PC with Word closed, Word open, `Normal.dotm`, another template, a document target, and a conflicting document style.

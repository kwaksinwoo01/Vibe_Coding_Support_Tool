# Word Editor SDK architecture

## Objective

The application is no longer a single `Normal.dotm` inspection script. It is a modular company Word asset manager with separate SDK boundaries for routine editing, destructive operations, comparison, template lifecycle, and header/footer assets.

## Runtime paths

### Fast routine path

Used for normal application startup, selecting a style, and editing style properties.

```text
file fingerprint
→ disk snapshot cache
→ fast style index if cache miss
→ selected-style detail load
→ targeted property write
→ Word Save
→ post-save read-back verification
```

The fast style index reads only:

- local/original style name;
- style type;
- built-in and in-use flags;
- priority;
- hidden state;
- Quick Style state.

All other properties are loaded only for selected styles.

### Fast document comparison

```text
word/styles.xml from both files
→ per-style XML fingerprints
→ changed/added/removed candidate names
→ Word COM detail reads for candidates only
→ merge plan
```

If a file does not expose a usable Open XML package or Word cannot resolve a candidate style name, the application falls back to the full COM comparison.

### Full audit path

A full style and list-template scan remains available for:

- explicit snapshot export;
- safe style deletion reference audit;
- approved template version archival when a complete audit record is required;
- fallback comparison.

These operations can be slower by design and must not be used for routine screen refreshes.

## SDK boundaries

### Style SDK

Files:

- `domain/style_mutation.py`
- `infrastructure/word_style_sdk.py`
- `infrastructure/safe_backup_style_gateway.py`
- `infrastructure/verified_style_gateway.py`
- `ui/style_management_window.py`

Responsibilities:

- fast style indexing;
- selected-style detail reads;
- property patches;
- style creation and duplication;
- guarded style deletion;
- context-menu actions;
- pre-write backup;
- post-save read-back verification;
- automatic property rollback when verification fails.

Built-in styles, the default paragraph style, and custom styles referenced by another style cannot be deleted.

### Word session SDK

Files:

- `infrastructure/production_word_gateway.py`
- `infrastructure/robust_word_com.py`

Responsibilities:

- COM registration diagnostics;
- one reusable hidden Word application on the UI thread;
- isolated short-lived COM apartments only when a non-UI worker is unavoidable;
- shutdown of only the Word process owned by the application.

Style writes run on the owner UI thread to prevent a second Word instance from competing for the same `Normal.dotm` lock.

### Cache SDK

File:

- `infrastructure/snapshot_cache.py`

Responsibilities:

- persistent index and full-snapshot caches;
- resolved-path identity;
- file-size and nanosecond modification-time invalidation;
- explicit invalidation after edits, style injection, or header/footer application.

The cache is never authoritative after the source file changes.

### Open XML comparison SDK

Files:

- `infrastructure/openxml_style_index.py`
- `services/fast_style_compare.py`

Responsibilities:

- inspect `word/styles.xml` without starting Word;
- identify only changed, added, or removed style candidates;
- preserve added style definitions in the merge plan;
- create incoming custom styles before applying their editable properties.

Removed styles are not automatically deleted by a merge. Destructive deletion remains a user-confirmed Style SDK action.

### Header/Footer SDK

Files:

- `infrastructure/header_footer_sdk.py`
- `services/header_footer_review.py`
- `ui/header_footer_management_window.py`

Responsibilities:

- register `.dotm` or `.dotx` header/footer layout templates;
- inventory actual header/footer entries by section and variant;
- record text fingerprints and object counts without exporting the text itself;
- compare added, removed, or changed entries;
- apply headers, footers, or both to a target document;
- map matching sections or repeat the source first section;
- back up the complete target file before application.

The SDK does not require Word's built-in default headers or footers. Missing default entries are valid and produce no validation error. Only actual company asset entries are inventoried.

`Range.FormattedText` is used for formatted content, fields, tables, and inline objects. Floating-shape fidelity must be verified against real company templates in desktop Word; the complete source template is retained as the authoritative preservation unit.

### Template lifecycle SDK

Files:

- `domain/template_lifecycle.py`
- `services/company_template_lifecycle_service.py`
- `services/template_lifecycle_service.py`
- `infrastructure/template_inventory.py`

Responsibilities:

- DCM and FDM profile registration and activation;
- approved whole-file template versions;
- Building Block, AutoText, style, header, and footer inventories;
- registered template asset versions;
- distribution packages and audit records.

A profile change review uses Open XML style candidates and a single Word open for the remaining inventory. Full scans are reserved for approved archival or fallback.

### Validation SDK

Files:

- `domain/validation.py`
- `domain/property_policy.py`
- `domain/style_mutation.py`

Responsibilities:

- property ranges;
- style references;
- list bindings;
- snapshot integrity;
- editable-property compatibility;
- deletion blockers;
- post-save value equality.

Validation does not invent requirements for Word's default header or footer galleries.

## Expected performance behavior

- First run after a file change: Word starts once and reads the fast index.
- Reopening an unchanged file: disk cache can populate the list without opening the file through Word.
- Selecting a style: only selected style definitions are read.
- Applying changes: only selected styles are read, written, and verified.
- Comparing documents: Open XML identifies candidates before Word COM reads details.
- Full export and deletion reference audit: intentionally slower complete operations.

Actual duration depends on Office startup time, security software, template size, network-linked resources, add-ins, and the number of changed styles.

## Required desktop integration tests

1. Start with Word closed and measure first index load.
2. Restart the editor without changing `Normal.dotm` and confirm a cache hit.
3. Edit one custom style and confirm post-save verification metadata.
4. Create and duplicate a paragraph style.
5. Attempt to delete a built-in and a referenced custom style; both must be blocked.
6. Delete an unreferenced custom style and confirm it is absent after reopening Word.
7. Compare two documents with one changed style and confirm only the candidate is read.
8. Register a company header/footer template that has no Word default header/footer.
9. Apply primary, first-page, and even-page content to a copied test document.
10. Confirm tables, fields, inline objects, and floating shapes against the source.
11. Switch DCM/FDM profiles while the editor-owned hidden Word is active.
12. Confirm a real user-open Word window still blocks profile replacement.

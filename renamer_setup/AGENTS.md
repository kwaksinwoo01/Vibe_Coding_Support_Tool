# Local Codex instructions — renamer_setup

Before changing code, read `CODEX_HANDOFF_RENAMER_WINERROR6.md` completely.

## Scope

- Work only inside `renamer_setup/` unless a repository-level build file must be adjusted.
- Do not modify unrelated projects in this repository.
- The user requires work on `main`; do not create a feature branch.
- Do not commit until the failure has been reproduced in ReNamer and the fix has been validated in ReNamer.

## Required method

- Reproduce the problem in the actual local Windows + ReNamer environment. A successful direct PowerShell invocation of `classifier.exe` is not sufficient.
- Inspect the complete traceback and identify the exact Python/Windows API call that raises `OSError: [WinError 6]` before proposing another fix.
- Verify that the installed binary is byte-for-byte the binary produced from the current working tree.
- Prefer evidence from runtime logs, hashes, Process Monitor, and minimal reproductions over assumptions.
- Stop incrementing installer versions for speculative changes. Bump the version only after a runtime-verified fix.
- Failed stdin/handle workarounds may be reverted or simplified when the true cause is established.

## Completion gate

Do not report completion until all acceptance criteria in the handoff document pass, including ReNamer preview producing a changed filename and `CLASSIFIER_EXIT code=0`.

# ReNamer project agent instructions

This file is the normative development-policy entry point for the ReNamer project in this repository.

Before changing ReNamer code or ReNamer SDK tooling:

1. Read this file completely.
2. Read `renamer_setup/MEMORY.md` completely for the current approved architecture, completed gates, active session, and next work.
3. Read task-specific handoff documents only when the task actually concerns that historical issue. In particular, read `renamer_setup/CODEX_HANDOFF_RENAMER_WINERROR6.md` when investigating or changing the WinError 6 / ReNamer process-handle path.

## Project scope

The ReNamer project owns these paths for the approved SDK work:

- `renamer_setup/`
- `tools/sdk-packages/renamer_sdk/`

The ReNamer project does not own `tools/sdk-packages/word_editor_sdk/`. Do not create, modify, reorganize, or define implementation policy for that project from a ReNamer session.

Do not modify unrelated projects in this repository. Repository-level files may be changed only when they are genuinely required by the ReNamer build, test, packaging, or integration path.

The active development branch is `main` unless the user explicitly changes that policy.

## Persistent documentation contract

`AGENTS.md` and `MEMORY.md` have different responsibilities.

### `AGENTS.md`

This file stores durable normative rules:

- project ownership and scope;
- SDK responsibility boundaries;
- dependency-direction rules;
- development gates;
- required validation method;
- documentation update requirements.

Do not use this file as a chronological work log.

### `MEMORY.md`

`renamer_setup/MEMORY.md` stores project-local durable working state:

- approved architecture decisions;
- completed implementation milestones;
- latest validated scenario counts;
- current gate/session status;
- known unresolved risks;
- next approved work;
- relevant commit SHAs when they help identify the validated baseline.

At the end of a meaningful ReNamer SDK or migration session, update `MEMORY.md` so a different environment or agent can resume without relying on chat history.

## SDK architecture policy

The development SDK lives at:

`tools/sdk-packages/renamer_sdk/`

Its approved top-level responsibility boundaries are:

- `core_sdk/`
- `build_sdk/`
- `test_sdk/`
- `sdk_suite/`
- `observability_sdk/`
- `validation_sdk/`
- `model_sdk/`
- `integration_sdk/`
- `migration_sdk/`
- `domain_sdk/`

Do not collapse these responsibilities into `core_sdk`.

### `core_sdk`

`core_sdk` owns only common execution principles and minimal foundation contracts such as operation results, execution context, lifecycle/status concepts, errors, and cross-SDK protocols.

`core_sdk` must not own:

- ReNamer business rules;
- name migration rules;
- release or deployment flow;
- build flow;
- test scenarios;
- installer behavior;
- filesystem or process integration policy.

### Responsibility ownership

- `model_sdk`: structured ReNamer SDK data/state models; no business execution.
- `domain_sdk`: pure ReNamer business rules and identity/normalization semantics; no filesystem or process I/O.
- `migration_sdk`: version-to-version state transition and migration planning; prefer pure computation.
- `validation_sdk`: input, plan, state, output, and contract validation; it must not perform the mutation it validates.
- `integration_sdk`: filesystem, process, OS, installer-facing, and repository/environment adapters; it must not decide domain policy.
- `observability_sdk`: events, diagnostics, counts, modes, reasons, and execution tracing; it must not decide success policy.
- `build_sdk`: ReNamer build/release consistency and artifact validation.
- `test_sdk`: independent oracle, scenario matrix, fixtures, and test harness. The oracle must not merely call the migration implementation it is validating.
- `sdk_suite`: toolchain/composition/orchestration only. It coordinates SDKs but does not contain ReNamer business algorithms.

## Dependency direction

Keep lower-level SDKs independent from higher-level orchestration and environment concerns.

Forbidden examples:

- `core_sdk -> migration_sdk`
- `core_sdk -> integration_sdk`
- `domain_sdk -> integration_sdk`
- product runtime code -> `tools/sdk-packages/renamer_sdk`

Development tooling may inspect or invoke later product SDK implementations for comparison, but product code must never depend on repository development tooling.

## Product SDK policy

The approved future product SDK location is:

`renamer_setup/sdk_packages/renamer_sdk/`

The product SDK will contain runtime responsibilities only. Development-only `build_sdk` and `test_sdk` do not belong in the packaged product SDK.

Do not implement or connect the product SDK until the development-SDK gate recorded in `MEMORY.md` is satisfied.

## Known-name migration policy B

The approved update semantics are:

- preserve the user's `DefaultName`; migration must not automatically change it;
- preserve user-added known names;
- preserve explicit user deletion of previously managed defaults;
- add newly introduced packaged defaults unless suppressed by a user-deletion tombstone;
- a user manually restoring a tombstoned name clears that tombstone;
- repeated execution for the same state/version must be idempotent;
- corrupted or unverifiable state must use a non-destructive fallback and must not cause user-data loss.

The development SDK oracle and validation contracts define the expected behavior before product implementation is allowed to proceed.

## Approved staged development gates

### Session 1 — strengthen development SDK edge cases

Extend `tools/sdk-packages/renamer_sdk` with legacy/no-state, corrupt-state, corrupt-snapshot, release-removal, normalization, `DefaultName` overlap, empty-input, and repeated-migration scenarios plus stronger validation/observability contracts.

### Session 2 — validate SDK architecture itself

Verify imports, absence of forbidden dependency directions/cycles, oracle independence, deterministic output, and complete scenario success.

### Gate 1

Do not create the product migration implementation until Sessions 1 and 2 pass and `MEMORY.md` records Gate 1 as passed.

### Session 3 — create product SDK

Create `renamer_setup/sdk_packages/renamer_sdk/` with runtime-only SDK boundaries.

### Session 4 — development oracle versus product SDK

Run the same scenarios against the independent development oracle and the product SDK. Expected and actual results must agree.

### Gate 2

Do not connect the installer/runtime update path until the product SDK passes the development oracle comparison and `MEMORY.md` records Gate 2 as passed.

### Session 5 — connect existing application

Only after Gate 2, integrate the product SDK with `names_config.py`, CLI (`sync-known-names`), and `installer/ReNamer_Setup.nsi`, then validate real fresh install, upgrade, reinstall, and user-setting preservation behavior.

## Validation discipline

Prefer deterministic and inspectable validation over speculative edits.

For SDK work, the baseline command is run from repository root with the development SDK on `PYTHONPATH`:

```powershell
$env:PYTHONPATH = (Resolve-Path .\tools\sdk-packages).Path
python -m renamer_sdk.sdk_suite
```

For release/build work, continue to validate encoding, tests, build output, and installer artifacts using the existing ReNamer scripts and gates.

PowerShell 5.1 scripts that are created or modified for this project must use UTF-8 BOM where the project encoding verifier requires it.

## WinError 6 historical gate

When work concerns the historical ReNamer `OSError: [WinError 6]` path, follow `CODEX_HANDOFF_RENAMER_WINERROR6.md` and reproduce/validate in the actual Windows + ReNamer environment. A successful direct PowerShell invocation alone is not sufficient evidence for that issue.

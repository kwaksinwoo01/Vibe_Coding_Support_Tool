# ReNamer project memory

This file is the persistent project-local working state for `renamer_setup` and the ReNamer SDK work owned by this project.

Read `renamer_setup/AGENTS.md` first. `AGENTS.md` is normative policy; this file records approved decisions, validated progress, unresolved items, and the next development gate.

Last updated: 2026-08-07

## Ownership boundary

ReNamer project scope for the current SDK effort:

- `renamer_setup/`
- `tools/sdk-packages/renamer_sdk/`

Explicitly out of scope for this project/session:

- `tools/sdk-packages/word_editor_sdk/`

The Word Editor project owns its own SDK structure and implementation. ReNamer sessions must not create or modify it.

## Current validated baseline

Validated development-SDK baseline before the documentation commits:

- repository branch: `main`
- ReNamer development SDK baseline SHA: `fa7959ca93d27773ee55308cf4fd8866af5b7161`
- baseline command:

```powershell
$env:PYTHONPATH = (Resolve-Path .\tools\sdk-packages).Path
python -m renamer_sdk.sdk_suite
```

User-verified output:

```text
[PASS] 7.4.1-to-7.4.2-adds-new-default
[PASS] preserves-user-addition-and-deletions
[PASS] reinstall-is-idempotent
[PASS] tombstone-blocks-later-reintroduction
[PASS] manual-restore-clears-tombstone
Policy B scenarios: 5 passed, 0 failed
```

Therefore the initial Policy B development-SDK baseline is accepted as **5 passed / 0 failed**.

This does **not** mean Gate 1 is passed. The approved edge-case and SDK-architecture validation sessions still remain.

## Documentation baseline

`renamer_setup/AGENTS.md` was promoted from a WinError-6-specific instruction file into the durable ReNamer project policy entry point.

Policy-document commit:

- `272ebeb17d124a389e1acb67feb589aad556d7ce`

The historical WinError 6 handoff remains task-specific and is only mandatory when that process-handle issue is being investigated or modified.

## Approved development SDK architecture

Development SDK location:

```text
tools/
└─ sdk-packages/
   └─ renamer_sdk/
      ├─ core_sdk/
      ├─ build_sdk/
      ├─ test_sdk/
      ├─ sdk_suite/
      ├─ observability_sdk/
      ├─ validation_sdk/
      ├─ model_sdk/
      ├─ integration_sdk/
      ├─ migration_sdk/
      └─ domain_sdk/
```

Responsibility split is mandatory. `core_sdk` must remain a minimal foundation/execution-contract layer and must not absorb business rules, migration logic, build flow, test scenarios, deployment behavior, or integration policy.

### Approved responsibility summary

- `core_sdk`: common execution contracts and minimal foundation types.
- `model_sdk`: structured ReNamer SDK models and state shapes.
- `domain_sdk`: pure ReNamer business semantics such as name identity and normalization.
- `migration_sdk`: version-to-version migration planning/state transition logic.
- `validation_sdk`: preconditions, plan/state/output invariants; no mutation ownership.
- `integration_sdk`: filesystem/process/OS/repository adapters; no domain-policy ownership.
- `observability_sdk`: diagnostics, events, counts, modes, reasons, execution tracing.
- `build_sdk`: build/release consistency and artifact validation.
- `test_sdk`: independent oracle, fixtures, scenarios, harness; must not simply call the implementation under test.
- `sdk_suite`: Toolchain/Orchestrator/composition only; no business algorithms.

## Approved future product SDK architecture

Future product SDK location:

```text
renamer_setup/
└─ sdk_packages/
   └─ renamer_sdk/
      ├─ core_sdk/
      ├─ sdk_suite/
      ├─ observability_sdk/
      ├─ validation_sdk/
      ├─ model_sdk/
      ├─ integration_sdk/
      ├─ migration_sdk/
      └─ domain_sdk/
```

Development-only `build_sdk` and `test_sdk` are not part of the packaged runtime SDK.

Current status: **not created yet by design**.

Product runtime code must never depend on `tools/sdk-packages/renamer_sdk`.

## Approved KnownNames update policy: Policy B

The migration target is an update-style installer that preserves user settings while applying new managed defaults.

The approved semantics are:

1. `DefaultName` is user-owned and must not be automatically changed by migration.
2. User-added known names are preserved.
3. A user deletion of a previously managed default is preserved.
4. A newly introduced packaged default is automatically added unless a tombstone suppresses it.
5. A tombstone preserves the user's deletion choice even if the packaged name disappears and later reappears in a future release.
6. If the user manually restores a tombstoned name, the tombstone is cleared.
7. Re-running migration against the same effective state is idempotent.
8. Corrupt or unverifiable migration state must not cause destructive removal of local user data.

Example target behavior for the 7.4.1 -> 7.4.2 transition:

```text
previous packaged defaults:
곽신우, 김민규, 이슬기, 정우형, 박승주

local user state:
곽신우, 김민규, 사용자추가이름

incoming packaged defaults:
곽신우, 김민규, 이슬기, 정우형, 박승주, 김예빈

expected result:
곽신우, 김민규, 사용자추가이름, 김예빈
```

The locally removed previous defaults stay removed. The user-added name stays. The newly introduced packaged default is added.

## Current implementation state

Implemented in development tooling:

- all approved top-level development SDK responsibility directories;
- minimal core execution contracts;
- migration input/plan models;
- pure name normalization/identity rules;
- Policy B migration planner;
- migration-plan validation;
- observability event collection;
- repository layout integration helper;
- build/release consistency validation helper;
- independent test oracle and initial scenario matrix;
- SDK suite/orchestrator;
- command entry point `python -m renamer_sdk.sdk_suite`.

Not yet implemented/connected:

- expanded edge-case scenario set;
- corrupt-state/snapshot behavior contract in full;
- Gate 1 architecture validation;
- `renamer_setup/sdk_packages/renamer_sdk` product SDK;
- development-oracle versus product-SDK comparison;
- `sync-known-names` product CLI;
- installer fresh-install/update branching for KnownNames;
- production Policy B state/snapshot persistence.

## Session and gate plan

### Session 1 — strengthen development SDK edge cases

Status: **NEXT**

Work only in `tools/sdk-packages/renamer_sdk` unless a small ReNamer-owned policy/test integration change is required.

Add/verify scenarios approximately covering:

- legacy 7.4.1 first migration with no migration state;
- corrupted state fallback;
- corrupted applied-defaults snapshot fallback;
- packaged default removed by a later release;
- duplicate and whitespace normalization;
- casefold-equivalent names;
- `DefaultName` overlapping a managed known name;
- empty local KnownNames;
- invalid/empty incoming defaults handling;
- repeated migrations remaining deterministic and idempotent.

Strengthen validation contracts for:

- `DefaultName` unchanged;
- user-added names never disappearing;
- user-deleted managed names never reappearing without manual restore;
- incoming new defaults appearing unless tombstoned;
- no normalized duplicates;
- idempotence;
- non-destructive corruption fallback;
- manual restore clearing tombstone;
- defined behavior for release-removed defaults;
- deterministic ordering.

Strengthen observability around mode, release, counts, fallback reason, and validation status without making actual personal names a required production log payload.

Expected completion evidence: expanded SDK suite passes with zero failures and the scenario count/coverage is recorded in this file.

### Session 2 — validate development SDK architecture

Status: **PENDING**

Verify:

- all SDKs import cleanly;
- forbidden dependency directions are absent;
- circular imports are absent;
- `core_sdk` does not depend on business/migration/integration layers;
- `domain_sdk` does not depend on integration/environment layers;
- `test_sdk` oracle is independent from `migration_sdk` implementation;
- `sdk_suite` orchestrates rather than owning business rules;
- deterministic repeat execution;
- all expanded scenarios pass.

### Gate 1 — development SDK approved for product implementation

Status: **NOT PASSED**

Gate 1 passes only after Sessions 1 and 2 complete successfully and this file is updated with the evidence.

Do not implement the product migration SDK before Gate 1.

### Session 3 — create product SDK

Status: **BLOCKED BY GATE 1**

Create runtime-only SDK at `renamer_setup/sdk_packages/renamer_sdk/` using the approved responsibility boundaries.

### Session 4 — compare development oracle with product SDK

Status: **BLOCKED BY SESSION 3**

Run the same scenarios through the independent development oracle and actual product SDK. Expected and actual results must agree.

### Gate 2 — product migration approved for application integration

Status: **NOT PASSED**

Do not connect `names_config.py`, CLI, or NSIS update behavior until Gate 2 is explicitly recorded as passed here.

### Session 5 — integrate application and installer

Status: **BLOCKED BY GATE 2**

Planned integration targets:

- `renamer_setup/src/renamer_document_classifier/names_config.py`
- `renamer_setup/src/renamer_document_classifier/cli.py`
- `renamer_setup/installer/ReNamer_Setup.nsi`

Target installer behavior:

```text
fresh install
→ show user settings page
→ configure DefaultName/KnownNames
→ establish managed-default state

upgrade
→ skip mandatory user-name re-entry
→ preserve DefaultName
→ run sync-known-names
→ merge new packaged defaults according to Policy B
```

## Current release context

Latest release synchronization work completed before SDK architecture work:

- ReNamer version: `7.4.2`
- release-build synchronization commit: `00867ca4d61728d71e53c4775c16ebbdac4da3bc`
- local installer build was reported successful as `renamer_setup/dist/ReNamer_Setup_7.4.2.exe`
- recorded SHA-256 from that build: `1A40D7CC48E2B8B46D4A3959B5C713E1B033DABF727BAF7C3AA12CA1EED7F33A`

That installer predates the future Policy B product/installer integration. Do not treat the existing 7.4.2 installer as proof that update-style KnownNames preservation is implemented.

## MEMORY update protocol

After each meaningful session, update this file before declaring the session complete.

Record at minimum:

- date;
- validated repository SHA or relevant commit SHA;
- session completed;
- tests/scenarios actually executed and their result;
- gate status changes;
- architectural decisions changed or confirmed;
- unresolved risks/failures;
- exact next session.

Do not record an unexecuted test as passed. Do not mark a gate passed from design approval alone.

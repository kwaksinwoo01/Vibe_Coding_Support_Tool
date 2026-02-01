---
name: refactorUiStructure
description: Refactor UI structure and standardize parameter names.
argument-hint: Description of the refactoring task including structural changes and parameter mappings.
---
Refactor the project structure to flatten dependencies and unify parameter naming conventions.

1. Goals:
- Flatten the dependency hierarchy by having the main controller directly manage all sub-modules.
- Remove redundant adapter/wrapper functions and intermediate logging code from bridge components.

- Synchronize parameter names across the entire project for consistency.

2. Structural Changes:
- Current: main_controller -> bridge_component -> [sub_modules]
- Target: main_controller -> [sub_modules, additional_panels]
- Action: Remove the bridge role from the bridge component. Sub-modules should be instantiated or managed directly from the main controller.

3. Parameter Refactoring:
- Identify all renamed parameters and update their names in all dependent files.
- Delete all unnecessary 'adapter functions' or 'transfer functions' created solely for parameter mapping.
- Integrate debugging logs into a single stream via log_panel, removing duplicate logs from main_controller and bridge_component.

4. Implementation Rules:
- For partially changed methods within classes, provide the complete code of the changed methods.
- Replace unchanged method bodies with "#(변경없음)" comments.
- Mark new methods with "#(추가)" comments.
- Remove deleted methods by eliminating their internal code.

Execute the refactoring by flattening the UI dependency graph and unifying parameter names.

Scope:
- Restructure UI control: main controller directly manages sub-modules and panels.
- Remove bridge role from bridge component; instantiate/manage children from main controller.
- Unify parameter names project-wide and delete adapter/transfer functions created only for mapping.
- Centralize logs via log_panel; remove duplicate logging from main_controller/bridge_component.

Target structure (before → after):
- Current: main_controller -> bridge_component -> [sub_modules]
- Goal: main_controller -> [sub_modules, log_panel, upload_panel]
- Break the bridge: bridge_component becomes a pure widget, no orchestration/adapter responsibilities.

Primary files:
- Controller: main_controller.py
- Bridge/Panels/Groups: bridge_component.py, sub_modules
- Add new modules if missing: log_panel.py, upload_panel.py

Parameter standardization:
- Use the following canonical parameter names everywhere:
  - file_model, file_id, file_data, prefix, company_name, rule_id, rename_pattern, target_path, target_filename, consent
- Replace legacy names:
  - naming_pattern → rename_pattern
  - new_filepath → target_path
  - new_filename → target_filename
  - consent_given → consent
  - set_property_data(data) → set_file_data(file_data)

Eliminate adapter/transfer functions:
- Delete functions that exist solely to translate parameter names between modules.
- Update all call sites to use canonical names; do not introduce new wrappers.

Logging unification:
- Route all UI logs and user-action traces through a single log stream handled by log_panel.
- Remove duplicate logger calls from main_controller and bridge_component; use event bus → log_panel.
- Align with event topics; prefer publish/subscribe over direct logging.

Coding rules for changes:
- Only modify what's needed for this refactor; avoid unrelated fixes.
- Keep code style consistent.
- Where methods are edited, provide complete updated method bodies in diffs; unchanged method bodies remain intact. (In commit descriptions, tag additions as "(추가)", removals as "(삭제)" for traceability.)
- Do not add cross-workflow dependencies.

Acceptance criteria:
- main_controller instantiates/manages sub_modules and panels directly.
- bridge_component no longer acts as a bridge; zero adapter/transfer functions remain.
- All referenced modules use the canonical parameter names listed above.
- All logging visible via log_panel single stream; duplicate logs removed.
- No new coupling.
- Tests pass and UI event bus flow remains functional.

Concrete edits to prioritize:
- In main_controller.py:
  - Add factories/initializers for the components; wire event bus subscriptions.
  - Replace calls to bridge bridging APIs with direct references to sub_modules/panels.
  - Swap any legacy naming usage to canonical names.
- In bridge_component.py:
  - Remove orchestration code and adapter/transfer helpers; keep only pure widget concerns.
  - Rename set_property_data → set_file_data and update internal usage.
  - Remove direct logging in favor of event bus emit to log_panel.
- In sub_modules (e.g., group_2_editable.py):
  - Standardize set_file_data(file_data) and internal param names (rename_pattern/target_*).
  - Update signatures to use canonical names.
  - Ensure functions refer to target_path/target_filename.
- Add log_panel.py and upload_panel.py if missing:
  - log_panel: subscribe to log topics, render a single consolidated stream.
  - upload_panel: encapsulate manual upload UI and events; no bridging.

Testing:
- Run tests:
  - python test/run_all_tests.py
  - Or: pytest -q

Artifacts & docs:
- Update task document with change summary.
- Record the parameter mapping table and migration notes.
- Note removed functions and new ownership.

Constraints:
- Strategy pattern and event bus usage must remain intact.
- No cross-workflow coupling.

Please proceed with the refactoring, providing changed files list and summary.

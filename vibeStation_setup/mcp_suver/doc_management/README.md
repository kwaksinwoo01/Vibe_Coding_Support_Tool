# Document Management Modules

**Architecture**: Facade Pattern

This directory contains specialized document management modules that were extracted from the monolithic `DocumentManagementEngine` class to follow the Single Responsibility Principle.

## Structure

```
doc_management/
├── __init__.py                    # Package exports
├── link_manager.py                # Document link management
├── version_manager.py             # Version tracking (N1.N2.N3)
├── checklist_manager.py           # Checklist operations
├── progress_manager.py            # Progress state tracking
├── mapping_manager.py             # Mapping table management (integrates MP tools)
├── error_session_manager.py       # Error tracking and resolution
├── document_modifier.py           # ADMP policy enforcement (migrated from ADMP)
├── document_updater.py            # WPD/PRD updates (migrated from ADMP)
└── template_generator.py          # Template generation (migrated from ADMP)
```

## Design Pattern: Facade

The `DocumentManagementEngine` class in `E_Document_Management.py` acts as a **Facade** that provides a unified interface to these specialized managers. Each manager is responsible for one aspect of document management.

### Benefits

1. **Single Responsibility**: Each manager has one clear purpose
2. **Separation of Concerns**: Functionality is logically grouped
3. **Maintainability**: Changes to one aspect don't affect others
4. **Testability**: Each manager can be tested independently
5. **No Duplication**: Integrates with ADMP and MP tools without reimplementation

## Managers

### 1. LinkManager (`link_manager.py`)

Handles document link validation and fixing.

**Responsibilities**:
- Inspect links in documents (Markdown format)
- Detect broken links
- Automatically fix broken links
- Track cross-references

**Methods**:
- `inspect_document_links(doc_path)` - Returns list of link info dicts
- `fix_broken_links(doc_path, link_list)` - Fix broken links, returns count
- `validate_and_fix_links(doc_path)` - Complete operation

**Usage**:
```python
from doc_management import LinkManager

link_mgr = LinkManager(workspace_root)
result = link_mgr.validate_and_fix_links(Path("docs_2/P1/P1-Feature.md"))
print(f"Fixed {result['links_fixed']} links")
```

---

### 2. VersionManager (`version_manager.py`)

Handles document version tracking following N1.N2.N3 format.

**Responsibilities**:
- Parse and format versions (N1.N2.N3)
- Increment versions at different levels
- Update document versions
- Track parent/child document relationships
- Add version notes to parent documents

**Methods**:
- `parse_version(version_str)` - Parse version to tuple
- `increment_version(old_version, level)` - Increment N1, N2, or N3
- `get_document_version(doc_path)` - Extract version from document
- `set_document_version(doc_path, new_version)` - Update version
- `update_version_for_tier_b(doc_path)` - Tier B context (N3 increment)
- `update_version_for_tier_c(doc_path)` - Tier C context (hierarchical update)
- `get_wpd_grade(doc_path)` - Get document grade (L0-L3)
- `get_parent_documents(doc_path)` - Get parent document list
- `get_child_documents(doc_path)` - Get child document list

**Usage**:
```python
from doc_management import VersionManager

ver_mgr = VersionManager(workspace_root)
result = ver_mgr.update_version_for_tier_b(Path("docs_2/P1/P1-Feature.md"))
print(f"Version updated: {result['old_version']} → {result['new_version']}")
```

---

### 3. ChecklistManager (`checklist_manager.py`)

Handles document checklist operations.

**Responsibilities**:
- Add checklist items
- Delete checklist items
- Mark items as complete/incomplete
- Validate checklist structure

**Methods**:
- `add_item(doc_path, item_description)` - Add new checklist item
- `delete_item(doc_path, item_description)` - Delete item
- `mark_complete(doc_path, item_description)` - Mark as complete
- `mark_incomplete(doc_path, item_description)` - Mark as incomplete
- `manage_item(doc_path, operation, item_description)` - Unified interface

**Usage**:
```python
from doc_management import ChecklistManager

checklist_mgr = ChecklistManager(workspace_root)
result = checklist_mgr.add_item(Path("docs_2/P1/P1-Feature.md"), "Implement feature X")
```

---

### 4. ProgressManager (`progress_manager.py`)

Handles document progress state management.

**Responsibilities**:
- Update progress states (Not Started, In Progress, Completed)
- Validate state transitions
- Track progress across document hierarchy
- Calculate completion percentages

**Methods**:
- `update_progress(doc_path, progress_state)` - Update document progress
- `get_progress(doc_path)` - Get current progress
- `mark_as_started(doc_path)` - Mark as In Progress
- `mark_as_completed(doc_path)` - Mark as Completed
- `mark_as_pending(doc_path)` - Mark as Pending
- `get_hierarchy_progress(doc_paths)` - Get summary for multiple documents

**Valid States**:
- "Not Started"
- "In Progress"
- "Completed"
- "📋 PENDING"
- "🔄 IN PROGRESS"
- "✅ COMPLETE"

**Usage**:
```python
from doc_management import ProgressManager

progress_mgr = ProgressManager(workspace_root)
result = progress_mgr.mark_as_started(Path("docs_2/P1/P1-Feature.md"))
```

---

### 5. MappingManager (`mapping_manager.py`)

Handles mapping table management by integrating with MP tools.

**Responsibilities**:
- Delegate to MP tools ecosystem
- Provide unified interface to MP operations
- Handle 500-line split logic (via mp_splitter.py)
- Validate mappings (via mp_validator.py)

**Integration Points**:
- `.github/agents/tool/mp/mp_reader_agent.py` - Read mappings
- `.github/agents/tool/mp/mp_manager.py` - Comprehensive management
- `.github/agents/tool/mp/mp_splitter.py` - Auto-split oversized files
- `.github/agents/tool/mp/mp_validator.py` - Validate mappings

**Methods**:
- `manage_mapping(current_mapping)` - Main operation (delegates to MP tools)
- `list_mappings()` - List available mapping tables
- `validate_mappings(mapping_file)` - Validate mappings
- `split_oversized_mapping(mapping_file)` - Split if > 500 lines
- `get_cli_commands()` - Get CLI command reference

**Usage**:
```python
from doc_management import MappingManager

mapping_mgr = MappingManager(workspace_root)
result = mapping_mgr.manage_mapping({"data": "mapping content"})

# Get CLI commands
commands = mapping_mgr.get_cli_commands()
print(commands["list_mappings"])
# Output: python .github/agents/tool/mp/mp_reader_agent.py --list
```

**Note**: This manager does NOT reimplement MP functionality - it delegates to the established MP tools to avoid duplication.

---

### 6. ErrorSessionManager (`error_session_manager.py`)

Handles error tracking and resolution workflow.

**Responsibilities**:
- Add error sessions to documents
- Create solution plans
- Route errors to appropriate tiers
- Mark errors as resolved
- Remove resolved errors

**Methods**:
- `add_error_sessions(doc_path, error_list)` - Add errors and create solution plans
- `get_error_sessions(doc_path)` - Extract error list from document
- `resolve_error_session(doc_path, error_description)` - Mark error as resolved
- `remove_error_session(doc_path, error_description)` - Remove error
- `create_solution_plan(error_description, target_doc, route_to_tier)` - Create plan

**Usage**:
```python
from doc_management import ErrorSessionManager

error_mgr = ErrorSessionManager(workspace_root)
result = error_mgr.add_error_sessions(
    Path("docs_2/P1/P1-Feature.md"),
    ["Error: Function X not working", "Error: Missing validation"]
)

# Returns solution plans with next_node="C" for routing to Tier C
print(result["solution_plans"])
```

---

### 7. DocumentModifier (`document_modifier.py`)

Handles safe document modification following ADMP (Agent Document Modification Policy).

**Responsibilities**:
- Enforce ADMP policy rules
- Protect immutable sections (Goal, Success Criteria, Scope)
- Allow modifications to designated sections
- Track modification attempts
- Add timestamps and justifications to modifications

**ADMP Policy**:
- **Immutable Sections**: Goal, Success Criteria, Scope (WPD), Original Success Criteria, Task Definition, Sign-off (PRD)
- **Modifiable Sections**: Implementation Summary, Work Progress, Test Results, Blockers and Workarounds, Agent Update
- **3-Strike Rule**: Track modification attempts for accountability

**Methods**:
- `can_modify(doc_type, section_name, modification_type)` - Check if modification allowed
- `modify_section(doc_path, doc_type, section_name, new_content, ...)` - Safely modify section
- `add_agent_update(doc_path, doc_type, update_content, justification)` - Add to Agent Update section
- `get_modification_history(doc_path)` - Get modification attempt history

**Usage**:
```python
from doc_management import DocumentModifier, ModificationPermissionError

doc_modifier = DocumentModifier(workspace_root)

# Safe modification
result = doc_modifier.add_agent_update(
    Path("docs_2/P1/P1-Feature.md"),
    "WPD",
    "Completed implementation of feature X",
    justification="Task completed successfully"
)

# Check permission before modifying
can_modify = doc_modifier.can_modify("WPD", "Goal", "modify")
# Returns False - Goal is immutable
```

---

### 8. DocumentUpdater (`document_updater.py`)

Handles WPD/PRD document updates with progress tracking.

**Responsibilities**:
- Update checklist item status with symbols
- Add timestamps to completed tasks
- Update implementation summaries
- Track progress systematically
- Batch updates across documents

**Status Symbols**:
- ✅ complete/done
- ❌ failed
- ⏳ in_progress
- 📋 pending
- 🚫 blocked

**Methods**:
- `update_checklist_item(doc_path, item_text, status, add_timestamp)` - Update checklist status
- `add_implementation_note(doc_path, note_content, section)` - Add timestamped note
- `batch_update_checklists(updates)` - Batch update multiple items
- `find_checklist_items(doc_path, section)` - Find all checklist items
- `get_changes()` - Get list of changes made

**Usage**:
```python
from doc_management import DocumentUpdater

doc_updater = DocumentUpdater(workspace_root)

# Update single checklist item
result = doc_updater.update_checklist_item(
    Path("docs_2/P1/P1-Feature.md"),
    "Implement feature X",
    status="complete",
    add_timestamp=True
)

# Add implementation note
result = doc_updater.add_implementation_note(
    Path("docs_2/P1/P1-Feature.md"),
    "Feature X implemented with optimization"
)

# Batch update
updates = [
    {"doc_path": "docs_2/P1/P1-Feature.md", "item_text": "Task 1", "status": "complete"},
    {"doc_path": "docs_2/P1/P1-Feature.md", "item_text": "Task 2", "status": "in_progress"}
]
result = doc_updater.batch_update_checklists(updates)
```

---

### 9. TemplateGenerator (`template_generator.py`)

Handles WPD and PRD template generation with version management.

**Responsibilities**:
- Generate WPD templates (L0-L3 grades)
- Generate PRD templates
- Automatic version management (N1.N2.N3)
- Template validation
- File creation with proper structure

**Version Management**:
- N1 (Major): Increment for major changes (N1+1, N2=0, N3=0)
- N2 (Minor): Increment for medium changes (N2+1, N3=0)
- N3 (Patch): Increment for small changes (N3+1)

**Methods**:
- `generate_wpd_template(Part_N, title, wpd_grade, version, description)` - Generate WPD template string
- `generate_prd_template(Part_N, title, wpd_source, version)` - Generate PRD template string
- `create_wpd_file(Part_N, title, wpd_grade, version, description)` - Create WPD file
- `create_prd_file(Part_N, title, wpd_source, version)` - Create PRD file
- `parse_version(version_str)` - Parse version to VersionInfo

**Usage**:
```python
from doc_management import TemplateGenerator, VersionInfo

template_gen = TemplateGenerator(workspace_root)

# Create WPD file
result = template_gen.create_wpd_file(
    Part_N="5",
    title="Feature-Implementation",
    wpd_grade="L1",
    version="1.0.0",
    description="Implement new feature X"
)
# Creates: docs_2/P5/P5-Feature-Implementation.md

# Create PRD file
result = template_gen.create_prd_file(
    Part_N="5",
    title="Feature-Implementation",
    wpd_source="P5/P5-Feature-Implementation.md",
    version="1.0.0"
)
# Creates: docs_2/prd/PRD-P5.md

# Version management
version = VersionInfo(1, 2, 3)
print(version.increment_major())  # 2.0.0
print(version.increment_minor())  # 1.3.0
print(version.increment_patch())  # 1.2.4
```

---

## Migration from ADMP

The ADMP (Agent Document Modification Policy) modules have been **migrated and integrated** into doc_management:

### Migrated Modules

| Original ADMP Module | New doc_management Module | Status |
|---------------------|---------------------------|--------|
| `agent_doc_modifier.py` | `document_modifier.py` | ✅ Migrated |
| `wpd_prd_updater.py` | `document_updater.py` | ✅ Migrated |
| `document_template.py` | `template_generator.py` | ✅ Migrated |
| `prd_generator.py` | `template_generator.py` | ✅ Merged |
| `document_version_updater.py` | `version_manager.py` | ✅ Merged |

### Migration Benefits

1. **Unified Namespace**: All document management in one place
2. **Consistent API**: Same pattern as other managers
3. **No Duplication**: Consolidated related functionality
4. **Single Responsibility**: Each manager has one clear purpose
5. **Better Testability**: Independent, focused modules

### Legacy ADMP Directory

The original `.github/agents/tool/ADMP/` directory is now deprecated. All functionality has been migrated to `doc_management/`.

---

## Integration with MP Tools

The `MappingManager` integrates with MP tools without duplication:

### MP Tools (`.github/agents/tool/mp/`)
- `mp_reader_agent.py` - Read mapping tables
- `mp_manager.py` - Comprehensive mapping management
- `mp_splitter.py` - Automatic 500-line splits
- `mp_validator.py` - Mapping validation
- `mp_sync_agent.py` - Synchronization

**Architecture Decision**: Instead of reimplementing these tools' functionality, the `MappingManager` provides a facade interface that delegates to them. This avoids code duplication and maintains single sources of truth.

---

## Usage in E_Document_Management.py

The `DocumentManagementEngine` uses all managers via the Facade pattern:

```python
class DocumentManagementEngine:
    """Document Management Facade"""
    
    def __init__(self, context, previous_payload=None):
        # Initialize all managers (9 total)
        self.link_manager = LinkManager(workspace_root)
        self.version_manager = VersionManager(workspace_root)
        self.checklist_manager = ChecklistManager(workspace_root)
        self.progress_manager = ProgressManager(workspace_root)
        self.mapping_manager = MappingManager(workspace_root)
        self.error_session_manager = ErrorSessionManager(workspace_root)
        self.document_modifier = DocumentModifier(workspace_root)
        self.document_updater = DocumentUpdater(workspace_root)
        self.template_generator = TemplateGenerator(workspace_root)
    
    # Facade methods delegate to specialized managers
    def manage_links(self, doc_path):
        return self.link_manager.validate_and_fix_links(doc_path)
    
    def manage_version(self, doc_path, tier_context="B"):
        if tier_context == "B":
            return self.version_manager.update_version_for_tier_b(doc_path)
        elif tier_context == "C":
            return self.version_manager.update_version_for_tier_c(doc_path)
    
    # ... and so on for all managers
```

---

## Testing

Each manager can be tested independently:

```python
# Test LinkManager
from doc_management import LinkManager
from pathlib import Path

link_mgr = LinkManager(Path('.'))
result = link_mgr.validate_and_fix_links(Path('test_doc.md'))
assert result['success'] == True

# Test VersionManager
from doc_management import VersionManager

ver_mgr = VersionManager(Path('.'))
assert ver_mgr.parse_version("1.2.3") == (1, 2, 3)
assert ver_mgr.increment_version("1.2.3", "N2") == "1.3.0"

# ... etc for all managers
```

---

## Migration Notes

This refactoring was done in two phases:

### Phase 1: DocumentManagementEngine Refactoring
1. **Eliminated the monolithic `DocumentManagementEngine` class** (was 966 lines)
2. **Followed Single Responsibility Principle** - each manager has one purpose
3. **Used Facade Pattern** - unified interface, separated implementation
4. **Allowed breaking changes** - no backward compatibility wrappers

### Phase 2: ADMP Integration
1. **Migrated ADMP modules into doc_management** (3,056 lines total)
2. **Consolidated related functionality** - no duplication
3. **Unified namespace** - all document management in one place
4. **Integrated with MP tools** - delegates instead of reimplementing

**Previous Structure** (before refactoring):
```
.github/agents/tool/
├── E_Document_Management.py (966 lines - monolithic)
└── ADMP/
    ├── agent_doc_modifier.py (512 lines)
    ├── document_template.py (653 lines)
    ├── document_version_updater.py (138 lines)
    ├── prd_generator.py (716 lines)
    ├── wpd_prd_updater.py (624 lines)
    └── run_doc_updater_workflow.py (413 lines)
```

**New Structure** (after refactoring):
```
.github/agents/tool/
├── E_Document_Management.py (500 lines - Facade)
└── doc_management/
    ├── link_manager.py (180 lines)
    ├── version_manager.py (350 lines)
    ├── checklist_manager.py (170 lines)
    ├── progress_manager.py (180 lines)
    ├── mapping_manager.py (200 lines)
    ├── error_session_manager.py (230 lines)
    ├── document_modifier.py (250 lines - from ADMP)
    ├── document_updater.py (280 lines - from ADMP)
    └── template_generator.py (270 lines - from ADMP)
```

**Total**: 9 specialized managers, ~2,310 lines (consolidated from 4,022 lines across scattered modules)

---

## References

- **Facade Pattern**: [Design Patterns: Elements of Reusable Object-Oriented Software](https://en.wikipedia.org/wiki/Facade_pattern)
- **Single Responsibility Principle**: [SOLID Principles](https://en.wikipedia.org/wiki/Single-responsibility_principle)
- **MP Tools Guide**: `.github/agents/tool/mp/MP_MANAGER_GUIDE.md`
- **ADMP (deprecated)**: `.github/agents/tool/ADMP/` - Now integrated into doc_management

---

**Version**: 2.0.0  
**Date**: 2026-01-08  
**Phase 1**: DocumentManagementEngine refactored ✅  
**Phase 2**: ADMP modules migrated ✅  
**Status**: Complete

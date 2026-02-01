# trigger_prd_update.py

Thin wrapper script for triggering Tier E document management operations.

## Purpose

Orchestrates document updates (PRD/WPD) via `DocumentManagementEngine` without creating adapters or bridges. Follows SRP: validation and orchestration only, all writes delegated to existing managers.

## Safety First

**Default mode**: `--dry-run` (plans operations without applying)  
**Apply mode**: Requires explicit `--apply` flag

## Usage

### Dry Run (Default - Safe)
```bash
python .github/agents/tool/scripts/trigger_prd_update.py \
    --payload-file payload.json \
    --dry-run
```

### Apply Changes
```bash
python .github/agents/tool/scripts/trigger_prd_update.py \
    --payload-file payload.json \
    --apply
```

## Payload Format

See `example_payload.json` for complete example.

```json
{
  "prd_path": "docs_2/prd/PRD-P1.md",
  "wpd_sources": [
    "docs_2/P1/P1.3.1-Rename-Module-Migration.md"
  ],
  "Part_Number": "3.1",
  "status": "complete",
  "summary": "Completed rename module migration",
  "changes": [
    "Removed backward compatibility",
    "Implemented breaking changes",
    "Created legacy reference document"
  ],
  "operations": [
    {
      "type": "update_checklist",
      "item_text": "Phase E: Rename Module Migration",
      "status": "complete",
      "add_timestamp": true
    },
    {
      "type": "add_prd_link"
    }
  ],
  "commit_id": "93215c6",
  "branch": "copilot/rename-module-migration",
  "author": "copilot",
  "timestamp": "2026-01-15T10:30:00Z",
  "dry_run": true
}
```

## Operation Types

### 1. `add_prd_link`
Adds PRD link to WPD documents.

**Delegates to**: `DocumentManagementEngine._add_prd_link_to_document()`

**Payload**:
```json
{
  "type": "add_prd_link"
}
```

### 2. `update_checklist`
Updates checklist item status with optional timestamp.

**Delegates to**: `DocumentUpdater.update_checklist_item()`

**Payload**:
```json
{
  "type": "update_checklist",
  "item_text": "Task description",
  "status": "complete",
  "add_timestamp": true
}
```

**Valid statuses**: `complete`, `done`, `failed`, `in_progress`, `pending`, `blocked`

### 3. `mapping_update`
Updates mapping table (MP files).

**Delegates to**: `MappingManager.manage_mapping()` via `DocumentManagementEngine`

**Payload**:
```json
{
  "type": "mapping_update",
  "mapping_data": {
    "module": "rename_service",
    "flow": "ai_rename_flow"
  }
}
```

## Output Format

### Dry Run Output
```json
{
  "success": true,
  "mode": "dry_run",
  "planned_operations": [
    {
      "type": "update_checklist",
      "status": "planned",
      "action": "Update checklist in docs_2/P1/...: Task -> complete",
      "target": "docs_2/P1/P1.3.1-Rename-Module-Migration.md",
      "timestamp": "2026-01-16T08:30:00"
    }
  ],
  "affected_files": [
    "docs_2/P1/P1.3.1-Rename-Module-Migration.md"
  ],
  "operation_count": 1
}
```

### Apply Output
```json
{
  "success": true,
  "mode": "apply",
  "applied_operations": [
    {
      "type": "update_checklist",
      "status": "applied",
      "action": "Updated checklist in docs_2/P1/...: Task -> complete",
      "target": "docs_2/P1/P1.3.1-Rename-Module-Migration.md",
      "result": {"success": true},
      "timestamp": "2026-01-16T08:30:00"
    }
  ],
  "modified_files": [
    "docs_2/P1/P1.3.1-Rename-Module-Migration.md"
  ],
  "operation_count": 1,
  "agent_state": {
    "tier": "E",
    "status": "SUCCESS",
    "logic_summary": "Applied 1 operations",
    "payload": {...}
  }
}
```

## Architecture Constraints

### ✅ Follows SRP
- **This script**: Validation and orchestration only
- **DocumentManagementEngine**: Facade for document operations
- **Managers**: Actual document modifications

### ❌ No Adapters/Bridges
- Directly uses existing `DocumentManagementEngine` and managers
- No compatibility shims or translation layers
- Breaking change approach - clean interfaces

### ✅ Safety First
- Default `dry_run=True`
- Validates payload before execution
- Returns detailed operation plans
- Clear error messages

## Testing

### Unit Tests
```bash
python -m pytest .github/agents/tool/tests/test_trigger_prd_update.py -v
```

### Integration Test (Dry Run)
```bash
# Create test payload
cat > /tmp/test_payload.json << 'EOF'
{
  "prd_path": "docs_2/prd/PRD-P1.md",
  "wpd_sources": ["docs_2/P1/P1.3.1-Rename-Module-Migration.md"],
  "operations": [
    {
      "type": "update_checklist",
      "item_text": "Test task",
      "status": "complete"
    }
  ]
}
EOF

# Run dry-run
python .github/agents/tool/scripts/trigger_prd_update.py \
    --payload-file /tmp/test_payload.json \
    --dry-run
```

## Error Handling

The script provides detailed error messages:

- **Missing required fields**: Lists all missing fields
- **Invalid operation type**: Specifies valid types
- **File not found**: Shows which file is missing
- **Operation failed**: Returns error from manager with stack trace

## Future Enhancements

To enable full automation:

1. **Change Detector**: Parse git diff to identify affected documents
2. **Payload Generator**: Convert code changes to payload format
3. **Content Summarizer**: Generate human-readable change descriptions
4. **Document Selector**: Map code changes to documentation sections

See `docs_2/P1/P1.3.1-Automation-Integration-Notes.md` for details.

## Related Files

- **Engine**: `.github/agents/tool/E_Document_Management.py`
- **Managers**: `.github/agents/tool/doc_management/*.py`
- **Models**: `.github/agents/tool/models/core.py`
- **Tests**: `.github/agents/tool/tests/test_trigger_prd_update.py`

## Author

Created as part of rename module migration (P1.3.1)  
Date: 2026-01-16  
Branch: copilot/trigger-prd-update

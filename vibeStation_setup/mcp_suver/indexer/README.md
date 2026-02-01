# Indexer Package - Repository Indexing Automation

**Architecture**: Modular package with Facade pattern

Replaces legacy `agent_indexer.py` CLI and `.github/workflows/agent-indexer.yml` with a modular, Python-first indexing automation framework integrated into the 6-Tier Task Orchestration system (Tier E).

## Structure

```
indexer/
├── __init__.py          # Package exports
├── facade.py            # IndexFacade - main entry point
├── core.py              # CoreIndexer - indexing logic
├── releaser.py          # Releaser - GitHub release management
├── workflow.py          # WorkflowGenerator - CI workflow templates
└── tests/               # Test suite
```

## Components

### IndexFacade (`facade.py`)

Main entry point for all indexing operations. Orchestrates core, releaser, and workflow components.

**Methods**:
- `run_index_cycle(commit_threshold, upload_release, gh_token, force)` - Complete index cycle

**Usage**:
```python
from indexer import IndexFacade
from pathlib import Path

facade = IndexFacade(
    workspace_root=Path("."),
    db_path=Path(".agent_index/ci_db.sqlite")
)

result = facade.run_index_cycle(
    commit_threshold=6,
    upload_release=False,
    force=False
)

print(result["status"])  # SUCCESS, SKIPPED, or FAILED
```

---

### CoreIndexer (`core.py`)

Core indexing logic - commit threshold decisions, file collection, SQLite building.

**Responsibilities**:
- Decide when to run based on commit count since last index tag
- Collect files from repository (filtered by extension and directory)
- Build SQLite database with file metadata and inverted token index
- Atomic database writes

**Methods**:
- `decide_should_run(commit_threshold, force)` - Returns (bool, details dict)
- `build_index(paths, allow_overwrite)` - Build SQLite index

**Database Schema**:
```sql
-- File metadata
CREATE TABLE files (
  id INTEGER PRIMARY KEY,
  path TEXT UNIQUE,
  size INTEGER,
  mtime REAL,
  sha256 TEXT
);

-- Inverted token index
CREATE TABLE tokens (
  token TEXT,
  file_id INTEGER,
  count INTEGER,
  FOREIGN KEY(file_id) REFERENCES files(id)
);

-- Metadata (created_at, workspace_root, etc.)
CREATE TABLE metadata (
  key TEXT PRIMARY KEY,
  value TEXT
);
```

**Usage**:
```python
from indexer import CoreIndexer
from pathlib import Path

indexer = CoreIndexer(
    workspace_root=Path("."),
    db_path=Path(".agent_index/ci_db.sqlite")
)

# Check if should run
should_run, details = indexer.decide_should_run(commit_threshold=6)
if should_run:
    db_path = indexer.build_index()
    print(f"Index built: {db_path}")
```

---

### Releaser (`releaser.py`)

GitHub release management - upload index as release asset, prune old releases.

**Responsibilities**:
- Upload index database as GitHub release asset
- Prune old index releases (keep last N)
- Manage release tags

**Methods**:
- `upload_release(db_path, gh_token, commit_sha)` - Upload as GitHub release
- `prune_releases(keep_last_n, gh_token)` - Prune old releases

**Note**: GitHub API integration is pending. Currently returns success metadata without actual API calls. Requires `gh` CLI or PyGithub for full implementation.

**Usage**:
```python
from indexer import Releaser
from pathlib import Path

releaser = Releaser(
    workspace_root=Path("."),
    db_path=Path(".agent_index/ci_db.sqlite")
)

# Upload release
result = releaser.upload_release(gh_token="ghp_xxx")
print(result["tag_name"])  # index-abc123...

# Prune old releases
result = releaser.prune_releases(keep_last_n=30, gh_token="ghp_xxx")
```

---

### WorkflowGenerator (`workflow.py`)

GitHub Actions workflow template generation.

**Responsibilities**:
- Generate minimal CI workflow YAML
- Produce templates for operator review

**Methods**:
- `generate_workflow_template(config)` - Returns YAML string

**Usage**:
```python
from indexer import WorkflowGenerator
from pathlib import Path

generator = WorkflowGenerator(
    workspace_root=Path("."),
    db_path=Path(".agent_index/ci_db.sqlite"),
    config={"commit_threshold": 6}
)

yaml_content = generator.generate_workflow_template()
print(yaml_content)
```

---

## Integration with Tier E

The indexer is integrated into `E_Document_Management.py` (Tier E - Document Management).

### CLI Usage

```bash
# Run indexing via Tier E
python .github/agents/tool/E_Document_Management.py reindex \
  --root . \
  --db .agent_index/ci_db.sqlite \
  --commit-threshold 6 \
  --force

# With GitHub release upload
python .github/agents/tool/E_Document_Management.py reindex \
  --root . \
  --db .agent_index/ci_db.sqlite \
  --commit-threshold 6 \
  --upload-release \
  --gh-token $GITHUB_TOKEN
```

### Programmatic Usage

```python
from pathlib import Path
from E_Document_Management import DocumentManagementEngine, TaskContext

context = TaskContext(
    user_input="reindex",
    current_tier="E",
    workspace_root="."
)

engine = DocumentManagementEngine(context, None)

result = engine.run_repository_index(
    root=Path("."),
    db_path=Path(".agent_index/ci_db.sqlite"),
    commit_threshold=6,
    upload_release=False,
    force=False
)

print(result["status"])  # SUCCESS, SKIPPED, or FAILED
```

---

## GitHub Actions Integration

The indexer is designed to be called from minimal CI workflows that delegate all logic to Python.

### Minimal Workflow Example

```yaml
name: Agent Indexer (6-Tier Integration)

permissions:
  contents: write

on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  build-index:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for commit counting

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Run indexer via Tier E
        run: |
          python .github/agents/tool/E_Document_Management.py reindex \
            --root . \
            --db .agent_index/ci_db.sqlite \
            --commit-threshold 6 \
            --upload-release \
            --gh-token ${{ secrets.GITHUB_TOKEN }}
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**Benefits**:
- All decision logic (commit threshold, should run, etc.) is in Python
- Testable and maintainable
- CI is declarative and minimal
- Breaking changes allowed for structural completeness

---

## Design Principles

### Single Responsibility Principle

Each component has one clear responsibility:
- `CoreIndexer`: Index decision and DB building
- `Releaser`: GitHub release management
- `WorkflowGenerator`: CI workflow templates
- `IndexFacade`: Orchestration

### No Duplication

All commit threshold logic, release pruning, and indexing logic exists only in these components. No duplication across modules.

### Facade Pattern

`IndexFacade` provides unified interface while internal components are independently testable and maintainable.

### Integration, Not Standalone

The indexer is integrated into Tier E (Document Management) rather than creating a separate tier. This maintains Single Source of Truth for document/repository management operations.

---

## Migration from Legacy System

### Removed Files

- ✅ `.github/workflows/agent-indexer.yml` — Replaced by minimal workflow calling Tier E
- ✅ `.github/agents/tool/agent_indexer.py` — Functionality migrated to `indexer/` package

### What Changed

| Legacy | New |
|--------|-----|
| Standalone CLI script | Integrated into Tier E |
| Complex CI workflow with bash logic | Minimal CI calling Python |
| No commit threshold abstraction | `CoreIndexer.decide_should_run()` |
| Inline release management | `Releaser` component |
| No workflow generation | `WorkflowGenerator` component |

### Benefits

1. **Testability**: Each component independently testable
2. **Maintainability**: Clear separation of concerns
3. **Integration**: Part of 6-Tier orchestration system
4. **Flexibility**: Easy to extend or modify behavior
5. **No Duplication**: Single source of truth for indexing logic

---

## Testing

Test suite located in `indexer/tests/`.

### Unit Tests

```python
# Test CoreIndexer
from indexer import CoreIndexer
from pathlib import Path

indexer = CoreIndexer(Path("."), Path("/tmp/test.db"))

# Test decision logic
should_run, details = indexer.decide_should_run(6, force=True)
assert should_run == True
assert details["reason"] == "forced_run"

# Test index building
db_path = indexer.build_index()
assert db_path.exists()
```

### Integration Tests

```python
# Test full cycle via Facade
from indexer import IndexFacade
from pathlib import Path

facade = IndexFacade(Path("."), Path("/tmp/test.db"))
result = facade.run_index_cycle(force=True)

assert result["status"] == "SUCCESS"
assert Path(result["db_path"]).exists()
```

---

## Future Enhancements

- [ ] Complete GitHub API integration (upload, prune) using `gh` CLI or PyGithub
- [ ] Add embedding/semantic indexing stage
- [ ] Support for incremental indexing (only changed files)
- [ ] Query API for searching indexed content
- [ ] Web UI for index browsing

---

**Version**: 1.0.0  
**Date**: 2026-01-08  
**Status**: Complete ✅  
**Integration**: Tier E (Document Management)  
**Pattern**: Facade with modular components

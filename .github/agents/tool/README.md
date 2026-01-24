# Agent Tools — 6-Tier Task Orchestration System

This folder (.github/agents/tool) contains the 6-tier task orchestration system, repository-level agent tools, and supporting utilities for CI/GitHub Actions workflows.

## 📋 Core Architecture

### 6-Tier Orchestration System

The system is organized into specialized modules that handle different task types:

| Tier | Module | Purpose | Auto-Chain |
| ------ | --------- | --------- | ----------- |
| **A** | `A_Working_Document_Progress.py` | Create work plans (WPD generation) | → B |
| **B** | `B_Performing_Tasks.py` | Execute plans (run milestones/phases) | → E |
| **C** | `C_Edit_working_document.py` | Modify existing plans | → E |
| **D** | `D_Issue_Analysis_Flow.py` | Analyze errors and debug | → C |
| **E** | `E_Document_Management.py` | Manage documents (PRD, sync) | None |
| **F** | `F_Unknown_logic.py` | Fallback classifier | Variable |

**Master Controller**: `main_agent.py` - Routes user input to appropriate tiers and chains execution.

### Data Models (models/)

Following Single Responsibility Principle:

```
models/
├── core/                    # Core data models
│   ├── states.py           # AgentState (universal workflow state)
│   ├── tier_states.py      # TierAState through TierFState
│   ├── tier_models.py      # Nested dataclasses (DocumentMetadata, etc.)
│   ├── documents.py        # WPDDocument, PRDDocument
│   ├── templates.py        # WPD templates (L0-L3)
│   └── types.py            # Enums and type definitions
├── validators/             # Validation logic
├── converters/             # Model transformation
├── serializers/            # JSON/markdown serialization
├── formatters/             # Output formatting
└── builders/               # Factory/builder patterns
```

## 🛠️ Utilities

### Agent Indexer
- **`agent_indexer.py`** — Lightweight repository indexer that builds SQLite index for fast file search
- **Workflow**: `.github/workflows/agent-indexer.yml` — Runs on main branch pushes (6+ commits)
- **Output**: `.agent_index/ci_db.sqlite` (uploaded as GitHub release asset)

### Supporting Utilities
- **`utils.py`** — State persistence (save_state, get_outline, save_outline)
- **`tools.py`** — Web search and document retrieval utilities
- **`md_autofix.py`** — Markdown formatting and validation

### Deprecated Modules (Migration Complete)
- ~~`agent_models.py`~~ — **REMOVED** (superseded by `models/core/tier_states.py`)
- ~~`business_anaalysist.py`~~ — **DEPRECATED** (superseded by 6-tier orchestration)

## 🚀 Quick Start

### Running the Orchestrator

```bash
# Direct tier execution
python main_agent.py "Create a work plan for feature X" .

# Tier A: Create work plan
python A_Working_Document_Progress.py "Create WPD for step 5" .

# Tier B: Execute plan
python B_Performing_Tasks.py "Execute plan" .
```

### Using Agent Indexer

```bash
# Build index
python agent_indexer.py index --root . --db .agent_index/db.sqlite

# Query index
python agent_indexer.py query --db .agent_index/db.sqlite --q "search term"
```

## 📚 Documentation

- **`6TIER_IMPLEMENTATION_REPORT.md`** — Implementation status and architecture details
- **`docs/`** — Additional documentation and specifications

## 🔄 Migration Guide

### From Old Models to New Architecture

**Old** → **New**:
- `agent_models.Task` → Use tier-specific states (TierAState, TierBState, etc.)
- `business_anaalysist.State` → AgentState with tier-specific payload
- Direct field access → Nested dataclass access (e.g., `tier_a.metadata.Part_N`)

**Example Migration**:

```python
# Old (deprecated)
from tool.agent_models import Task
state = {"task_history": [Task(...)]}

# New (current)
from models.core import AgentState, TierBState
tier_b = TierBState(phase_results=[...])
state = AgentState(tier="B", status="SUCCESS", payload=tier_b.to_payload())
```

## 📥 How to Download Agent Index (CI Artifact)

After the workflow runs it will create a Release and attach the index file as a release asset (filename `ci_db_<commit>.sqlite`). Agents that need access can download the release asset in multiple ways:

- **Manual**: Open the release page in GitHub (Releases → Assets) and download the file.
- **CLI / script** (example uses GitHub REST API and `curl` with a Personal Access Token):

	1) Get the latest release JSON:

		 curl -s -H "Authorization: token $GITHUB_TOKEN" \
			 "https://api.github.com/repos/:owner/:repo/releases/latest" | jq -r '.assets[] | select(.name | contains("ci_db_")) | .url'

	2) Download an asset using the returned asset URL (use the same token and request the asset with the appropriate accept header):

		 curl -L -H "Authorization: token $GITHUB_TOKEN" -H "Accept: application/octet-stream" \
			 -o ci_db_latest.sqlite "<asset_download_url_returned_by_previous_call>"

For automation in GitHub Actions, you can also use a workflow step that downloads release assets using actions/download-release-asset or scripts that call the GitHub REST API. Make sure the token you use has `contents: read` permission (or use `GITHUB_TOKEN` provided to the workflow).

## 🔍 Next Steps / Recommendations

- Move CI artifacts to a shared cache or object store (S3, GCS) instead of relying on GitHub artifact downloads for production integration.
- Add an embedding/semantic indexing stage (local model or service) to provide better semantic search results.
- Optionally wrap the indexer as a small HTTP service (FastAPI/Flask) if agents should query the index remotely with access control.
- Complete migration of all legacy code to use tier-specific states from `models/core`.
- Consolidated detailed reports (integration, migration, refactor) into `6TIER_IMPLEMENTATION_REPORT.md` and this `README.md` to reduce duplication and simplify discovery; full archived copies are stored under `.github/docs/archive/`.


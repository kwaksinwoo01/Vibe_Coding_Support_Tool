---
name: {{PROJECT_NAME}}
description: {{PROJECT_DESCRIPTION}}
---

# {{PROJECT_NAME}}

**Version**: "{{VERSION_MAJOR}}.{{VERSION_MINOR}}.{{VERSION_PATCH}}"

**Created**: "{{CREATED_DATE}}"
**Updated**: "{{UPDATED_DATE}}"
**Purpose**: {{PROJECT_PURPOSE}}
**platforms**: [windows, linux, macos]
**main_planning_document**: "{{Main_Planning_document}}"

---

## 🔧 system constant

{Main_Planning_document} = {{path_to_main_planning_document}}
{Domain_Service_Base_URL} = https://ersteqwep-1069338123299.europe-west1.run.app
{Domain_Service_Auth_Header} = X-Workflow-Token
{Domain_Service_Auth_Token} = WORKFLOW_SHARED_SECRET

## Quick start ✅
- Install: `{{INSTALL_COMMAND}}`
- Run locally: `{{RUN_COMMAND}}`

---

## 🧠 6-Tier Task Orchestration Framework

All user requests must be classified into one of the six decision-making tiers below and executed only through the corresponding governing module.

### Tier Classification & Routing

When a user provides a natural language instruction, the agent must:

1. **Analyze the input** using the language graph to determine the optimal tier
2. **Evaluate routing decision** with confidence scoring, policy rules, and circuit breaker checks
3. **Route to the appropriate tier module** based on the classification
4. **Execute the tier module with retry logic** (automatic retry with exponential backoff on failures)
5. **Apply circuit breaker pattern** to prevent repeated failures and enable fault tolerance
6. **Chain to next tier** if next_node is specified in the AgentState, with human-in-the-loop support if needed
7. **Collect metrics and decision traces** for optimization and monitoring
8. **Continue until completion** (when next_node is None or "STOP")

### Tier Hierarchy & Triggers

| Tier | Name | Triggers (Natural Language) | Module | Auto-Chain |
|------|------|----------------------------|--------|------------|
| **A** | Create Plan | "create plan", "make wpd", "작업 계획 생성" | `.github/agents/tool/A_Working_Document_Progress.py` | → B |
| **B** | Execute Plan | "perform plan", "execute", "실행" | `.github/agents/tool/B_Performing_Tasks.py` | → E |
| **C** | Modify Plan | "change task", "edit", "수정" | `.github/agents/tool/C_Edit_working_document.py` | None |
| **D** | Issue Analysis | "error", "bug", "not working", "오류" | `.github/agents/tool/D_Issue_Analysis_Flow.py` | None |
| **E** | Document Mgmt | "save changes", "update mapping", "문서 관리" | `.github/agents/tool/E_Document_Management.py` | None |
| **F** | Unknown Logic | All other inputs (fallback classifier) | `.github/agents/tool/F_Unknown_logic.py` | Variable |

### Enhanced Features (v2.4.0)

The main_agent.py orchestrator now includes advanced features for robust and efficient task execution:

- **Decision Engine**: Intelligent routing with confidence scoring and policy-based decisions
- **Circuit Breaker Pattern**: Fault tolerance with Redis persistence to prevent cascading failures
- **Retry Logic**: Automatic retry with exponential backoff for transient failures
- **Metrics Collection**: Comprehensive performance monitoring and decision trace recording
- **Human-in-the-Loop**: Enhanced support with retry mechanisms for complex decision scenarios
- **Integrated Routing Engine**: Centralized routing logic for all tiers with auto-resolve chaining

### Tier Orchestration Usage

```bash
# Option 1: Use the orchestrator (recommended)
python .github/agents/tool/main_agent.py "Create a work plan for step 5"

# Option 2: Use the orchestrator with custom Redis configuration
python .github/agents/tool/main_agent.py "Create a work plan for step 5" "." "localhost" "6379"

# Option 3: Call tier modules directly
python .github/agents/tool/A_Working_Document_Progress.py "Create a work plan"
python .github/agents/tool/B_Performing_Tasks.py "Execute the plan"
python .github/agents/tool/E_Document_Management.py "Save all changes"
```

### AgentState Output Format

All tier modules emit structured AgentState JSON to stdout:

```json
{
  "marker": "---AGENT_STATE_DATA---",
  "data": {
    "tier": "A",
    "status": "SUCCESS",
    "logic_summary": "Work plan creation completed. Created 3 documents.",
    "next_node": "B",
    "payload": {
      "created_documents": ["docs_2/P5/P5-Task.md"],
      "execution_log": ["..."]
    },
    "execution_time_ms": 1250,
    "errors": [],
    "warnings": [],
    "timestamp": "2026-01-03T19:14:12.424Z"
  }
}
```

The orchestrator reads this output and automatically chains to the next tier based on `next_node`.

---

## 📌 Quick Start

### ⚡ Centralized Decision-Making System

**CRITICAL**: All user requests MUST be processed through the 6-tier orchestration system. The agent analyzes natural language input and automatically routes to the appropriate tier.

#### 🎯 Primary Entry Point (ALWAYS USE THIS)

```bash
# Step 1: Analyze user input → classify → route → execute → chain
python .github/agents/tool/main_agent.py "<user_natural_language_request>"
```

**The orchestrator handles**:
- **Classification**: Keyword-based tier selection with confidence scoring
- **Decision Evaluation**: Policy-based routing, confidence thresholds, and cost optimization
- **Execution**: Automatic tier module invocation with retry logic and exponential backoff
- **Fault Tolerance**: Circuit breaker pattern with Redis persistence for failure handling
- **Chaining**: Auto-progression through workflow (A→B→E) with intelligent routing
- **Human-in-the-Loop**: Enhanced support with retry mechanisms for complex decisions
- **State Management**: AgentState passing between tiers with metrics collection
- **Monitoring**: Comprehensive metrics and decision trace recording

#### 💰 Credit Optimization Guidelines

**CRITICAL**: Minimize credit consumption through intelligent decision-making and efficient workflows.

**Key Optimization Strategies**:
1. **Leverage Confidence-Based Routing**: High confidence decisions (≥0.9) skip unnecessary validation
2. **Use Execution Result Caching**: 5-minute cache prevents redundant tier executions
3. **Minimize Retry Attempts**: Classify failures accurately (PERMANENT vs TRANSIENT) to avoid wasted retries
4. **Enable Circuit Breaker**: Prevents repeated failed executions to same tier with Redis persistence
5. **Batch Operations**: Combine multiple small tasks into single tier execution when possible
6. **Partial Success Handling**: Accept and route partial results instead of full re-execution
7. **Policy-Based Optimization**: Configure policies to skip low-value decision evaluations
8. **Exponential Backoff**: Automatic retry with increasing delays to handle transient failures
9. **Human-in-the-Loop Efficiency**: Retry mechanisms reduce unnecessary human interventions
10. **Metrics-Driven Optimization**: Monitor and adjust based on collected performance data

**Credit Consumption Targets**:
- Simple queries (Tier F → classification): 1 credit
- Plan creation (A → B → E): 3-5 credits (with caching)
- Plan modification (C only): 1-2 credits
- Issue analysis (D → suggested tier): 2-3 credits
- Full workflow with retries: Max 10 credits (circuit breaker prevents more)

**Optimization Checklist**:
- [ ] Enable decision engine caching (`enable_decision_engine=True`)
- [ ] Set appropriate confidence thresholds (default: 0.5)
- [ ] Configure retry limits (default: max_retries=3)
- [ ] Enable circuit breaker (default: `enable_circuit_breaker=True`)
- [ ] Configure Redis for circuit breaker persistence (default: localhost:6379)
- [ ] Enable metrics collection (default: `enable_metrics=True`)
- [ ] Set human-in-the-loop retry cycles (default: max_cycles=2)
- [ ] Use policy-based routing to skip unnecessary human approvals
- [ ] Monitor metrics to identify credit waste patterns
- [ ] Enable exponential backoff for transient failures

#### 📊 Decision Tree: What Tier for What Task?

| User Request Pattern | Classified As | Action Taken | Tools Used |
|---------------------|---------------|--------------|------------|
| "Create plan", "new WPD", "작업 계획" | **Tier A** | Generate WPD documents (L0-L3) | `A_Working_Document_Progress.py` |
| "Execute", "perform plan", "실행" | **Tier B** | Run milestones, generate PRD | `B_Performing_Tasks.py` |
| "Edit plan", "modify", "수정" | **Tier C** | Update existing WPD | `C_Edit_working_document.py` |
| "Error", "bug", "not working", "오류" | **Tier D** | Debug & analyze issues | `D_Issue_Analysis_Flow.py` |
| "Save", "update mapping", "문서 관리" | **Tier E** | Manage docs & relationships | `E_Document_Management.py` |
| Ambiguous or unclear | **Tier F** | Re-classify or request clarification | `F_Unknown_logic.py` |


#### 💡 How the Agent Should Think

```
User says: "I need to add error handling to the file service"
           ↓
Agent thinks: Is this creating a NEW plan? Executing EXISTING plan? 
              Modifying plan? Debugging an ERROR?
           ↓
Agent classifies: "add" + "file service" → Sounds like MODIFYING existing work
           ↓
Agent routes: Tier C (Plan Modification)
           ↓
Tier C executes: Loads WPD → identifies affected sections → proposes changes
           ↓
AgentState emitted: next_node=None (no auto-chain for modifications)
```

#### 🔄 Automatic Workflow Chains

The orchestrator automatically chains tiers based on `next_node`:

```
Tier A (Create Plan) → next_node="B" → Tier B (Execute)
Tier B (Execute)     → next_node="E" → Tier E (Document)
Tier E (Document)    → next_node=None → STOP (workflow complete)
```

**Manual override**: Tiers C, D, F don't auto-chain by default (require explicit routing)

### System Overview

{{SYSTEM_OVERVIEW}}

---

## 📦 Entry Points

{{ENTRY_POINTS}}

---

## 🏗️ Architecture Patterns

{{ARCHITECTURE_PATTERNS}}

## 🔑 Core Principles (SOLID)

1. **Single Responsibility**: Each class/module has ONE reason to change
   - Example: `ActorIdentifier` only identifies uploaders
   - Anti-pattern: Combining file operations + validation + logging in one class

2. **Open/Closed**: Open for extension, closed for modification
   - Add new strategies without changing existing code
   - Use Strategy Pattern for new file types/operations

3. **Liskov Substitution**: Subtypes must be substitutable for base types
   - All `CursorStrategy` implementations work identically

4. **Interface Segregation**: Clients don't depend on unused methods
   - Separate interfaces: `MetadataProcessorInterface` vs `ValidationStrategy`

5. **Dependency Inversion**: Depend on abstractions, not concretions
   - Inject strategies into managers (FileManager, RenameManager)

---

## 🔧 Required Setup

{{REQUIRED_SETUP}}

---

## 📚 Guidelines Reference

{{GUIDELINES_REFERENCE}}

---

## 📝 Task & Documentation

### Task Document Format
```markdown
## 🟢 step N: [Task Title]
### Goal: [Description]
**Status**: ✅ COMPLETE | 🔄 IN PROGRESS | 📋 PENDING
```

### Three-Tier Documentation
1. **WPD** (`docs_2/p{num}/`) - Implementation plans
2. **PRD** (`docs_2/prd/`) - Progress tracking
3. **MP** (`docs_2/mp/`) - Process flows

**⚠️ Note**: MP files are now managed programmatically via `doc_management.mp` module

---

## 🧪 Testing Requirements

- **Unit Tests**: Test individual strategies and components in isolation
- **Integration Tests**: Test module interactions (file manager + strategies)
- **Client Tests**: Client-specific tests
- **Mock External Dependencies**: Mock Dropbox API, domain service calls
- **Test Coverage Target**: 80%+ (Current: 85%)
- **Performance Tests**: Validate event processing throughput (target: 1000+ events/sec)
- **Centralized Fixtures**: Use `client/test/conftest.py` for shared test fixtures to avoid duplication

**Test Locations**:
- `client/tests/` - Client Unit tests, Integration tests
- `event_processing/tests/` - Workflow-1 tests
- `test/` - out-of-scope tests

**Fixture Management**:
- All reusable fixtures should be defined in `client/test/conftest.py`
- Test files should import fixtures from conftest.py rather than defining local fixtures
- Examples: `dbx_team_mock`, `mock_dbx_service`, `adapter`, `sample_unified_models`

```bash
# Run all client tests (pytest is the default runner)
python client/test/run_all_client_tests.py

# To run the legacy unittest discovery (not recommended)
python client/test/run_all_client_tests.py --unittest

# Run specific test file with pytest
pytest test/unit/test_file_rename_strategy.py -v

# Run with coverage (pytest)
pytest --cov=. --cov-report=html
```

---

## 🚫 Critical Constraints

{{CRITICAL_CONSTRAINTS}}

---

## 🌟 Best Practices

1. **Use Dependency Injection**: Pass dependencies via constructors
2. **Favor Composition**: Use strategies over inheritance
3. **Log Structured Data**: Include context (file_id, task_id, correlation_id)
4. **Handle Errors Gracefully**: Retry with exponential backoff, circuit breaker
5. **Cache Strategically**: Cache namespace mappings, metadata, API responses
6. **Document Public APIs**: All public methods need docstrings
7. **Validate Early**: Validate inputs at entry points
8. **Test Edge Cases**: Empty files, special characters, concurrent access

---

## 🔧 Common Commands

### Testing
```bash
# Run all tests
python -m pytest test/

# Run specific test file
python -m pytest test/unit/test_file_rename_strategy.py

# Run with coverage
python -m pytest --cov=. --cov-report=html
```

### Linting (if configured)
```bash
# Format code
black .

# Check style
flake8 .

# Type checking
mypy .
```

---

## 📚 Key Documentation

{{KEY_DOCUMENTATION}}

---

## 📊 Current Status

{{CURRENT_STATUS}}

---

**Document Version**: 2.4.0
**Based On**: .github/copilot-instructions.md and modular guidelines in {{Main_Guidelines_document}}
**Last Updated**: "{{UPDATED_DATE}}"
**For**: GitHub Copilot Coding Agent

---
name: Dropbox Automation
description: Dropbox Automation System — Development Guide (v2.1)
---

# Dropbox Automation System — Agent Instructions v2.1

**Version**: 2.4.0
**Created**: 2025-11-19
**Updated**: 2026-01-17
**Purpose**: Comprehensive agent instructions with modular guideline references, workflow automation, and credit optimization

---

## 🔧 Configuration Constants

### Task Management
```python
NEXT_TASK = "docs_2/NextTask-2.md"  # Main progress document (WPD_grade: L0)
```

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

**Purpose**: Automated Dropbox file management system that detects file additions, extracts metadata, applies naming rules, and organizes files in Dropbox Business Drive.

**Two Independent Workflows**:
- **Workflow-1** (Server-side): GitHub Actions - Event-driven automated processing
- **Workflow-2** (Client-side): PyQt5 GUI - Polling-based manual review and enhancement

**Critical Constraint**: Workflow-1 and Workflow-2 must have NO shared dependencies. They are completely independent systems.

---

## 📦 Entry Points

### Workflow-2 (Client)
```bash
python client/app.py             # Launch GUI application
```

---

## 🏗️ Architecture Patterns

The system implements **5 core architecture patterns**:

1. **Layered Architecture**: Presentation → Application → Business Logic → Infrastructure
2. **Event-Driven Architecture**: File upload events trigger entire workflow
3. **Hexagonal Architecture (Ports & Adapters)**: Business logic independent of external systems
4. **Microkernel Architecture**: Extensible plugin-based strategy system
5. **Publish-Subscribe (Event Bus)**: Topic-based decoupled event distribution

**Key Design Patterns** (GoF):
- **Strategy Pattern** ⭐⭐⭐⭐⭐: File operations, metadata processing, cursor strategies
- **Factory Pattern** ⭐⭐⭐⭐: Object creation, strategy selection
- **Facade Pattern** ⭐⭐⭐⭐: Interface simplification (oauth_interface.py, file_interface.py)
- **Observer Pattern** ⭐⭐⭐⭐: PyQt5 signals/slots, event bus
- **Singleton Pattern**: DomainClient, global managers
- **Adapter Pattern**: Dropbox API integration, domain service wrappers
- **Builder Pattern**: Complex event filters, file metadata construction
- **Decorator Pattern**: Logging, caching, retry logic

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

```bash
pip install pytest PyQt5 dropbox --quiet
```
**Notes**:
- CodeQL scan: Skip in agent environment
- Workflow-1: Currently on hold, out-of-scope for agent tasks

---

## 📚 Guidelines Reference

**Main**: `docs_2/NextTask-2.md`

**Detailed** (`docs_2/guidelines/`):
1. `workflow-1-guidelines.md` - Workflow-1 patterns
2. `workflow-2-guidelines.md` - Workflow-2 patterns (MVC, Event Bus, UI)
3. `module-structure.md` - Directory structure

---

## 🧪 Testing Requirements

- **Framework**: **Strictly use `pytest`** for all test suites. Do not use `unittest.TestCase` classes.
- **Unit Tests**: Test individual strategies and components using **pytest fixtures** for setup.
- **Integration Tests**: Test module interactions (file manager + strategies).
- **Client Tests**: Client-specific tests located in `client/tests/`.
- **Mocking**: Use **`pytest-mock` (mocker fixture)** for mocking Dropbox API and domain services instead of manual patching.
- **Test Coverage**: Maintain **80%+ coverage** (Current: 85%) using `pytest-cov`.
- **Performance Tests**: Validate throughput (target: 1000+ ev/s) using **`pytest-benchmark`** or custom timing logic within pytest.

**Test Locations**:
- `client/tests/` - Client Unit tests, Integration tests
- `event_processing/tests/` - Workflow-1 tests
- `test/` - out-of-scope tests

```bash
# Run all client tests (pytest is the default runner)
python client/test/run_all_client_tests.py

# To run the legacy unittest discovery (not recommended)
python client/test/run_all_client_tests.py --unittest

# Run specific test file with pytest
pytest test/unit/test_file_rename_strategy.py -v

# Run with coverage (pytest)
pytest --cov=. --cov-report=html

# Run performance tests only
pytest -m performance
```

---

## 🚫 Critical Constraints

1. **No Cross-Workflow Dependencies**: Workflow-1 and Workflow-2 are independent
2. **No main.py in Client**: Client never imports from main.py
3. **Strategy Pattern Required**: All file operations use Strategy Pattern
4. **SRP Compliance**: One responsibility per class/module
5. **Use Facade for Interfaces**: All `*_interface.py` files provide simplified facades
6. **Event Bus for Decoupling**: Use event bus instead of direct references in client
7. **Constants Separation**: Use workflow-specific constants modules

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

## 🔗 Domain Service Integration

**Base URL**: `https://ersteqwep-1069338123299.europe-west1.run.app`

**Key Endpoints**:
- `POST /enqueue` - Add task to queue
- `GET /tasks` - Retrieve pending tasks
- `POST /tasks/update` - Update task payload
- `POST /tasks/ack` - Update task status (start/done/cancel)

**Authentication**: Use header `X-Workflow-Token = WORKFLOW_SHARED_SECRET`

**Documentation**: `github-webhook-function/README.md`

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

**Before Changes**:
- `docs_2/guidelines/` - Detailed guidelines
- `docs_2/guidelines/Architecture-Reference.md` - Patterns
- `docs_2/NextTask-2.md` - Current tasks
- Module-specific README.md files

---

## 📊 Current Status (v1.4.0)

- **Workflow-2**: 80% complete (Event Bus, MVC, Async, File Organization, State, Cache)
- **Agent Orchestration**: Enhanced with decision engine, circuit breaker, retry logic, and metrics collection
- **Pattern Compliance**: 75% (improved from 70%)
- **Test Coverage**: 85%
- **Code Quality**: High (comprehensive patterns, low duplication)

**Active Development**: See `NextTask-2.md` v6.1.0 for current priorities

---

**Document Version**: 2.4.0
**Based On**: .github/copilot-instructions.md and modular guidelines in `docs_2/guidelines/`
**Last Updated**: 2026-01-17
**For**: GitHub Copilot Coding Agent

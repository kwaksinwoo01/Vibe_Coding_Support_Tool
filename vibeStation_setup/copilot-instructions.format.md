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
{Domain_Service_Auth_Header} = X-Workflow-Token
{Domain_Service_Auth_Token} = WORKFLOW_SHARED_SECRET

## Quick start guide

- Install: `{{INSTALL_COMMAND}}`
- Run locally: `{{RUN_COMMAND}}`

### Tier Orchestration Usage

Primary Entry Point:

```bash
python .github/agents/tool/main_agent.py "<user_natural_language_request>"
```

```bash
python .github/agents/tool/main_agent.py "Create a work plan for step 5"
python .github/agents/tool/main_agent.py "Create a work plan for step 5" "." "localhost" "6379"
python .github/agents/tool/A_Working_Document_Progress.py "Create a work plan"
python .github/agents/tool/B_Performing_Tasks.py "Execute the plan"
python .github/agents/tool/E_Document_Management.py "Save all changes"
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

---

### Tier Hierarchy & Triggers

| Tier | Name | Triggers (Natural Language) | Module | Auto-Chain |
|------|------|----------------------------|--------|------------|
| **A** | Create Plan | "create plan", "make wpd", "작업 계획 생성", "new WPD", "작업 계획" | `.github/agents/tool/A_Working_Document_Progress.py` | → B |
| **B** | Execute Plan | "perform plan", "execute", "실행" | `.github/agents/tool/B_Performing_Tasks.py` | → E |
| **C** | Modify Plan | "change task", "edit", "Edit plan", "modify", "수정" | `.github/agents/tool/C_Edit_working_document.py` | None |
| **D** | Issue Analysis | "error", "bug", "not working", "오류" | `.github/agents/tool/D_Issue_Analysis_Flow.py` | None |
| **E** | Document Mgmt | "save changes",  "Save", "update mapping", "문서 관리" | `.github/agents/tool/E_Document_Management.py` | None |
| **F** | Unknown Logic | Ambiguous or unclear | `.github/agents/tool/F_Unknown_logic.py` | Variable |

---

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

### 🎯 Primary Entry Point (ALWAYS USE THIS)

**The orchestrator handles**:

- **Classification**: Keyword-based tier selection with confidence scoring
- **Decision Evaluation**: Policy-based routing, confidence thresholds, and cost optimization
- **Execution**: Automatic tier module invocation with retry logic and exponential backoff
- **Fault Tolerance**: Circuit breaker pattern with Redis persistence for failure handling
- **Chaining**: Auto-progression through workflow (A→B→E) with intelligent routing
- **Human-in-the-Loop**: Enhanced support with retry mechanisms for complex decisions
- **State Management**: AgentState passing between tiers with metrics collection
- **Monitoring**: Comprehensive metrics and decision trace recording

---

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

#### 🔄 Automatic Workflow Chains

The orchestrator automatically chains tiers based on `next_node`:

```
Tier A (Create Plan) → next_node="B" → Tier B (Execute)
Tier B (Execute)     → next_node="E" → Tier E (Document)
Tier E (Document)    → next_node=None → STOP (workflow complete)
...

```

---

### System Overview

{{SYSTEM_OVERVIEW}}

---

## 📦 Entry Points

{{ENTRY_POINTS}}

---

## 🏗️ Architecture Patterns

{{ARCHITECTURE_PATTERNS}}

## 🔑 Core Principles (SOLID)

1. {{CORE_PRINCIPLES}}
2. {{CORE_PRINCIPLES}}
3. {{CORE_PRINCIPLES}}
4. {{CORE_PRINCIPLES}}
5. {{CORE_PRINCIPLES}}
...

---

## 🔧 Required Setup

{{REQUIRED_SETUP}}

---

## 📚 Guidelines Reference

{{GUIDELINES_REFERENCE}}

---

## 🧪 Testing Requirements

{{TESTING_REQUIREMENTS}}

---

## 🚫 Critical Constraints

{{CRITICAL_CONSTRAINTS}}

---

## 📚 Key Documentation

{{KEY_DOCUMENTATION}}

---

## 📊 Current Status

{{CURRENT_STATUS}}

---

**Document Version**: "{{VERSION_MAJOR}}.{{VERSION_MINOR}}.{{VERSION_PATCH}}"
**Created**: "{{CREATED_DATE}}"
**Based On**: .github/copilot-instructions.md and modular guidelines in {{Main_Guidelines_document}}
**Last Updated**: "{{UPDATED_DATE}}"

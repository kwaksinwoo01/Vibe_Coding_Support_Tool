# Decision Policies Configuration

## Overview

This directory contains the split decision policies configuration for the 6-tier orchestration system. Each policy rule is stored as an individual JSON file for better maintainability and version control.

## Structure

```
decision_policies/
├── metadata.json                        # Configuration metadata
├── low_confidence_human_approval.json   # Priority: 100
├── max_retries_issue_analysis.json      # Priority: 95
├── cost_limit_fallback.json             # Priority: 90
├── failure_to_issue_analysis.json       # Priority: 85
├── high_confidence_fast_track.json      # Priority: 80
├── partial_success_enhancement.json     # Priority: 75
├── slow_execution_warning.json          # Priority: 60
├── tier_a_to_b_chain.json              # Priority: 50
├── tier_b_to_e_chain.json              # Priority: 50
└── tier_c_to_e_chain.json              # Priority: 50
```

## Policy Rule Format

Each policy file contains a single rule with the following structure:

```json
{
  "name": "rule_name",
  "description": "Rule description",
  "condition": {
    "field": "field_name",
    "operator": "==|!=|<|<=|>|>=",
    "value": "value"
  },
  "action": {
    "requires_human_approval": true|false,
    "use_alternative": true|false,
    "alternative_tier": "A|B|C|D|E|F",
    "metadata": {
      "reason": "explanation",
      "...": "..."
    }
  },
  "priority": 0-100,
  "enabled": true|false
}
```

## Policy Descriptions

### High Priority (80-100)

- **low_confidence_human_approval** (100): Requires human approval when routing confidence is below 0.4
- **max_retries_issue_analysis** (95): Routes to issue analysis (D) after 3 failed retries
- **cost_limit_fallback** (90): Falls back to tier E when estimated cost exceeds 100.0
- **failure_to_issue_analysis** (85): Routes failed executions to issue analysis tier (D)
- **high_confidence_fast_track** (80): Fast tracks high confidence decisions (>=0.9)

### Medium Priority (60-79)

- **partial_success_enhancement** (75): Routes partial successes to document management (E)
- **slow_execution_warning** (60): Flags executions taking over 10 seconds

### Low Priority (50)

- **tier_a_to_b_chain** (50): Auto-chains successful Tier A to Tier B
- **tier_b_to_e_chain** (50): Auto-chains successful Tier B to Tier E
- **tier_c_to_e_chain** (50): Auto-chains successful Tier C to Tier E

## Usage

The `PolicyEngine` in `vibeStation_setup/mcp_suver/lang_graph_moduel/policy_engine.py` automatically loads all JSON files (except `metadata.json`) from this directory.

```python
from pathlib import Path
from lang_graph_moduel.policy_engine import PolicyEngine

config_dir = Path("vibeStation_setup/config/decision_policies")
engine = PolicyEngine(str(config_dir))
```

## Adding New Policies

1. Create a new JSON file in this directory
2. Follow the policy rule format above
3. Set an appropriate priority (higher = evaluated first)
4. The engine will automatically load it on next startup

## Migration Notes

**Previous Format**: Single `decision_policies.json` file in `mcp_suver/config/`
**Current Format**: Split files in `vibeStation_setup/config/decision_policies/`

**No backward compatibility** - the old format is no longer supported.

## Version

- **Version**: 1.0.0
- **Format**: Split JSON files
- **Last Updated**: 2026-02-02

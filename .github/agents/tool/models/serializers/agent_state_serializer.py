"""
AgentState serializer for stdout emission.

**Single Responsibility**: Serialize AgentState to JSON and emit to stdout.
This module is changed only when AgentState JSON format changes.

**Responsibility**: AgentState JSON serialization and stdout emission
**Reason to Change**: When AgentState JSON format or emission behavior changes
"""

import json
import sys
from typing import Dict, Any
from ..core import AgentState


AGENT_STATE_MARKER = "---AGENT_STATE_DATA---"


def emit_agent_state(state: AgentState) -> None:
    """
    Emit an AgentState to stdout in JSON format.
    
    The output format includes a marker for the orchestrator to parse:
    ---AGENT_STATE_DATA---
    {JSON data}
    ---AGENT_STATE_DATA---
    
    Args:
        state: AgentState to emit
    """
    output = {
        "marker": AGENT_STATE_MARKER,
        "data": state.to_dict(),
    }
    
    # Print marker line
    print(AGENT_STATE_MARKER)
    # Print JSON data
    print(json.dumps(output, indent=2, default=str))
    # Print marker line
    print(AGENT_STATE_MARKER)
    sys.stdout.flush()


def serialize_agent_state(state: AgentState) -> str:
    """
    Serialize an AgentState to JSON string.
    
    Args:
        state: AgentState to serialize
    
    Returns:
        JSON string representation of the state
    """
    return json.dumps(state.to_dict(), indent=2, default=str)


__all__ = [
    "emit_agent_state",
    "serialize_agent_state",
    "AGENT_STATE_MARKER",
]

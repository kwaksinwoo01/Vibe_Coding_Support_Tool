"""
Task execution context model.

**Single Responsibility**: Define task execution context data structure.
This module is changed only when context requirements change.

**Responsibility**: Task context model definition
**Reason to Change**: When task execution context structure needs modification
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from .states import AgentState


@dataclass
class TaskContext:
    """
    Task execution context.
    
    Encapsulates all contextual information needed for tier execution.
    Clean data class without backward compatibility wrappers.
    
    Attributes:
        user_input: User's natural language input
        current_tier: Currently executing tier (A-F)
        workspace_root: Repository root path
        document_path: Optional path to target document
        document_type: Optional document type (WPD, PRD, etc.)
        config: Additional configuration parameters
        previous_state: Optional state from previous tier execution
        session_id: Unique session identifier
    """
    user_input: str = ""
    current_tier: str = ""
    workspace_root: str = ""
    document_path: Optional[str] = None
    document_type: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)
    previous_state: Optional[AgentState] = None
    session_id: str = ""


__all__ = [
    "TaskContext",
]

"""
AgentState builder for creating state instances.

**Single Responsibility**: Create AgentState instances with various initial states.
This module is changed only when AgentState creation logic changes.

**Responsibility**: AgentState creation and initialization
**Reason to Change**: When AgentState creation patterns or defaults change
"""

from typing import Optional, Dict, Any, List
from ..core import AgentState


def create_success_state(
    tier: str,
    logic_summary: str = "",
    payload: Optional[Dict[str, Any]] = None,
    next_node: Optional[str] = None,
    execution_time_ms: float = 0.0,
) -> AgentState:
    """
    Create an AgentState with SUCCESS status.
    
    Args:
        tier: Current tier (A-F)
        logic_summary: Human-readable summary
        payload: Execution results data
        next_node: Next tier to execute
        execution_time_ms: Execution time in milliseconds
    
    Returns:
        AgentState with SUCCESS status
    """
    return AgentState(
        tier=tier,
        status="SUCCESS",
        logic_summary=logic_summary,
        payload=payload or {},
        next_node=next_node,
        execution_time_ms=execution_time_ms,
    )


def create_failure_state(
    tier: str,
    logic_summary: str = "",
    errors: Optional[List[str]] = None,
    payload: Optional[Dict[str, Any]] = None,
    execution_time_ms: float = 0.0,
) -> AgentState:
    """
    Create an AgentState with FAILED status.
    
    Args:
        tier: Current tier (A-F)
        logic_summary: Human-readable summary
        errors: List of error messages
        payload: Partial execution results
        execution_time_ms: Execution time in milliseconds
    
    Returns:
        AgentState with FAILED status
    """
    return AgentState(
        tier=tier,
        status="FAILED",
        logic_summary=logic_summary,
        payload=payload or {},
        errors=errors or [],
        execution_time_ms=execution_time_ms,
    )


def create_pending_state(
    tier: str,
    logic_summary: str = "",
    payload: Optional[Dict[str, Any]] = None,
    execution_time_ms: float = 0.0,
) -> AgentState:
    """
    Create an AgentState with PENDING status.
    
    Args:
        tier: Current tier (A-F)
        logic_summary: Human-readable summary
        payload: Current execution state
        execution_time_ms: Execution time in milliseconds
    
    Returns:
        AgentState with PENDING status
    """
    return AgentState(
        tier=tier,
        status="PENDING",
        logic_summary=logic_summary,
        payload=payload or {},
        execution_time_ms=execution_time_ms,
    )


__all__ = [
    "create_success_state",
    "create_failure_state",
    "create_pending_state",
]

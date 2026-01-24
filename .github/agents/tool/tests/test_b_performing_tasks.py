"""
Test suite for B_Performing_Tasks.py (Tier B: Plan Execution)

Tests the refactored Tier B implementation using new dataclass hierarchy:
- AgentState, TierBState, DocumentSources, TaskContext
- Validates execution flow, phase parsing, and state management
- Tests backward compatibility with previous_payload
"""

import sys
import pytest
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from B_Performing_Tasks import TaskExecutionEngine, main
from models.core import AgentState, TierBState, DocumentSources, TaskContext


class TestTaskExecutionEngine:
    """Test TaskExecutionEngine class"""
    
    def test_init_with_empty_context(self):
        """Test initialization with minimal context"""
        context = TaskContext(
            user_input="Perform work plan",
            current_tier="B",
            workspace_root="."
        )
        
        engine = TaskExecutionEngine(context)
        
        assert engine.tier == "B"
        assert engine.state.tier == "B"
        assert engine.state.status == "PENDING"
        assert isinstance(engine.tier_state, TierBState)
        assert isinstance(engine.tier_state.sources, DocumentSources)
    
    def test_init_with_previous_state_from_tier_a(self):
        """Test initialization with previous state from Tier A"""
        # Create mock Tier A state
        tier_a_state = AgentState(
            tier="A",
            status="SUCCESS",
            wpd_grade="L2",
            wpd_source_path="docs_2/P5/P5-Test.md",
            payload={
                "created_documents": ["docs_2/P5/P5-Test.md"]
            }
        )
        
        context = TaskContext(
            user_input="continue from tier a",
            current_tier="B",
            workspace_root=".",
            previous_state=tier_a_state
        )
        
        engine = TaskExecutionEngine(context)
        
        # Verify WPD source extraction
        assert engine.state.wpd_source_path == "docs_2/P5/P5-Test.md"
        assert engine.state.wpd_grade == "L2"
        assert engine.tier_state.sources.wpd_sources == ["docs_2/P5/P5-Test.md"]
    
    def test_validate_user_input_with_keywords(self):
        """Test user input validation with various keywords"""
        test_cases = [
            ("Perform work plan", True),
            ("execute plan", True),
            ("run plan", True),
            ("작업 계획 실행", True),
            ("continue from tier a", True),
            ("Create new document", False),
            ("Random text", False),
        ]
        
        for user_input, expected in test_cases:
            context = TaskContext(
                user_input=user_input,
                current_tier="B",
                workspace_root="."
            )
            engine = TaskExecutionEngine(context)
            
            assert engine.validate_user_input() == expected, f"Failed for input: {user_input}"
    
    def test_validate_user_input_with_tier_a_chaining(self):
        """Test validation when chained from Tier A"""
        tier_a_state = AgentState(
            tier="A",
            status="SUCCESS",
            payload={"created_documents": ["test.md"]}
        )
        
        context = TaskContext(
            user_input="any text",  # Should pass validation due to chaining
            current_tier="B",
            workspace_root=".",
            previous_state=tier_a_state
        )
        
        engine = TaskExecutionEngine(context)
        assert engine.validate_user_input() is True
    
    def test_parse_phases_new_format(self):
        """Test parsing phases from new Execution Plan format"""
        wpd_content = """# Work Plan Document

## 🔧 Execution Plan

### Phase 5.1: Setup Environment
- [ ] Install dependencies
- [ ] Configure settings
- [x] Create workspace

### Phase 5.2: Implement Features
- [ ] Add feature A
- [ ] Add feature B

## 🎯 Success Criteria
"""
        
        context = TaskContext(
            user_input="execute plan",
            current_tier="B",
            workspace_root="."
        )
        engine = TaskExecutionEngine(context)
        
        phases = engine.parse_phases(wpd_content)
        
        assert len(phases) == 2
        assert phases[0]["phase_number"] == "5.1"
        assert phases[0]["phase_title"] == "Setup Environment"
        assert len(phases[0]["checklist"]) == 3
        assert phases[0]["checklist"][2]["completed"] is True
        
        assert phases[1]["phase_number"] == "5.2"
        assert phases[1]["phase_title"] == "Implement Features"
        assert len(phases[1]["checklist"]) == 2
    
    def test_parse_phases_legacy_format(self):
        """Test parsing legacy milestone format"""
        wpd_content = """# Work Plan Document

## 🎯 Milestones
- [x] Setup environment
- [ ] Implement feature A
- [ ] Test implementation

## Other Section
"""
        
        context = TaskContext(
            user_input="execute plan",
            current_tier="B",
            workspace_root="."
        )
        engine = TaskExecutionEngine(context)
        
        milestones = engine.parse_phases(wpd_content)
        
        assert len(milestones) == 3
        assert milestones[0]["title"] == "Setup environment"
        assert milestones[0]["completed"] is True
        assert milestones[1]["completed"] is False
    
    def test_execute_phase(self):
        """Test individual phase execution"""
        phase = {
            "title": "Phase 1: Test Phase",
            "order": 1,
            "completed": False,
            "checklist": [
                {"text": "Task 1", "completed": False},
                {"text": "Task 2", "completed": False}
            ]
        }
        
        context = TaskContext(
            user_input="execute plan",
            current_tier="B",
            workspace_root="."
        )
        engine = TaskExecutionEngine(context)
        
        result = engine.execute_phase(phase)
        
        assert result["phase"] == "Phase 1: Test Phase"
        assert result["order"] == 1
        assert result["status"] == "COMPLETED"
        assert len(result["checklist_results"]) == 2
        assert "start_time" in result
        assert "end_time" in result
    
    def test_generate_execution_report(self):
        """Test execution report generation"""
        phases = [
            {"title": "Phase 1", "order": 1},
            {"title": "Phase 2", "order": 2}
        ]
        
        results = [
            {
                "phase": "Phase 1",
                "status": "COMPLETED",
                "start_time": "2024-01-01T00:00:00",
                "end_time": "2024-01-01T00:01:00",
                "output": "Success",
                "errors": [],
                "checklist_results": []
            },
            {
                "phase": "Phase 2",
                "status": "FAILED",
                "start_time": "2024-01-01T00:01:00",
                "end_time": "2024-01-01T00:02:00",
                "output": "",
                "errors": ["Error occurred"],
                "checklist_results": []
            }
        ]
        
        context = TaskContext(
            user_input="execute plan",
            current_tier="B",
            workspace_root="."
        )
        engine = TaskExecutionEngine(context)
        
        report = engine.generate_execution_report(phases, results)
        
        # Updated assertions for PRD format
        assert "# PRD-P" in report  # Now generates PRD format
        assert "**Document Type**: PRD" in report
        assert "**Total Phases** | 2" in report
        assert "**Completed** | 1" in report
        assert "**Failed** | 1" in report
        assert "✅ Phase 1" in report
        assert "❌ Phase 2" in report
    
    def test_execute_failure_no_plan(self, tmp_path):
        """Test execute() when no work plan is found"""
        context = TaskContext(
            user_input="execute plan",
            current_tier="B",
            workspace_root=str(tmp_path)
        )
        
        engine = TaskExecutionEngine(context)
        state = engine.execute()
        
        assert state.status == "FAILED"
        assert "No work plan found" in state.errors[0]
    
    def test_execute_failure_invalid_input(self):
        """Test execute() with invalid user input"""
        context = TaskContext(
            user_input="Create document",
            current_tier="B",
            workspace_root="."
        )
        
        engine = TaskExecutionEngine(context)
        state = engine.execute()
        
        assert state.status == "FAILED"
        assert "does not match Tier B" in state.errors[0]


class TestMainFunction:
    """Test main() entry point"""
    
    def test_main_with_minimal_input(self):
        """Test main() with minimal parameters"""
        state = main(
            user_input="execute plan",
            workspace_root="/tmp"
        )
        
        assert isinstance(state, AgentState)
        assert state.tier == "B"
        # Will fail due to no work plan, but structure is validated
        assert state.status == "FAILED"
    
    def test_main_with_previous_payload(self):
        """Test main() with previous_payload for chaining"""
        previous_payload = {
            "tier": "A",
            "status": "SUCCESS",
            "logic_summary": "WPD created",
            "payload": {
                "created_documents": ["docs_2/P5/P5-Test.md"]
            },
            "wpd_grade": "L2",
            "wpd_source_path": "docs_2/P5/P5-Test.md",
            "execution_time_ms": 100.0,
            "errors": [],
            "warnings": [],
            "timestamp": "2024-01-01T00:00:00",
            "decision_trace": []
        }
        
        state = main(
            user_input="any text",
            workspace_root="/tmp",
            previous_payload=previous_payload
        )
        
        assert isinstance(state, AgentState)
        assert state.tier == "B"
        # Chaining should work
        assert state.wpd_source_path == "docs_2/P5/P5-Test.md"
        assert state.wpd_grade == "L2"


class TestDataclassHierarchy:
    """Test proper usage of new dataclass hierarchy"""
    
    def test_tier_b_state_structure(self):
        """Test TierBState dataclass structure"""
        tier_b = TierBState()
        
        # Verify nested DocumentSources
        assert isinstance(tier_b.sources, DocumentSources)
        
        # Verify execution tracking in DocumentSources
        assert hasattr(tier_b.sources, 'total_phases')
        assert hasattr(tier_b.sources, 'completed_phases')
        assert hasattr(tier_b.sources, 'failed_phases')
        assert hasattr(tier_b.sources, 'phase_results')
        
        # Verify tier-specific fields
        assert hasattr(tier_b, 'current_phase')
        assert hasattr(tier_b, 'start_time')
        assert hasattr(tier_b, 'end_time')
        assert hasattr(tier_b, 'total_duration_ms')
    
    def test_tier_b_state_to_payload(self):
        """Test TierBState.to_payload() serialization"""
        tier_b = TierBState()
        tier_b.sources.total_phases = 5
        tier_b.sources.completed_phases = 3
        tier_b.sources.failed_phases = 1
        tier_b.current_phase = "Phase 5.2"
        tier_b.start_time = "2024-01-01T00:00:00"
        tier_b.end_time = "2024-01-01T00:05:00"
        
        payload = tier_b.to_payload()
        
        # Verify structure
        assert "sources" in payload
        assert payload["sources"]["total_phases"] == 5
        assert payload["sources"]["completed_phases"] == 3
        assert payload["current_phase"] == "Phase 5.2"
        assert payload["start_time"] == "2024-01-01T00:00:00"
        
        # Verify backward-compatible keys
        assert "execution_report_path" in payload
    
    def test_document_sources_structure(self):
        """Test DocumentSources dataclass structure"""
        sources = DocumentSources()
        
        # Original fields
        assert hasattr(sources, 'wpd_sources')
        assert hasattr(sources, 'prd_path')
        assert hasattr(sources, 'execution_report_path')
        
        # Execution tracking fields (moved from TierBState)
        assert hasattr(sources, 'execution_results')
        assert hasattr(sources, 'milestone_status')
        assert hasattr(sources, 'total_phases')
        assert hasattr(sources, 'completed_phases')
        assert hasattr(sources, 'failed_phases')
        assert hasattr(sources, 'phase_results')
    
    def test_agent_state_fields_separation(self):
        """Test that AgentState contains only common fields"""
        state = AgentState(tier="B", status="SUCCESS")
        
        # Common fields that should exist
        assert hasattr(state, 'wpd_grade')
        assert hasattr(state, 'wpd_source_path')
        assert hasattr(state, 'execution_log')
        assert hasattr(state, 'execution_time_ms')
        
        # Tier-specific fields should NOT exist in AgentState
        assert not hasattr(state, 'sources')
        assert not hasattr(state, 'start_time')  # Only in TierBState for backward compat
        assert not hasattr(state, 'end_time')


class TestBreakingChanges:
    """Test breaking changes and migration paths"""
    
    def test_no_start_end_time_in_agent_state(self):
        """Verify start_time/end_time removed from AgentState"""
        state = AgentState(tier="B", status="SUCCESS")
        
        # These fields should not exist in AgentState anymore
        assert not hasattr(state, 'start_time')
        assert not hasattr(state, 'end_time')
    
    def test_execution_tracking_in_document_sources(self):
        """Verify execution tracking moved to DocumentSources"""
        tier_b = TierBState()
        
        # Execution tracking should be in sources
        assert hasattr(tier_b.sources, 'total_phases')
        assert hasattr(tier_b.sources, 'completed_phases')
        assert hasattr(tier_b.sources, 'failed_phases')
        assert hasattr(tier_b.sources, 'execution_results')
        assert hasattr(tier_b.sources, 'milestone_status')
    
    def test_backward_compatibility_in_payload(self):
        """Test backward-compatible payload structure"""
        tier_b = TierBState()
        tier_b.sources.execution_report_path = "reports/ER_123.md"
        tier_b.sources.prd_path = "docs_2/prd/PRD-5.md"
        
        payload = tier_b.to_payload()
        
        # Backward-compatible top-level keys should exist
        assert "execution_report_path" in payload
        assert "prd_path" in payload
        assert payload["execution_report_path"] == "reports/ER_123.md"
        assert payload["prd_path"] == "docs_2/prd/PRD-5.md"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

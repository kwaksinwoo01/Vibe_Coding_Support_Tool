"""
Integration tests for D_Issue_Analysis_Flow.py

Tests:
- End-to-end workflow from user input to routing decision
- Integration of all analysis modules
- Error handling
- State creation and payload generation
"""

import pytest

from D_Issue_Analysis_Flow import IssueAnalysisEngine, main
from models.core import AgentState, TierDState


class TestIssueAnalysisEngine:
    """Integration tests for IssueAnalysisEngine"""

    @pytest.fixture
    def engine(self):
        """Create engine instance"""
        return IssueAnalysisEngine()

    def test_execute_bug_issue(self, engine):
        """Test execute with bug issue"""
        result = engine.execute("ValueError occurred in process_data function")
        
        assert isinstance(result, AgentState)
        assert result.tier == "D"
        assert result.status == "SUCCESS"
        assert result.next_node is not None
        assert len(result.execution_log) > 0

    def test_execute_design_flaw(self, engine):
        """Test execute with design flaw"""
        result = engine.execute("The system architecture needs to be redesigned")
        
        assert isinstance(result, AgentState)
        assert result.tier == "D"
        assert result.status == "SUCCESS"
        assert result.next_node in ["A", "C"]  # Design flaw should route to A or C

    def test_execute_documentation_issue(self, engine):
        """Test execute with documentation issue"""
        result = engine.execute("The README needs to be updated")
        
        assert isinstance(result, AgentState)
        assert result.tier == "D"
        assert result.status == "SUCCESS"
        assert result.next_node == "E"  # Documentation should route to E

    def test_execute_with_error_context(self, engine):
        """Test execute with additional error context"""
        error_context = {
            "error_message": "TypeError: unsupported operand type(s)",
            "file": "module.py",
            "line": 42
        }
        result = engine.execute("Type error in the code", error_context)
        
        assert isinstance(result, AgentState)
        assert result.status == "SUCCESS"
        # Error context should be in payload
        payload = result.payload
        assert "error_details" in payload

    def test_payload_contains_tier_d_state(self, engine):
        """Test that payload contains TierDState data"""
        result = engine.execute("Test issue")
        
        payload = result.payload
        assert "issue_description" in payload
        assert "issue_classification" in payload
        assert "root_cause_analysis" in payload
        assert "resolution_strategy" in payload
        assert "routing_info" in payload

    def test_tier_d_state_from_payload(self, engine):
        """Test that TierDState can be reconstructed from payload"""
        result = engine.execute("Test issue")
        
        payload = result.payload
        tier_d_state = TierDState.from_payload(payload)
        
        assert isinstance(tier_d_state, TierDState)
        assert tier_d_state.issue_description != ""

    def test_logic_summary_populated(self, engine):
        """Test that logic summary is populated"""
        result = engine.execute("Error in the system")
        
        assert result.logic_summary != ""
        assert "classified" in result.logic_summary.lower() or "issue" in result.logic_summary.lower()

    def test_wpd_grade_set(self, engine):
        """Test that WPD grade is set"""
        result = engine.execute("Test issue")
        
        assert result.wpd_grade in ["L0", "L1", "L2", "L3"]

    def test_execution_log_populated(self, engine):
        """Test that execution log is populated"""
        result = engine.execute("Test issue")
        
        assert len(result.execution_log) > 0
        # Should have logs for each step
        log_text = "\n".join(result.execution_log)
        assert "Step 1" in log_text
        assert "Step 2" in log_text
        assert "Step 3" in log_text
        assert "Step 4" in log_text

    def test_bug_routes_to_c(self, engine):
        """Test bug with implementation error routes to C"""
        result = engine.execute("TypeError in the implementation")
        
        assert result.next_node == "C"

    def test_environment_error_routes_to_b(self, engine):
        """Test environment error routes to B"""
        result = engine.execute("Environment configuration error during setup")
        
        assert result.next_node == "B"

    def test_data_error_routes_to_e(self, engine):
        """Test data error routes to E"""
        result = engine.execute("Invalid data format error")
        
        assert result.next_node == "E"

    def test_unknown_issue_routes_to_f(self, engine):
        """Test unknown issue routes to F"""
        result = engine.execute("Something is wrong but unclear what")
        
        assert result.next_node == "F"

    def test_error_handling(self, engine):
        """Test error handling for exceptions"""
        # Force an error by passing invalid type (this should be handled gracefully)
        # The actual implementation uses str() conversion, so it shouldn't fail
        # Instead, test with empty input
        result = engine.execute("")
        
        # Should still return AgentState, even if it routes to F for unknown
        assert isinstance(result, AgentState)

    def test_classification_confidence_in_payload(self, engine):
        """Test classification confidence is in payload"""
        result = engine.execute("Critical error in the system")
        
        payload = result.payload
        classification = payload.get("issue_classification", {})
        assert "confidence_score" in classification
        assert 0.0 <= classification["confidence_score"] <= 1.0

    def test_routing_confidence_in_payload(self, engine):
        """Test routing confidence is in payload"""
        result = engine.execute("Error in module")
        
        payload = result.payload
        routing = payload.get("routing_info", {})
        assert "routing_confidence" in routing
        assert 0.0 <= routing["routing_confidence"] <= 1.0

    def test_analysis_timestamp_set(self, engine):
        """Test analysis timestamp is set"""
        result = engine.execute("Test issue")
        
        payload = result.payload
        assert "analysis_timestamp" in payload
        assert payload["analysis_timestamp"] != ""


class TestMainFunction:
    """Test main entry point function"""

    def test_main_returns_agent_state(self):
        """Test main function returns AgentState"""
        result = main("Test issue")
        
        assert isinstance(result, AgentState)
        assert result.tier == "D"

    def test_main_with_workspace_root(self):
        """Test main function with workspace_root parameter"""
        result = main("Test issue", workspace_root=".")
        
        assert isinstance(result, AgentState)

    def test_main_with_error_context(self):
        """Test main function with error_context parameter"""
        error_context = {"error_message": "Test error"}
        result = main("Test issue", workspace_root=".", error_context=error_context)
        
        assert isinstance(result, AgentState)
        payload = result.payload
        assert "error_details" in payload


class TestExceptionHandling:
    """Test exception handling in IssueAnalysisEngine"""

    def test_execute_handles_exceptions_gracefully(self):
        """Test that execute handles exceptions and returns failure state"""
        from unittest.mock import Mock, patch
        
        engine = IssueAnalysisEngine()
        
        # Mock classifier to raise an exception
        with patch.object(engine.classifier, 'classify', side_effect=RuntimeError("Test exception")):
            result = engine.execute("Test issue")
            
            # Should return AgentState with FAILED status
            assert isinstance(result, AgentState)
            assert result.tier == "D"
            assert result.status == "FAILED"
            assert "Test exception" in result.errors[0] if result.errors else "RuntimeError" in result.logic_summary
            assert len(result.execution_log) > 0

    def test_execute_logs_exception_details(self):
        """Test that exceptions are properly logged"""
        from unittest.mock import Mock, patch
        
        engine = IssueAnalysisEngine()
        
        with patch.object(engine.root_cause_analyzer, 'analyze', side_effect=ValueError("Analysis failed")):
            result = engine.execute("Test issue")
            
            assert result.status == "FAILED"
            # Check that error is logged
            log_text = "\n".join(result.execution_log)
            assert "CRITICAL ERROR" in log_text or "FAILURE" in log_text

    def test_execute_exception_includes_execution_log(self):
        """Test that execution log is preserved on exception"""
        from unittest.mock import Mock, patch
        
        engine = IssueAnalysisEngine()
        
        # Mock to fail after some logging
        with patch.object(engine.strategy_engine, 'create_strategy', side_effect=Exception("Strategy error")):
            result = engine.execute("Test issue")
            
            assert result.status == "FAILED"
            # Log should have entries before the failure
            assert len(result.execution_log) > 0
            # Should have initial step logs
            log_text = "\n".join(result.execution_log)
            assert "Step 1" in log_text or "Step 2" in log_text


class TestCLIEntryPoint:
    """Test command-line interface entry point"""

    def test_cli_missing_arguments(self):
        """Test CLI with missing arguments"""
        import sys
        import subprocess
        
        result = subprocess.run(
            [sys.executable, "D_Issue_Analysis_Flow.py"],
            cwd="/home/runner/work/turbo-system/turbo-system/.github/agents/tool",
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 1
        assert "Usage:" in result.stdout or "Usage:" in result.stderr

    def test_cli_with_user_input(self):
        """Test CLI with user input argument"""
        import sys
        import subprocess
        
        result = subprocess.run(
            [sys.executable, "D_Issue_Analysis_Flow.py", "Test error issue"],
            cwd="/home/runner/work/turbo-system/turbo-system/.github/agents/tool",
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Should execute successfully (returncode 0)
        assert result.returncode == 0

    def test_cli_with_workspace_root(self):
        """Test CLI with both user_input and workspace_root"""
        import sys
        import subprocess
        
        result = subprocess.run(
            [sys.executable, "D_Issue_Analysis_Flow.py", "Test issue", "."],
            cwd="/home/runner/work/turbo-system/turbo-system/.github/agents/tool",
            capture_output=True,
            text=True,
            timeout=10
        )
        
        assert result.returncode == 0


class TestTierDStateValidation:
    """Test TierDState validation for required fields"""

    def test_tierdstate_rejects_old_payloads(self):
        """Test that TierDState.from_payload rejects old unstructured payloads"""
        old_payload = {
            "issue_description": "Error in system",
            "error_details": {"message": "ValueError"}
        }
        
        # Should raise KeyError for missing structured fields
        with pytest.raises(KeyError) as exc_info:
            TierDState.from_payload(old_payload)
        
        assert "Missing" in str(exc_info.value)
        assert "issue_classification" in str(exc_info.value)

    def test_tierdstate_rejects_none_fields(self):
        """Test that TierDState.from_payload rejects None structured fields"""
        payload = {
            "issue_description": "Test",
            "error_details": {},
            "issue_classification": None,
            "root_cause_analysis": None,
            "resolution_strategy": None,
            "routing_info": None
        }
        
        # Should raise ValueError for None fields
        with pytest.raises(ValueError) as exc_info:
            TierDState.from_payload(payload)
        
        assert "cannot be None" in str(exc_info.value)

    def test_tierdstate_construction_requires_structured_fields(self):
        """Test that TierDState construction validates required fields"""
        # Creating with None fields should fail in __post_init__
        with pytest.raises(ValueError) as exc_info:
            TierDState(
                issue_description="Test",
                error_details={},
                issue_classification=None,
                root_cause_analysis=None,
                resolution_strategy=None,
                routing_info=None
            )
        
        assert "requires all structured fields" in str(exc_info.value)

    def test_tierdstate_accepts_valid_structured_payload(self):
        """Test that TierDState accepts properly structured payload"""
        from models.core.reporting_models import (
            IssueClassification,
            RootCauseAnalysis,
            ResolutionStrategy,
            RoutingInfo
        )
        
        # Create valid structured objects
        classification = IssueClassification(issue_type="bug", severity="high")
        root_cause = RootCauseAnalysis(root_cause="Test cause")
        strategy = ResolutionStrategy(approach="fix_implementation")
        routing = RoutingInfo(target_tier="C")
        
        payload = {
            "issue_description": "Test issue",
            "error_details": {},
            "issue_classification": classification.to_dict(),
            "root_cause_analysis": root_cause.to_dict(),
            "resolution_strategy": strategy.to_dict(),
            "routing_info": routing.to_dict(),
            "analysis_metadata": {},
            "analysis_timestamp": "2025-01-13T00:00:00"
        }
        
        # Should succeed
        tier_d_state = TierDState.from_payload(payload)
        assert tier_d_state.issue_description == "Test issue"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

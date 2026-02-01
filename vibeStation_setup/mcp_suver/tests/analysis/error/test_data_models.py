"""
Unit tests for analysis/error/data_models.py

Tests:
- IssueClassification serialization/deserialization
- RootCauseAnalysis serialization/deserialization
- ResolutionStrategy serialization/deserialization
- RoutingInfo serialization/deserialization
- Edge cases and validation
"""

import pytest
from datetime import datetime

from models.core.reporting_models import (
    IssueClassification,
    RootCauseAnalysis,
    ResolutionStrategy,
    RoutingInfo,
)


class TestIssueClassification:
    """Test IssueClassification data model"""

    def test_default_initialization(self):
        """Test default initialization"""
        classification = IssueClassification()
        assert classification.issue_type == ""
        assert classification.severity == "medium"
        assert classification.confidence_score == 0.0
        assert classification.keywords == []
        assert classification.category == ""

    def test_full_initialization(self):
        """Test initialization with all fields"""
        classification = IssueClassification(
            issue_type="bug",
            severity="high",
            confidence_score=0.95,
            keywords=["error", "exception", "ValueError"],
            category="implementation_error"
        )
        assert classification.issue_type == "bug"
        assert classification.severity == "high"
        assert classification.confidence_score == 0.95
        assert classification.keywords == ["error", "exception", "ValueError"]
        assert classification.category == "implementation_error"

    def test_to_dict(self):
        """Test serialization to dict"""
        classification = IssueClassification(
            issue_type="bug",
            severity="high",
            confidence_score=0.95,
            keywords=["error"],
            category="implementation_error"
        )
        data = classification.to_dict()
        assert isinstance(data, dict)
        assert data["issue_type"] == "bug"
        assert data["severity"] == "high"
        assert data["confidence_score"] == 0.95
        assert data["keywords"] == ["error"]
        assert data["category"] == "implementation_error"

    def test_from_dict(self):
        """Test deserialization from dict"""
        data = {
            "issue_type": "design_flaw",
            "severity": "medium",
            "confidence_score": 0.85,
            "keywords": ["architecture", "design"],
            "category": "architecture"
        }
        classification = IssueClassification.from_dict(data)
        assert classification.issue_type == "design_flaw"
        assert classification.severity == "medium"
        assert classification.confidence_score == 0.85
        assert classification.keywords == ["architecture", "design"]
        assert classification.category == "architecture"

    def test_round_trip_serialization(self):
        """Test serialization and deserialization round trip"""
        original = IssueClassification(
            issue_type="documentation",
            severity="low",
            confidence_score=0.9,
            keywords=["doc", "readme"],
            category=""
        )
        data = original.to_dict()
        restored = IssueClassification.from_dict(data)
        
        assert restored.issue_type == original.issue_type
        assert restored.severity == original.severity
        assert restored.confidence_score == original.confidence_score
        assert restored.keywords == original.keywords
        assert restored.category == original.category

    def test_from_dict_with_extra_fields(self):
        """Test from_dict ignores extra fields"""
        data = {
            "issue_type": "bug",
            "severity": "high",
            "extra_field": "should be ignored",
            "another_extra": 123
        }
        classification = IssueClassification.from_dict(data)
        assert classification.issue_type == "bug"
        assert classification.severity == "high"
        assert not hasattr(classification, "extra_field")


class TestRootCauseAnalysis:
    """Test RootCauseAnalysis data model"""

    def test_default_initialization(self):
        """Test default initialization"""
        analysis = RootCauseAnalysis()
        assert analysis.root_cause == ""
        assert analysis.affected_components == []
        assert analysis.error_context == {}
        assert analysis.evidence == []
        assert analysis.confidence_level == "medium"
        assert isinstance(analysis.analysis_timestamp, str)

    def test_full_initialization(self):
        """Test initialization with all fields"""
        timestamp = datetime.now().isoformat()
        analysis = RootCauseAnalysis(
            root_cause="Missing type check",
            affected_components=["module_x.py", "util.py"],
            error_context={"line": 42, "function": "process_data"},
            evidence=["TypeError at line 42", "No validation"],
            confidence_level="high",
            analysis_timestamp=timestamp
        )
        assert analysis.root_cause == "Missing type check"
        assert analysis.affected_components == ["module_x.py", "util.py"]
        assert analysis.error_context == {"line": 42, "function": "process_data"}
        assert analysis.evidence == ["TypeError at line 42", "No validation"]
        assert analysis.confidence_level == "high"
        assert analysis.analysis_timestamp == timestamp

    def test_to_dict(self):
        """Test serialization to dict"""
        analysis = RootCauseAnalysis(
            root_cause="Missing validation",
            affected_components=["main.py"],
            error_context={"line": 10},
            evidence=["Error occurred"],
            confidence_level="high"
        )
        data = analysis.to_dict()
        assert isinstance(data, dict)
        assert data["root_cause"] == "Missing validation"
        assert data["affected_components"] == ["main.py"]
        assert data["error_context"] == {"line": 10}
        assert data["evidence"] == ["Error occurred"]
        assert data["confidence_level"] == "high"

    def test_from_dict(self):
        """Test deserialization from dict"""
        data = {
            "root_cause": "Algorithm inefficiency",
            "affected_components": ["algo.py"],
            "error_context": {"complexity": "O(n^2)"},
            "evidence": ["Slow performance"],
            "confidence_level": "medium",
            "analysis_timestamp": "2025-01-13T10:00:00"
        }
        analysis = RootCauseAnalysis.from_dict(data)
        assert analysis.root_cause == "Algorithm inefficiency"
        assert analysis.affected_components == ["algo.py"]
        assert analysis.error_context == {"complexity": "O(n^2)"}
        assert analysis.evidence == ["Slow performance"]
        assert analysis.confidence_level == "medium"
        assert analysis.analysis_timestamp == "2025-01-13T10:00:00"

    def test_round_trip_serialization(self):
        """Test serialization and deserialization round trip"""
        original = RootCauseAnalysis(
            root_cause="Test issue",
            affected_components=["test.py"],
            error_context={"test": "data"},
            evidence=["Evidence 1"],
            confidence_level="low"
        )
        data = original.to_dict()
        restored = RootCauseAnalysis.from_dict(data)
        
        assert restored.root_cause == original.root_cause
        assert restored.affected_components == original.affected_components
        assert restored.error_context == original.error_context
        assert restored.evidence == original.evidence
        assert restored.confidence_level == original.confidence_level


class TestResolutionStrategy:
    """Test ResolutionStrategy data model"""

    def test_default_initialization(self):
        """Test default initialization"""
        strategy = ResolutionStrategy()
        assert strategy.approach == ""
        assert strategy.estimated_effort == "medium"
        assert strategy.target_tier == ""
        assert strategy.wpd_grade == "L0"
        assert strategy.priority == 5
        assert strategy.dependencies == []
        assert strategy.rollback_plan == ""
        assert strategy.estimated_duration_hours == 0.0

    def test_full_initialization(self):
        """Test initialization with all fields"""
        strategy = ResolutionStrategy(
            approach="fix_implementation",
            estimated_effort="high",
            target_tier="C",
            wpd_grade="L2",
            priority=8,
            dependencies=["test_review"],
            rollback_plan="Revert to previous commit",
            estimated_duration_hours=4.5
        )
        assert strategy.approach == "fix_implementation"
        assert strategy.estimated_effort == "high"
        assert strategy.target_tier == "C"
        assert strategy.wpd_grade == "L2"
        assert strategy.priority == 8
        assert strategy.dependencies == ["test_review"]
        assert strategy.rollback_plan == "Revert to previous commit"
        assert strategy.estimated_duration_hours == 4.5

    def test_to_dict(self):
        """Test serialization to dict"""
        strategy = ResolutionStrategy(
            approach="refactor_design",
            estimated_effort="high",
            target_tier="A",
            wpd_grade="L3",
            priority=9
        )
        data = strategy.to_dict()
        assert isinstance(data, dict)
        assert data["approach"] == "refactor_design"
        assert data["estimated_effort"] == "high"
        assert data["target_tier"] == "A"
        assert data["wpd_grade"] == "L3"
        assert data["priority"] == 9

    def test_from_dict(self):
        """Test deserialization from dict"""
        data = {
            "approach": "update_documentation",
            "estimated_effort": "low",
            "target_tier": "E",
            "wpd_grade": "L0",
            "priority": 3,
            "dependencies": ["doc_review"],
            "rollback_plan": "Revert document changes",
            "estimated_duration_hours": 1.0
        }
        strategy = ResolutionStrategy.from_dict(data)
        assert strategy.approach == "update_documentation"
        assert strategy.estimated_effort == "low"
        assert strategy.target_tier == "E"
        assert strategy.wpd_grade == "L0"
        assert strategy.priority == 3
        assert strategy.dependencies == ["doc_review"]
        assert strategy.rollback_plan == "Revert document changes"
        assert strategy.estimated_duration_hours == 1.0

    def test_round_trip_serialization(self):
        """Test serialization and deserialization round trip"""
        original = ResolutionStrategy(
            approach="investigate",
            estimated_effort="medium",
            target_tier="F",
            wpd_grade="L1",
            priority=5,
            dependencies=[],
            rollback_plan="No rollback needed",
            estimated_duration_hours=2.0
        )
        data = original.to_dict()
        restored = ResolutionStrategy.from_dict(data)
        
        assert restored.approach == original.approach
        assert restored.estimated_effort == original.estimated_effort
        assert restored.target_tier == original.target_tier
        assert restored.wpd_grade == original.wpd_grade
        assert restored.priority == original.priority
        assert restored.dependencies == original.dependencies
        assert restored.rollback_plan == original.rollback_plan
        assert restored.estimated_duration_hours == original.estimated_duration_hours


class TestRoutingInfo:
    """Test RoutingInfo data model"""

    def test_default_initialization(self):
        """Test default initialization"""
        routing = RoutingInfo()
        assert routing.target_tier == ""
        assert routing.routing_reason == ""
        assert routing.routing_confidence == 0.0
        assert routing.requires_clarification is False
        assert routing.clarification_questions == []
        assert routing.metadata == {}
        assert isinstance(routing.routing_timestamp, str)

    def test_full_initialization(self):
        """Test initialization with all fields"""
        timestamp = datetime.now().isoformat()
        routing = RoutingInfo(
            target_tier="C",
            routing_reason="Implementation error requires fix",
            routing_confidence=0.95,
            requires_clarification=False,
            clarification_questions=[],
            metadata={"analysis_steps": 3},
            routing_timestamp=timestamp
        )
        assert routing.target_tier == "C"
        assert routing.routing_reason == "Implementation error requires fix"
        assert routing.routing_confidence == 0.95
        assert routing.requires_clarification is False
        assert routing.clarification_questions == []
        assert routing.metadata == {"analysis_steps": 3}
        assert routing.routing_timestamp == timestamp

    def test_with_clarification(self):
        """Test routing with clarification required"""
        routing = RoutingInfo(
            target_tier="F",
            routing_reason="Unknown issue type",
            routing_confidence=0.6,
            requires_clarification=True,
            clarification_questions=[
                "Can you provide more details?",
                "What is the expected behavior?"
            ]
        )
        assert routing.requires_clarification is True
        assert len(routing.clarification_questions) == 2

    def test_to_dict(self):
        """Test serialization to dict"""
        routing = RoutingInfo(
            target_tier="A",
            routing_reason="Design flaw requires new plan",
            routing_confidence=0.85,
            metadata={"priority": "high"}
        )
        data = routing.to_dict()
        assert isinstance(data, dict)
        assert data["target_tier"] == "A"
        assert data["routing_reason"] == "Design flaw requires new plan"
        assert data["routing_confidence"] == 0.85
        assert data["metadata"] == {"priority": "high"}

    def test_from_dict(self):
        """Test deserialization from dict"""
        data = {
            "target_tier": "E",
            "routing_reason": "Documentation update needed",
            "routing_confidence": 0.9,
            "requires_clarification": False,
            "clarification_questions": [],
            "metadata": {"doc_type": "readme"},
            "routing_timestamp": "2025-01-13T10:00:00"
        }
        routing = RoutingInfo.from_dict(data)
        assert routing.target_tier == "E"
        assert routing.routing_reason == "Documentation update needed"
        assert routing.routing_confidence == 0.9
        assert routing.requires_clarification is False
        assert routing.metadata == {"doc_type": "readme"}
        assert routing.routing_timestamp == "2025-01-13T10:00:00"

    def test_round_trip_serialization(self):
        """Test serialization and deserialization round trip"""
        original = RoutingInfo(
            target_tier="B",
            routing_reason="Environment retry needed",
            routing_confidence=0.75,
            requires_clarification=True,
            clarification_questions=["What environment?"],
            metadata={"retry_count": 1}
        )
        data = original.to_dict()
        restored = RoutingInfo.from_dict(data)
        
        assert restored.target_tier == original.target_tier
        assert restored.routing_reason == original.routing_reason
        assert restored.routing_confidence == original.routing_confidence
        assert restored.requires_clarification == original.requires_clarification
        assert restored.clarification_questions == original.clarification_questions
        assert restored.metadata == original.metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
